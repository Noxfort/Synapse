import time
import pytest
from unittest.mock import patch, MagicMock
from src.services.fenix_service import FenixService, TriggerType

def test_fenix_emergency_trigger(qtbot, mock_storage_manager, mock_app_state):
    """Test FenixService triggers fallback cycle when reconstruction error exceeds threshold."""
    service = FenixService(storage_manager=mock_storage_manager, app_state=mock_app_state)
    service.is_monitoring_active = True
    # We want to test the signals emitted by the service
    # Patching sleep to make the thread run instantly in test
    with patch('src.services.fenix_service.time.sleep', return_value=None):
        with qtbot.waitSignal(service.request_fallback_activation, timeout=2000) as blocker:
            # 0.35 is > self.reconstruction_threshold of 0.30
            service.check_health_metrics(current_reconstruction_error=0.35)
            
    # The signal should be emitted with True to activate fallback
    assert blocker.args == [True]
    assert service.is_running is True

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
    # Patch local module sleep so thread is correctly mocked
    with patch('src.services.fenix_service.time.sleep', side_effect=lambda x: orig_sleep(0.01)):
        # Trigger opportunistically
        with qtbot.waitSignal(service.cycle_finished, timeout=4000) as blocker:
            service.start_fenix_cycle(TriggerType.OPPORTUNISTIC)
            orig_sleep(0.02) # main thread yields to ensure thread starts
            # Immediately request a stop
            service.stop_cycle()
            
    success, message = blocker.args
    assert success is False
    assert "Cycle Aborted by User" in message
    assert service.is_running is False

def test_fenix_full_opportunistic_cycle(qtbot, mock_storage_manager, mock_app_state):
    """Test full cycle execution when triggered opportunistically."""
    service = FenixService(storage_manager=mock_storage_manager, app_state=mock_app_state)
    mock_storage_manager.save_model_checkpoint.return_value = "final_path.pth"
    
    orig_sleep = time.sleep
    # Patch local module sleep so thread is correctly mocked but yields to Qt Event Loop
    with patch('src.services.fenix_service.time.sleep', side_effect=lambda x: orig_sleep(0.01)):
        with qtbot.waitSignal(service.cycle_finished, timeout=4000) as blocker:
            service.start_fenix_cycle(TriggerType.OPPORTUNISTIC)
            
    success, message = blocker.args
    
    assert success is True
    assert "Model Evolved" in message
    assert service.is_running is False
    # Ensure hot swap was requested
    mock_storage_manager.save_model_checkpoint.assert_called_once()
