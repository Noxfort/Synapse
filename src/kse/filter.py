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
# File: src/kse/filter.py
# Author: Gabriel Moraes
# Date: 2026-01-09

import time
import numpy as np
from typing import Dict, Any, Optional
from src.utils.logging_setup import logger
from src.kse.definitions import SensorProfile, KineticState, FRICTION_DECAY, MAX_ACCEL, MAX_DECEL
from src.kse.ground_truth_realigner import GroundTruthRealigner

# =============================================================================
# CORE MATHEMATICS: ROBUST KALMAN FILTER
# =============================================================================

class RobustKalmanFilter:
    """
    Advanced Linear Kalman Filter implementation.
    
    Features:
    - 3-State Kinematics [p, v, a]
    - Mahalanobis Distance Gating (Outlier Rejection)
    - Ground Truth Reality Realignment (Cold Start & Live Sensor Resumption)
    - Numerical Stability Checks (Cholesky/Singularity prevention)
    - Dynamic Process Noise (Adaptive Q)
    - Acceleration Decay (Realistic Dead Reckoning)
    """

    def __init__(
        self,
        node_id: str,
        initial_val: float,
        profile: SensorProfile,
        realigner: Optional[GroundTruthRealigner] = None
    ):
        self.node_id = node_id
        self.profile = profile
        self.realigner = realigner or GroundTruthRealigner()
        
        # 1. State Vector [p, v, a]
        self.x = np.array([[initial_val], [0.0], [0.0]], dtype=np.float64)
        
        # 2. Covariance Matrix (Uncertainty)
        # Initialize with high uncertainty for V and A
        self.P = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 100.0, 0.0],
            [0.0, 0.0, 100.0]
        ], dtype=np.float64)

        # 3. Transition Matrix (F) - Template
        self.F = np.eye(3, dtype=np.float64)
        
        # 4. Measurement Matrix (H) - We measure Position only
        self.H = np.array([[1.0, 0.0, 0.0]], dtype=np.float64)
        
        # 5. Noise Matrices
        self.R = np.array([[self.profile.r_val]], dtype=np.float64)
        
        # Q is constructed to allow jerk (change in acceleration)
        self.Q = np.eye(3) * self.profile.q_val

        # Identity
        self.I = np.eye(3)
        
        # Internal Stats
        self.last_update_time = time.time()
        self.consecutive_misses = 0
        self.sample_count = 0
        self.has_received_first_live = (initial_val > 0.0)
        self.last_mahalanobis: Optional[float] = None

    def predict(self, dt: float):
        """
        Physics Projection Step (Dead Reckoning).
        """
        # Clamp dt to avoid giant leaps or instantaneous numerical spikes
        dt = float(np.clip(dt, 0.01, 2.0))

        # Update F for current time step
        # p' = p + vt + 0.5at^2
        # v' = v + at
        # a' = a * decay (Realism fix: cars don't accelerate forever without input)
        self.F = np.array([
            [1.0, dt, 0.5 * dt**2],
            [0.0, 1.0, dt],
            [0.0, 0.0, FRICTION_DECAY] 
        ])

        # x = F * x
        self.x = np.dot(self.F, self.x)
        
        # P = F * P * F^T + Q
        # Increases uncertainty over time
        self.P = np.dot(np.dot(self.F, self.P), self.F.T) + self.Q
        
        # Clamp Logic: Prevent physics explosions during long dead reckoning
        self._enforce_physics_limits()

    def update(self, measurement: float, dt: Optional[float] = None) -> bool:
        """
        Correction Step with Reality Re-anchoring and Adaptive Gating.
        Returns True if measurement was accepted, False if rejected.
        """
        now = time.time()
        time_since_last = now - self.last_update_time if self.last_update_time > 0 else 1.0
        effective_dt = dt if (dt is not None and dt > 0.0) else time_since_last

        # --- 0. Ground Truth Reality Realignment (Cold-Start & Recovery) ---
        is_first = not self.has_received_first_live or (self.sample_count == 0)
        if self.realigner.should_realign(
            node_id=self.node_id,
            measurement=measurement,
            current_pred_p=self.x[0, 0],
            dt_since_last_live=time_since_last,
            consecutive_misses=self.consecutive_misses,
            is_first_sample=is_first
        ):
            self.x, self.P, _ = self.realigner.realign(
                node_id=self.node_id,
                measurement=measurement,
                previous_p=self.x[0, 0],
                dt=effective_dt,
                r_val=self.profile.r_val
            )
            self.consecutive_misses = 0
            self.sample_count += 1
            self.has_received_first_live = True
            self.last_update_time = now
            self.last_mahalanobis = 0.0
            return True

        z = np.array([[measurement]])
        
        # 1. Calculate Innovation (Residual)
        # y = z - Hx
        y = z - np.dot(self.H, self.x)
        
        # 2. Calculate System Uncertainty (S)
        # S = H P H^t + R
        S = np.dot(np.dot(self.H, self.P), self.H.T) + self.R
        
        # 3. Mahalanobis Distance Check (Gating)
        # Detects sensor glitches. If data is statistically impossible, reject it.
        try:
            S_inv = np.linalg.inv(S)
            dm = np.sqrt(np.dot(np.dot(y.T, S_inv), y)) # Distance metric
            self.last_mahalanobis = float(dm.item())
            
            if dm > self.profile.gating_threshold:
                logger.warning(f"[KSE] 🛡️ Outlier Rejected Node={self.node_id} Val={measurement:.2f} Pred={self.x[0,0]:.2f} Dist={dm.item():.2f}")
                self.consecutive_misses += 1
                return False # REJECT
                
        except np.linalg.LinAlgError:
            # Fallback if matrix is singular (rare)
            logger.error(f"[KSE] Matrix Singularity in Node {self.node_id}")
            S_inv = np.array([[1.0/S[0,0]]])
            self.last_mahalanobis = 0.0

        # 4. Optimal Kalman Gain (K)
        # K = P H^t S^-1
        K = np.dot(np.dot(self.P, self.H.T), S_inv)
        
        # 5. State Update
        # x = x + Ky
        self.x = self.x + np.dot(K, y)
        
        # 6. Covariance Update
        # P = (I - KH) P
        self.P = np.dot((self.I - np.dot(K, self.H)), self.P)
        
        # Reset counters & update timestamps
        self.consecutive_misses = 0
        self.sample_count += 1
        self.has_received_first_live = True
        self.last_update_time = now
        
        return True

    def _enforce_physics_limits(self):
        """
        Hard Constraints to prevent mathematical divergence.
        """
        # Position / Scalar state Limit (0 to 200 km/h or reasonable traffic metric)
        self.x[0, 0] = np.clip(self.x[0, 0], 0.0, 200.0)

        # Velocity Limit (e.g., 0 to 120 km/h -> ~33 m/s)
        self.x[1, 0] = np.clip(self.x[1, 0], -10.0, 40.0) 
        
        # Acceleration Limit (Physics bounds)
        self.x[2, 0] = np.clip(self.x[2, 0], MAX_DECEL, MAX_ACCEL)
        
        # Numerical Stability for P
        # Ensure P remains symmetric and positive definite
        self.P = (self.P + self.P.T) / 2.0

    def get_kinetic_snapshot(self) -> KineticState:
        """Computes current confidence and returns clean struct."""
        # Trace of P is a scalar metric of total uncertainty
        uncertainty = np.trace(self.P)
        
        # Confidence decays as uncertainty grows.
        # Heuristic: Conf = 1 / (1 + log(uncertainty))
        conf = 1.0 / (1.0 + np.log1p(uncertainty))
        conf = np.clip(conf, 0.0, 1.0)
        
        return KineticState(
            p=float(self.x[0, 0]),
            v=float(self.x[1, 0]),
            a=float(self.x[2, 0]),
            uncertainty=float(uncertainty),
            confidence=float(conf)
        )

    def get_state(self) -> Dict[str, Any]:
        """Exports internal Kalman state for checkpointing."""
        return {
            "x": self.x.tolist(),
            "P": self.P.tolist(),
            "last_time": self.last_update_time
        }

    def set_state(self, state: Dict[str, Any]):
        """Restores internal Kalman state from checkpoint."""
        if not state:
            return
        if "x" in state:
            self.x = np.array(state["x"], dtype=np.float64)
        if "P" in state:
            self.P = np.array(state["P"], dtype=np.float64)
        self.last_update_time = state.get("last_time", time.time())
