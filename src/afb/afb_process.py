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
# File: src/afb/afb_process.py
# Author: Gabriel Moraes
# Date: 2026-08-18

"""
AFB Process Manager — Autonomous Fallback Bridge (Isolated Safety Process).

Runs in a separate OS process, fully decoupled from PyTorch/GPU.
Activated by Auditor / Safety Alarms to sustain continuous output transmission
via historical replay until neural networks normalize or system restarts.
"""

import time
import multiprocessing as mp
from typing import Dict, Any, Optional
import logging

from src.afb.replay_engine import ReplayEngine

logger = logging.getLogger("Synapse.AFBProcess")


def _afb_worker_loop(cmd_queue: mp.Queue, status_queue: mp.Queue, data_path: Optional[str] = None):
    """
    Isolated background process main loop for AFB.
    Zero PyTorch, zero GPU, minimal memory footprint.
    """
    replay_engine = ReplayEngine(data_path=data_path)
    is_active = False
    transmission_count = 0

    while True:
        try:
            # Non-blocking check for control commands
            while not cmd_queue.empty():
                cmd = cmd_queue.get_nowait()
                if cmd == "ACTIVATE":
                    is_active = True
                elif cmd == "DEACTIVATE":
                    is_active = False
                elif cmd == "STATUS":
                    status_queue.put({
                        "is_active": is_active,
                        "transmission_count": transmission_count,
                        "is_loaded": replay_engine.is_loaded,
                        "sensor_count": len(replay_engine.sensor_ids)
                    })
                elif cmd == "SHUTDOWN":
                    return

            if is_active:
                # Generate and broadcast replay frame
                frame = replay_engine.get_replay_frame()
                transmission_count += 1
                # Output frame hook / transmission simulation
                time.sleep(0.1)  # 10Hz transmission rate
            else:
                time.sleep(0.05)  # Idle polling interval

        except Exception as e:
            time.sleep(0.1)


class AFBProcessManager:
    """
    Manages the lifecycle of the isolated Autonomous Fallback Bridge (AFB) process.
    """

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path
        self._cmd_queue: Optional[mp.Queue] = None
        self._status_queue: Optional[mp.Queue] = None
        self._process: Optional[mp.Process] = None
        self._is_active: bool = False

    def start(self):
        """Spawns the isolated AFB process."""
        if self._process is not None and self._process.is_alive():
            return

        self._cmd_queue = mp.Queue()
        self._status_queue = mp.Queue()
        self._process = mp.Process(
            target=_afb_worker_loop,
            args=(self._cmd_queue, self._status_queue, self.data_path),
            daemon=True,
            name="Synapse-AFB-Worker"
        )
        self._process.start()
        logger.info(f"[AFBProcessManager] 🛡️ Autonomous Fallback Bridge process spawned (PID: {self._process.pid}).")

    def activate_fallback(self):
        """Signals the isolated AFB process to start active replay transmission."""
        self._is_active = True
        if self._cmd_queue is not None and self._process is not None and self._process.is_alive():
            self._cmd_queue.put("ACTIVATE")
            logger.warning("[AFBProcessManager] 🚨 AFB Fallback ACTIVATED. Replaying historical transmission.")

    def deactivate_fallback(self):
        """Signals the isolated AFB process to return to standby."""
        self._is_active = False
        if self._cmd_queue is not None and self._process is not None and self._process.is_alive():
            self._cmd_queue.put("DEACTIVATE")
            logger.info("[AFBProcessManager] 🟢 AFB Fallback DEACTIVATED. Standing down.")

    @property
    def is_fallback_active(self) -> bool:
        return self._is_active

    def get_status(self) -> Dict[str, Any]:
        """Queries status from the isolated AFB process."""
        if self._cmd_queue is not None and self._status_queue is not None and self._process is not None and self._process.is_alive():
            self._cmd_queue.put("STATUS")
            try:
                # Wait up to 100ms for status response
                if self._status_queue.get(timeout=0.1):
                    pass
            except Exception:
                pass
        return {
            "is_alive": self._process.is_alive() if self._process else False,
            "is_fallback_active": self._is_active
        }

    def stop(self):
        """Gracefully terminates the isolated AFB process."""
        if self._cmd_queue is not None and self._process is not None and self._process.is_alive():
            self._cmd_queue.put("SHUTDOWN")
            self._process.join(timeout=1.0)
            if self._process.is_alive():
                self._process.terminate()
        logger.info("[AFBProcessManager] AFB process terminated.")
