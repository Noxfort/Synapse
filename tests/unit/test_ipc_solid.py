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
# File: tests/unit/test_ipc_solid.py
# Author: Gabriel Moraes
# Date: 2026-08-30

"""
Unit Tests for IPC Subsystem (SOLID Architecture Verification).
"""

import io
import json
import pytest
from unittest.mock import MagicMock

from PyQt6.QtCore import QObject, pyqtSignal

from src.ipc.ipc_protocol import IpcMessage, IpcEvent, IpcResponse
from src.ipc.stdio_transport import StdioTransport
from src.ipc.command_router import IpcCommandRouter
from src.ipc.event_bridge import IpcEventBridge
from src.ipc.serializers import TopologySerializer
from src.handlers.system_handler import SystemCommandHandler
from src.handlers.map_handler import MapCommandHandler
from src.handlers.source_handler import SourceCommandHandler
from src.handlers.database_handler import DatabaseCommandHandler
from src.handlers.dialog_handler import SystemDialogHandler
from src.handlers.handler_registry import register_default_command_handlers
from src.ipc.stdio_daemon import StdioDaemon
from src.domain.app_state import AppState
from src.domain.entities import MapNode, MapEdge, DataSource, SourceType, SourceStatus


class MockSystemSignals(QObject):
    log_message = pyqtSignal(str)
    status_message = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    optimization_finished = pyqtSignal()
    bootstrap_finished = pyqtSignal()
    online_system_started = pyqtSignal()
    online_system_stopped = pyqtSignal()
    engine_data_processed = pyqtSignal(dict)
    engine_global_results = pyqtSignal(dict)
    linguist_update = pyqtSignal(str, str, float)
    audit_update = pyqtSignal(bool, float, float, list)
    drift_update = pyqtSignal(str, dict)
    xai_result_received = pyqtSignal(dict)
    cmd_explain_buffer = pyqtSignal()
    cmd_explain_local = pyqtSignal(str)
    cmd_explain_global = pyqtSignal()

    def start_optimization(self):
        return True

    def stop_optimization(self):
        pass

    def start_offline_bootstrap(self):
        pass

    def stop_offline_bootstrap(self):
        pass

    def start_online_operation(self):
        pass

    def stop_online_operation(self):
        pass


def test_stdio_transport_stream_io():
    """Verifies that StdioTransport writes thread-safe lines and reads from streams."""
    fake_stdin = io.StringIO('{"action": "ping", "id": "1"}\n')
    fake_stdout = io.StringIO()

    transport = StdioTransport(stdin_stream=fake_stdin, stdout_stream=fake_stdout)
    assert transport.write_line('{"test": true}') is True
    assert '{"test": true}\n' in fake_stdout.getvalue()


def test_ipc_command_router_extensibility():
    """Verifies Open/Closed extensibility of IpcCommandRouter."""
    router = IpcCommandRouter()

    # Register custom action
    router.register("custom_action", lambda msg: {"echo": msg.payload.get("val")})
    assert router.has_action("custom_action")

    responses = []
    emitter = lambda resp: responses.append(resp)

    # Dispatch custom action
    msg = IpcMessage(action="custom_action", id="req-1", payload={"val": 42})
    router.dispatch(msg, emitter)

    assert len(responses) == 1
    assert responses[0].id == "req-1"
    assert responses[0].success is True
    assert responses[0].result == {"echo": 42}

    # Dispatch unknown action
    unknown_msg = IpcMessage(action="non_existent", id="req-2")
    router.dispatch(unknown_msg, emitter)

    assert len(responses) == 2
    assert responses[1].id == "req-2"
    assert responses[1].success is False
    assert "Unknown action" in (responses[1].error or "")


def test_topology_serializer():
    """Verifies TopologySerializer formats domain graph into UI structure."""
    mock_state = MagicMock()
    mock_state.get_all_nodes.return_value = [
        MapNode(id="node_1", x=10.0, y=20.0, node_type="priority", real_name="Junction 1", tl_logic_id="tl_1")
    ]
    mock_state.get_all_edges.return_value = [
        MapEdge(id="edge_1", from_node="node_1", to_node="node_2", shape=[[10.0, 20.0], [30.0, 40.0]])
    ]

    payload = TopologySerializer.serialize_topology(mock_state)
    assert payload["loaded"] is True
    assert len(payload["nodes"]) == 1
    assert payload["nodes"][0]["id"] == "node_1"
    assert payload["nodes"][0]["is_tls"] is True
    assert len(payload["edges"]) == 1
    assert payload["edges"][0]["from"] == "node_1"


def test_ipc_event_bridge(qapp):
    """Verifies that IpcEventBridge translates Qt signals into emitted IPC events."""
    mock_controller = MagicMock()
    mock_system = MockSystemSignals()
    mock_controller.system = mock_system
    mock_controller.project = MagicMock()
    mock_state = MagicMock()

    emitted_events = []
    event_emitter = lambda ev, data: emitted_events.append((ev, data))

    bridge = IpcEventBridge(event_emitter=event_emitter)
    bridge.bind_signals(mock_controller, mock_state)

    # Fire signal
    mock_system.log_message.emit("Test status info")
    assert len(emitted_events) == 1
    assert emitted_events[0][0] == "log_message"
    assert emitted_events[0][1]["message"] == "Test status info"

    mock_system.online_system_started.emit()
    assert len(emitted_events) == 2
    assert emitted_events[1][0] == "phase_transition"
    assert emitted_events[1][1]["phase"] == "RUNNING_ONLINE"


