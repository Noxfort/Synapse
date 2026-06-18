# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2025 Noxfort Systems
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
# File: src/factories/engine_component_factory.py
# Author: Gabriel Moraes
# Date: 2026-04-27
#
# SOLID Refactoring:
# - [SRP] Extracted from _EngineWorker.initialize() — this class is
#   responsible ONLY for constructing the runtime engine components.
# - [DIP] All consumers depend on the EngineComponents abstraction
#   (NamedTuple), not on concrete class imports.

from typing import NamedTuple, TYPE_CHECKING

from src.domain.app_state import AppState

if TYPE_CHECKING:
    from src.engine.inference_engine import InferenceEngine
    from src.workers.xai_worker import XAIWorker
    from src.services.linguist_service import LinguistService


class EngineComponents(NamedTuple):
    """Typed container for all pre-built engine subsystems."""
    inference_engine: 'InferenceEngine'
    xai_worker: 'XAIWorker'
    linguist_service: 'LinguistService'


class EngineComponentFactory:
    """
    Factory for the Runtime Engine subsystem graph.

    SOLID Roles:
    - [SRP] Single purpose: construct and wire engine components.
    - [DIP] Consumers receive an EngineComponents tuple — they never
      import or instantiate concrete subsystem classes themselves.

    This class was extracted from the 70-line body of
    _EngineWorker.initialize() in runtime_launcher.py.
    """

    def __init__(self, app_state: AppState):
        self.app_state = app_state

    def build(self) -> EngineComponents:
        """
        Constructs all engine components and returns them as a typed tuple.

        Build order mirrors the original _EngineWorker.initialize():
          1. Shared dependencies (Ingestion, Graph, Historical, Enricher)
          2. XAI subsystem (XAIWorker + XAIManager)
          3. Neural core (InferenceEngine)
          4. Linguist subsystem (AgentFactory + LinguistService)
        """
        # --- Lazy imports (keeps module lightweight at import time) ---
        from src.engine.inference_engine import InferenceEngine
        from src.workers.ingestion_worker import IngestionWorker
        from src.managers.graph_manager import GraphManager
        from src.services.historical_manager import HistoricalManager
        from src.services.linguist_service import LinguistService
        from src.managers.xai_manager import XAIManager
        from src.workers.xai_worker import XAIWorker
        from src.services.semantic_enricher import SemanticEnricher
        from src.factories.agent_factory import AgentFactory

        # ── 1. Shared Dependencies ──────────────────────────────────────
        ingestion = IngestionWorker(self.app_state)
        graph_manager = GraphManager(self.app_state)
        historical_manager = HistoricalManager(self.app_state)
        enricher = SemanticEnricher(self.app_state)

        # ── 2. XAI Subsystem ────────────────────────────────────────────
        xai_worker = XAIWorker(model_config={"feature_dim": 4})
        xai_manager = XAIManager(xai_worker, enricher)

        # ── 3. Neural Core (InferenceEngine V4) ─────────────────────────
        inference_engine = InferenceEngine(
            self.app_state,
            ingestion,
            graph_manager,
            historical_manager,
            xai_manager
        )

        # ── 4. Linguist Subsystem ───────────────────────────────────────
        config = getattr(self.app_state, 'config', {})
        agent_factory = AgentFactory(config)
        linguist_service = LinguistService(self.app_state, ingestion, agent_factory)

        return EngineComponents(
            inference_engine=inference_engine,
            xai_worker=xai_worker,
            linguist_service=linguist_service,
        )
