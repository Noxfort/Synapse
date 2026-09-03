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
# File: src/fenix/recovery_policy.py
# Author: Gabriel Moraes
# Date: 2026-09-01

"""
Crash Recovery and Resilience Policies for F.E.N.I.X. (SOLID Architecture).
Strictly adheres to SRP by managing only crash tracking, window pruning, and restart limits.
"""

import time
import threading
from typing import List, Callable, Optional

from src.utils.logging_setup import get_logger
from src.fenix.protocols import IRecoveryPolicy

logger = get_logger("FenixRecoveryPolicy")


class WindowedCrashRecoveryPolicy(IRecoveryPolicy):
    """
    Tracks process crash timestamps within a sliding time window.
    Decides whether a process can be resurrected based on max crash threshold.
    """

    def __init__(
        self,
        max_consecutive_crashes: int = 5,
        crash_window_seconds: float = 60.0,
        restart_backoff_seconds: float = 1.0,
        time_provider: Optional[Callable[[], float]] = None,
    ):
        self.max_consecutive_crashes = max_consecutive_crashes
        self.crash_window_seconds = crash_window_seconds
        self.restart_backoff_seconds = restart_backoff_seconds
        self._time_provider = time_provider or time.time
        self._crash_timestamps: List[float] = []
        self._lock = threading.Lock()

    @property
    def crash_count(self) -> int:
        """Returns the number of crashes that occurred within the sliding window."""
        with self._lock:
            self._prune_expired_crashes()
            return len(self._crash_timestamps)

    def _prune_expired_crashes(self) -> None:
        """Removes crash timestamps older than the sliding window."""
        now = self._time_provider()
        self._crash_timestamps = [
            t for t in self._crash_timestamps
            if now - t <= self.crash_window_seconds
        ]

    def record_crash(self, exit_code: int) -> None:
        """
        Records a process crash and prunes expired history.

        Args:
            exit_code: Exit code of the terminated process.
        """
        with self._lock:
            now = self._time_provider()
            self._crash_timestamps.append(now)
            self._prune_expired_crashes()
            logger.warning(
                f"[RECOVERY POLICY] Crash recorded (Exit code: {exit_code}). "
                f"Active crashes in {self.crash_window_seconds}s window: {len(self._crash_timestamps)}"
            )

    def should_restart(self) -> bool:
        """
        Evaluates whether the process is allowed to restart without exceeding crash limits.

        Returns:
            bool: True if crashes in window <= max_consecutive_crashes, False otherwise.
        """
        with self._lock:
            self._prune_expired_crashes()
            return len(self._crash_timestamps) <= self.max_consecutive_crashes

    def get_backoff_seconds(self) -> float:
        """Returns the configured restart backoff delay in seconds."""
        return self.restart_backoff_seconds

    def reset(self) -> None:
        """Clears all recorded crash history."""
        with self._lock:
            self._crash_timestamps.clear()
            logger.info("[RECOVERY POLICY] Crash history reset.")
