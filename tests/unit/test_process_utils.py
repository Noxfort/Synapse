# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
import pytest
from unittest.mock import patch, MagicMock
from src.utils.process_utils import hard_kill

def test_hard_kill_executes_os_exit():
    """Test that hard_kill calls psutil kill on children and os._exit."""
    with patch("os._exit") as mock_exit, patch("psutil.Process") as mock_psutil_proc, patch("os.killpg") as mock_killpg:
        mock_child = MagicMock()
        mock_psutil_proc.return_value.children.return_value = [mock_child]
        
        hard_kill(exit_code=0)
        
        mock_child.kill.assert_called_once()
        mock_exit.assert_called_once_with(0)
