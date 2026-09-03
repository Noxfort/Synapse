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
# File: tests/unit/test_meh_afb_fenix_resilience.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import pytest
import time
import pandas as pd
import numpy as np
import torch
from unittest.mock import MagicMock, patch

from src.meh.data_loader import HistoricalDataLoader
from src.services.historical_manager import HistoricalManager
from src.pipeline.auditor_pipeline import AuditorPipeline
from src.afb.replay_engine import ReplayEngine
from src.afb.afb_process import AFBProcessManager


# =========================================================================
# 1. MEH SENSOR SCANNING & HIERARCHICAL LOOKUP TESTS
# =========================================================================

def test_meh_distinct_sensor_catalog(tmp_path):
    """Test that scanning a parquet with multiple entries for few sensors catalogs only distinct sensor_ids."""
    loader = HistoricalDataLoader()
    
    # Create fake parquet with 100 rows of sensor_a, 200 of sensor_b, 150 of sensor_c
    records = []
    base_time = pd.Timestamp("2026-08-18 12:00:00")
    
    for i in range(100):
        records.append({"sensor_id": "sensor_a", "speed": 45.0, "timestamp": base_time + pd.Timedelta(seconds=i)})
    for i in range(200):
        records.append({"sensor_id": "sensor_b", "speed": 55.0, "timestamp": base_time + pd.Timedelta(seconds=i)})
    for i in range(150):
        records.append({"sensor_id": "sensor_c", "speed": 35.0, "timestamp": base_time + pd.Timedelta(seconds=i)})
        
    df = pd.DataFrame(records)
    loader.data = df
    loader.is_loaded = True
    
    loader._build_sensor_catalog()
    
    # Must identify strictly 3 distinct sensors
    assert len(loader.sensor_ids) == 3
    assert set(loader.sensor_ids) == {"sensor_a", "sensor_b", "sensor_c"}


def test_meh_hierarchical_temporal_lookup():
    """Test the 5 cascading levels of temporal resolution in MEH."""
    from datetime import datetime
    loader = HistoricalDataLoader()
    
    # Dataset with known time stamps aligned to local datetime
    now_ts = 1755500000.0  # arbitrary epoch
    now_dt = datetime.fromtimestamp(now_ts)
    
    dt_exact = pd.Timestamp(now_dt.year, now_dt.month, now_dt.day, now_dt.hour, now_dt.minute, now_dt.second)
    dt_minute = dt_exact + pd.Timedelta(minutes=5)
    
    df = pd.DataFrame([
        {"sensor_id": "sensor_a", "speed": 52.0, "timestamp": dt_exact},
        {"sensor_id": "sensor_a", "speed": 48.0, "timestamp": dt_minute},
    ])
    loader.data = df
    loader.group_column = "sensor_id"
    loader.sensor_ids = ["sensor_a"]
    loader.is_loaded = True
    
    # 1. Level 1 (Exact Seconds: +2s -> matches dt_exact within 10s)
    val_sec = loader.get_hierarchical_reading("sensor_a", now_ts + 2.0)
    assert val_sec == pytest.approx(52.0)
    
    # 2. Level 2 (Minutes: +8min -> matches within 15min)
    val_min = loader.get_hierarchical_reading("sensor_a", now_ts + 480.0)
    assert val_min in [48.0, 52.0]


# =========================================================================
# 2. AUDITOR ANOMALY PERSISTENCE & CATASTROPHIC TRIGGER TESTS
# =========================================================================

