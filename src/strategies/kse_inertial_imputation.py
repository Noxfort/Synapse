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
# File: src/strategies/kse_inertial_imputation.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import numpy as np
from typing import Tuple, Optional
from src.interfaces.node import IPhysicsEngine
from src.utils.logging_setup import logger


class KseInertialImputationStrategy:
    """
    Single Responsibility: Kinematic Dead-Reckoning Imputation (SOLID SRP).
    
    Responsibilities:
    - Extrapolates missing or recovering sensor states using physics momentum.
    - Applies smooth asymptotic decay toward macroscopic road equilibrium.
    - Prevents sudden collapses to 0.0 or static flatlines during sensor gaps.
    """

    def __init__(self, baseline_density: float = 15.0, decay_rate: float = 0.05):
        self.baseline_density = baseline_density
        self.decay_rate = decay_rate

    def project_with_inertia(
        self,
        source_id: str,
        dt: float,
        physics_engine: IPhysicsEngine,
        last_known_val: Optional[float] = None
    ) -> Tuple[float, str]:
        """
        Executes dead reckoning on the physics engine with smooth asymptotic damping.
        
        Returns:
            (imputed_value: float, strategy_name: str)
        """
        clamped_dt = max(0.01, min(2.0, dt))
        physics_engine.predict(clamped_dt)

        kse_snapshot = physics_engine.get_kinetic_snapshot()
        raw_p = float(getattr(kse_snapshot, "p", self.baseline_density))
        raw_v = float(getattr(kse_snapshot, "v", 0.0))

        # Asymptotic decay toward baseline equilibrium over extended dead reckoning
        # target = baseline (15.0) or last known val
        target = float(last_known_val) if (last_known_val is not None and last_known_val > 0.0) else self.baseline_density
        damping = float(np.exp(-self.decay_rate * clamped_dt))
        
        imputed_val = (raw_p * damping) + (target * (1.0 - damping))
        
        # Physical boundary: traffic density/volume is non-negative and capped at jam density
        imputed_val = float(np.clip(imputed_val, 0.5, 125.0))

        return imputed_val, "KSE (Inertial Dead Reckoning)"
