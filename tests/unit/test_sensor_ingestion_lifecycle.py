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
# File: tests/unit/test_sensor_ingestion_lifecycle.py
# Author: Gabriel Moraes
# Date: 2026-08-19

import io
import json
import time
from unittest.mock import MagicMock, patch

import pytest
from src.domain.app_state import AppState
from src.domain.entities import DataSource, SourceStatus, SourceType
from src.domain.source_repository import SourceRepository
from src.infrastructure.json_source_storage import JsonSourceStorage
from src.infrastructure.parsers import IPayloadParser, JsonPayloadParser, PolyglotPayloadParser
from src.infrastructure.sensor_gateway import (
    IngestionHandler,
    SensorGateway,
    SensorHTTPServer,
    global_parser_registry,
)
from src.infrastructure.sensor_id_extractor import SensorIdExtractor
from src.interfaces.sensor_gateway import IPolyglotPayloadParser, ISensorGateway, ISensorIdExtractor
from src.pipeline.ingestion_pipeline import IngestionPipeline


def test_source_repository_add_local_and_global(tmp_path):
    """Verifies that SourceRepository registers local and global data sources correctly."""
    storage_file = str(tmp_path / "sources.json")
    storage = JsonSourceStorage(storage_file)
    repo = SourceRepository(storage)

    # 1. Add Local Source
    local_src = DataSource(
        id="src_cam_01",
        name="Camera Av Paulista",
        source_type=SourceType.API,
        connection_string="http://localhost:8080",
        is_local=True,
        status=SourceStatus.QUARANTINE,
    )
    repo.add(local_src)
    assert repo.get("src_cam_01") is not None
    assert repo.get("src_cam_01").name == "Camera Av Paulista"
    assert repo.get("src_cam_01").is_local is True

    # 2. Add Global Source
    global_src = DataSource(
        id="src_waze_01",
        name="Waze API Central",
        source_type=SourceType.API,
        connection_string="https://api.traffic.mock/v1",
        is_local=False,
        status=SourceStatus.QUARANTINE,
    )
    repo.add(global_src)
    assert repo.get("src_waze_01") is not None
    assert repo.get("src_waze_01").is_local is False
    assert len(repo.get_all()) == 2


def test_ingestion_pipeline_zero_trust_and_quarantine():
    """Verifies Zero Trust blocking and sample collection in quarantine."""
    app_state = AppState()

    # 1. Register sensor in QUARANTINE
    loop_sensor = DataSource(
        id="sensor_loop_01",
        name="Laço Indutivo Marginal",
        source_type=SourceType.API,
        connection_string="http://192.168.1.100",
        is_local=True,
        status=SourceStatus.QUARANTINE,
    )
    app_state.add_data_source(loop_sensor)

    pipeline = IngestionPipeline(app_state)

    # 2. Packet from registered sensor in QUARANTINE -> accepted is True and collects sample
    for i in range(5):
        accepted = pipeline.process_packet("sensor_loop_01", {"value": 40.0, "timestamp": 1000 + i})
        assert accepted is True

    # 3. Packet from unknown sensor -> MUST BE BLOCKED (Zero Trust)
    assert pipeline.process_packet("unknown_intruder_sensor", {"value": 99.0}) is False

    # 4. Verify that samples were stored in quarantine
    samples = pipeline.get_quarantine_data("sensor_loop_01")
    assert len(samples) == 5
    assert samples[0]["value"] == 40.0


def test_sensor_gateway_payload_parsers():
    """Verifies polyglot parsers for JSON, XML, and CSV telemetry."""
    # JSON
    json_data = global_parser_registry.parse("application/json", '{"source_id": "rad_01", "speed": 62.5}')
    assert json_data["source_id"] == "rad_01"
    assert json_data["speed"] == 62.5

    # CSV Key=Value
    csv_data = global_parser_registry.parse("text/plain", "source_id=rad_02,speed=45.0,count=12")
    assert csv_data["source_id"] == "rad_02"
    assert csv_data["speed"] == "45.0"

    # XML
    xml_raw = "<traffic><source_id>cam_03</source_id><flow>1500</flow></traffic>"
    xml_data = global_parser_registry.parse("application/xml", xml_raw)
    assert xml_data["source_id"] == "cam_03"
    assert xml_data["flow"] == "1500"


def test_sensor_id_extractor_url_path_and_normalization():
    """Verifies that SensorIdExtractor prioritizes URL path, normalizes zero-padding, and handles raw CSV/JSON/XML."""
    # 1. URL Path takes priority over payload and IP
    extracted_1 = SensorIdExtractor.extract(
        payload={"camera_id": "other_cam"}, client_ip="192.168.1.50", request_path="/src_1"
    )
    assert extracted_1 == "src_1"

    # 2. Tolerant normalization (src_01 -> src_1, SRC_02 -> src_2, cam_03 -> src_3)
    assert SensorIdExtractor.extract(payload={}, client_ip="127.0.0.1", request_path="/src_01") == "src_1"
    assert SensorIdExtractor.extract(payload={}, client_ip="127.0.0.1", request_path="/SRC_02") == "src_2"
    assert SensorIdExtractor.extract(payload={}, client_ip="127.0.0.1", request_path="/cam_03") == "src_3"
    assert SensorIdExtractor.extract(payload={}, client_ip="127.0.0.1", request_path="/api/sensors/src_5") == "src_5"

    # 3. Raw CSV payload without internal ID -> resolved via URL path
    raw_csv_dict = {"field_0": "65.5", "field_1": "12"}
    assert SensorIdExtractor.extract(payload=raw_csv_dict, client_ip="192.168.200.10", request_path="/src_4") == "src_4"

    # 4. Fallback to payload when path is root or generic
    assert SensorIdExtractor.extract(payload={"source_id": "src_10"}, client_ip="127.0.0.1", request_path="/") == "src_10"
    assert SensorIdExtractor.extract(payload={"camera_id": "src_08"}, client_ip="127.0.0.1", request_path="/events") == "src_8"

    # 5. Fallback to IP when no path and no payload ID
    assert SensorIdExtractor.extract(payload={"speed": 50}, client_ip="192.168.200.50", request_path="/") == "device_192_168_200_50"


