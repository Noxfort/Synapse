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
# File: src/interfaces/node.py
# Author: Gabriel Moraes
# Date: 2026-08-19

from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable


@runtime_checkable
class IPhysicsEngine(Protocol):
    """Contract for kinetic/physical filtering engines (e.g. Robust Kalman Filter)."""
    def predict(self, dt: float) -> None: ...
    def update(self, measurement: float) -> bool: ...
    def get_kinetic_snapshot(self) -> Any: ...
    def get_state(self) -> Dict[str, Any]: ...
    def set_state(self, state: Dict[str, Any]) -> None: ...


@runtime_checkable
class INodeValidationStrategy(Protocol):
    """Contract for adaptive sensor validation and learning verification (e.g. 1-5-10 rule)."""
    def evaluate(
        self,
        source_id: str,
        step_count: int,
        loss: Optional[float],
        agent: Any,
        is_validated: bool,
        is_rejected: bool
    ) -> Tuple[bool, bool, str]:
        """Evaluates convergence and returns (is_validated, is_rejected, status_string)."""
        ...


@runtime_checkable
class INodeImputationStrategy(Protocol):
    """Contract for resolving sensor dropouts / synthetic data fallbacks."""
    def impute(
        self,
        source_id: str,
        timestamp: float,
        dt: float,
        physics_engine: IPhysicsEngine,
        historical_manager: Optional[Any] = None,
        fallback_steps: int = 0
    ) -> Tuple[float, str]:
        """Computes the replacement sensor value and method label: (value, method_used)."""
        ...


# --- NODE ORCHESTRATION & DELEGATES ---

@runtime_checkable
class INodeStepProcessor(Protocol):
    """Contract for processing ground-truth real sensor readings."""
    def process(self, value: float, state: Any) -> Dict[str, Any]: ...
    def is_ready(self) -> bool: ...


@runtime_checkable
class INodeGhostProcessor(Protocol):
    """Contract for processing synthetic / dropout sensor readings."""
    def process(self, state: Any) -> Dict[str, Any]: ...


@runtime_checkable
class INodeStatusNotifier(Protocol):
    """Contract for dispatching sensor node lifecycle status transitions."""
    def notify_status(self, source_id: str, status: Any) -> None: ...


@runtime_checkable
class INodeSnapshotFormatter(Protocol):
    """Contract for formatting node telemetry and physics snapshot reports."""
    def format_step_report(
        self,
        source_id: str,
        status: str,
        value: float,
        loss: float,
        embedding: Any,
        is_ready: bool,
        steps: int,
        physics_engine: IPhysicsEngine
    ) -> Dict[str, Any]: ...

    def format_ghost_report(
        self,
        source_id: str,
        method_used: str,
        value: float,
        embedding: Any,
        fallback_steps: int,
        physics_engine: IPhysicsEngine
    ) -> Dict[str, Any]: ...


@runtime_checkable
class ITrafficNode(Protocol):
    """Contract for a traffic sensing node orchestrator (Pure Facade)."""
    @property
    def source_id(self) -> str: ...

    @property
    def is_ready(self) -> bool: ...

    @property
    def is_validated(self) -> bool: ...

    @property
    def is_rejected(self) -> bool: ...

    @property
    def last_value(self) -> float: ...

    @property
    def memory(self) -> Optional[Any]: ...

    @property
    def agent(self) -> Optional[Any]: ...

    @property
    def kse(self) -> Optional[IPhysicsEngine]: ...

    def step(self, value: float) -> Dict[str, Any]: ...
    def ghost_step(self) -> Dict[str, Any]: ...
    def get_state(self) -> Dict[str, Any]: ...
    def set_state(self, state: Dict[str, Any]) -> None: ...


# --- NODE PERSISTENCE & FACTORY CONTRACTS (DIP) ---

@runtime_checkable
class INodeCheckpointStorage(Protocol):
    """Contract for persisting and restoring node checkpoint states (DIP / Persistence Abstraction)."""
    def save_node_checkpoint(self, source_id: str, state: Dict[str, Any]) -> bool: ...
    def load_node_checkpoint(self, source_id: str) -> Optional[Dict[str, Any]]: ...


@runtime_checkable
class INodeFactory(Protocol):
    """Contract for creating traffic node instances (DIP / Abstract Factory)."""
    def create_node(self, source_id: str, **kwargs: Any) -> ITrafficNode: ...


@runtime_checkable
class INodeManager(Protocol):
    """Contract for node lifecycle and orchestration manager (DIP)."""
    def add_node(self, source_id: str) -> bool: ...
    def remove_node(self, source_id: str) -> None: ...
    def update_node(self, source_id: str, value: float) -> Optional[Dict[str, Any]]: ...
    def trigger_fallback(self, source_id: str, error_msg: str) -> Optional[Dict[str, Any]]: ...
    def save_all_nodes(self) -> None: ...
    def get_node(self, source_id: str) -> Optional[ITrafficNode]: ...
    def get_all_nodes(self) -> Dict[str, ITrafficNode]: ...
    def get_ready_nodes_ids(self) -> List[str]: ...
    def get_agents_for_pbt(self) -> Dict[str, Any]: ...

