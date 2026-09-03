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
# File: src/domain/app_state.py
# Author: Gabriel Moraes
# Date: 2026-08-28

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from typing import Dict, List, Optional, Any

from src.domain.entities import MapNode, MapEdge, DataSource
from src.domain.topology_repository import TopologyRepository
from src.managers.interaction_manager import InteractionManager
from src.interfaces.topology import ITopologyRepository
from src.interfaces.interaction import IInteractionManager


class AppState(QObject):
    """
    Central Application State Facade / Orchestrator.
    
    SOLID Architecture:
    - [SRP] Coordinates sub-domain managers (Topology, Sources, UI Interaction) and central Qt signals.
    - [DIP] Injected with abstract protocols (ITopologyRepository, ISourceRepository/Manager, IInteractionManager).
    - [Encapsulation] Interacts with sub-managers through their public interface.
    """
    
    # Re-exposing Signals for application-wide reactivity
    map_data_loaded = pyqtSignal()
    association_mode_changed = pyqtSignal(bool)
    data_association_changed = pyqtSignal(str, str)
    data_source_added = pyqtSignal(DataSource)
    data_source_removed = pyqtSignal(str)
    source_origin_toggled = pyqtSignal(str, bool)

    def __init__(
        self,
        topology: Optional[ITopologyRepository] = None,
        sources: Optional[Any] = None,
        interaction: Optional[IInteractionManager] = None,
    ):
        super().__init__()
        
        # 1. Dependency Inversion Resolution with Sensible Defaults
        self.topology: ITopologyRepository = topology if topology is not None else TopologyRepository()
        
        if sources is not None:
            self.sources = sources
        else:
            # Lazy import to prevent circular or premature domain-to-manager dependencies
            from src.managers.source_manager import SourceManager
            self.sources = SourceManager()

        self.interaction: IInteractionManager = interaction if interaction is not None else InteractionManager()
        
        # Restore persisted map path from source repository if available
        if hasattr(self.sources, "get_map_path"):
            restored_map = self.sources.get_map_path()
            if restored_map:
                if hasattr(self.topology, "set_map_file_path"):
                    self.topology.set_map_file_path(restored_map)
                else:
                    self.topology._map_file_path = restored_map

        # Synchronization Flags
        self.is_meh_ready = False
        
        # 2. Wire Signals
        self._wire_signals()

    def _wire_signals(self) -> None:
        """Connects child events to central AppState signals."""
        if hasattr(self.topology, "map_loaded"):
            self.topology.map_loaded.connect(self.map_data_loaded)
        if hasattr(self.sources, "source_added"):
            self.sources.source_added.connect(self.data_source_added)
        if hasattr(self.sources, "source_removed"):
            self.sources.source_removed.connect(self.data_source_removed)
        if hasattr(self.sources, "association_changed"):
            self.sources.association_changed.connect(self.data_association_changed)
        if hasattr(self.sources, "source_origin_toggled"):
            self.sources.source_origin_toggled.connect(self.source_origin_toggled)
        if hasattr(self.interaction, "mode_changed"):
            self.interaction.mode_changed.connect(self.association_mode_changed)

    # =========================================================================
    # TOPOLOGY DELEGATION METHODS
    # =========================================================================

    @pyqtSlot(list, list)
    def set_map_data(self, nodes_data: List[dict], edges_data: List[dict]):
        self.topology.load_data(nodes_data, edges_data)

    def set_map_source_path(self, path: str):
        if hasattr(self.topology, "set_map_file_path"):
            self.topology.set_map_file_path(path)
        else:
            self.topology._map_file_path = path

        if hasattr(self.sources, "set_map_path"):
            self.sources.set_map_path(path)

    def get_map_source_path(self) -> Optional[str]:
        if hasattr(self.topology, "get_map_file_path"):
            return self.topology.get_map_file_path()
        return getattr(self.topology, "_map_file_path", None)

    def clear(self):
        """Resets topology, data sources, and interaction states."""
        if hasattr(self.topology, "clear"):
            self.topology.clear()
        if hasattr(self.sources, "clear"):
            self.sources.clear()
        if hasattr(self.interaction, "exit_association_mode"):
            self.interaction.exit_association_mode()

    def get_all_nodes(self) -> List[MapNode]:
        return self.topology.get_all_nodes()
    
    def get_all_edges(self) -> List[MapEdge]:
        return self.topology.get_all_edges()

    def get_node(self, node_id: str) -> Optional[MapNode]:
        return self.topology.get_node(node_id)

    def get_edge(self, edge_id: str) -> Optional[MapEdge]:
        return self.topology.get_edge(edge_id)

    # =========================================================================
    # SOURCE DELEGATION METHODS
    # =========================================================================
    
    def add_data_source(self, source: DataSource):
        if hasattr(self.sources, "add"):
            self.sources.add(source)

    def emit_restored_sources(self):
        """Emit source_added for all pre-loaded sources (call AFTER UI signal wiring)."""
        if hasattr(self.sources, "emit_restored_sources"):
            self.sources.emit_restored_sources()

    def remove_data_source(self, source_id: str):
        if hasattr(self.sources, "remove"):
            self.sources.remove(source_id)

    def get_data_source(self, source_id: str) -> Optional[DataSource]:
        if hasattr(self.sources, "get"):
            return self.sources.get(source_id)
        return None
    
    def get_all_data_sources(self) -> List[DataSource]:
        if hasattr(self.sources, "get_all"):
            return self.sources.get_all()
        return []
    
    def get_source_by_device_id(self, device_id: str) -> Optional[DataSource]:
        if hasattr(self.sources, "get"):
            return self.sources.get(device_id)
        return None

    def get_next_source_id(self) -> str:
        """Returns the next unique monotonic source ID."""
        if hasattr(self.sources, "get_next_source_id"):
            return self.sources.get_next_source_id()
        return "src_1"

    def register_source(self, source: DataSource):
        self.add_data_source(source)
    
    def update_source_value(self, source_id: str, value: float):
        if hasattr(self.sources, "update_value"):
            self.sources.update_value(source_id, value)

    def notify_source_updated(self, source: DataSource):
        """Notifies and persists updates to a data source."""
        if hasattr(self.sources, "notify_source_updated"):
            self.sources.notify_source_updated(source)

    def toggle_source_origin(self, source_id: str):
        """Toggle source between Local and Global scope."""
        if hasattr(self.sources, "toggle_origin"):
            self.sources.toggle_origin(source_id)

    # =========================================================================
    # INTERACTION & ASSOCIATION DELEGATION
    # =========================================================================

    @pyqtSlot(str)
    def enter_association_mode(self, source_id: str):
        if hasattr(self.interaction, "enter_association_mode"):
            self.interaction.enter_association_mode(source_id)
        
    @pyqtSlot()
    def exit_association_mode(self):
        if hasattr(self.interaction, "exit_association_mode"):
            self.interaction.exit_association_mode()

    def is_in_association_mode(self) -> bool:
        if hasattr(self.interaction, "is_active"):
            return self.interaction.is_active
        return False
    
    @pyqtSlot(str)
    def associate_selected_source_to_element(self, element_id: str):
        if not self.is_in_association_mode() or not self.interaction.selected_id:
            return
            
        source_id = self.interaction.selected_id
        if hasattr(self.sources, "associate"):
            self.sources.associate(source_id, element_id)
        self.exit_association_mode()

    def get_sources_associated_with_element(self, element_id: str) -> List[str]:
        if hasattr(self.sources, "get_associations"):
            return self.sources.get_associations(element_id)
        return []

    def get_element_for_source(self, source_id: str) -> Optional[str]:
        if hasattr(self.sources, "get_element_for_source"):
            return self.sources.get_element_for_source(source_id)
        return None


# Backward-compatibility re-exports
__all__ = ["AppState", "TopologyRepository", "InteractionManager"]
