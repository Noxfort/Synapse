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
# File: src/interfaces/providers.py
# Author: Gabriel Moraes
# Date: 2026-08-19

from typing import Any, List, Protocol, runtime_checkable


@runtime_checkable
class ITopologyProvider(Protocol):
    """Interface for components that only need to READ map/graph topology data."""
    def get_all_nodes(self) -> List[Any]: ...
    def get_all_edges(self) -> List[Any]: ...


@runtime_checkable
class ISourceProvider(Protocol):
    """Interface for components that only need to READ sensor data sources."""
    def get_all_data_sources(self) -> List[Any]: ...
    def get_data_source(self, source_id: str) -> Any: ...


@runtime_checkable
class ISensorCalibrator(Protocol):
    """Contract for dynamic sensor calibration and online bias correction."""
    def update_observability(self, active_mask: Any) -> None: ...
    def apply(self, raw_output: Any, current_history: Any, observability_mask: Any = None) -> Any: ...
    def reset(self) -> None: ...
