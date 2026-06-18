import pytest
import math
from unittest.mock import MagicMock
from src.afb.afb_engine import AFBEngine
from src.afb.models import SensorReading, NO_DATA

def test_afb_engine_strategy_cascade():
    """Test the AFB Engine correctly cascades through strategies based on sensor count."""
    engine = AFBEngine()
    
    # Cascade 1: 3 Sensors -> Should trigger TrimmedMean
    readings_3 = [
        SensorReading("S1", 50.0, 0.9),
        SensorReading("S2", 52.0, 0.9),
        SensorReading("S3", 48.0, 0.9)
    ]
    res_trim = engine.fuse(readings_3)
    assert res_trim.strategy == "trimmed_mean"
    assert engine._strategy_hits["trimmed_mean"] == 1
    
    # Cascade 2: 2 Sensors -> Should trigger KalmanLite
    readings_2 = [
        SensorReading("S1", 50.0, 0.9),
        SensorReading("S2", 52.0, 0.9)
    ]
    res_kalman = engine.fuse(readings_2)
    assert res_kalman.strategy == "kalman_lite"
    assert engine._strategy_hits["kalman_lite"] == 1
    
    # Cascade 3: 0 Sensors -> Should trigger LastKnownGood
    # To test LastKnownGood, it needs a cached value, which is populated
    # automatically when TrimmedMean or KalmanLite succeed.
    res_lkg = engine.fuse([])
    assert res_lkg.strategy == "last_known_good"
    assert engine._strategy_hits["last_known_good"] == 1

def test_afb_engine_nan_filtering():
    """Test that the engine filters out NaN values before fusion."""
    engine = AFBEngine()
    
    readings = [
        SensorReading("S1", 50.0, 0.9),
        SensorReading("S2", math.nan, 0.9), # Should be dropped
    ]
    
    # If NaN is dropped, it becomes 1 sensor -> KalmanLite
    res = engine.fuse(readings)
    assert res.strategy == "kalman_lite"
    assert res.source_count == 1 # Only valid S1 was used

def test_afb_engine_yields_to_meh():
    """Test engine yields to MEH when no strategies can handle the input."""
    # Create engine with an empty strategy list
    engine = AFBEngine()
    engine._strategies.clear()
    
    result = engine.fuse([SensorReading("S1", 50.0, 0.9)])
    
    # Should return NO_DATA (Level 3 degrade)
    assert result == NO_DATA
    assert result.is_degraded is True
