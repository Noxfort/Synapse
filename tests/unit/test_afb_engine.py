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
# File: tests/unit/test_afb_engine.py
# Author: Gabriel Moraes
# Date: 2026-08-29

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


def test_replay_engine_hierarchical_resolution():
    """Test ReplayEngine hierarchical temporal resolution tiers."""
    from src.afb.replay_engine import ReplayEngine
    from datetime import datetime
    import pandas as pd

    # Mock telemetry reader returning historical samples
    mock_reader = MagicMock()
    # Create sample data for a known Tuesday 14:30:00 (timestamp: 2026-09-08 14:30:00)
    # 2026-09-08 was a Tuesday (weekday = 1)
    base_dt = datetime(2026, 9, 8, 14, 30, 0)
    mock_reader.query_telemetry_history.return_value = [
        {
            "sensor_str_id": "sensor_north",
            "sensor_int_id": 1,
            "speed": 55.0,
            "flow_rate": 350.0,
            "occupancy": 0.15,
            "sample_count": 10,
            "status": 1,
            "collected_at": base_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "scenario_name": "peak_hour"
        }
    ]

    engine = ReplayEngine(telemetry_reader=mock_reader)
    assert engine.is_loaded is True
    assert engine.source_type == "database"
    assert "sensor_north" in engine.sensor_ids

    # 1. Exact Seconds match (+/- 10s) -> Tier 1
    target_ts = base_dt.timestamp() + 5.0 # 5 seconds later
    frame_t1 = engine.get_replay_frame(target_ts)
    assert frame_t1["_metadata"]["resolution_tier"] == "tier_1_seconds"
    assert frame_t1["readings"]["sensor_north"]["speed"] == 55.0
    assert frame_t1["readings"]["sensor_north"]["confidence"] == 0.95

    # 2. Minutes match (+/- 15min) -> Tier 2
    target_ts_t2 = base_dt.timestamp() + 600.0 # 10 minutes later
    frame_t2 = engine.get_replay_frame(target_ts_t2)
    assert frame_t2["_metadata"]["resolution_tier"] == "tier_2_minutes"
    assert frame_t2["readings"]["sensor_north"]["speed"] == 55.0
    assert frame_t2["readings"]["sensor_north"]["confidence"] == 0.85

    # 3. Same Day-of-Week & Same Hour (+/- 1h, but different day) -> Tier 3
    # Next Tuesday at 14:00 (1 week later)
    target_ts_t3 = (base_dt + pd.Timedelta(days=7, minutes=-20)).timestamp()
    frame_t3 = engine.get_replay_frame(target_ts_t3)
    assert frame_t3["_metadata"]["resolution_tier"] == "tier_3_weekday_hour"
    assert frame_t3["readings"]["sensor_north"]["confidence"] == 0.75

    # 4. Fallback when empty data -> Safe Baseline
    empty_engine = ReplayEngine(data_path="/non/existent/path.parquet")
    empty_engine.is_loaded = False
    empty_engine.data = None
    empty_frame = empty_engine.get_replay_frame()
    assert empty_frame["_metadata"]["resolution_tier"] == "tier_5_safe_baseline"
    assert "sensor_fallback" in empty_frame["readings"]

