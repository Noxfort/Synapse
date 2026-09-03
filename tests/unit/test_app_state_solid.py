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
# File: tests/unit/test_app_state_solid.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import pytest
from unittest.mock import MagicMock
from PyQt6.QtCore import QObject, pyqtSignal

from src.domain.entities import MapNode, MapEdge, DataSource, SourceType, SourceStatus
from src.domain.topology_repository import TopologyRepository
from src.managers.interaction_manager import InteractionManager
from src.domain.app_state import AppState
from src.interfaces.topology import ITopologyRepository, ITopologyReader
from src.interfaces.interaction import IInteractionManager
from src.interfaces.sources import ISourceRepository


# =============================================================================
# 1. SRP TESTS: TopologyRepository
# =============================================================================

def test_topology_repository_srp_lifecycle():
    """Verify TopologyRepository manages static map entities and emits Qt signal."""
    repo = TopologyRepository()
    assert isinstance(repo, ITopologyRepository)
    assert isinstance(repo, ITopologyReader)

    signal_received = []
    repo.map_loaded.connect(lambda: signal_received.append(True))

    nodes_raw = [
        {"id": "node_1", "x": 10.0, "y": 20.0, "type": "traffic_light", "name": "Cruzamento Central", "tl_logic_id": "TL_01"},
        {"id": "node_2", "x": 50.0, "y": 60.0, "type": "priority", "name": "Entrada Norte"}
    ]
    edges_raw = [
        {"id": "edge_1_2", "from_node": "node_1", "to_node": "node_2", "shape": "10.0,20.0 50.0,60.0", "name": "Av. Brasil"}
    ]

    repo.load_data(nodes_raw, edges_raw)

    assert signal_received == [True]
    assert len(repo.get_all_nodes()) == 2
    assert len(repo.get_all_edges()) == 1

    node = repo.get_node("node_1")
    assert node is not None
    assert node.x == 10.0
    assert node.tl_logic_id == "TL_01"

    edge = repo.get_edge("edge_1_2")
    assert edge is not None
    assert edge.from_node == "node_1"
    assert edge.to_node == "node_2"

    # Map file path encapsulation
    repo.set_map_file_path("/maps/city.net.xml")
    assert repo.get_map_file_path() == "/maps/city.net.xml"
    assert repo.map_file_path == "/maps/city.net.xml"

    # Clear
    repo.clear()
    assert len(signal_received) == 2
    assert repo.get_all_nodes() == []
    assert repo.get_all_edges() == []
    assert repo.get_map_file_path() is None


# =============================================================================
# 2. SRP TESTS: InteractionManager
# =============================================================================

def test_interaction_manager_srp_lifecycle():
    """Verify InteractionManager handles transient UI association modes and signals."""
    mgr = InteractionManager()
    assert isinstance(mgr, IInteractionManager)

    mode_signals = []
    mgr.mode_changed.connect(lambda active: mode_signals.append(active))

    assert mgr.is_active is False
    assert mgr.selected_id is None

    # Enter mode
    mgr.enter_association_mode("src_radar_1")
    assert mgr.is_active is True
    assert mgr.selected_id == "src_radar_1"
    assert mode_signals == [True]

    # Exit mode
    mgr.exit_association_mode()
    assert mgr.is_active is False
    assert mgr.selected_id is None
    assert mode_signals == [True, False]


# =============================================================================
# 3. DIP TESTS: AppState Dependency Injection with Mocks
# =============================================================================

class MockTopology(QObject):
    map_loaded = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.nodes = []
        self.edges = []
        self.path = None

    def load_data(self, n, e):
        self.nodes = n
        self.edges = e
        self.map_loaded.emit()

    def clear(self):
        self.nodes = []
        self.edges = []
        self.path = None

    def get_all_nodes(self): return self.nodes
    def get_all_edges(self): return self.edges
    def get_node(self, nid): return next((n for n in self.nodes if n.get("id") == nid), None)
    def get_edge(self, eid): return next((e for e in self.edges if e.get("id") == eid), None)
    def get_map_file_path(self): return self.path
    def set_map_file_path(self, path): self.path = path


