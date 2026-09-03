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
# File: src/fenix/process_supervisor.py
# Author: Gabriel Moraes
# Date: 2026-09-01

"""
F.E.N.I.X. Out-of-Process Supervisor & Facade Orchestrator (SOLID Architecture).

Adheres strictly to SOLID:
- [SRP] Acts exclusively as a high-level facade/orchestrator coordinating process lifecycle
        states and delegating low-level tasks to specialized components (Runner, Recovery Policy, Evolution).
- [OCP] Open for extension via pluggable IProcessRunner, IRecoveryPolicy, and IEvolutionCoordinator implementations.
- [LSP] Concrete strategies and runners are fully substitutable via runtime protocols.
- [ISP] Clean, segregated protocols (IProcessRunner, IRecoveryPolicy, IEvolutionCoordinator).
- [DIP] Injected with abstractions/protocols rather than hardwired to concrete low-level implementations.
"""

import os
import sys
import time
import threading
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass
from enum import Enum

from src.utils.logging_setup import get_logger
from src.fenix.protocols import (
    IProcessRunner,
    IRecoveryPolicy,
    IEvolutionCoordinator,
    IFenixStrategy,
    IDriftEvaluator,
    IMaintenanceScheduler,
)
from src.fenix.process_runner import SubprocessRunner
from src.fenix.recovery_policy import WindowedCrashRecoveryPolicy
from src.fenix.evolution_coordinator import FenixEvolutionCoordinator

logger = get_logger("FenixSupervisor")


