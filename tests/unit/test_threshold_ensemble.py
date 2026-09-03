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
# File: tests/unit/test_threshold_ensemble.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import pytest
import numpy as np
from src.strategies.threshold_ensemble import DynamicThresholdEnsemble
from src.strategies.node_validation_strategy import AdaptiveValidationStrategy


def test_dynamic_threshold_road_capacity_scaling():
    """Verify Layer D scales threshold based on lanes and speed limit."""
    ensemble = DynamicThresholdEnsemble(base_threshold=0.20)
    
    # 1 Lane @ 50 km/h (13.89 m/s) -> Factor 1.0
    factor_base = ensemble.compute_road_factor({"lanes": 1, "max_speed": 13.89})
    assert abs(factor_base - 1.0) < 0.01

    # 3 Lanes @ 100 km/h (27.78 m/s) -> Factor capped at 2.5
    factor_express = ensemble.compute_road_factor({"lanes": 3, "max_speed": 27.78})
    assert factor_express > 1.5


def test_dynamic_threshold_moving_variance_and_convergence():
    """Verify Layer A & convergence passes requirement."""
    ensemble = DynamicThresholdEnsemble(
        base_threshold=0.20,
        required_consecutive_passes=3,
        max_warmup_budget=15
    )

    # Step 1: initial loss 0.18 (pass 1)
    is_conv, is_rej, tau, _ = ensemble.evaluate_sample("sensor_1", 1, loss=0.18)
    assert not is_conv and not is_rej

    # Step 2: loss 0.17 (pass 2)
    is_conv, is_rej, tau, _ = ensemble.evaluate_sample("sensor_1", 2, loss=0.17)
    assert not is_conv and not is_rej

    # Step 3: loss 0.16 (pass 3 -> Converged!)
    is_conv, is_rej, tau, reason = ensemble.evaluate_sample("sensor_1", 3, loss=0.16)
    assert is_conv is True
    assert is_rej is False
    assert "Ensemble Convergence" in reason


def test_dynamic_threshold_mahalanobis_chi2_gating():
    """Verify Layer B rejects invalid Mahalanobis distances exceeding Chi2 critical threshold."""
    ensemble = DynamicThresholdEnsemble(base_threshold=0.20, required_consecutive_passes=2)

    # Valid loss but huge mahalanobis distance (dm=5.0 -> dm^2 = 25.0 > 6.635)
    is_conv, is_rej, tau, _ = ensemble.evaluate_sample(
        "sensor_bad",
        1,
        loss=0.10,
        mahalanobis_dist=5.0
    )
    # Consecutive passes should NOT increase
    assert ensemble._consecutive_passes.get("sensor_bad", 0) == 0


def test_dynamic_threshold_spot_tail_margin():
    """Verify Layer C accommodates extreme bursts without instant failure."""
    ensemble = DynamicThresholdEnsemble(base_threshold=0.20, spot_quantile=0.95)

    # Establish baseline losses
    for i in range(10):
        ensemble.update_loss_stats("sensor_spot", 0.15)

    # Sudden burst excess
    margin = ensemble.compute_spot_tail_margin("sensor_spot", 0.40, mu=0.15)
    # Threshold accommodates burst
    tau = ensemble.compute_dynamic_threshold("sensor_spot", 0.40)
    assert tau >= 0.20


def test_adaptive_validation_strategy_integration():
    """Verify AdaptiveValidationStrategy facade correctly integrates DynamicThresholdEnsemble."""
    strategy = AdaptiveValidationStrategy()
    
    # 3 consecutive good steps
    strategy.evaluate("sensor_live", 1, 0.12, agent=None, is_validated=False, is_rejected=False)
    strategy.evaluate("sensor_live", 2, 0.11, agent=None, is_validated=False, is_rejected=False)
    is_val, is_rej, status = strategy.evaluate("sensor_live", 3, 0.10, agent=None, is_validated=False, is_rejected=False)
    
    assert is_val is True
    assert is_rej is False
    assert status == "Active"
