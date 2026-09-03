# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# File: tests/unit/test_ingestion_adapters_architecture.py
# Author: Gabriel Moraes
# Date: 2026-08-29

import time
import pytest
from unittest.mock import MagicMock, patch

from src.domain.app_state import AppState
from src.domain.entities import DataSource, SourceStatus, SourceType
from src.adapters.base_adapter import BaseIngestionAdapter
from src.adapters.file_replay_adapter import FileReplayAdapter
from src.adapters.http_poller_adapter import HttpPollerAdapter
from src.adapters.http_push_adapter import HttpPushAdapter
from src.adapters.ingestion_hub import IngestionHub
from src.adapters.mqtt_adapter import MqttIngestionAdapter
from src.adapters.websocket_adapter import WebSocketIngestionAdapter
from src.interfaces.ingestion_adapters import IIngestionAdapter, IIngestionHub
from src.pipeline.ingestion_pipeline import IngestionPipeline
from src.workers.ingestion_worker import IngestionWorker


def test_adapters_protocol_conformance():
    """Verifies that all concrete adapters conform to IIngestionAdapter runtime protocol."""
    push_adapter = HttpPushAdapter(port=18080)
    poller_adapter = HttpPollerAdapter()
    mqtt_adapter = MqttIngestionAdapter()
    ws_adapter = WebSocketIngestionAdapter()
    replay_adapter = FileReplayAdapter()

    assert isinstance(push_adapter, IIngestionAdapter)
    assert isinstance(poller_adapter, IIngestionAdapter)
    assert isinstance(mqtt_adapter, IIngestionAdapter)
    assert isinstance(ws_adapter, IIngestionAdapter)
    assert isinstance(replay_adapter, IIngestionAdapter)

    pipeline = MagicMock(spec=IngestionPipeline)
    hub = IngestionHub(pipeline)
    assert isinstance(hub, IIngestionHub)


def test_ingestion_hub_lifecycle_and_routing():
    """Tests hub adapter registration, start/stop lifecycle and packet routing."""
    app_state = AppState()
    pipeline = IngestionPipeline(app_state)
    hub = IngestionHub(pipeline)

    # Register DataSource in state so Zero Trust allows it
    src = DataSource(id="cam_01", name="Camera Paulista", status=SourceStatus.QUARANTINE, is_local=True)
    app_state.add_data_source(src)

    received_packets = []

    def on_received(source_id, payload, meta):
        received_packets.append((source_id, payload, meta))

    hub.register_listener(on_received)

    # Create dummy custom adapter inheriting from BaseIngestionAdapter
    class CustomMockAdapter(BaseIngestionAdapter):
        def _do_start(self):
            pass

        def _do_stop(self):
            pass

        def simulate_inbound(self, sid, data):
            self.emit_packet(sid, data, metadata={"custom_field": 42})

    custom_adapter = CustomMockAdapter(adapter_id="custom_mock", transport_name="CustomProtocol")
    hub.register_adapter(custom_adapter)
    hub.start_all()

    assert hub.is_running
    assert custom_adapter.is_running

    # Emit data from adapter -> should route through pipeline into listener
    custom_adapter.simulate_inbound("cam_01", {"speed": 55.4, "flow": 120})

    assert len(received_packets) == 1
    sid, payload, meta = received_packets[0]
    assert sid == "cam_01"
    assert payload["speed"] == 55.4
    assert meta["transport"] == "CustomProtocol"
    assert meta["custom_field"] == 42

    # Check quarantine buffer in pipeline
    q_data = pipeline.get_quarantine_data("cam_01")
    assert len(q_data) == 1

    hub.stop_all()
    assert not hub.is_running
    assert not custom_adapter.is_running


def test_mqtt_adapter_topic_extraction_and_routing():
    """Tests that MqttIngestionAdapter extracts source_id and routes payload to Zero Trust pipeline."""
    app_state = AppState()
    pipeline = IngestionPipeline(app_state)
    hub = IngestionHub(pipeline)

    src = DataSource(id="cam_north", name="Camera North", status=SourceStatus.QUARANTINE, is_local=True)
    app_state.add_data_source(src)

    mqtt_adapter = MqttIngestionAdapter(adapter_id="mqtt_test")
    hub.register_adapter(mqtt_adapter)
    hub.start_all()

    # Simulate MQTT packet published to topic 'traffic/cameras/cam_north/telemetry'
    mqtt_adapter.simulate_message("traffic/cameras/cam_north/telemetry", {"flow": 450, "occupancy": 0.12})

    # Verify pipeline received packet without caring it was MQTT
    q_data = pipeline.get_quarantine_data("cam_north")
    assert len(q_data) == 1
    assert q_data[0]["flow"] == 450

    hub.stop_all()


def test_websocket_and_file_replay_adapters():
    """Tests WebSocket stream adapter and FileReplay step execution."""
    app_state = AppState()
    pipeline = IngestionPipeline(app_state)
    hub = IngestionHub(pipeline)

    src_ws = DataSource(id="edge_ai_ws", name="Edge AI WebSocket", status=SourceStatus.QUARANTINE, is_local=True)
    src_replay = DataSource(id="history_src", name="Historical CSV Replay", status=SourceStatus.QUARANTINE, is_local=True)
    app_state.add_data_source(src_ws)
    app_state.add_data_source(src_replay)

    ws_adapter = WebSocketIngestionAdapter(adapter_id="ws_test")
    replay_adapter = FileReplayAdapter(adapter_id="replay_test", source_id="history_src")
    replay_adapter.load_dataset([
        {"timestamp": 1000, "speed": 60.0},
        {"timestamp": 1001, "speed": 62.5},
        {"timestamp": 1002, "speed": 59.0},
    ])

    hub.register_adapter(ws_adapter)
    hub.register_adapter(replay_adapter)
    hub.start_all()

    # 1. Stream WebSocket frame
    ws_adapter.handle_stream_frame("edge_ai_ws", {"detections": 15, "avg_speed": 48.0})
    assert len(pipeline.get_quarantine_data("edge_ai_ws")) == 1

    # 2. Step FileReplay
    record1 = replay_adapter.step()
    record2 = replay_adapter.step()
    assert record1["speed"] == 60.0
    assert record2["speed"] == 62.5
    assert len(pipeline.get_quarantine_data("history_src")) == 2

    hub.stop_all()


def test_ingestion_worker_integration_with_hub():
    """Verifies that IngestionWorker delegates to IngestionHub and retains backward compatibility."""
    app_state = AppState()
    worker = IngestionWorker(app_state)

    src_local = DataSource(id="local_radar", name="Local Radar", status=SourceStatus.QUARANTINE, is_local=True)
    src_global = DataSource(id="waze_global", name="Waze Global", status=SourceStatus.QUARANTINE, is_local=False, connection_string="http://localhost:8088/api/waze")
    app_state.add_data_source(src_local)
    app_state.add_data_source(src_global)

    received_signals = []
    worker.data_ready.connect(lambda sid, data: received_signals.append((sid, data)))

    # Direct push via gateway backward compatible reference
    worker.gateway.handle_inbound_request(
        content_type="application/json",
        decoded_body='{"speed": 72.0, "vehicle_count": 8}',
        client_ip="127.0.0.1",
        request_path="/local_radar",
        content_length=42,
    )

    assert len(received_signals) == 1
    sid, data = received_signals[0]
    assert sid == "local_radar"
    assert data["speed"] == 72.0