def test_sensor_gateway_solid_facade_and_listeners():
    """Verifies SensorGateway as pure orchestrator/facade with dependency injection and listener registration."""
    # 1. Custom mock parser
    custom_parser = MagicMock(spec=IPayloadParser)
    custom_parser.can_parse.return_value = True
    custom_parser.parse.return_value = {"custom_metric": 42}

    parser_registry = PolyglotPayloadParser([custom_parser])

    # 2. Custom mock extractor
    custom_extractor = MagicMock(spec=ISensorIdExtractor)
    custom_extractor.extract.return_value = "custom_sensor_99"

    # 3. Instantiate Gateway with injected dependencies (DIP)
    gateway = SensorGateway(
        host="127.0.0.1",
        port=9999,
        parser_registry=parser_registry,
        id_extractor=custom_extractor,
    )

    # 4. Verify Protocol Conformance
    assert isinstance(gateway, ISensorGateway)
    assert isinstance(parser_registry, IPolyglotPayloadParser)
    assert isinstance(custom_extractor, ISensorIdExtractor)

    # 5. Register pure Python listener
    received_packets = []
    def on_packet(source_id: str, payload: dict):
        received_packets.append((source_id, payload))

    gateway.register_listener(on_packet)

    # 6. Track Qt signal emission
    signal_received = []
    gateway.data_received.connect(lambda src_id, pl: signal_received.append((src_id, pl)))

    # 7. Orchestrate packet processing
    result = gateway.handle_inbound_request(
        content_type="application/custom",
        decoded_body="custom_data",
        client_ip="10.0.0.1",
        request_path="/api/custom",
        content_length=11,
    )

    assert result == {"custom_metric": 42}
    assert len(received_packets) == 1
    assert received_packets[0] == ("custom_sensor_99", {"custom_metric": 42})
    assert len(signal_received) == 1
    assert signal_received[0] == ("custom_sensor_99", {"custom_metric": 42})

    # 8. Unregister listener
    gateway.unregister_listener(on_packet)
    gateway.handle_inbound_request(
        content_type="application/custom",
        decoded_body="custom_data_2",
        client_ip="10.0.0.1",
        request_path="/api/custom",
        content_length=13,
    )
    # Callback was unregistered, count remains 1
    assert len(received_packets) == 1
    # Qt signal continues emitting, count is 2
    assert len(signal_received) == 2


def test_source_repository_monotonic_id_generation(tmp_path):
    """Verifies that SourceRepository produces strictly monotonic src_N IDs even after deletion."""
    storage_file = str(tmp_path / "sources_monotonic.json")
    storage = JsonSourceStorage(storage_file)
    repo = SourceRepository(storage)

    assert repo.get_next_source_id() == "src_1"

    # Add src_1
    repo.add(DataSource(id="src_1", name="Sensor 1", is_local=True))
    assert repo.get_next_source_id() == "src_2"

    # Add src_2 and src_3
    repo.add(DataSource(id="src_2", name="Sensor 2", is_local=True))
    repo.add(DataSource(id="src_3", name="Sensor 3", is_local=True))
    assert repo.get_next_source_id() == "src_4"

    # Delete src_2 -> next ID MUST still be src_4 (no recycling to avoid ghost packets)
    repo.remove("src_2")
    assert repo.get("src_2") is None
    assert repo.get_next_source_id() == "src_4"


def test_runtime_phase_one_plus_one_gating():
    """Verifies that HFT gRPC connection is gated strictly on 1+1 sensor validation."""
    from src.phases.runtime_phase import RuntimePhase

    app_state = AppState()
    fenix_mock = MagicMock()

    # 1. Register Local and Global sensors in Quarantine
    local_src = DataSource(
        id="loc_01",
        name="Local Sensor 01",
        source_type=SourceType.API,
        connection_string="http://127.0.0.1:8080",
        is_local=True,
        status=SourceStatus.QUARANTINE,
    )
    global_src = DataSource(
        id="glob_01",
        name="Global API 01",
        source_type=SourceType.API,
        connection_string="https://api.waze.test/v1",
        is_local=False,
        status=SourceStatus.QUARANTINE,
    )
    app_state.add_data_source(local_src)
    app_state.add_data_source(global_src)

    phase = RuntimePhase(app_state, fenix_mock)

    with patch.object(phase.launcher, "start_engines") as mock_start_engines, \
         patch.object(phase.connector, "start_connection") as mock_start_conn:

        # Start Phase 2
        started = phase.start()
        assert started is True
        mock_start_engines.assert_called_once()
        # gRPC connection MUST NOT start because sensors are still in Quarantine!
        mock_start_conn.assert_not_called()

        # Promote only Local -> still not satisfied (needs 1 local + 1 global)
        local_src.status = SourceStatus.ACTIVE
        app_state.data_source_added.emit(local_src)
        mock_start_conn.assert_not_called()

        # Promote Global -> 1+1 rule satisfied!
        global_src.status = SourceStatus.ACTIVE
        app_state.data_source_added.emit(global_src)
        # gRPC connection MUST now start!
        mock_start_conn.assert_called_once()