class MockSources(QObject):
    source_added = pyqtSignal(DataSource)
    source_removed = pyqtSignal(str)
    association_changed = pyqtSignal(str, str)
    source_origin_toggled = pyqtSignal(str, bool)

    def __init__(self):
        super().__init__()
        self.items = {}
        self.associations = {}
        self.map_path = None

    def add(self, s):
        self.items[s.id] = s
        self.source_added.emit(s)

    def remove(self, sid):
        if sid in self.items:
            del self.items[sid]
            self.source_removed.emit(sid)

    def get(self, sid): return self.items.get(sid)
    def get_all(self): return list(self.items.values())
    def update_value(self, sid, val):
        if sid in self.items: self.items[sid].latest_value = val
    def associate(self, sid, eid):
        self.associations[eid] = [sid]
        self.association_changed.emit(sid, eid)
    def get_associations(self, eid): return self.associations.get(eid, [])
    def get_element_for_source(self, sid):
        for eid, sids in self.associations.items():
            if sid in sids: return eid
        return None
    def toggle_origin(self, sid):
        if sid in self.items:
            self.items[sid].is_local = not self.items[sid].is_local
            self.source_origin_toggled.emit(sid, self.items[sid].is_local)
    def get_next_source_id(self): return f"src_{len(self.items) + 1}"
    def set_map_path(self, p): self.map_path = p
    def get_map_path(self): return self.map_path
    def clear(self):
        self.items.clear()
        self.associations.clear()
        self.map_path = None


class MockInteraction(QObject):
    mode_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self._active = False
        self._sel = None

    def enter_association_mode(self, sid):
        self._active = True
        self._sel = sid
        self.mode_changed.emit(True)

    def exit_association_mode(self):
        self._active = False
        self._sel = None
        self.mode_changed.emit(False)

    @property
    def is_active(self): return self._active

    @property
    def selected_id(self): return self._sel


def test_app_state_dependency_injection():
    """Verify AppState can be instantiated with custom injected sub-managers (DIP)."""
    mock_topo = MockTopology()
    mock_sources = MockSources()
    mock_inter = MockInteraction()

    app_state = AppState(
        topology=mock_topo,
        sources=mock_sources,
        interaction=mock_inter
    )

    assert app_state.topology is mock_topo
    assert app_state.sources is mock_sources
    assert app_state.interaction is mock_inter

    # Signal propagation tests
    map_loaded_events = []
    source_added_events = []
    source_removed_events = []
    assoc_changed_events = []
    origin_toggled_events = []
    assoc_mode_events = []

    app_state.map_data_loaded.connect(lambda: map_loaded_events.append(True))
    app_state.data_source_added.connect(lambda s: source_added_events.append(s.id))
    app_state.data_source_removed.connect(lambda sid: source_removed_events.append(sid))
    app_state.data_association_changed.connect(lambda s, e: assoc_changed_events.append((s, e)))
    app_state.source_origin_toggled.connect(lambda s, l: origin_toggled_events.append((s, l)))
    app_state.association_mode_changed.connect(lambda a: assoc_mode_events.append(a))

    # Trigger topology load
    app_state.set_map_data([{"id": "n1"}], [{"id": "e1"}])
    assert map_loaded_events == [True]

    # Trigger source operations
    src = DataSource(id="src_99", name="Mock Camera", is_local=True)
    app_state.add_data_source(src)
    assert source_added_events == ["src_99"]

    app_state.toggle_source_origin("src_99")
    assert origin_toggled_events == [("src_99", False)]

    # Trigger UI association workflow orchestration
    app_state.enter_association_mode("src_99")
    assert assoc_mode_events == [True]
    assert app_state.is_in_association_mode() is True

    app_state.associate_selected_source_to_element("edge_cross")
    assert assoc_changed_events == [("src_99", "edge_cross")]
    assert app_state.is_in_association_mode() is False
    assert assoc_mode_events == [True, False]

    # Remove source
    app_state.remove_data_source("src_99")
    assert source_removed_events == ["src_99"]


def test_app_state_default_instantiation():
    """Verify AppState provides sensible default sub-managers when none are injected."""
    app_state = AppState()
    assert isinstance(app_state.topology, TopologyRepository)
    assert isinstance(app_state.interaction, InteractionManager)
    assert app_state.get_all_nodes() == []
    assert app_state.get_all_edges() == []
    assert app_state.get_all_data_sources() == []
