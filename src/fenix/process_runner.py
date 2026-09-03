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
# File: src/fenix/process_runner.py
# Author: Gabriel Moraes
# Date: 2026-09-01

"""
Low-level OS Process Runner implementation for F.E.N.I.X. (SOLID Architecture).
Strictly adheres to SRP by managing only subprocess lifecycles, signals, and streams.
"""

import sys
import subprocess
import threading
from typing import Optional, List, Dict

from src.utils.logging_setup import get_logger
from src.fenix.protocols import IProcessRunner

logger = get_logger("FenixProcessRunner")


class SubprocessRunner(IProcessRunner):
    """
    Subprocess execution manager wrapping Python's `subprocess.Popen`.
    Provides thread-safe spawning, polling, and graceful termination with SIGKILL fallback.
    """

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    @property
    def pid(self) -> Optional[int]:
        """Returns the PID of the active subprocess, or None if not running."""
        with self._lock:
            if self._process is not None:
                return self._process.pid
            return None

    @property
    def is_alive(self) -> bool:
        """Returns True if the subprocess exists and has not terminated."""
        with self._lock:
            if self._process is None:
                return False
            return self._process.poll() is None

    def spawn(self, command: List[str], env: Optional[Dict[str, str]] = None) -> bool:
        """
        Spawns an OS subprocess with the specified command and environment.

        Args:
            command: Command line argument list.
            env: Optional environment variables dictionary.

        Returns:
            bool: True if process was successfully spawned, False on error.
        """
        with self._lock:
            try:
                logger.info(f"[PROCESS RUNNER] Executing: {' '.join(command)}")
                self._process = subprocess.Popen(
                    command,
                    env=env,
                    stdin=sys.stdin,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                )
                return True
            except Exception as e:
                logger.error(f"[PROCESS RUNNER] Failed to spawn process: {e}")
                self._process = None
                return False

    def terminate(self, timeout_seconds: float = 5.0) -> None:
        """
        Gracefully terminates the subprocess (SIGTERM), falling back to SIGKILL on timeout.

        Args:
            timeout_seconds: Maximum time to wait for graceful termination before killing.
        """
        with self._lock:
            if self._process is None:
                return

            pid = self._process.pid
            logger.info(f"[PROCESS RUNNER] Terminating child process [PID: {pid}]...")
            try:
                self._process.terminate()
                try:
                    self._process.wait(timeout=timeout_seconds)
                except subprocess.TimeoutExpired:
                    logger.warning(
                        f"[PROCESS RUNNER] Child process [PID: {pid}] did not terminate within {timeout_seconds}s. "
                        "Forcing SIGKILL..."
                    )
                    self._process.kill()
                    self._process.wait(timeout=2.0)
            except Exception as e:
                logger.error(f"[PROCESS RUNNER] Error stopping child process [PID: {pid}]: {e}")
            finally:
                self._process = None

    def poll(self) -> Optional[int]:
        """
        Polls the subprocess status.

        Returns:
            Optional[int]: Exit code if process has terminated, or None if still running.
        """
        with self._lock:
            if self._process is None:
                return None
            return self._process.poll()
