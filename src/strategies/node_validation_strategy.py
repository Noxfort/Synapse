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
# File: src/strategies/node_validation_strategy.py
# Author: Gabriel Moraes
# Date: 2026-08-18

import numpy as np
from typing import Optional, Tuple, Any, Dict
from src.interfaces.node import INodeValidationStrategy
from src.strategies.threshold_ensemble import DynamicThresholdEnsemble
from src.utils.logging_setup import logger


class AdaptiveValidationStrategy:
    """
    Implements progressive online validation using Dynamic Multi-Layer Ensemble (SOLID SRP/OCP/DIP).
    
    Responsibilities:
    - Analyzes convergence loss on newly attached sensors using DynamicThresholdEnsemble (A+B+C+D).
    - Validates and freezes AI model when loss meets dynamic convergence criteria.
    - Rejects sensor if convergence is not achieved within max_warmup_steps budget.
    """

    def __init__(
        self,
        loss_convergence_threshold: float = 0.15,
        max_warmup_steps: int = 10,
        ensemble: Optional[DynamicThresholdEnsemble] = None
    ):
        self.loss_convergence_threshold = loss_convergence_threshold
        self.max_warmup_steps = max_warmup_steps
        self.ensemble = ensemble or DynamicThresholdEnsemble(
            base_threshold=loss_convergence_threshold,
            max_warmup_budget=max_warmup_steps
        )

    def evaluate(
        self,
        source_id: str,
        step_count: int,
        loss: Optional[float],
        agent: Any,
        is_validated: bool,
        is_rejected: bool,
        mahalanobis_dist: Optional[float] = None,
        road_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, bool, str]:
        """
        Evaluates convergence state using multi-layer dynamic threshold ensemble.
        Returns:
            (is_validated: bool, is_rejected: bool, status_description: str)
        """
        if is_rejected:
            return False, True, "Rejected"

        if is_validated:
            return True, False, "Active"

        loss_val = float(loss) if (loss is not None and not np.isnan(loss)) else 1.0

        # Layer B / Chi2 check from Kalman filter if available
        chi2_rejected = False
        if mahalanobis_dist is not None and np.asarray(mahalanobis_dist).size > 0:
            try:
                dm = float(mahalanobis_dist)
                if (dm ** 2) > self.ensemble.CHI2_CRITICAL_99:
                    chi2_rejected = True
            except (ValueError, TypeError):
                pass

        # Dynamic Threshold calculation from Ensemble (Layers D, A, B, C)
        dynamic_tau = self.ensemble.compute_dynamic_threshold(source_id, loss_val, road_context)
        effective_threshold = max(self.loss_convergence_threshold, dynamic_tau)

        if not chi2_rejected and loss_val < effective_threshold:
            if hasattr(agent, "freeze"):
                agent.freeze()
            logger.info(
                f"[AdaptiveValidation] ✅ Node/Sensor '{source_id}' converged at sample {step_count} "
                f"(loss={loss_val:.4f} < {effective_threshold:.4f}). Validated, Frozen & Active!"
            )
            return True, False, "Active"

        if step_count > self.max_warmup_steps:
            logger.warning(
                f"[AdaptiveValidation] 🚫 Node/Sensor '{source_id}' rejected after {step_count} samples "
                f"without convergence (loss={loss_val:.4f} >= {effective_threshold:.4f})."
            )
            return False, True, "Rejected"

        status_str = f"Calibrando ({step_count}/{self.max_warmup_steps})"
        return False, False, status_str

