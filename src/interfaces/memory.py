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
# File: src/interfaces/memory.py
# Author: Gabriel Moraes
# Date: 2026-08-19

from typing import Any, List, Optional, Protocol, Tuple, Union, runtime_checkable


@runtime_checkable
class ISpatioTemporalMemory(Protocol):
    """Contract for continuous spatio-temporal tensor buffering."""
    def update_node(self, node_id: str, features: Any) -> bool: ...
    def get_tensor(self, batch_first: bool = True, device: Optional[Any] = None) -> Any: ...
    def get_observability_mask(self, device: Optional[Any] = None) -> Any: ...


@runtime_checkable
class IEpisodicMemory(Protocol):
    """Contract for episodic replay buffers and anomaly recording."""
    def record_episode(self, sensor_id: str, signature: Any, anomaly_score: float, **kwargs: Any) -> None: ...
    def sample_batch(self, batch_size: int, device: Optional[Any] = None) -> Optional[Tuple[Any, Any]]: ...


@runtime_checkable
class ISemanticMemory(Protocol):
    """Contract for fast dynamic ontology and concept memory."""
    def set_concept(self, concept_name: str, embedding: Any, **kwargs: Any) -> None: ...
    def find_nearest_concept(self, query_embedding: Any, threshold: float = 0.80) -> Tuple[Optional[str], float]: ...


@runtime_checkable
class ITopologyMemory(Protocol):
    """Contract for dynamic graph connectivity tracking."""
    def set_graph(self, num_nodes: int, edge_list: List[Tuple[int, int]], **kwargs: Any) -> None: ...
    def get_edge_index_tensor(self, device: Optional[Any] = None) -> Any: ...


@runtime_checkable
class ITemporalMemory(Protocol):
    """Contract for sliding-window temporal memory buffers."""
    def push(self, data: Union[List[float], Any, float]) -> None: ...
    def is_ready(self) -> bool: ...
    def get_tensor(self) -> Any: ...
    def get_numpy(self) -> Any: ...
    def rollback(self, steps: int) -> None: ...
    def clear(self) -> None: ...
    def get_state(self) -> List[List[float]]: ...
    def set_state(self, state: List[List[float]]) -> None: ...
