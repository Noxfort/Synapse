# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
import pytest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent, QKeySequence

from ui.main_window import MainWindow

@pytest.fixture(scope="module")
def qapp():
    """Ensure a single QApplication instance exists for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

def test_main_window_toggle_fullscreen(qapp, mock_app_state):
    """Test that toggle_fullscreen toggles MainWindow full screen state."""
    mock_controller = MagicMock()
    mock_controller.app_state = mock_app_state
    
    window = MainWindow(mock_controller)
    assert not window.isFullScreen()
    
    # Toggle to full screen
    window.toggle_fullscreen()
    assert window.isFullScreen()
    
    # Toggle back to normal
    window.toggle_fullscreen()
    assert not window.isFullScreen()
    
    window.close()

def test_main_menu_fullscreen_shortcut(qapp, mock_app_state):
    """Test that MainMenu contains the toggle full screen action with F11 shortcut."""
    mock_controller = MagicMock()
    mock_controller.app_state = mock_app_state
    
    window = MainWindow(mock_controller)
    menu = window.main_menu
    
    assert hasattr(menu, "toggle_fullscreen_act")
    shortcut = menu.toggle_fullscreen_act.shortcut()
    assert shortcut == QKeySequence(Qt.Key.Key_F11)
    
    window.close()

def test_key_press_event_f11(qapp, mock_app_state):
    """Test that pressing F11 triggers full screen toggle on MainWindow."""
    mock_controller = MagicMock()
    mock_controller.app_state = mock_app_state
    
    window = MainWindow(mock_controller)
    assert not window.isFullScreen()
    
    event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_F11, Qt.KeyboardModifier.NoModifier)
    window.keyPressEvent(event)
    assert window.isFullScreen()
    
    window.keyPressEvent(event)
    assert not window.isFullScreen()
    
    window.close()
