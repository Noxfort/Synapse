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
# File: tests/integration/test_orchestrator.py
# Author: Gabriel Moraes
# Date: 2026-08-29

import pytest
from unittest.mock import patch, MagicMock

from src.orchestrators.lifecycle_orchestrator import LifecycleOrchestrator, SystemMode

@pytest.fixture
def mock_service_container():
    with patch('src.orchestrators.lifecycle_orchestrator.ServiceContainer') as MockContainer:
        container_instance = MockContainer.return_value
        services = {
            "inference_engine": MagicMock(),
            "cartographer": MagicMock(),
            "fenix": MagicMock(),
            "storage_manager": MagicMock()
        }
        container_instance.build.return_value = services
        yield MockContainer

@pytest.fixture
def mock_boot_sequence():
    with patch('src.orchestrators.lifecycle_orchestrator.BootSequence') as MockBoot:
        yield MockBoot


def test_orchestrator_boot_sequence_success(qtbot, mock_service_container, mock_boot_sequence):
    """Test successful boot sequence transitions through OFFLINE -> RUNNING."""
    orchestrator = LifecycleOrchestrator()
    
    assert orchestrator.current_mode == SystemMode.OFFLINE
    
    # We expect status_changed to be emitted twice: BOOTING then RUNNING
    with qtbot.waitSignals([orchestrator.status_changed, orchestrator.status_changed]) as blocker:
        orchestrator.boot_system()
        
    assert mock_boot_sequence.execute.called
    assert orchestrator.current_mode == SystemMode.RUNNING

def test_orchestrator_boot_sequence_failure(qtbot, mock_service_container, mock_boot_sequence):
    """Test boot sequence failure transitions to ERROR state."""
    orchestrator = LifecycleOrchestrator()
    
    # Make boot sequence throw an exception
    mock_boot_sequence.execute.side_effect = Exception("Hardware failure")
    
    with qtbot.waitSignal(orchestrator.error_occurred) as blocker:
        orchestrator.boot_system()
        
    assert orchestrator.current_mode == SystemMode.ERROR
    assert blocker.args[0] == "Hardware failure"

def test_orchestrator_shutdown_sequence(qtbot, mock_service_container):
    """Test shutdown transitions system back to OFFLINE and stops timers."""
    orchestrator = LifecycleOrchestrator()
    orchestrator.current_mode = SystemMode.RUNNING
    
    # Mocking timers to check if they were stopped
    orchestrator.engine_timer = MagicMock()
    orchestrator.health_timer = MagicMock()
    
    orchestrator.shutdown_system()
    
    assert orchestrator.current_mode == SystemMode.OFFLINE
    orchestrator.engine_timer.stop.assert_called_once()
    orchestrator.health_timer.stop.assert_called_once()
    
    orchestrator.inference_engine.stop.assert_called_once()
    orchestrator.fenix.stop_watchdog.assert_called_once()

def test_orchestrator_prevent_optimization_offline(mock_service_container):
    """Test optimization is blocked if system is OFFLINE."""
    orchestrator = LifecycleOrchestrator()
    assert orchestrator.current_mode == SystemMode.OFFLINE
    
    orchestrator.start_optimization()
    
    assert orchestrator.current_mode == SystemMode.OFFLINE
    assert orchestrator.optimizer_service is None
