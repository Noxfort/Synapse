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
# File: src/factories/node_factory.py
# Author: Gabriel Moraes
# Date: 2026-08-18

import torch
from typing import Optional, Dict, Any, Callable

from src.node.traffic_node import TrafficNode
from src.memory.temporal_memory import TemporalMemory
from src.factories.agent_factory import AgentFactory
from src.kse.filter import RobustKalmanFilter
from src.kse.definitions import PROFILES
from src.strategies.node_validation_strategy import AdaptiveValidationStrategy
from src.strategies.node_imputation_strategy import HierarchicalImputationStrategy
from src.domain.entities import SourceStatus
from src.interfaces.memory import ITemporalMemory
from src.interfaces.node import (
    IPhysicsEngine,
    INodeValidationStrategy,
    INodeImputationStrategy
)


class NodeFactory:
    """
    Factory for assembling Traffic Nodes with configured strategies and components (DIP / Abstract Factory).
    """

    @staticmethod
    def create_node(
        source_id: str,
        config: Optional[dict] = None,
        device: Optional[torch.device] = None,
        historical_manager: Optional[Any] = None,
        graph_manager: Optional[Any] = None,
        on_status_change: Optional[Callable[[str, SourceStatus], None]] = None,
        memory: Optional[ITemporalMemory] = None,
        agent: Optional[Any] = None,
        physics_engine: Optional[IPhysicsEngine] = None,
        validation_strategy: Optional[INodeValidationStrategy] = None,
        imputation_strategy: Optional[INodeImputationStrategy] = None,
        seq_len: int = 60,
        feature_dim: int = 1,
        embedding_dim: int = 32
    ) -> TrafficNode:
        """
        Builds a fully wired TrafficNode instance with appropriate strategies and defaults.
        """
        config = config or {}
        device = device or torch.device("cpu")

        # 1. Memory Component
        if memory is None:
            memory = TemporalMemory(feature_dim=feature_dim, max_len=seq_len)

        # 2. AI Specialist Agent
        if agent is None:
            agent = AgentFactory.create_specialist(
                config=config,
                input_dim=feature_dim,
                output_dim=embedding_dim
            )
            if hasattr(agent, "to"):
                agent.to(device)

        # 3. Physics Engine (KSE)
        if physics_engine is None:
            profile = PROFILES["DEFAULT"]
            if "cam" in source_id.lower():
                profile = PROFILES["CAMERA"]
            elif "loop" in source_id.lower():
                profile = PROFILES["INDUCTIVE"]
            physics_engine = RobustKalmanFilter(node_id=source_id, initial_val=0.0, profile=profile)

        # 4. Validation Strategy (1-5-10 rule)
        if validation_strategy is None:
            validation_strategy = AdaptiveValidationStrategy(
                loss_convergence_threshold=0.15,
                max_warmup_steps=10
            )

        # 5. Imputation Strategy (Cascading Golden DB + KSE Physics)
        if imputation_strategy is None:
            imputation_strategy = HierarchicalImputationStrategy(tolerance=0.25)

        return TrafficNode(
            source_id=source_id,
            memory=memory,
            agent=agent,
            historical_manager=historical_manager,
            physics_engine=physics_engine,
            validation_strategy=validation_strategy,
            imputation_strategy=imputation_strategy,
            on_status_change=on_status_change,
            graph_manager=graph_manager
        )

    create_traffic_node = create_node
