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
# File: tests/unit/test_source_refactoring.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import os
import json
import pytest
from unittest.mock import MagicMock, patch

from src.domain.entities import DataSource, SourceType, SourceStatus
from src.interfaces.sources import ISourceRepository, ISourceStorage, ISourceProbeService
from src.infrastructure.json_source_storage import JsonSourceStorage
from src.services.source_probe_service import HttpSourceProbeService
from src.domain.source_repository import SourceRepository
from src.managers.source_manager import SourceManager


def test_interfaces_and_protocols():
    """Verify that concrete classes satisfy their respective Protocol contracts."""
    storage = JsonSourceStorage()
    assert isinstance(storage, ISourceStorage)

    repo = SourceRepository()
    assert isinstance(repo, ISourceRepository)

    probe = HttpSourceProbeService()
    assert isinstance(probe, ISourceProbeService)


def test_pure_source_repository_operations():
    """Verify that SourceRepository operates purely in memory without persistence/networking."""
    repo = SourceRepository()

    src1 = DataSource(id="src_1", name="Sensor A", is_local=True)
    src2 = DataSource(id="src_2", name="Sensor B", is_local=False)

    repo.add(src1)
    repo.add(src2)
    assert len(repo.get_all()) == 2
    assert repo.get("src_1") == src1

    # Monotonic ID
    assert repo.get_next_source_id() == "src_3"

    # Associations
    repo.associate("src_1", "edge_99")
    assert repo.get_associations("edge_99") == ["src_1"]
    assert repo.get_element_for_source("src_1") == "edge_99"

    # Origin toggle
    new_origin = repo.toggle_origin("src_1")
    assert new_origin is False
    assert repo.get("src_1").is_local is False

    # Removal cleans associations
    removed = repo.remove("src_1")
    assert removed == src1
    assert repo.get("src_1") is None
    assert repo.get_associations("edge_99") == []


def test_json_source_storage_persistence(tmp_path):
    """Verify JsonSourceStorage correctly writes and reads JSON."""
    file_path = str(tmp_path / "storage_test.json")
    storage = JsonSourceStorage(file_path)

    src = DataSource(id="src_10", name="Camera 10", is_local=True)
    saved = storage.save({"src_10": src}, {"node_1": ["src_10"]}, "/path/to/map.xml")
    assert saved is True

    sources, associations, map_path = storage.load()
    assert map_path == "/path/to/map.xml"
    assert "src_10" in sources
    assert associations == {"node_1": ["src_10"]}


def test_source_manager_orchestration(tmp_path):
    """Verify SourceManager orchestrates repository, storage, probe service and Qt signals."""
    storage_file = str(tmp_path / "manager_test.json")
    storage = JsonSourceStorage(storage_file)
    repo = SourceRepository()
    mock_probe = MagicMock(spec=ISourceProbeService)

    manager = SourceManager(repository=repo, storage=storage, probe_service=mock_probe)

    added_signals = []
    removed_signals = []
    manager.source_added.connect(lambda s: added_signals.append(s.id))
    manager.source_removed.connect(lambda sid: removed_signals.append(sid))

    # 1. Add source
    src = DataSource(
        id="src_1",
        name="Global API",
        source_type=SourceType.API,
        connection_string="https://api.traffic.test",
        is_local=False,
        status=SourceStatus.QUARANTINE
    )
    manager.add(src)

    assert added_signals == ["src_1"]
    mock_probe.probe.assert_called_once_with(src)
    assert manager.get("src_1") is not None

    # 2. Persistence verified
    reloaded_sources, _, _ = storage.load()
    assert "src_1" in reloaded_sources

    # 3. Remove source
    manager.remove("src_1")
    assert removed_signals == ["src_1"]
    assert manager.get("src_1") is None
