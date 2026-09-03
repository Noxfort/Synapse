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
# File: src/factories/phase_factory.py
# Author: Gabriel Moraes
# Date: 2026-08-19

"""
Phase Pipeline Factory (SOLID: SRP & OCP).

Encapsulates instantiation and configuration of system lifecycle phases,
allowing open extension of new processing phases without modifying core controllers.
"""

from typing import Dict, Any, Optional

from src.domain.app_state import AppState
from src.services.fenix_service import FenixService
from src.phases.optimization_phase import OptimizationPhase
from src.phases.bootstrap_phase import BootstrapPhase
from src.phases.runtime_phase import RuntimePhase


class PhasePipelineFactory:
    """
    Factory responsible for building the phase execution pipeline.
    """

    @staticmethod
    def create_pipeline(
        app_state: AppState,
        fenix_service: FenixService,
        custom_phases: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Builds and returns the system phases pipeline dictionary.
        
        Args:
            app_state: Global application domain state.
            fenix_service: Service managing Fenix inference/training engine.
            custom_phases: Optional override or addition of custom phases.
            
        Returns:
            Dictionary mapping phase identifiers to their initialized phase handlers.
        """
        pipeline: Dict[str, Any] = {
            "optimization": OptimizationPhase(app_state),
            "bootstrap": BootstrapPhase(app_state),
            "runtime": RuntimePhase(app_state, fenix_service)
        }

        if custom_phases:
            pipeline.update(custom_phases)

        return pipeline
