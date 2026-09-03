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
# File: src/factories/engine_component_factory.py
# Author: Gabriel Moraes
# Date: 2026-08-30

from typing import NamedTuple, TYPE_CHECKING

from src.domain.app_state import AppState

if TYPE_CHECKING:
    from src.engine.inference_engine import InferenceEngine
    from src.engine.data_flow_router import DataFlowRouter
    from src.workers.xai_worker import XAIWorker
    from src.managers.xai_manager import XAIManager
    from src.services.linguist_service import LinguistService
    from src.workers.ingestion_worker import IngestionWorker
    from src.managers.graph_manager import GraphManager
    from src.services.historical_manager import HistoricalManager


class EngineComponents(NamedTuple):
    """Typed container for all pre-built engine subsystems."""
    inference_engine: 'InferenceEngine'
    data_flow_router: 'DataFlowRouter'
    xai_worker: 'XAIWorker'
    xai_manager: 'XAIManager'
    linguist_service: 'LinguistService'
    ingestion: 'IngestionWorker'
    graph_manager: 'GraphManager'
    historical_manager: 'HistoricalManager'


class EngineComponentFactory:
    """
    Factory for the Runtime Engine subsystem graph.

    SOLID Roles:
    - [SRP] Single purpose: construct and wire engine components.
    - [DIP] Consumers receive an EngineComponents tuple — they never
      import or instantiate concrete subsystem classes themselves.
    """

    def __init__(self, app_state: AppState):
        self.app_state = app_state

    def build(self) -> EngineComponents:
        """
        Constructs all engine components and returns them as a typed tuple.
        """
        # --- Lazy imports (keeps module lightweight at import time) ---
        from src.engine.inference_engine import InferenceEngine
        from src.engine.data_flow_router import DataFlowRouter
        from src.workers.ingestion_worker import IngestionWorker
        from src.managers.graph_manager import GraphManager
        from src.services.historical_manager import HistoricalManager
        from src.services.linguist_service import LinguistService
        from src.managers.xai_manager import XAIManager
        from src.workers.xai_worker import XAIWorker
        from src.services.semantic_enricher import SemanticEnricher
        from src.factories.agent_factory import AgentFactory

        from src.engine.neural_factory import NeuralFactory
        from src.engine.snapshot_builder import SnapshotBuilder
        from src.engine.cycle_processor import CycleProcessor
        from src.engine.gating_policy import SourceGatingPolicy
        from src.engine.forecast_imputer import ForecastImputer

        # ── 1. Shared Dependencies ──────────────────────────────────────
        ingestion = IngestionWorker(self.app_state)
        graph_manager = GraphManager(self.app_state)
        historical_manager = HistoricalManager(self.app_state)
        enricher = SemanticEnricher(self.app_state)

        # ── 2. Data Flow Router (Fast Path) ─────────────────────────────
        data_flow_router = DataFlowRouter(self.app_state, graph_manager)
        ingestion.data_ready.connect(data_flow_router.handle_data_flow)

        # ── 3. XAI Subsystem ────────────────────────────────────────────
        xai_worker = XAIWorker(model_config={"feature_dim": 4})
        xai_manager = XAIManager(xai_worker, enricher)

        # ── 4. Neural Core (Pure Orchestrator) ──────────────────────────
        neural_factory = NeuralFactory()
        device = neural_factory.get_device()
        agents = neural_factory.build_all(self.app_state)

        snapshot_builder = SnapshotBuilder(
            app_state=self.app_state,
            graph_manager=graph_manager,
            embedding_dim=32
        )

        processor = CycleProcessor(
            app_state=self.app_state,
            device=device,
            coordinator=agents.get('coordinator'),
            fuser=agents.get('fuser'),
            auditor=agents.get('auditor'),
            xai_manager=xai_manager,
            graph_manager=graph_manager
        )

        gating_policy = SourceGatingPolicy(linguist_throttle_cycles=5)
        forecast_imputer = ForecastImputer()

        inference_engine = InferenceEngine(
            app_state=self.app_state,
            graph_manager=graph_manager,
            snapshot_builder=snapshot_builder,
            processor=processor,
            gating_policy=gating_policy,
            forecast_imputer=forecast_imputer,
            ingestion=ingestion,
        )

        # ── 5. Linguist Subsystem ───────────────────────────────────────
        config = getattr(self.app_state, 'config', {})
        agent_factory = AgentFactory(config)
        linguist_service = LinguistService(self.app_state, ingestion, agent_factory)

        return EngineComponents(
            inference_engine=inference_engine,
            data_flow_router=data_flow_router,
            xai_worker=xai_worker,
            xai_manager=xai_manager,
            linguist_service=linguist_service,
            ingestion=ingestion,
            graph_manager=graph_manager,
            historical_manager=historical_manager,
        )
