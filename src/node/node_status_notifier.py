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
# File: src/node/node_status_notifier.py
# Author: Gabriel Moraes
# Date: 2026-08-19

from typing import Optional, Callable, Any
from src.domain.entities import SourceStatus
from src.interfaces.node import INodeStatusNotifier


class NodeStatusNotifier:
    """
    Handles dispatching sensor validation and lifecycle status transitions.
    Decouples individual Traffic Nodes from global state repositories and manager hierarchies.
    """

    def __init__(
        self,
        on_status_change: Optional[Callable[[str, SourceStatus], None]] = None,
        graph_manager: Optional[Any] = None
    ):
        self._on_status_change = on_status_change
        self._graph_manager = graph_manager

    def notify_status(self, source_id: str, status: SourceStatus) -> None:
        """Dispatches status updates to configured callbacks or central AppState."""
        if self._on_status_change is not None:
            self._on_status_change(source_id, status)
        elif self._graph_manager and hasattr(self._graph_manager, "app_state") and self._graph_manager.app_state:
            app_state = self._graph_manager.app_state
            for src in app_state.get_all_data_sources():
                if src.id == source_id or app_state.get_element_for_source(src.id) == source_id:
                    src.status = status
