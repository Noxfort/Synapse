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
# File: src/transmission/transmitter_process.py
# Author: Gabriel Moraes
# Date: 2026-09-04

"""
Dedicated HFT Transmission Process (Level 2 Safety Gateway).

Architecture & Responsibilities:
1. Runs in a dedicated, isolated OS process (Fault-Domain Isolation).
   - Zero PyTorch, Zero GPU, Zero Tensor allocations.
   - Immune to neural crashes, CUDA OOMs, and GIL contention.
2. Maintains permanent gRPC stream with CARINA.
3. Receives realtime frames from Synapse Core via 1-to-1 `multiprocessing.Pipe`.
4. Seamless Fallback (Bumpless Transfer):
   - If pipe.poll(timeout=0.25) expires (Core silent > 250ms) OR emergency_flag is set:
     Queries AFB ReplayEngine (hierarchical DB lookup) and dispatches contingency frame.
   - CARINA experiences zero packet drop and zero socket resets.
"""

import os
import sys
import time
import asyncio
import logging
import multiprocessing
from multiprocessing.connection import Connection
from typing import Optional, Dict, Any, Tuple

from src.afb.replay_engine import ReplayEngine

logger = logging.getLogger("Synapse.TransmitterProcess")


class TransmitterWorker:
    """
    Worker running inside the dedicated transmission process.
    """

    def __init__(
        self,
        pipe_receiver: Connection,
        emergency_flag: Any,
        stop_event: Any,
        endpoint: str = "localhost:50051",
        data_path: Optional[str] = None,
        db_engine: Optional[Any] = None,
        connector: Optional[Any] = None,
        poll_timeout: float = 0.25,
    ):
        self.pipe_receiver = pipe_receiver
        self.emergency_flag = emergency_flag
        self.stop_event = stop_event
        self.endpoint = endpoint
        self.poll_timeout = poll_timeout

        # Initialize AFB ReplayEngine (DB-backed hierarchical fallback)
        self.afb_replay = ReplayEngine(data_path=data_path, db_engine=db_engine)
        
        # Injected connector (e.g. for unit tests) or lazily created GrpcConnector
        self._connector = connector
        self._is_running = False

    async def run(self):
        """Main async execution loop."""
        self._is_running = True
        logger.info(f"[Transmitter] Process started (PID: {os.getpid()}). Connecting to CARINA at {self.endpoint}...")

        # Initialize GrpcConnector if not injected
        if self._connector is None:
            try:
                from src.infrastructure.grpc_connector import GrpcConnector
                self._connector = GrpcConnector(endpoint=self.endpoint)
                await self._connector.start_channel()
                await self._connector.start_streaming()
                logger.info("[Transmitter] gRPC connection established with CARINA.")
            except Exception as e:
                logger.warning(f"[Transmitter] Could not connect gRPC channel: {e}")

        consecutive_fallbacks = 0

        while self._is_running and not self.stop_event.is_set():
            loop_start = time.perf_counter()

            # 1. Check for Emergency Flag (forced by FÊNIX during Hot-Reset)
            is_emergency = False
            if hasattr(self.emergency_flag, "is_set"):
                is_emergency = self.emergency_flag.is_set()
            elif isinstance(self.emergency_flag, bool):
                is_emergency = self.emergency_flag

            packet_to_send: Optional[Dict[str, Any]] = None

            if is_emergency:
                # Emergency Mode active: bypass Core and synthesize from AFB
                packet_to_send = self._generate_afb_packet(source_tag="AFB_FENIX_HOT_RESET")
                consecutive_fallbacks += 1
            else:
                # Normal Mode: wait for Core frame via Pipe with strict 250ms deadline
                try:
                    has_data = self.pipe_receiver.poll(timeout=self.poll_timeout)
                except Exception as e:
                    logger.debug(f"[Transmitter] Pipe poll error: {e}")
                    has_data = False

                if has_data:
                    try:
                        received = self.pipe_receiver.recv()
                        if isinstance(received, dict) and received.get("command") == "STOP":
                            logger.info("[Transmitter] STOP command received via Pipe.")
                            break
                        packet_to_send = received
                        if consecutive_fallbacks > 0:
                            logger.info(f"[Transmitter] Core recovered after {consecutive_fallbacks} fallback cycles. Resuming normal transmission.")
                            consecutive_fallbacks = 0
                    except Exception as e:
                        logger.error(f"[Transmitter] Error receiving from Pipe: {e}")
                        packet_to_send = None

                if packet_to_send is None:
                    # Timeout exceeded (> 250ms)! Core is silent or lagging
                    consecutive_fallbacks += 1
                    packet_to_send = self._generate_afb_packet(source_tag="AFB_TIMEOUT_FALLBACK")
                    if consecutive_fallbacks == 1:
                        logger.warning("[Transmitter] ⚠️ Core silent (>250ms deadline). Commencing AFB Historical Transmission.")

            # 2. Dispatch to CARINA stream
            if packet_to_send and self._connector:
                try:
                    await self._connector.enqueue_traffic_frame(packet_to_send)
                except Exception as e:
                    logger.error(f"[Transmitter] Error enqueuing frame to CARINA: {e}")

            # Yield control to event loop to allow gRPC generator to flush
            elapsed = time.perf_counter() - loop_start
            sleep_time = max(0.001, self.poll_timeout - elapsed) if is_emergency else 0.001
            await asyncio.sleep(sleep_time)

        # Cleanup on shutdown
        if self._connector and hasattr(self._connector, "stop"):
            try:
                await self._connector.stop()
            except Exception:
                pass

        logger.info("[Transmitter] Transmission process terminated gracefully.")

    def _generate_afb_packet(self, source_tag: str) -> Dict[str, Any]:
        """Synthesizes a full traffic frame using the AFB DB-backed ReplayEngine."""
        afb_frame = self.afb_replay.get_replay_frame()
        meta = afb_frame.get("_metadata", {})
        readings = afb_frame.get("readings", {})

        return {
            "timestamp": meta.get("timestamp", time.time()),
            "source": f"{source_tag}:{meta.get('resolution_tier', 'unknown')}",
            "edges": readings,
            "is_fallback": True
        }