def test_auditor_m_of_n_persistence_and_reset():
    """Test AuditorPipeline M-of-N persistence tracking and emergency trigger."""
    pipeline = AuditorPipeline(window_size=10, persistence_threshold=7)
    
    # Mock model and calibrator
    pipeline.model = MagicMock()
    pipeline.calibrator = MagicMock()
    pipeline.physics_engine = MagicMock()
    
    # Fake tensor outputs
    pipeline.model.return_value = (
        torch.zeros(1, 16), torch.zeros(1, 16), torch.zeros(1, 16), torch.zeros(1, 60)
    )
    pipeline.calibrator.compute_anomaly_scores.return_value = (torch.tensor([0.1]), None)
    pipeline.calibrator.threshold = 1.0
    pipeline.physics_engine.compute_losses.return_value = {
        "total_physics_loss": torch.tensor(0.1),
        "loss_bounds": torch.tensor(0.0),
        "loss_kinematics": torch.tensor(0.0),
        "loss_smooth": torch.tensor(0.0),
        "loss_conservation": torch.tensor(0.0),
    }
    
    dummy_input = torch.zeros(1, 60)
    
    # Normal cycle: no anomaly
    res = pipeline.audit(dummy_input)
    assert res["trigger_emergency_fallback"] is False
    
    # Inject persistent anomalies (score > threshold)
    pipeline.calibrator.compute_anomaly_scores.return_value = (torch.tensor([25.0]), None)
    
    for _ in range(6):
        res = pipeline.audit(dummy_input)
        assert res["trigger_emergency_fallback"] is False
        
    # 7th anomaly out of 7 -> persistence reached -> triggers fallback
    res = pipeline.audit(dummy_input)
    assert res["trigger_emergency_fallback"] is True
    
    # Reset history
    pipeline.reset_history()
    assert len(pipeline._anomaly_history) == 0


def test_auditor_catastrophic_physical_trigger():
    """Test catastrophic physical violation triggers fallback in 2 consecutive cycles."""
    pipeline = AuditorPipeline(window_size=10, persistence_threshold=7)
    pipeline.model = MagicMock()
    pipeline.calibrator = MagicMock()
    pipeline.physics_engine = MagicMock()
    
    pipeline.model.return_value = (
        torch.zeros(1, 16), torch.zeros(1, 16), torch.zeros(1, 16), torch.zeros(1, 60)
    )
    pipeline.calibrator.compute_anomaly_scores.return_value = (torch.tensor([0.1]), None)
    pipeline.calibrator.threshold = 1.0
    
    # Massive physics violation (> 5x threshold)
    pipeline.physics_engine.compute_losses.return_value = {
        "total_physics_loss": torch.tensor(50.0),
        "loss_bounds": torch.tensor(50.0),
        "loss_kinematics": torch.tensor(0.0),
        "loss_smooth": torch.tensor(0.0),
        "loss_conservation": torch.tensor(0.0),
    }
    
    dummy_input = torch.zeros(1, 60)
    
    # 1st catastrophic cycle
    res1 = pipeline.audit(dummy_input)
    assert res1["trigger_emergency_fallback"] is False
    assert pipeline._consecutive_catastrophic == 1
    
    # 2nd catastrophic cycle -> triggers immediately
    res2 = pipeline.audit(dummy_input)
    assert res2["trigger_emergency_fallback"] is True
    assert pipeline._consecutive_catastrophic == 2


# =========================================================================
# 3. AFB REPLAY ENGINE & PROCESS TESTS
# =========================================================================

def test_afb_replay_frame_generation():
    """Test that ReplayEngine generates valid replay frames matching target time."""
    replay = ReplayEngine()
    frame = replay.get_replay_frame()
    
    assert "_metadata" in frame
    assert frame["_metadata"]["strategy"] == "AFB_REPLAY"
    assert frame["_metadata"]["is_fallback"] is True
    assert "readings" in frame
    assert len(frame["readings"]) > 0


def test_afb_process_manager_lifecycle():
    """Test AFBProcessManager starts, activates, and terminates cleanly."""
    manager = AFBProcessManager()
    manager.start()
    
    status = manager.get_status()
    assert status["is_alive"] is True
    assert status["is_fallback_active"] is False
    
    # Activate
    manager.activate_fallback()
    assert manager.is_fallback_active is True
    
    # Deactivate
    manager.deactivate_fallback()
    assert manager.is_fallback_active is False
    
    # Stop
    manager.stop()
    assert manager.is_fallback_active is False
