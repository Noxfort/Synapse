import pytest
from unittest.mock import MagicMock
from src.services.historical_manager import HistoricalManager

def test_historical_manager_edge_mapping():
    """Test HistoricalManager maps flat data to edges appropriately."""
    mock_app_state = MagicMock()
    # Mocking that there are 2 edges in the graph, with valid 'id' attributes
    edge_1 = MagicMock()
    edge_1.id = "edge_1"
    edge_2 = MagicMock()
    edge_2.id = "edge_2"
    mock_app_state.get_all_edges.return_value = [edge_1, edge_2]
    
    manager = HistoricalManager(app_state=mock_app_state)
    
    # Mock the internal fallback_engine to return flat predictions
    manager.fallback_engine = MagicMock()
    manager.fallback_engine.is_ready = True
    # Fake flat fallback returns values per sensor
    # Fake flat fallback returns values per metric keys
    manager.fallback_engine.get_fallback_state.return_value = {
        "edge_1_speed": 40.0,
        "edge_1_density": 50.0,
        "edge_2_speed": 40.0,
        "edge_2_density": 45.0
    }
    mock_app_state.is_meh_ready = True
    
    # Run the top-level mapping
    predictions = manager.get_current_state_prediction()
    
    assert "edge_1" in predictions
    assert "edge_2" in predictions
    # KSE expects the edge mappings to have density
    assert predictions["edge_1"]["density"] == 50.0
    assert predictions["edge_2"]["density"] == 45.0

def test_historical_manager_synthetic_fallback():
    """Test manager provides synthetic edges if topology is empty."""
    mock_app_state = MagicMock()
    # No edges defined
    mock_app_state.get_all_edges.return_value = []
    
    manager = HistoricalManager(app_state=mock_app_state)
    mock_app_state.is_meh_ready = True
    
    # Make sure fallback fails so we get the pure synthethic structure
    # But we MUST map synthetic from SOME data, or it won't trigger the generation.
    # FallbackEngine must be ready, returning something like just a "speed" overall.
    manager.fallback_engine = MagicMock()
    manager.fallback_engine.is_ready = True
    manager.fallback_engine.sensor_profiles = {}
    manager.fallback_engine.get_fallback_state.return_value = {"speed": 45.0, "density": 20.0}
    
    predictions = manager.get_current_state_prediction()
    
    # Should create at least one synthetic edge to prevent system crash
    assert "synthetic_edge" in predictions
    assert predictions["synthetic_edge"]["density"] == 20.0 # Arbitrary low traffic default