def run_transmitter_worker(
    pipe_receiver: Connection,
    emergency_flag: Any,
    stop_event: Any,
    endpoint: str = "localhost:50051",
    data_path: Optional[str] = None,
    db_engine: Optional[Any] = None,
    connector: Optional[Any] = None,
    poll_timeout: float = 0.25,
):
    """
    Target entry point executed inside the isolated child process.
    Sets up asyncio event loop and executes the TransmitterWorker.
    """
    worker = TransmitterWorker(
        pipe_receiver=pipe_receiver,
        emergency_flag=emergency_flag,
        stop_event=stop_event,
        endpoint=endpoint,
        data_path=data_path,
        db_engine=db_engine,
        connector=connector,
        poll_timeout=poll_timeout,
    )
    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        logger.info("[Transmitter] Process interrupted by user.")
    except Exception as e:
        logger.critical(f"[Transmitter] Unhandled exception in worker loop: {e}", exc_info=True)


def start_transmitter_process(
    endpoint: str = "localhost:50051",
    data_path: Optional[str] = None,
    db_engine: Optional[Any] = None,
    connector: Optional[Any] = None,
    poll_timeout: float = 0.25,
) -> Tuple[multiprocessing.Process, Connection, Any, Any]:
    """
    Convenience factory to spawn the dedicated transmission process.
    
    Returns:
        tuple (process, pipe_sender, emergency_event, stop_event)
    """
    # In Python multiprocessing.Pipe(duplex=False), conn1 is read-only and conn2 is write-only.
    pipe_receiver, pipe_sender = multiprocessing.Pipe(duplex=False)
    emergency_event = multiprocessing.Event()
    stop_event = multiprocessing.Event()

    proc = multiprocessing.Process(
        target=run_transmitter_worker,
        args=(pipe_receiver, emergency_event, stop_event),
        kwargs={
            "endpoint": endpoint,
            "data_path": data_path,
            "db_engine": db_engine,
            "connector": connector,
            "poll_timeout": poll_timeout,
        },
        name="SynapseTransmitterProcess",
        daemon=True,
    )
    proc.start()
    return proc, pipe_sender, emergency_event, stop_event
