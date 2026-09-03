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
# File: src/engine/gating_policy.py
# Author: Gabriel Moraes
# Date: 2026-08-30

import logging
from src.domain.app_state import AppState
from src.domain.entities import SourceStatus
from src.interfaces.engine import GatingEvaluation, IGatingPolicy


class SourceGatingPolicy(IGatingPolicy):
    """
    Evaluates source readiness, quarantine status, and determines whether
    real-time neural inference should proceed or remain frozen.
    
    SOLID Responsibility:
    - [SRP] Exclusively encapsulates source health, gating rules (1 Local + 1 Global min),
      and Linguist check scheduling.
    - [OCP] Gating conditions or source thresholds can be adjusted or subclassed without
      touching the InferenceEngine orchestrator.
    """

    def __init__(self, linguist_throttle_cycles: int = 5):
        self.linguist_throttle_cycles = linguist_throttle_cycles
        self.logger = logging.getLogger(__name__)

    def evaluate(self, app_state: AppState, cycle_count: int) -> GatingEvaluation:
        """
        Evaluates the current state of all data sources in AppState.
        """
        all_sources = app_state.get_all_data_sources()
        has_quarantine = any(s.status == SourceStatus.QUARANTINE for s in all_sources)
        
        active_local = sum(1 for s in all_sources if s.is_local and s.status == SourceStatus.ACTIVE)
        active_global = sum(1 for s in all_sources if not s.is_local and s.status == SourceStatus.ACTIVE)
        
        is_frozen = not (active_local >= 1 and active_global >= 1)
        
        # Linguist trigger: immediate on quarantine, throttled otherwise
        should_trigger_linguist = has_quarantine or (cycle_count % self.linguist_throttle_cycles == 0)
        
        return GatingEvaluation(
            is_frozen=is_frozen,
            should_trigger_linguist=should_trigger_linguist,
            active_local=active_local,
            active_global=active_global,
            has_quarantine=has_quarantine
        )

    def log_frozen_status(self, eval_result: GatingEvaluation, cycle_count: int) -> None:
        """Logs throttling/waiting status periodically when system is frozen."""
        if eval_result.is_frozen and (cycle_count % 5 == 1):
            self.logger.info(
                f"[GatingPolicy] ❄️ Operação em tempo real CONGELADA. "
                f"Aguardando validação semântico-física pelo LinguistAgent "
                f"(Ativos: {eval_result.active_local} Local, {eval_result.active_global} Global | Mínimo: 1 Local + 1 Global)."
            )
