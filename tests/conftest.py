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
# File: tests/conftest.py
# Author: Gabriel Moraes
# Date: 2026-08-29

import pytest
from unittest.mock import MagicMock
from src.domain.app_state import AppState
from src.managers.storage_manager import StorageManager

@pytest.fixture
def mock_storage_manager():
    """
    Returns a mocked StorageManager that avoids creating real directories.
    """
    sm = MagicMock()
    sm.get_datalake_base_path.return_value = "/tmp/mock/datalake/base"
    sm.get_datalake_golden_path.return_value = "/tmp/mock/datalake/golden"
    sm.get_checkpoint_path.return_value = "/tmp/mock/Checkpoint"
    sm.save_model_checkpoint.return_value = "/tmp/mock/Checkpoint/model.pth"
    sm.is_connected = True
    return sm

@pytest.fixture
def mock_app_state():
    """
    Returns a mocked AppState to avoid complex UI/Topology setups during unit tests.
    """
    app_state = MagicMock(spec=AppState)
    
    # Mocking essential signals to allow .connect() checks
    class MockSignal:
        def connect(self, *args, **kwargs): pass
        def emit(self, *args, **kwargs): pass
        
    app_state.map_data_loaded = MockSignal()
    app_state.association_mode_changed = MockSignal()
    app_state.data_association_changed = MockSignal()
    app_state.data_source_added = MockSignal()
    app_state.data_source_removed = MockSignal()
    app_state.source_origin_toggled = MockSignal()
    
    app_state.get_all_data_sources.return_value = []
    app_state.get_map_source_path.return_value = None
    return app_state


@pytest.fixture(autouse=True)
def isolate_sources_json(tmp_path, monkeypatch):
    """Prevents tests from writing or reading user's real ~/Documentos/Synapse/config/sources.json."""
    mock_sources_path = str(tmp_path / "test_sources.json")
    monkeypatch.setattr(
        "src.infrastructure.json_source_storage.JsonSourceStorage.get_default_path",
        lambda cls: mock_sources_path
    )

