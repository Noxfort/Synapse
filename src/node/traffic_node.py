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
# File: src/node/traffic_node.py
# Author: Gabriel Moraes
# Date: 2026-08-19

import numpy as np
from typing import Optional, Dict, Any, Callable

# Domain Contracts & Entities
from src.domain.entities import SourceStatus
from src.interfaces.memory import ITemporalMemory
from src.interfaces.node import (
    IPhysicsEngine,
    INodeValidationStrategy,
    INodeImputationStrategy,
    INodeStepProcessor,
    INodeGhostProcessor,
    INodeStatusNotifier,
    INodeSnapshotFormatter
)
from src.strategies.node_validation_strategy import AdaptiveValidationStrategy
from src.strategies.node_imputation_strategy import HierarchicalImputationStrategy
from src.node.node_state import NodeState
from src.node.node_status_notifier import NodeStatusNotifier
from src.node.node_snapshot_formatter import NodeSnapshotFormatter
from src.node.node_step_processor import NodeStepProcessor
from src.node.node_ghost_processor import NodeGhostProcessor
from src.utils.logging_setup import logger


class TrafficNode:
    """
    Represents a single traffic sensing node (e.g., an intersection or camera).
    
    Pure Orchestrator / Facade Architecture (SOLID Compliant):
    - [SRP] Pure facade coordinating state, real-step ingestion, and ghost-step imputation.
    - [OCP] Pluggable validation, imputation, and processing pipeline delegates.
    - [LSP] Conforms strictly to domain protocols without defensive inspection.
    - [ISP] Segregated status notification callback replaces bloated manager dependencies.
    - [DIP] Depends entirely on abstract domain protocols and injected processors.
    """

    def __init__(
        self,
        source_id: str,
        memory: Optional[ITemporalMemory] = None,
        agent: Optional[Any] = None,
        historical_manager: Optional[Any] = None,
        physics_engine: Optional[IPhysicsEngine] = None,
        validation_strategy: Optional[INodeValidationStrategy] = None,
        imputation_strategy: Optional[INodeImputationStrategy] = None,
        on_status_change: Optional[Callable[[str, SourceStatus], None]] = None,
        graph_manager: Optional[Any] = None,
        state: Optional[NodeState] = None,
        step_processor: Optional[INodeStepProcessor] = None,
        ghost_processor: Optional[INodeGhostProcessor] = None,
        status_notifier: Optional[INodeStatusNotifier] = None,
        snapshot_formatter: Optional[INodeSnapshotFormatter] = None,
        **kwargs: Any
    ):
        self.source_id = source_id
        self._memory = memory
        self._agent = agent
        self._historical_manager = historical_manager
        self._physics_engine = physics_engine

        # State Holder (SRP)
        output_dim = getattr(agent, "output_dim", 32) if agent else 32
        self.state: NodeState = state or NodeState(
            source_id=source_id,
            last_embedding=np.zeros(output_dim)
        )

        # Strategies
        self.validation_strategy: INodeValidationStrategy = (
            validation_strategy or AdaptiveValidationStrategy(
                loss_convergence_threshold=0.15,
                max_warmup_steps=10
            )
        )
        self.imputation_strategy: INodeImputationStrategy = (
            imputation_strategy or HierarchicalImputationStrategy(tolerance=0.25)
        )

        # Output Formatter & Notifier (SRP/ISP)
        self.snapshot_formatter: INodeSnapshotFormatter = (
            snapshot_formatter or NodeSnapshotFormatter()
        )
        self.status_notifier: INodeStatusNotifier = (
            status_notifier or NodeStatusNotifier(
                on_status_change=on_status_change,
                graph_manager=graph_manager
            )
        )

        # Sub-Processors (Pipelines)
        self._step_processor: INodeStepProcessor = (
            step_processor or NodeStepProcessor(
                memory=self._memory,
                agent=self._agent,
                physics_engine=self._physics_engine,
                validation_strategy=self.validation_strategy,
                status_notifier=self.status_notifier,
                snapshot_formatter=self.snapshot_formatter
            )
        )
        self._ghost_processor: INodeGhostProcessor = (
            ghost_processor or NodeGhostProcessor(
                memory=self._memory,
                agent=self._agent,
                physics_engine=self._physics_engine,
                imputation_strategy=self.imputation_strategy,
                snapshot_formatter=self.snapshot_formatter,
                historical_manager=self._historical_manager
            )
        )

    # --- Properties for Encapsulation & Backward Compatibility ---

    @property
    def memory(self) -> Optional[ITemporalMemory]:
        return self._memory

    @property
    def agent(self) -> Optional[Any]:
        return self._agent

    @property
    def kse(self) -> Optional[IPhysicsEngine]:
        return self._physics_engine

    @property
    def is_ready(self) -> bool:
        """Returns True if the node is validated or has sufficient temporal warm-up."""
        return self.state.is_validated or self._step_processor.is_ready()

    @property
    def is_validated(self) -> bool:
        return self.state.is_validated

    @is_validated.setter
    def is_validated(self, val: bool):
        self.state.is_validated = val

    @property
    def is_rejected(self) -> bool:
        return self.state.is_rejected

    @is_rejected.setter
    def is_rejected(self, val: bool):
        self.state.is_rejected = val

    @property
    def steps_processed(self) -> int:
        return self.state.steps_processed

    @steps_processed.setter
    def steps_processed(self, val: int):
        self.state.steps_processed = val

    @property
    def fallback_steps(self) -> int:
        return self.state.fallback_steps

    @fallback_steps.setter
    def fallback_steps(self, val: int):
        self.state.fallback_steps = val

    @property
    def last_value(self) -> float:
        return self.state.last_value

    @last_value.setter
    def last_value(self, val: float):
        self.state.last_value = val

    @property
    def last_timestamp(self) -> float:
        return self.state.last_timestamp

    @last_timestamp.setter
    def last_timestamp(self, val: float):
        self.state.last_timestamp = val

    @property
    def last_embedding(self) -> np.ndarray:
        return self.state.last_embedding

    @last_embedding.setter
    def last_embedding(self, val: np.ndarray):
        self.state.last_embedding = val

    # --- Pure Facade Actions ---

    def step(self, value: float) -> Dict[str, Any]:
        """
        Coordinates the ingestion and processing of a ground-truth sensor reading.
        Delegates completely to NodeStepProcessor.
        """
        return self._step_processor.process(value, self.state)

    def ghost_step(self) -> Dict[str, Any]:
        """
        Coordinates missing data imputation during sensor dropouts.
        Delegates completely to NodeGhostProcessor.
        """
        return self._ghost_processor.process(self.state)

    def tick(self) -> None:
        """
        Cycle hook: triggers synthetic imputation if no sensor data was received during this cycle.
        """
        if not self.state.updated_this_cycle:
            self.ghost_step()
        self.state.reset_cycle()

    # --- State Checkpoint & Persistence Facade ---

    def get_state(self) -> Dict[str, Any]:
        """Exports the full internal state via clean component delegation."""
        return {
            "source_id": self.source_id,
            "steps_processed": self.state.steps_processed,
            "memory_buffer": self._memory.get_state() if self._memory is not None and hasattr(self._memory, "get_state") else [],
            "agent_state": self._agent.get_state() if self._agent is not None and hasattr(self._agent, "get_state") else {},
            "kse_state": self._physics_engine.get_state() if self._physics_engine is not None and hasattr(self._physics_engine, "get_state") else {}
        }

    def set_state(self, state: Dict[str, Any]) -> None:
        """Restores state checkpoints via component delegation."""
        if not isinstance(state, dict):
            return

        try:
            self.state.from_dict(state)

            if "memory_buffer" in state and self._memory is not None and hasattr(self._memory, "set_state"):
                try:
                    self._memory.set_state(state["memory_buffer"])
                except Exception as e:
                    logger.error(f"[TrafficNode] Failed to restore memory for {self.source_id}: {e}")

            if "agent_state" in state and self._agent is not None and hasattr(self._agent, "set_state"):
                try:
                    self._agent.set_state(state["agent_state"])
                except Exception as e:
                    logger.error(f"[TrafficNode] Failed to restore agent state for {self.source_id}: {e}")

            if "kse_state" in state and self._physics_engine is not None and hasattr(self._physics_engine, "set_state"):
                try:
                    self._physics_engine.set_state(state["kse_state"])
                    if hasattr(self._physics_engine, "get_kinetic_snapshot"):
                        kse_snap = self._physics_engine.get_kinetic_snapshot()
                        if kse_snap is not None:
                            self.state.last_value = float(getattr(kse_snap, "p", 0.0))
                except Exception as e:
                    logger.error(f"[TrafficNode] Failed to restore physics state for {self.source_id}: {e}")

        except Exception as e:
            logger.error(f"[TrafficNode] Failed to restore state for {self.source_id}: {e}")