class ProcessState(Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    CRASHED = "CRASHED"
    RESTARTING = "RESTARTING"


@dataclass
class SupervisorConfig:
    """Configuration options for process supervision."""
    max_consecutive_crashes: int = 5
    crash_window_seconds: float = 60.0
    restart_backoff_seconds: float = 1.0
    health_poll_interval_seconds: float = 1.0
    core_args: Optional[List[str]] = None


class FenixProcessSupervisor:
    """
    Process 2 — Master Watchdog & Self-Healing Guardian Facade.

    Coordinates process lifecycle states, health checking, and self-healing resurrection.
    Delegates process spawning/termination to `IProcessRunner`, resilience logic to
    `IRecoveryPolicy`, and background training to `IEvolutionCoordinator`.
    """

    def __init__(
        self,
        config: Optional[SupervisorConfig] = None,
        runner: Optional[IProcessRunner] = None,
        recovery_policy: Optional[IRecoveryPolicy] = None,
        evolution_coordinator: Optional[IEvolutionCoordinator] = None,
        evolution_strategy: Optional[IFenixStrategy] = None,
        drift_evaluator: Optional[IDriftEvaluator] = None,
        scheduler: Optional[IMaintenanceScheduler] = None,
        on_status_changed: Optional[Callable[[ProcessState, str], None]] = None,
    ):
        self.config = config or SupervisorConfig()
        self.runner = runner or SubprocessRunner()
        self.recovery_policy = recovery_policy or WindowedCrashRecoveryPolicy(
            max_consecutive_crashes=self.config.max_consecutive_crashes,
            crash_window_seconds=self.config.crash_window_seconds,
            restart_backoff_seconds=self.config.restart_backoff_seconds,
        )
        self.evolution_coordinator = evolution_coordinator or FenixEvolutionCoordinator(
            strategy=evolution_strategy,
            drift_evaluator=drift_evaluator,
            scheduler=scheduler,
        )
        self.on_status_changed = on_status_changed

        self._state = ProcessState.STOPPED
        self._stop_requested = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    @property
    def state(self) -> ProcessState:
        """Returns the current high-level state of the supervised process."""
        return self._state

    @property
    def child_pid(self) -> Optional[int]:
        """Returns the PID of the supervised child process."""
        return self.runner.pid

    def is_child_alive(self) -> bool:
        """Checks if the supervised child process is currently alive."""
        return self.runner.is_alive

    def _set_state(self, new_state: ProcessState, message: str = ""):
        """Updates internal state and notifies registered listeners."""
        self._state = new_state
        logger.info(f"[FENIX SUPERVISOR] State: {new_state.value} | {message}")
        if self.on_status_changed:
            try:
                self.on_status_changed(new_state, message)
            except Exception as e:
                logger.error(f"Error in on_status_changed callback: {e}")

    # =========================================================================
    # PROCESS LIFECYCLE MANAGEMENT (FACADE DELEGATION)
    # =========================================================================

    def start(self, custom_command: Optional[List[str]] = None) -> bool:
        """Starts the supervised Core Engine process and watchdog loop."""
        with self._lock:
            if self._state in (ProcessState.RUNNING, ProcessState.STARTING):
                logger.warning("[FENIX SUPERVISOR] Core Process already running or starting.")
                return True

            self._stop_requested = False
            self._set_state(ProcessState.STARTING, "Spawning Neural Core Process...")

            success = self._spawn_child(custom_command)
            if not success:
                self._set_state(ProcessState.STOPPED, "Failed to spawn child process.")
                return False

            self._set_state(ProcessState.RUNNING, f"Neural Core running [PID: {self.child_pid}]")

            # Start background watchdog monitor
            if self._monitor_thread is None or not self._monitor_thread.is_alive():
                self._monitor_thread = threading.Thread(target=self._supervision_loop, daemon=True)
                self._monitor_thread.start()

            return True

    def stop(self, timeout_seconds: float = 5.0) -> None:
        """Gracefully terminates the supervised process, evolution workers, and watchdog."""
        self._stop_requested = True
        self.evolution_coordinator.stop()

        with self._lock:
            if not self.runner.is_alive and self.runner.pid is None:
                self._set_state(ProcessState.STOPPED, "Already stopped.")
                return

            logger.info(f"[FENIX SUPERVISOR] Terminating Core Process [PID: {self.child_pid}]...")
            self.runner.terminate(timeout_seconds=timeout_seconds)
            self._set_state(ProcessState.STOPPED, "Core Process stopped gracefully.")

    def _spawn_child(self, custom_command: Optional[List[str]] = None) -> bool:
        """Builds default execution environment and delegates process creation to runner."""
        if custom_command:
            cmd = custom_command
        else:
            args = self.config.core_args or ["--daemon"]
            cmd = [sys.executable, "synapse.py"] + args

        env = os.environ.copy()
        env["SYNAPSE_SUPERVISED"] = "1"
        env["PYTHONUNBUFFERED"] = "1"

        return self.runner.spawn(cmd, env=env)

    # =========================================================================
    # WATCHDOG & AUTO-RESURRECTION LOOP
    # =========================================================================

    def _supervision_loop(self) -> None:
        """Continuous watchdog checking child health and resurrecting on crash."""
        logger.info("[FENIX SUPERVISOR] 🛡️ Watchdog monitoring loop active.")
        while not self._stop_requested:
            time.sleep(self.config.health_poll_interval_seconds)

            if self._stop_requested:
                break

            with self._lock:
                if not self.runner.is_alive and self.runner.pid is None:
                    continue

                exit_code = self.runner.poll()
                if exit_code is not None:
                    # Child died!
                    self._handle_child_crash(exit_code)

    def _handle_child_crash(self, exit_code: int) -> None:
        """Autopsy and auto-resurrection when child process terminates."""
        self.recovery_policy.record_crash(exit_code)

        logger.critical(
            f"[FENIX SUPERVISOR] 🔥 CRITICAL: Neural Core Process [PID: {self.child_pid}] "
            f"died with exit code {exit_code}! (Active crashes in window: {self.recovery_policy.crash_count})"
        )

        if self._stop_requested:
            self._set_state(ProcessState.STOPPED, "Child exited during requested shutdown.")
            return

        if not self.recovery_policy.should_restart():
            self._set_state(
                ProcessState.CRASHED,
                f"Exceeded max crash limit ({self.config.max_consecutive_crashes}) within {self.config.crash_window_seconds}s. Halting."
            )
            return

        # Auto-resurrection
        backoff = self.recovery_policy.get_backoff_seconds()
        self._set_state(
            ProcessState.RESTARTING,
            f"Auto-resurrecting Neural Core Process in {backoff}s..."
        )
        time.sleep(backoff)

        success = self._spawn_child()
        if success:
            self._set_state(ProcessState.RUNNING, f"Neural Core resurrected [PID: {self.child_pid}]")
        else:
            self._set_state(ProcessState.CRASHED, "Failed to resurrect Neural Core.")

    # =========================================================================
    # LEVEL 2 EVOLUTION DELEGATION
    # =========================================================================

    def trigger_level2_evolution(self, on_complete: Optional[Callable[[bool, str], None]] = None) -> bool:
        """Delegates background Level 2 model evolution to the evolution coordinator."""
        return self.evolution_coordinator.trigger_evolution(on_complete=on_complete)
