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
# File: src/strategies/node_imputation_strategy.py
# Author: Gabriel Moraes
# Date: 2026-08-18

from typing import Optional, Tuple, Any
from src.interfaces.node import INodeImputationStrategy, IPhysicsEngine
from src.strategies.kse_inertial_imputation import KseInertialImputationStrategy
from src.utils.logging_setup import logger


class HierarchicalImputationStrategy:
    """
    Implements cascading fallback imputation (SOLID SRP/OCP/DIP).
    
    Phases:
    1. Check Historical Golden DB (MEH Cascading / Hierarchical Match).
       - If non-zero historical data exists: Snap physics to truth and return historical value.
    2. Missing Data Gap / Data Hole / Zero Profile:
       - Delegates to KseInertialImputationStrategy (Last Known Good State + Kinematic Dead Reckoning).
    """

    def __init__(
        self,
        tolerance: float = 0.25,
        inertial_strategy: Optional[KseInertialImputationStrategy] = None
    ):
        self.tolerance = tolerance
        self.inertial_strategy = inertial_strategy or KseInertialImputationStrategy()

    def impute(
        self,
        source_id: str,
        timestamp: float,
        dt: float,
        physics_engine: IPhysicsEngine,
        historical_manager: Optional[Any] = None,
        fallback_steps: int = 0
    ) -> Tuple[float, str]:
        """
        Computes the imputed value and strategy description.
        Returns:
            (final_val: float, method_used: str)
        """
        historical_val = None

        # --- PHASE 1: CHECK GOLDEN DATABASE (MEH Cascading Resolution) ---
        if historical_manager is not None:
            if hasattr(historical_manager, "get_hierarchical_reading"):
                historical_val = historical_manager.get_hierarchical_reading(source_id, timestamp)
            if historical_val is None and hasattr(historical_manager, "get_exact_reading"):
                historical_val = historical_manager.get_exact_reading(source_id, timestamp, tolerance=self.tolerance)

        # Only accept MEH reading if it contains real non-zero traffic profile
        if historical_val is not None and float(historical_val) > 0.1:
            # HIT! Recorded historical truth exists for this moment.
            physics_engine.predict(dt)
            physics_engine.update(float(historical_val))
            final_val = float(historical_val)
            method_used = "MEH (Hierarchical Match)"
        else:
            # MISS or ZERO profile -> PHASE 2: KSE INERTIAL DEAD RECKONING / PHYSICS PROJECTION
            physics_engine.predict(dt)
            kse_snapshot = physics_engine.get_kinetic_snapshot()
            raw_p = float(getattr(kse_snapshot, "p", 15.0))
            if hasattr(kse_snapshot, "p") and raw_p > 0.0:
                final_val = raw_p
            else:
                final_val, _ = self.inertial_strategy.project_with_inertia(
                    source_id=source_id,
                    dt=dt,
                    physics_engine=physics_engine,
                    last_known_val=raw_p
                )
            method_used = "KSE (Physics Projection)"

        # Physical safety: Flow/Density cannot be negative
        final_val = max(0.0, final_val)

        if fallback_steps % 10 == 0:
            logger.info(f"[HierarchicalImputation] 🛡️ FALLBACK: {method_used} | Node={source_id} | Val: {final_val:.2f}")

        return final_val, method_used

