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
# File: src/infrastructure/hft_grpc_client.py
# Author: Gabriel Moraes
# Date: 2026-08-19

import grpc
import os
import sys
import time
from datetime import datetime
from typing import Any, AsyncGenerator, List, Optional, Tuple

# Ensure proto modules are reachable
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

from proto import synapse_hft_pb2
from proto import synapse_hft_pb2_grpc
from src.utils.debug_logger import carina_logger
from src.utils.logging_setup import get_logger

logger = get_logger("HFT.Transport")


class HFTGrpcClient:
    """
    Low-level gRPC Transport Client.
    Responsible exclusively for socket/channel lifecycle, proto RPC invocations, and network I/O.
    """

    MAX_MESSAGE_LENGTH = 50 * 1024 * 1024  # 50 MB

    def __init__(self, endpoint: str = "localhost:50051", channel_options: Optional[List[Tuple[str, Any]]] = None):
        self.endpoint = endpoint
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[synapse_hft_pb2_grpc.HFTLinkStub] = None
        self._is_running: bool = False
        self._is_connected: bool = False
        self._custom_channel_options = channel_options

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def _build_channel_options(self) -> List[Tuple[str, Any]]:
        if self._custom_channel_options is not None:
            return self._custom_channel_options
        return [
            ('grpc.keepalive_time_ms', 30000),
            ('grpc.keepalive_timeout_ms', 10000),
            ('grpc.keepalive_permit_without_calls', 1),
            ('grpc.http2.max_pings_without_data', 0),
            ('grpc.max_send_message_length', self.MAX_MESSAGE_LENGTH),
            ('grpc.max_receive_message_length', self.MAX_MESSAGE_LENGTH),
        ]

    async def start_channel(self) -> None:
        """Initializes raw gRPC Channel with configured options."""
        if self.channel:
            return

        logger.info(f"🔗 Opening Channel to {self.endpoint}...")
        opts = self._build_channel_options()
        self.channel = grpc.aio.insecure_channel(self.endpoint, options=opts)
        self.stub = synapse_hft_pb2_grpc.HFTLinkStub(self.channel)
        self._is_running = True

    async def close(self) -> None:
        """Closes gRPC channel gracefully."""
        self._is_running = False
        self._is_connected = False
        if self.channel:
            await self.channel.close()
            self.channel = None
            self.stub = None
            logger.info("🔌 Channel Closed.")

    async def ping(self, timeout: float = 2.0) -> bool:
        """Sends a lightweight Ping RPC to verify server availability."""
        if not self.channel:
            await self.start_channel()
        try:
            await self.stub.Ping(synapse_hft_pb2.Empty(), timeout=timeout)
            self._is_connected = True
            return True
        except grpc.aio.AioRpcError:
            self._is_connected = False
            return False

    async def load_scenario(self, proto_scenario: synapse_hft_pb2.ScenarioDefinition, timeout: float = 60.0) -> Any:
        """Invokes LoadScenario RPC with latency telemetry."""
        if not self.channel:
            await self.start_channel()

        _rpc_start = time.time()
        _ts_start = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        try:
            response = await self.stub.LoadScenario(proto_scenario, timeout=timeout)
            _ts_end = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            nodes_count = len(proto_scenario.graph.nodes) if proto_scenario.HasField("graph") else 0
            edges_count = len(proto_scenario.graph.edges) if proto_scenario.HasField("graph") else 0
            carina_logger.info(
                f"GRPC_SCENARIO | nodes={nodes_count} | edges={edges_count} "
                f"| start={_ts_start} | end={_ts_end} "
                f"| latency={(time.time()-_rpc_start)*1000:.1f}ms "
                f"| accepted={getattr(response, 'accepted', False)}"
            )
            return response
        except Exception as e:
            _ts_end = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            carina_logger.info(
                f"GRPC_SCENARIO | ERROR | start={_ts_start} | end={_ts_end} "
                f"| latency={(time.time()-_rpc_start)*1000:.1f}ms | error={e}"
            )
            raise

    async def system_control(self, request: synapse_hft_pb2.ControlCommand, timeout: float = 5.0) -> Any:
        """Invokes SystemControl RPC with latency telemetry."""
        if not self.channel:
            await self.start_channel()

        _rpc_start = time.time()
        _ts_start = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        cmd_name = synapse_hft_pb2.ControlCommand.Action.Name(request.action) if hasattr(request, "action") else str(request)
        try:
            response = await self.stub.SystemControl(request, timeout=timeout)
            _ts_end = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            carina_logger.info(
                f"GRPC_COMMAND | cmd={cmd_name} "
                f"| start={_ts_start} | end={_ts_end} "
                f"| latency={(time.time()-_rpc_start)*1000:.1f}ms "
                f"| success={getattr(response, 'success', False)}"
            )
            return response
        except Exception as e:
            _ts_end = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            carina_logger.info(
                f"GRPC_COMMAND | cmd={cmd_name} | ERROR "
                f"| start={_ts_start} | end={_ts_end} "
                f"| latency={(time.time()-_rpc_start)*1000:.1f}ms | error={e}"
            )
            raise

    async def stream_traffic(self, frame_generator: AsyncGenerator[synapse_hft_pb2.TrafficFrame, None]) -> Any:
        """Streams traffic frames via StreamTraffic RPC."""
        if not self.channel:
            await self.start_channel()
        return await self.stub.StreamTraffic(frame_generator)
