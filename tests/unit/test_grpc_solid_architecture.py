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
# File: tests/unit/test_grpc_solid_architecture.py
# Author: Gabriel Moraes
# Date: 2026-08-19

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.interfaces.transport import (
    IHFTTransport,
    IHFTStreamer,
    IHFTRecoveryManager,
    IHFTConnector,
)
from src.infrastructure.hft_grpc_client import HFTGrpcClient
from src.infrastructure.hft_streamer import HFTStreamer
from src.infrastructure.hft_recovery import HFTRecoveryManager
from src.infrastructure.grpc_connector import GrpcConnector


def test_solid_protocol_conformance():
    """Verifies that all components satisfy their respective Protocol contracts."""
    grpc_client = HFTGrpcClient(endpoint="localhost:50051")
    streamer = HFTStreamer()
    recovery = HFTRecoveryManager()
    connector = GrpcConnector()

    assert isinstance(grpc_client, IHFTTransport)
    assert isinstance(streamer, IHFTStreamer)
    assert isinstance(recovery, IHFTRecoveryManager)
    assert isinstance(connector, IHFTConnector)


@pytest.mark.asyncio
async def test_facade_dependency_injection_and_delegation():
    """Verifies DIP: GrpcConnector receives mock subcomponents and delegates correctly."""
    mock_transport = AsyncMock()
    mock_transport.is_running = True
    mock_transport.is_connected = True
    mock_transport.ping.return_value = True
    
    mock_load_resp = MagicMock()
    mock_load_resp.accepted = True
    mock_transport.load_scenario.return_value = mock_load_resp
    
    mock_ctrl_resp = MagicMock()
    mock_ctrl_resp.success = True
    mock_ctrl_resp.new_state = "START"
    mock_transport.system_control.return_value = mock_ctrl_resp

    mock_streamer = MagicMock()
    mock_streamer.start = MagicMock()
    mock_streamer.stop = MagicMock()
    mock_streamer.enqueue_frame = AsyncMock()

    mock_recovery = MagicMock()
    mock_recovery.set_recovery_payload = MagicMock()

    mock_serializer = MagicMock()
    mock_serializer.pack_scenario.return_value = MagicMock()
    mock_serializer.pack_traffic_frame.return_value = MagicMock()

    # Instantiate Facade with Injected Mocks
    connector = GrpcConnector(
        endpoint="localhost:50051",
        transport=mock_transport,
        streamer=mock_streamer,
        recovery=mock_recovery,
        serializer=mock_serializer,
    )

    # 1. Ping delegation
    result = await connector.ping()
    assert result is True
    mock_transport.ping.assert_awaited_once()

    # 2. Scenario upload delegation
    map_data = {"nodes": [], "edges": []}
    scenario_result = await connector.send_scenario(map_data)
    assert scenario_result is True
    mock_recovery.set_recovery_payload.assert_called_once_with(map_data)
    mock_serializer.pack_scenario.assert_called_once_with(map_data)
    mock_transport.load_scenario.assert_awaited_once()

    # 3. System control delegation
    state_result = await connector.set_system_state("START")
    assert state_result is True
    mock_transport.system_control.assert_awaited_once()

    # 4. Enqueue traffic frame delegation
    frame_data = {"traffic": [{"edge_id": "e1", "speed": 10.0}]}
    await connector.enqueue_traffic_frame(frame_data)
    mock_serializer.pack_traffic_frame.assert_called_once_with(frame_data)
    mock_streamer.enqueue_frame.assert_awaited_once()

    # 5. Close delegation
    await connector.close()
    mock_streamer.stop.assert_called_once()
    mock_transport.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_recovery_manager_workflow():
    """Verifies that HFTRecoveryManager successfully orchestrates the recovery flow."""
    recovery = HFTRecoveryManager(poll_interval=0.01)
    mock_map = {"map_id": "test_123"}
    recovery.set_recovery_payload(mock_map)

    mock_transport = AsyncMock()
    mock_transport.is_running = True
    mock_transport.ping.return_value = True
    
    mock_resp = MagicMock()
    mock_resp.accepted = True
    mock_transport.load_scenario.return_value = mock_resp

    mock_serializer = MagicMock()
    mock_serializer.pack_scenario.return_value = MagicMock()

    set_system_state_cb = AsyncMock(return_value=True)

    success = await recovery.perform_recovery(
        transport=mock_transport,
        serializer=mock_serializer,
        set_system_state_cb=set_system_state_cb,
    )

    assert success is True
    mock_transport.ping.assert_awaited_once()
    mock_serializer.pack_scenario.assert_called_once_with(mock_map)
    mock_transport.load_scenario.assert_awaited_once()
    set_system_state_cb.assert_awaited_once_with("START")
