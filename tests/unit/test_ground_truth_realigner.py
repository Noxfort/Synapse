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
# File: tests/unit/test_ground_truth_realigner.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import pytest
import numpy as np
from src.kse.ground_truth_realigner import GroundTruthRealigner
from src.kse.filter import RobustKalmanFilter
from src.kse.definitions import SensorProfile


def test_ground_truth_realigner_cold_start():
    """Verify cold start (sample 1) triggers reality anchor instead of outlier rejection."""
    realigner = GroundTruthRealigner()
    assert realigner.should_realign("node_1", measurement=75.0, current_pred_p=0.0, dt_since_last_live=0.1, consecutive_misses=0, is_first_sample=True) is True

    new_x, new_P, delta = realigner.realign("node_1", measurement=75.0, previous_p=0.0, dt=0.1, r_val=2.0)
    assert new_x[0, 0] == 75.0
    assert new_P[0, 0] == 2.0
    assert delta == 75.0


def test_robust_kalman_filter_cold_start_high_value():
    """Verify RobustKalmanFilter initialized at 0.0 accepts high first measurement immediately."""
    profile = SensorProfile(name="Vision", r_val=2.0, q_val=0.1, gating_threshold=3.0)
    kf = RobustKalmanFilter(node_id="camera_1", initial_val=0.0, profile=profile)

    # First real measurement: 80.0 km/h (would be 40+ sigma away from 0.0 if not for GroundTruthRealigner)
    accepted = kf.update(measurement=80.0, dt=0.1)
    assert accepted is True
    assert kf.x[0, 0] == 80.0
    assert kf.sample_count == 1
    assert kf.consecutive_misses == 0


def test_ground_truth_realigner_after_long_gap():
    """Verify sensor data resumption after dead-reckoning gap re-anchors properly."""
    profile = SensorProfile(name="Loop", r_val=2.0, q_val=0.1, gating_threshold=3.0)
    kf = RobustKalmanFilter(node_id="loop_1", initial_val=40.0, profile=profile)

    # Simulate dead reckoning for 5 seconds
    kf.predict(5.0)

    # Fresh ground truth arrives: 30.0
    accepted = kf.update(measurement=30.0, dt=5.0)
    assert accepted is True
    assert kf.x[0, 0] == 30.0
