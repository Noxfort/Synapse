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
# File: src/managers/node_manager.py
# Author: Gabriel Moraes
# Date: 2025-12-03

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import torch

from src.interfaces.node import (
    ITrafficNode,
    INodeCheckpointStorage,
    INodeFactory
)
from src.factories.node_factory import NodeFactory
from src.managers.storage_manager import StorageManager
from src.utils.logging_setup import get_logger

logger = get_logger("NodeManager")


class NodeManager:
    """
    Manages the lifecycle and state of Traffic Nodes (Sensors).
    
    SOLID & DIP Architecture:
    - [SRP] Exclusively coordinates node lifecycle, probation timing, and orchestration delegation.
    - [DIP] Depends on abstract contracts (ITrafficNode, INodeCheckpointStorage, INodeFactory).
    - [OCP] Pluggable checkpoint storage and node creation factories injected via constructor.
    """

    def __init__(
        self,
        config: Optional[dict] = None,
        device: Optional[torch.device] = None,
        historical_manager: Optional[Any] = None,
        graph_manager: Optional[Any] = None,
        storage: Optional[INodeCheckpointStorage] = None,
        node_factory: Optional[Union[INodeFactory, Any]] = None,
        probation_duration: float = 60.0
    ):
        self.config = config or {}
        self.device = device or torch.device("cpu")
        self.historical_manager = historical_manager
        self.graph_manager = graph_manager
        
        # Injected abstractions with sensible defaults (DIP)
        self.storage: INodeCheckpointStorage = storage or StorageManager()
        self.node_factory = node_factory or NodeFactory
        
        self._nodes: Dict[str, ITrafficNode] = {}
        
        # Probation State: {source_id: start_timestamp}
        self.probation_nodes: Dict[str, datetime] = {}
        self.probation_duration = probation_duration
        
        # Extract dimensions from config
        self.feature_dim = self.config.get("feature_dim", 1)
        self.embedding_dim = 32

    def add_node(self, source_id: str) -> bool:
        """Instantiates and registers a new TrafficNode via the factory abstraction."""
        if source_id in self._nodes:
            return False
            
        create_fn = getattr(self.node_factory, "create_node", None) or getattr(self.node_factory, "create_traffic_node", None)
        if callable(create_fn):
            node = create_fn(
                source_id=source_id,
                config=self.config,
                device=self.device,
                historical_manager=self.historical_manager,
                graph_manager=self.graph_manager,
                feature_dim=self.feature_dim,
                embedding_dim=self.embedding_dim
            )
        elif callable(self.node_factory):
            node = self.node_factory(
                source_id=source_id,
                config=self.config,
                device=self.device,
                historical_manager=self.historical_manager,
                graph_manager=self.graph_manager,
                feature_dim=self.feature_dim,
                embedding_dim=self.embedding_dim
            )
        else:
            raise TypeError(f"Invalid node factory provided: {self.node_factory}")

        # Restore State (Hibernation Wake-up)
        if self._load_node_checkpoint(node):
            logger.info(f"🕯️ Node '{source_id}' restored. Entering Probation.")
            self.probation_nodes[source_id] = datetime.now()

        self._nodes[source_id] = node
        return True

    def remove_node(self, source_id: str) -> None:
        """Removes a registered node and cleans up probation state."""
        if source_id in self._nodes:
            del self._nodes[source_id]
            if source_id in self.probation_nodes:
                del self.probation_nodes[source_id]
            logger.info(f"Removed Node: {source_id}")

    def update_node(self, source_id: str, value: float) -> Optional[Dict[str, Any]]:
        """
        Orchestrates the NORMAL data step for a node.
        """
        if source_id not in self._nodes:
            return None
            
        self._check_probation(source_id)
            
        node = self._nodes[source_id]
        result = node.step(value)
        
        # Inject Status Override for UI during probation
        if source_id in self.probation_nodes:
            elapsed = (datetime.now() - self.probation_nodes[source_id]).total_seconds()
            remaining = int(self.probation_duration - elapsed)
            result["status"] = f"Probation ({remaining}s)"
            
        return result

    def trigger_fallback(self, source_id: str, error_msg: str) -> Optional[Dict[str, Any]]:
        """
        Orchestrates the FALLBACK step (Ghost Step) when a sensor fails.
        Uses historical data to keep forecasting pipelines active.
        """
        if source_id not in self._nodes:
            return None
            
        logger.warning(f"🚑 Triggering Fallback for {source_id}: {error_msg}")
        node = self._nodes[source_id]
        
        # Ghost Step uses historical data / physics imputation
        result = node.ghost_step()
        return result

    def save_all_nodes(self) -> None:
        """Persists the state of all active nodes using the injected storage abstraction."""
        if not self._nodes:
            return
        
        logger.info("💾 Hibernating: Saving state for all nodes...")
        count = 0
        for nid, node in self._nodes.items():
            try:
                state = node.get_state()
                if self.storage.save_node_checkpoint(nid, state):
                    count += 1
            except Exception as e:
                logger.error(f"Failed to save state for {nid}: {e}")
                
        logger.info(f"Saved {count} node checkpoints.")

    # --- Internal Helpers ---

    def _load_node_checkpoint(self, node: ITrafficNode) -> bool:
        """Restores checkpoint state for a node using the injected storage abstraction."""
        try:
            state = self.storage.load_node_checkpoint(node.source_id)
            if state is not None:
                node.set_state(state)
                return True
        except Exception as e:
            logger.error(f"Corrupted checkpoint for {node.source_id}: {e}")
        return False

    def _check_probation(self, source_id: str) -> None:
        if source_id in self.probation_nodes:
            start_time = self.probation_nodes[source_id]
            elapsed = (datetime.now() - start_time).total_seconds()
            
            if elapsed > self.probation_duration:
                logger.info(f"🎉 Node '{source_id}' passed probation!")
                del self.probation_nodes[source_id]

    # --- Accessors ---

    def get_node(self, source_id: str) -> Optional[ITrafficNode]:
        return self._nodes.get(source_id)

    def get_all_nodes(self) -> Dict[str, ITrafficNode]:
        return self._nodes

    def get_ready_nodes_ids(self) -> List[str]:
        return sorted([nid for nid, node in self._nodes.items() if node.is_ready])

    def get_agents_for_pbt(self) -> Dict[str, Any]:
        return {nid: node.agent for nid, node in self._nodes.items()}