def test_stdio_daemon_facade_and_dip(qapp):
    """Verifies StdioDaemon pure facade architecture and dependency injection."""
    mock_controller = MagicMock()
    mock_system = MockSystemSignals()
    mock_controller.system = mock_system
    mock_controller.start_optimization_flow.return_value = True

    mock_transport = MagicMock(spec=StdioTransport)
    mock_router = IpcCommandRouter()
    mock_event_bridge = MagicMock(spec=IpcEventBridge)

    daemon = StdioDaemon(
        controller=mock_controller,
        transport=mock_transport,
        router=mock_router,
        event_bridge=mock_event_bridge,
    )

    assert daemon.controller is mock_controller
    assert daemon.transport is mock_transport
    assert daemon.router is mock_router
    assert daemon.event_bridge is mock_event_bridge

    # Test event emission through facade
    daemon.emit_event("ready", {"status": "ok"})
    mock_transport.write_line.assert_called()

    # Test command dispatching
    msg = IpcMessage(action="ping", id="msg-ping")
    daemon.dispatch_command(msg)
    # write_line should be called with response JSON
    assert mock_transport.write_line.call_count >= 2


def test_command_handlers_source_management():
    """Verifies SourceCommandHandler CRUD operations and state delegation."""
    app_state = AppState()
    source_handler = SourceCommandHandler(app_state)

    # 1. Add Source
    add_msg = IpcMessage(
        action="add_source",
        id="add-1",
        payload={"id": "src_test", "name": "Sensor Alpha", "is_local": True, "connection": "mqtt://127.0.0.1"}
    )
    res_add = source_handler.handle_add_source(add_msg)
    assert res_add["id"] == "src_test"
    assert res_add["name"] == "Sensor Alpha"

    # 2. Get Sources
    get_msg = IpcMessage(action="get_sources", id="get-1")
    res_get = source_handler.handle_get_sources(get_msg)
    assert len(res_get["sources"]) == 1
    assert res_get["sources"][0]["id"] == "src_test"

    # 3. Toggle Origin
    toggle_msg = IpcMessage(action="toggle_origin", id="tog-1", payload={"source_id": "src_test"})
    source_handler.handle_toggle_origin(toggle_msg)
    src_obj = app_state.get_data_source("src_test")
    assert src_obj is not None
    assert src_obj.is_local is False

    # 4. Remove Source
    rem_msg = IpcMessage(action="remove_source", id="rem-1", payload={"source_id": "src_test"})
    source_handler.handle_remove_source(rem_msg)
    assert len(source_handler.handle_get_sources(get_msg)["sources"]) == 0


def test_map_command_handler_dependency_injection():
    """Verifies MapCommandHandler works with injected mock MapService (DIP)."""
    mock_state = MagicMock()
    mock_map_svc = MagicMock()
    mock_map_svc.load_network.return_value = True
    mock_map_svc.nodes = [MapNode(id="n1", x=0.0, y=0.0, node_type="junction")]
    mock_map_svc.edges = [MapEdge(id="e1", from_node="n1", to_node="n1", shape=[[0.0, 0.0], [1.0, 1.0]])]

    handler = MapCommandHandler(app_state=mock_state, map_service=mock_map_svc)
    assert handler.map_service is mock_map_svc

    responses = []
    responder = lambda ok, res=None, err=None: responses.append((ok, res, err))

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".net.xml") as tmp:
        msg = IpcMessage(action="load_map", id="map-1", payload={"path": tmp.name})
        handler.handle_load_map(msg, responder)

    assert len(responses) == 1
    assert responses[0][0] is True
    mock_map_svc.load_network.assert_called_once()


def test_database_command_handler_dependency_injection():
    """Verifies DatabaseCommandHandler works with injected factories and services (DIP)."""
    mock_controller = MagicMock()
    mock_emitter = MagicMock()
    mock_inspection_svc = MagicMock()
    mock_inspection_svc.inspect_parquet.return_value = {"num_rows": 100, "columns": ["speed"]}

    mock_worker = MagicMock()
    mock_worker_factory = MagicMock(return_value=mock_worker)

    handler = DatabaseCommandHandler(
        controller=mock_controller,
        event_emitter=mock_emitter,
        data_inspection_service=mock_inspection_svc,
        postgres_worker_factory=mock_worker_factory,
    )

    responses = []
    responder = lambda ok, res=None, err=None: responses.append((ok, res, err))

    # Test Parquet Inspection
    msg = IpcMessage(action="inspect_parquet", id="db-1", payload={"path": "/fake/path.parquet"})
    handler.handle_inspect_parquet(msg, responder)
    assert len(responses) == 1
    assert responses[0][0] is True
    assert responses[0][1]["num_rows"] == 100

    # Test DB Connection
    msg_test = IpcMessage(action="test_db_connection", id="db-2", payload={"config": {"host": "localhost"}})
    handler.handle_test_db_connection(msg_test, responder)
    mock_worker_factory.assert_called_once()
    mock_worker.do_check_connection.assert_called_once_with({"host": "localhost"})
