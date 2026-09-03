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
# File: tests/unit/test_fenix_supervisor.py
# Author: Gabriel Moraes
# Date: 2026-09-01

import time
import pytest
from unittest.mock import MagicMock, patch

from src.fenix.process_supervisor import (
    FenixProcessSupervisor,
    ProcessState,
    SupervisorConfig,
)
from src.fenix.recovery_policy import WindowedCrashRecoveryPolicy
from src.fenix.process_runner import SubprocessRunner
from src.fenix.evolution_coordinator import FenixEvolutionCoordinator
from src.fenix.protocols import (
    IProcessRunner,
    IRecoveryPolicy,
    IEvolutionCoordinator,
    IFenixStrategy,
    StrategyCallbacks,
)


# =============================================================================
# RECOVERY POLICY UNIT TESTS (SRP / PURE LOGIC)
# =============================================================================

def test_recovery_policy_sliding_window_and_limits():
    """Verifies that WindowedCrashRecoveryPolicy tracks crashes and enforces limit."""
    current_time = 1000.0
    time_provider = lambda: current_time

    policy = WindowedCrashRecoveryPolicy(
        max_consecutive_crashes=2,
        crash_window_seconds=60.0,
        restart_backoff_seconds=2.5,
        time_provider=time_provider,
    )

    assert policy.crash_count == 0
    assert policy.should_restart() is True
    assert policy.get_backoff_seconds() == 2.5

    # Crash 1
    policy.record_crash(1)
    assert policy.crash_count == 1
    assert policy.should_restart() is True

    # Crash 2
    policy.record_crash(1)
    assert policy.crash_count == 2
    assert policy.should_restart() is True

    # Crash 3 -> Exceeds max 2 crashes in window
    policy.record_crash(1)
    assert policy.crash_count == 3
    assert policy.should_restart() is False

    # Advance time beyond sliding window (60s)
    current_time = 1061.0
    assert policy.crash_count == 0
    assert policy.should_restart() is True

    # Reset
    policy.record_crash(1)
    assert policy.crash_count == 1
    policy.reset()
    assert policy.crash_count == 0


# =============================================================================
# PROCESS RUNNER UNIT TESTS
# =============================================================================

def test_subprocess_runner_spawn_and_lifecycle():
    """Verifies that SubprocessRunner manages child processes correctly."""
    mock_popen = MagicMock()
    mock_popen.pid = 44444
    mock_popen.poll.return_value = None

    runner = SubprocessRunner()
    assert runner.is_alive is False
    assert runner.pid is None
    assert runner.poll() is None

    with patch("subprocess.Popen", return_value=mock_popen):
        success = runner.spawn(["echo", "hello"])
        assert success is True
        assert runner.is_alive is True
        assert runner.pid == 44444
        assert runner.poll() is None

        runner.terminate(timeout_seconds=0.1)
        mock_popen.terminate.assert_called_once()
        assert runner.is_alive is False


# =============================================================================
# EVOLUTION COORDINATOR UNIT TESTS
# =============================================================================

def test_evolution_coordinator_async_execution():
    """Verifies that FenixEvolutionCoordinator executes background strategy."""
    mock_strategy = MagicMock()
    mock_strategy.name = "MockEvolution"
    mock_strategy.execute.return_value = True

    coordinator = FenixEvolutionCoordinator(strategy=mock_strategy)
    assert coordinator.is_evolving is False

    results = []
    success = coordinator.trigger_evolution(on_complete=lambda ok, msg: results.append((ok, msg)))
    assert success is True

    # Wait for thread
    time.sleep(0.1)

    assert len(results) == 1
    assert results[0][0] is True
    assert coordinator.is_evolving is False
    mock_strategy.execute.assert_called_once()


# =============================================================================
# PROCESS SUPERVISOR (FACADE / ORCHESTRATOR) TESTS
# =============================================================================

def test_supervisor_initial_state():
    """Verifies that supervisor starts in STOPPED state with no child process."""
    supervisor = FenixProcessSupervisor()
    assert supervisor.state == ProcessState.STOPPED
    assert supervisor.child_pid is None
    assert supervisor.is_child_alive() is False


def test_supervisor_start_and_stop_lifecycle():
    """Tests normal start and graceful stop lifecycle of the supervisor."""
    mock_popen = MagicMock()
    mock_popen.pid = 99999
    mock_popen.poll.return_value = None  # Process is running

    state_transitions = []
    supervisor = FenixProcessSupervisor(
        on_status_changed=lambda state, msg: state_transitions.append(state)
    )

    with patch("subprocess.Popen", return_value=mock_popen):
        success = supervisor.start()
        assert success is True
        assert supervisor.state == ProcessState.RUNNING
        assert supervisor.child_pid == 99999
        assert supervisor.is_child_alive() is True
        assert ProcessState.STARTING in state_transitions
        assert ProcessState.RUNNING in state_transitions

        # Graceful stop
        supervisor.stop(timeout_seconds=0.1)
        assert supervisor.state == ProcessState.STOPPED
        assert supervisor.child_pid is None
        mock_popen.terminate.assert_called_once()


