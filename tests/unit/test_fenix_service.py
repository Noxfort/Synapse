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
# File: tests/unit/test_fenix_service.py
# Author: Gabriel Moraes
# Date: 2026-08-29

import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.services.fenix_service import FenixService, TriggerType
from src.fenix.hot_reset_strategy import Level1HotResetStrategy
from src.fenix.evolution_strategy import Level2EvolutionStrategy
from src.fenix.maintenance_scheduler import MaintenanceScheduler
from src.fenix.drift_evaluator import DriftEvaluator
from src.fenix.protocols import StrategyCallbacks


# =========================================================================
# 1. MODULAR COMPONENT UNIT TESTS
# =========================================================================

def test_maintenance_scheduler(tmp_path):
    """Test MaintenanceScheduler slot detection and JSON schedule loading."""
    sched_file = tmp_path / "test_schedule.json"
    sched_file.write_text('{"0_3": 0, "0_4": 1, "0_5": 2}', encoding='utf-8')
    
    scheduler = MaintenanceScheduler(schedule_path=sched_file)
    mapping = scheduler.load_schedule()
    assert len(mapping) == 3
    
    # Mock datetime to Monday (weekday 0) at 3 AM -> valley slot (0)
    fake_dt_valley = MagicMock()
    fake_dt_valley.weekday.return_value = 0
    fake_dt_valley.hour = 3
    is_valley, key = scheduler.is_opportunity_slot(fake_dt_valley)
    assert is_valley is True
    assert key == "0_3"
    
    # Mock datetime to Monday at 4 AM -> normal slot (1)
    fake_dt_normal = MagicMock()
    fake_dt_normal.weekday.return_value = 0
    fake_dt_normal.hour = 4
    is_valley_norm, key_norm = scheduler.is_opportunity_slot(fake_dt_normal)
    assert is_valley_norm is False
    assert key_norm == "0_4"


def test_drift_evaluator():
    """Test DriftEvaluator threshold checking and multi-day gatekeeper."""
    evaluator = DriftEvaluator(reconstruction_threshold=0.30, min_drift_days=7)
    
    assert evaluator.is_anomaly_critical(0.35) is True
    assert evaluator.is_anomaly_critical(0.15) is False
    assert evaluator.has_significant_multiday_drift() is True


def test_hot_reset_strategy_isolated():
    """Test Level1HotResetStrategy executes callbacks in order."""
    strategy = Level1HotResetStrategy()
    assert "Hot-Reset" in strategy.name
    
    progress_mock = MagicMock()
    fallback_mock = MagicMock()
    reset_mock = MagicMock()
    hot_swap_mock = MagicMock()
    
    callbacks = StrategyCallbacks(
        on_progress=progress_mock,
        on_request_fallback=fallback_mock,
        on_request_neural_reset=reset_mock,
        on_request_model_hot_swap=hot_swap_mock,
        is_interrupted=lambda: False
    )
    
    with patch('time.sleep', return_value=None):
        result = strategy.execute(callbacks)
        
    assert result is True
    assert fallback_mock.call_count == 2
    fallback_mock.assert_any_call(True)
    fallback_mock.assert_any_call(False)
    reset_mock.assert_called_once()


def test_evolution_strategy_isolated(mock_storage_manager):
    """Test Level2EvolutionStrategy executes retraining and checkpoint saving."""
    mock_storage_manager.save_model_checkpoint.return_value = "saved_candidate.pth"
    strategy = Level2EvolutionStrategy(storage=mock_storage_manager)
    assert "Evolution" in strategy.name
    
    progress_mock = MagicMock()
    fallback_mock = MagicMock()
    reset_mock = MagicMock()
    hot_swap_mock = MagicMock()
    
    callbacks = StrategyCallbacks(
        on_progress=progress_mock,
        on_request_fallback=fallback_mock,
        on_request_neural_reset=reset_mock,
        on_request_model_hot_swap=hot_swap_mock,
        is_interrupted=lambda: False
    )
    
    with patch('time.sleep', return_value=None):
        result = strategy.execute(callbacks)
        
    assert result is True
    mock_storage_manager.save_model_checkpoint.assert_called_once()
    hot_swap_mock.assert_called_once_with("saved_candidate.pth")


# =========================================================================
# 2. FENIX SERVICE FACADE / ORCHESTRATOR TESTS
# =========================================================================

def test_fenix_emergency_trigger(qtbot, mock_storage_manager, mock_app_state):
    """Test FenixService triggers Level 1 Hot-Reset when reconstruction error exceeds threshold."""
    service = FenixService(storage_manager=mock_storage_manager, app_state=mock_app_state)
    service.is_monitoring_active = True
    
    with patch('src.fenix.hot_reset_strategy.time.sleep', return_value=None):
        with qtbot.waitSignal(service.request_fallback_activation, timeout=2000) as blocker:
            # 0.35 is > self.reconstruction_threshold of 0.30
            service.check_health_metrics(current_reconstruction_error=0.35)
            
    assert blocker.args == [True]
    assert service.is_running is True
    service.stop_cycle()


def test_fenix_ignores_normal_error(qtbot, mock_storage_manager, mock_app_state):
    """Test FenixService does NOT trigger on normal errors."""
    service = FenixService(storage_manager=mock_storage_manager, app_state=mock_app_state)
    service.is_monitoring_active = True
    
    # Normal error (0.10 < 0.30)
    service.check_health_metrics(current_reconstruction_error=0.10)
    
    assert service.is_running is False


def test_fenix_cycle_aborts_on_stop_request(qtbot, mock_storage_manager, mock_app_state):
    """Test the Fenix cycle aborts safely if stop requested mid-flight."""
    service = FenixService(storage_manager=mock_storage_manager, app_state=mock_app_state)
    
    orig_sleep = time.sleep
    with patch('src.fenix.evolution_strategy.time.sleep', side_effect=lambda x: orig_sleep(0.01)):
        with qtbot.waitSignal(service.cycle_finished, timeout=4000) as blocker:
            service.start_fenix_cycle(TriggerType.OPPORTUNISTIC)
            orig_sleep(0.02)
            service.stop_cycle()
            
    success, message = blocker.args
    assert success is False
    assert "Aborted" in message or "Evolution Error" in message
    assert service.is_running is False


def test_fenix_full_opportunistic_cycle(qtbot, mock_storage_manager, mock_app_state):
    """Test full Level 2 cycle execution when triggered opportunistically."""
    service = FenixService(storage_manager=mock_storage_manager, app_state=mock_app_state)
    mock_storage_manager.save_model_checkpoint.return_value = "final_path.pth"
    
    orig_sleep = time.sleep
    with patch('src.fenix.evolution_strategy.time.sleep', side_effect=lambda x: orig_sleep(0.01)):
        with qtbot.waitSignal(service.cycle_finished, timeout=4000) as blocker:
            service.start_fenix_cycle(TriggerType.OPPORTUNISTIC)
            
    success, message = blocker.args
    
    assert success is True
    assert "Evolution Complete" in message
    assert service.is_running is False
    mock_storage_manager.save_model_checkpoint.assert_called_once()
