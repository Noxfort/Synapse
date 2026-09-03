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
# File: src/strategies/threshold_ensemble.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from collections import deque

from src.utils.logging_setup import logger


class DynamicThresholdEnsemble:
    """
    Multi-Layer Dynamic Threshold & Convergence Ensemble (SOLID SRP).
    
    Combines 4 distinct dimensions:
    - Layer D (Road Physics Context): Scales margins by lane capacity and speed limits.
    - Layer A (Adaptive 3-Sigma / Moving Z-Score): Tracks online variance per sensor.
    - Layer B (Mahalanobis Chi-Square Gate): Verifies Kalman innovation consistency.
    - Layer C (Streaming Extreme Value Theory / SPOT): Absorbs legitimate traffic shockwaves.
    
    Eliminates rigid hardcoded thresholds (such as fixed loss >= 0.15).
    """

    # Chi-Square critical value for 1 DoF at p=0.01 (99% confidence level)
    CHI2_CRITICAL_99 = 6.635

    def __init__(
        self,
        base_threshold: float = 0.20,
        window_size: int = 20,
        required_consecutive_passes: int = 3,
        max_warmup_budget: int = 25,
        spot_quantile: float = 0.95
    ):
        self.base_threshold = base_threshold
        self.window_size = window_size
        self.required_consecutive_passes = required_consecutive_passes
        self.max_warmup_budget = max_warmup_budget
        self.spot_quantile = spot_quantile

        # State tracking per sensor/node: source_id -> deque of losses
        self._loss_history: Dict[str, deque] = {}
        self._consecutive_passes: Dict[str, int] = {}
        self._spot_excesses: Dict[str, List[float]] = {}

    def compute_road_factor(self, road_context: Optional[Dict[str, Any]]) -> float:
        """
        Layer D: Calculates physical road capacity scale factor.
        Higher capacity roads (multilane expressways) naturally tolerate higher raw volume variance.
        """
        if not road_context:
            return 1.0

        lanes = int(road_context.get("lanes", 1))
        max_speed = float(road_context.get("max_speed", 13.89))  # 50 km/h baseline
        
        # Baseline reference: 1 lane @ 50 km/h (13.89 m/s)
        capacity_ratio = (lanes * max_speed) / (1.0 * 13.89)
        # Bounded between 0.8x and 2.5x to preserve mathematical stability
        return float(np.clip(capacity_ratio, 0.8, 2.5))

    def update_loss_stats(self, source_id: str, loss_val: float) -> Tuple[float, float]:
        """
        Layer A: Online moving mean and standard deviation of loss.
        """
        if source_id not in self._loss_history:
            self._loss_history[source_id] = deque(maxlen=self.window_size)
            self._spot_excesses[source_id] = []

        history = self._loss_history[source_id]
        history.append(loss_val)

        if len(history) < 2:
            return loss_val, float(self.base_threshold * 0.5)

        arr = np.array(history, dtype=np.float64)
        return float(np.mean(arr)), float(np.std(arr))

    def compute_spot_tail_margin(self, source_id: str, loss_val: float, mu: float) -> float:
        """
        Layer C: Streaming Peaks-Over-Threshold (SPOT / EVT).
        Models heavy-tailed residual excesses to adapt to legitimate traffic bursts.
        """
        if loss_val > mu:
            excess = loss_val - mu
            excesses = self._spot_excesses.get(source_id, [])
            excesses.append(excess)
            if len(excesses) > 30:
                excesses.pop(0)
            self._spot_excesses[source_id] = excesses

            if len(excesses) >= 5:
                # Generalized Pareto tail quantile approximation
                tail_q = float(np.percentile(excesses, self.spot_quantile * 100))
                return max(0.0, tail_q * 0.5)
                
        return 0.0

    def compute_dynamic_threshold(
        self,
        source_id: str,
        loss_val: float,
        road_context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Synthesizes Layers D, A, and C into an adaptive tolerance threshold tau(t).
        """
        gamma_road = self.compute_road_factor(road_context)
        mu_loss, sigma_loss = self.update_loss_stats(source_id, loss_val)
        spot_margin = self.compute_spot_tail_margin(source_id, loss_val, mu_loss)

        # Statistical envelope: base target + empirical sensor variance margin + SPOT tail margin
        stat_envelope = self.base_threshold + (0.5 * sigma_loss) + (0.5 * spot_margin)
        
        # Modulated by road physical capacity
        dynamic_tau = stat_envelope * gamma_road
        return float(np.clip(dynamic_tau, self.base_threshold, self.base_threshold * 2.5))

    def evaluate_sample(
        self,
        source_id: str,
        step_count: int,
        loss: Optional[float],
        mahalanobis_dist: Optional[float] = None,
        road_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, bool, float, str]:
        """
        Evaluates convergence and outlier state using the complete A+B+C+D ensemble.
        
        Returns:
            (is_converged: bool, is_rejected: bool, dynamic_threshold: float, reason: str)
        """
        loss_val = float(loss) if (loss is not None and not np.isnan(loss)) else 0.50
        dynamic_tau = self.compute_dynamic_threshold(source_id, loss_val, road_context)

        # Layer B: Chi-Square validation from Kalman Filter if available
        chi2_passed = True
        if mahalanobis_dist is not None and not np.isnan(mahalanobis_dist):
            chi2_stat = float(mahalanobis_dist ** 2)
            if chi2_stat > self.CHI2_CRITICAL_99:
                chi2_passed = False

        # Loss within dynamic envelope
        loss_passed = (loss_val <= dynamic_tau)

        passes = self._consecutive_passes.get(source_id, 0)

        if loss_passed and chi2_passed:
            passes += 1
            self._consecutive_passes[source_id] = passes
        else:
            # Decay consecutive passes smoothly rather than instant hard reset
            self._consecutive_passes[source_id] = max(0, passes - 1)

        # Convergence Rule: N consecutive successful passes within dynamic threshold
        if self._consecutive_passes[source_id] >= self.required_consecutive_passes:
            reason = (
                f'Ensemble Convergence: {self._consecutive_passes[source_id]} passes '
                f'(loss={loss_val:.4f} <= tau={dynamic_tau:.4f}, chi2_ok={chi2_passed})'
            )
            return True, False, dynamic_tau, reason

        # Rejection Rule: Exhausted step budget without achieving convergence
        if step_count > self.max_warmup_budget:
            reason = (
                f'Exceeded budget ({step_count}/{self.max_warmup_budget}) '
                f'without stable convergence (loss={loss_val:.4f} > tau={dynamic_tau:.4f})'
            )
            return False, True, dynamic_tau, reason

        status_str = f'Calibrando ({step_count}/{self.max_warmup_budget} | Passes: {self._consecutive_passes[source_id]}/{self.required_consecutive_passes})'
        return False, False, dynamic_tau, status_str

    def reset_sensor(self, source_id: str) -> None:
        """Clears state for a given sensor (e.g. on re-initialization)."""
        self._loss_history.pop(source_id, None)
        self._consecutive_passes.pop(source_id, None)
        self._spot_excesses.pop(source_id, None)
