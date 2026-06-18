import pytest
import math
from src.afb.models import SensorReading, NO_DATA
from src.afb.strategies import TrimmedMeanStrategy, KalmanLiteStrategy, LastKnownGoodStrategy

def test_trimmed_mean_strategy():
    strategy = TrimmedMeanStrategy()
    
    # Needs at least 3
    assert strategy.can_handle(3) is True
    assert strategy.can_handle(2) is False
    
    # Provide 5 readings. 
    # Values: 10 (low outlier), 50, 50, 55, 100 (high outlier)
    # Trimmed should use: 50, 50, 55 (Mean: 51.66)
    readings = [
        SensorReading("S1", 10.0, 0.9),
        SensorReading("S2", 50.0, 0.9),
        SensorReading("S3", 50.0, 0.9),
        SensorReading("S4", 100.0, 0.9),
        SensorReading("S5", 55.0, 0.9),
    ]
    
    result = strategy.fuse(readings)
    
    assert result.strategy == "trimmed_mean"
    assert result.source_count == 5
    assert 51.0 < result.value < 52.0
    
    # Test confidence calculation (should be high because 50, 50, 55 have low variance)
    assert result.confidence > 0.8

def test_kalman_lite_strategy():
    strategy = KalmanLiteStrategy(process_noise=0.5)
    
    assert strategy.can_handle(2) is True
    assert strategy.can_handle(3) is False
    
    # Simulate a time series of noisy readings mapping to the same metric key
    # True value is around 100.
    series = [90.0, 110.0, 95.0, 105.0, 100.0]
    
    for val in series:
        result = strategy.fuse(
            [SensorReading("S1", val, 0.8)], 
            metric_key="edge_1"
        )
        
    # After filtering the series, the estimate should converge closer to 100
    assert result.strategy == "kalman_lite"
    assert 95.0 <= result.value <= 105.0

def test_last_known_good_strategy():
    strategy = LastKnownGoodStrategy(decay_rate=0.1) # Faster decay for test
    
    assert strategy.can_handle(0) is True
    assert strategy.can_handle(1) is False
    
    # Step 1: No data, no cache -> Should return NO_DATA
    result = strategy.fuse([], metric_key="edge_1", meh_baseline=20.0)
    assert result == NO_DATA
    
    # Cache a last known good value (e.g. 50 km/h)
    strategy.update_cache("edge_1", 50.0)
    
    import time
    from unittest.mock import patch
    
    # Test decay over time. Baseline is 20. Last is 50.
    # At T + 0: Should remain close to 50
    with patch('time.time', return_value=time.time()):
        r1 = strategy.fuse([], metric_key="edge_1", meh_baseline=20.0)
        assert math.isclose(r1.value, 50.0, rel_tol=1e-5)  # e^0 = 1, decayed = 20 + 30*1 = 50
        assert math.isclose(r1.confidence, 0.7, rel_tol=1e-5)  # Max confidence
    
    # At T + 10s: Should decay towards 20
    # exp(-0.1 * 10) = exp(-1) = 0.367
    # decayed = 20 + 30*0.367 = 31.0
    with patch('time.time', return_value=time.time() + 10.0):
        r2 = strategy.fuse([], metric_key="edge_1", meh_baseline=20.0)
        assert 30.0 < r2.value < 32.0   
        assert r2.confidence < 0.7 # Confidence must drop
