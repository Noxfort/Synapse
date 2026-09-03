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
# File: src/fenix/protocols.py
# Author: Gabriel Moraes
# Date: 2026-08-19

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Protocol, Optional, Any, List, Dict, Tuple, runtime_checkable
from datetime import datetime


class TriggerType(Enum):
    EMERGENCY = 1      # Fênix Nível 1: Hot-Reset (Auditor Trigger, ~1-2s)
    OPPORTUNISTIC = 2  # Fênix Nível 2: Autonomous Multi-Day Evolution (Traffic Valley)


@dataclass
class StrategyCallbacks:
    """
    Decouples execution strategies from framework-specific signal systems (e.g., PyQt6).
    """
    on_progress: Callable[[str, int], None]
    on_request_fallback: Callable[[bool], None]
    on_request_neural_reset: Callable[[], None]
    on_request_model_hot_swap: Callable[[str], None]
    is_interrupted: Callable[[], bool]


@runtime_checkable
class IFenixStrategy(Protocol):
    """
    Standard interface for all F.E.N.I.X. recovery and evolution strategies.
    """
    @property
    def name(self) -> str:
        """Name of the strategy."""
        ...

    def execute(self, callbacks: StrategyCallbacks) -> bool:
        """
        Executes the strategy lifecycle.
        
        Args:
            callbacks: Framework-agnostic callbacks for state updates and triggers.
            
        Returns:
            bool: True if execution succeeded, False otherwise.
        """
        ...


@runtime_checkable
class IStorageProtocol(Protocol):
    """
    Protocol for checkpoint and model storage persistence.
    """
    def save_model_checkpoint(self, source_path: str, tag: str = "default") -> str:
        ...


@runtime_checkable
class IProcessRunner(Protocol):
    """
    Protocol for low-level OS process management and execution.
    """
    def spawn(self, command: List[str], env: Optional[Dict[str, str]] = None) -> bool:
        """Spawns an OS subprocess."""
        ...

    def terminate(self, timeout_seconds: float = 5.0) -> None:
        """Gracefully terminates the subprocess (SIGTERM -> SIGKILL if timed out)."""
        ...

    def poll(self) -> Optional[int]:
        """Returns the process exit code if terminated, or None if still running."""
        ...

    @property
    def pid(self) -> Optional[int]:
        """Returns the process PID or None if not running."""
        ...

    @property
    def is_alive(self) -> bool:
        """Checks if the subprocess is currently running."""
        ...


@runtime_checkable
class IRecoveryPolicy(Protocol):
    """
    Protocol for crash recovery rules, backoff calculations, and restart limits.
    """
    def record_crash(self, exit_code: int) -> None:
        """Records a process crash occurrence."""
        ...

    def should_restart(self) -> bool:
        """Evaluates whether the process should be restarted or halted."""
        ...

    def get_backoff_seconds(self) -> float:
        """Returns the backoff duration in seconds before attempting resurrection."""
        ...

    def reset(self) -> None:
        """Resets the crash history and recovery state."""
        ...

    @property
    def crash_count(self) -> int:
        """Returns the number of active crashes within the current monitoring window."""
        ...


@runtime_checkable
class IEvolutionCoordinator(Protocol):
    """
    Protocol for managing asynchronous model evolution cycles.
    """
    def trigger_evolution(self, on_complete: Optional[Callable[[bool, str], None]] = None) -> bool:
        """Triggers a background evolution cycle."""
        ...

    def stop(self) -> None:
        """Stops or interrupts any active evolution cycle."""
        ...

    @property
    def is_evolving(self) -> bool:
        """Returns whether an evolution cycle is currently running."""
        ...


@runtime_checkable
class IDriftEvaluator(Protocol):
    """
    Protocol for evaluating data/concept drift and anomaly severity.
    """
    def has_significant_multiday_drift(self) -> bool:
        ...

    def is_anomaly_critical(self, reconstruction_error: float) -> bool:
        ...


@runtime_checkable
class IMaintenanceScheduler(Protocol):
    """
    Protocol for checking opportunity/valley maintenance windows.
    """
    def is_opportunity_slot(self, dt: Optional[datetime] = None) -> Tuple[bool, str]:
        ...

