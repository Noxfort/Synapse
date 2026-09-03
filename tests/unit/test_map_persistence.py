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
# File: tests/unit/test_map_persistence.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import os
import json
import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication

from src.domain.entities import DataSource, SourceType, SourceStatus
from src.domain.source_repository import SourceRepository
from src.infrastructure.json_source_storage import JsonSourceStorage
from src.domain.app_state import AppState
from src.managers.storage_manager import StorageManager



@pytest.fixture(scope="module")
def qapp():
    """Ensure a single QApplication instance exists for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_json_source_storage_map_roundtrip(tmp_path):
    """Verifies that JsonSourceStorage saves and restores map_path alongside sources."""
    storage_file = str(tmp_path / "test_sources.json")
    storage = JsonSourceStorage(storage_file)

    src = DataSource(
        id="src_1",
        name="Test Camera",
        source_type=SourceType.API,
        connection_string="http://localhost:8080",
        is_local=True,
        status=SourceStatus.ACTIVE,
    )
    data_sources = {"src_1": src}
    associations = {"edge_123": ["src_1"]}
    map_path = "/path/to/my_network.net.xml"

    # 1. Save
    assert storage.save(data_sources, associations, map_path) is True

    # 2. Verify file content on disk
    with open(storage_file, "r", encoding="utf-8") as f:
        content = json.load(f)
    assert content.get("map_path") == map_path
    assert "sources" in content
    assert "associations" in content
    assert content["associations"] == associations

    # 3. Load and assert round-trip
    restored_sources, restored_associations, restored_map = storage.load()
    assert restored_map == map_path
    assert "src_1" in restored_sources
    assert restored_sources["src_1"].name == "Test Camera"
    assert restored_associations == {"edge_123": ["src_1"]}


def test_source_repository_persists_and_restores_map(tmp_path):
    """Verifies that SourceRepository retains and reloads map_path across instances."""
    storage_file = str(tmp_path / "sources.json")
    storage = JsonSourceStorage(storage_file)

    repo1 = SourceRepository(storage)
    assert repo1.get_map_path() is None

    repo1.set_map_path("/abs/path/city_network.net.xml")
    assert repo1.get_map_path() == "/abs/path/city_network.net.xml"

    # New instance using the same storage file
    repo2 = SourceRepository(storage)
    assert repo2.get_map_path() == "/abs/path/city_network.net.xml"


def test_app_state_map_persistence_and_clear(tmp_path):
    """Verifies that AppState correctly synchronizes map_path with SourceRepository and resets on clear."""
    storage_file = str(tmp_path / "app_state_sources.json")
    storage = JsonSourceStorage(storage_file)

    app_state = AppState()
    app_state.sources = SourceRepository(storage)
    
    map_file = "/path/to/sim_network.net.xml"
    app_state.set_map_source_path(map_file)

    assert app_state.get_map_source_path() == map_file
    assert app_state.sources.get_map_path() == map_file

    # Verify reload in fresh AppState
    new_app_state = AppState()
    new_app_state.sources = SourceRepository(storage)
    new_app_state.topology._map_file_path = new_app_state.sources.get_map_path()
    assert new_app_state.get_map_source_path() == map_file

    # Verify clear
    app_state.clear()
    assert app_state.get_map_source_path() is None
    assert app_state.get_all_nodes() == []
    assert app_state.get_all_edges() == []
    assert app_state.get_all_data_sources() == []


def test_storage_manager_save_and_load_state(tmp_path):
    """Verifies that StorageManager can save and load full AppState projects."""
    project_file = str(tmp_path / "project.json")
    sm = StorageManager()

    storage_file = str(tmp_path / "dummy_sources.json")
    storage = JsonSourceStorage(storage_file)

    app_state = AppState()
    app_state.sources = SourceRepository(storage)

    src = DataSource(
        id="src_sensor",
        name="Radar",
        source_type=SourceType.API,
        connection_string="http://radar.local",
        is_local=True,
    )
    app_state.add_data_source(src)
    app_state.set_map_source_path("/path/to/network.net.xml")

    # Save state
    assert sm.save_state(app_state, project_file) is True
    assert os.path.exists(project_file)

    # Load state into a fresh AppState
    fresh_state = AppState()
    fresh_state.sources = SourceRepository(str(tmp_path / "fresh_sources.json"))
    assert sm.load_state(fresh_state, project_file) is True
    assert fresh_state.get_map_source_path() == "/path/to/network.net.xml"
    assert fresh_state.get_data_source("src_sensor") is not None


def test_project_controller_create_new_project_flow(tmp_path):
    """Verifies that create_new_project clears AppState, emits signal, and clears storage."""
    storage_file = str(tmp_path / "reset_sources.json")
    storage = JsonSourceStorage(storage_file)

    app_state = AppState()
    app_state.sources = SourceRepository(storage)
    app_state.set_map_source_path("/path/to/old_map.net.xml")
    app_state.add_data_source(DataSource(
        id="src_1",
        name="Old Cam",
        source_type=SourceType.API,
        connection_string="http://old.local",
        is_local=True
    ))

    assert app_state.get_map_source_path() == "/path/to/old_map.net.xml"
    assert len(app_state.get_all_data_sources()) == 1

    from src.controllers.project_controller import ProjectController
    from src.managers.storage_manager import StorageManager

    sm = StorageManager()
    project_ctrl = ProjectController(app_state, sm)

    signal_received = []
    project_ctrl.project_cleared.connect(lambda: signal_received.append(True))

    project_ctrl.create_new_project()

    assert signal_received == [True]
    assert app_state.get_map_source_path() is None
    assert app_state.get_all_data_sources() == []

    # Verify storage file reflects empty state
    repo_check = SourceRepository(storage)
    assert repo_check.get_map_path() is None
    assert repo_check.get_all() == []