def test_supervisor_auto_resurrection_on_crash():
    """Tests that supervisor detects child death and auto-resurrects the process."""
    mock_crashed_proc = MagicMock()
    mock_crashed_proc.pid = 11111
    mock_crashed_proc.poll.return_value = 139  # SegFault exit code

    mock_resurrected_proc = MagicMock()
    mock_resurrected_proc.pid = 22222
    mock_resurrected_proc.poll.return_value = None

    config = SupervisorConfig(
        max_consecutive_crashes=3,
        restart_backoff_seconds=0.01,
        health_poll_interval_seconds=0.01,
    )

    status_changes = []
    supervisor = FenixProcessSupervisor(
        config=config,
        on_status_changed=lambda st, msg: status_changes.append(st)
    )

    with patch("subprocess.Popen", side_effect=[mock_crashed_proc, mock_resurrected_proc]):
        supervisor.start()
        assert supervisor.state == ProcessState.RUNNING

        # Simulate a crash handling tick
        supervisor._handle_child_crash(139)

        assert ProcessState.RESTARTING in status_changes
        assert supervisor.state == ProcessState.RUNNING
        assert supervisor.child_pid == 22222

        supervisor.stop()


def test_supervisor_exceed_crash_limit_halts():
    """Tests that supervisor halts and enters CRASHED state when max crash limit is exceeded."""
    config = SupervisorConfig(
        max_consecutive_crashes=2,
        crash_window_seconds=10.0,
        restart_backoff_seconds=0.01,
    )

    supervisor = FenixProcessSupervisor(config=config)
    mock_proc = MagicMock()
    mock_proc.pid = 33333

    with patch("subprocess.Popen", return_value=mock_proc):
        supervisor.start()

        # Crash 1 -> Restarts
        supervisor._handle_child_crash(1)
        assert supervisor.state == ProcessState.RUNNING

        # Crash 2 -> Restarts
        supervisor._handle_child_crash(1)
        assert supervisor.state == ProcessState.RUNNING

        # Crash 3 -> Exceeds limit (2) -> Enters CRASHED
        supervisor._handle_child_crash(1)
        assert supervisor.state == ProcessState.CRASHED

        supervisor.stop()


def test_supervisor_background_evolution():
    """Tests background Level 2 Evolution execution via supervisor."""
    mock_strategy = MagicMock()
    mock_strategy.name = "MockEvolution"
    mock_strategy.execute.return_value = True

    supervisor = FenixProcessSupervisor(evolution_strategy=mock_strategy)

    results = []
    success = supervisor.trigger_level2_evolution(
        on_complete=lambda ok, msg: results.append((ok, msg))
    )

    assert success is True

    # Wait briefly for background evolution thread
    time.sleep(0.1)

    assert len(results) == 1
    assert results[0][0] is True
    assert mock_strategy.execute.called


def test_supervisor_custom_injected_components():
    """Tests DIP & OCP: Inversion of Control via custom Runner, Recovery Policy, and Coordinator."""
    mock_runner = MagicMock(spec=IProcessRunner)
    mock_runner.pid = 77777
    mock_runner.is_alive = True
    mock_runner.spawn.return_value = True

    mock_policy = MagicMock(spec=IRecoveryPolicy)
    mock_policy.should_restart.return_value = True
    mock_policy.get_backoff_seconds.return_value = 0.001
    mock_policy.crash_count = 1

    mock_coordinator = MagicMock(spec=IEvolutionCoordinator)
    mock_coordinator.trigger_evolution.return_value = True

    supervisor = FenixProcessSupervisor(
        runner=mock_runner,
        recovery_policy=mock_policy,
        evolution_coordinator=mock_coordinator,
    )

    assert supervisor.start() is True
    assert supervisor.child_pid == 77777
    assert supervisor.is_child_alive() is True

    # Evolution delegation
    assert supervisor.trigger_level2_evolution() is True
    mock_coordinator.trigger_evolution.assert_called_once()

    # Crash delegation
    supervisor._handle_child_crash(1)
    mock_policy.record_crash.assert_called_with(1)
    mock_policy.should_restart.assert_called()

    # Stop delegation
    supervisor.stop()
    mock_runner.terminate.assert_called_once()
    mock_coordinator.stop.assert_called_once()
