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
# File: src/node/node_ghost_processor.py
# Author: Gabriel Moraes
# Date: 2026-08-19

import time
from typing import Dict, Any, Optional

from src.interfaces.memory import ITemporalMemory
from src.interfaces.node import (
    IPhysicsEngine,
    INodeImputationStrategy,
    INodeGhostProcessor,
    INodeSnapshotFormatter
)
from src.node.node_state import NodeState


class NodeGhostProcessor:
    """
    Executes synthetic data fallback and missing data imputation when a sensor drops out.
    Stages:
    1. Historical readiness gate check
    2. Hierarchical / Physical value imputation via strategy
    3. Memory ingestion of synthetic reading and fallback counter tracking
    4. Continuous latent neural embedding refresh
    5. Formatted synthetic telemetry generation
    """

    def __init__(
        self,
        memory: ITemporalMemory,
        agent: Any,
        physics_engine: Optional[IPhysicsEngine],
        imputation_strategy: INodeImputationStrategy,
        snapshot_formatter: INodeSnapshotFormatter,
        historical_manager: Optional[Any] = None
    ):
        self._memory = memory
        self._agent = agent
        self._physics_engine = physics_engine
        self._imputation_strategy = imputation_strategy
        self._snapshot_formatter = snapshot_formatter
        self._historical_manager = historical_manager

    def process(self, state: NodeState) -> Dict[str, Any]:
        """Coordinates missing data imputation during sensor dropouts."""
        now = time.time()
        dt = now - state.last_timestamp
        if dt > 10.0 or dt <= 0.0:
            dt = 0.1
        state.last_timestamp = now

        # Impute missing value via Strategy (MEH Cascading Match vs. KSE Physics Projection)
        final_val, method_used = self._imputation_strategy.impute(
            source_id=state.source_id,
            timestamp=now,
            dt=dt,
            physics_engine=self._physics_engine,
            historical_manager=self._historical_manager,
            fallback_steps=state.fallback_steps
        )

        state.last_value = final_val

        # Ingest synthetic reading into memory
        if self._memory is not None:
            self._memory.push([final_val])
        state.increment_fallback()

        # Keep neural embeddings fresh
        current_embedding = state.last_embedding
        if self._memory is not None and hasattr(self._agent, "predict"):
            history_np = self._memory.get_numpy()
            pred_emb = self._agent.predict(history_np)
            if pred_emb is not None:
                current_embedding = pred_emb
                state.last_embedding = current_embedding

        return self._snapshot_formatter.format_ghost_report(
            source_id=state.source_id,
            method_used=method_used,
            value=final_val,
            embedding=current_embedding,
            fallback_steps=state.fallback_steps,
            physics_engine=self._physics_engine
        )
