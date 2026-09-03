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
# File: tests/unit/test_optimization_phase.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import os
import tempfile
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from src.domain.app_state import AppState
from src.domain.entities import DataSource, SourceType, SourceStatus
from src.phases.optimization_phase import OptimizationPhase
from src.services.optimizer_service import OptimizerService
from src.handlers.database_handler import DatabaseCommandHandler
from src.ipc.ipc_protocol import IpcMessage


@pytest.fixture
def sample_parquet():
    df = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=20, freq="1min"),
        "speed": [50.0 + i for i in range(20)],
        "volume": [100 + i * 2 for i in range(20)],
    })
    tmp = tempfile.NamedTemporaryFile(suffix=".parquet", delete=False)
    tmp.close()
    df.to_parquet(tmp.name)
    yield tmp.name
    if os.path.exists(tmp.name):
        os.unlink(tmp.name)


@pytest.fixture
def mock_app_state(sample_parquet, tmp_path):
    app_state = AppState()
    
    # Create fake map file
    map_file = tmp_path / "test_map.net.xml"
    map_file.write_text("<net></net>")
    app_state.set_map_source_path(str(map_file))

    # Add live local sensor
    local_src = DataSource(
        id="src_local_1",
        name="Local Camera",
        source_type=SourceType.API,
        connection_string="http://localhost:8080",
        is_local=True,
        status=SourceStatus.ACTIVE,
    )
    # Add live global sensor
    global_src = DataSource(
        id="src_global_1",
        name="Global Waze",
        source_type=SourceType.API,
        connection_string="http://localhost:8088",
        is_local=False,
        status=SourceStatus.ACTIVE,
    )
    app_state.add_data_source(local_src)
    app_state.add_data_source(global_src)

    return app_state


def test_optimization_phase_missing_map(tmp_path):
    app_state = AppState()
    # Add live sensors
    app_state.add_data_source(DataSource("l1", "Cam", SourceType.API, "http://l", is_local=True))
    app_state.add_data_source(DataSource("g1", "Waze", SourceType.API, "http://g", is_local=False))
    
    phase = OptimizationPhase(app_state)
    errors = []
    phase.error_occurred.connect(lambda msg: errors.append(msg))
    
    success = phase.start()
    assert success is False
    assert len(errors) == 1
    assert "Map Source is MANDATORY" in errors[0]


def test_optimization_phase_missing_live_sensors(tmp_path):
    app_state = AppState()
    map_file = tmp_path / "map.net.xml"
    map_file.write_text("<net/>")
    app_state.set_map_source_path(str(map_file))
    
    # Only local sensor, missing global
    app_state.add_data_source(DataSource("l1", "Cam", SourceType.API, "http://l", is_local=True))
    
    phase = OptimizationPhase(app_state)
    errors = []
    phase.error_occurred.connect(lambda msg: errors.append(msg))
    
    success = phase.start()
    assert success is False
    assert len(errors) == 1
    assert "Missing LIVE data sources" in errors[0]


def test_optimization_phase_missing_parquet(mock_app_state):
    # App state has map and live sensors, but NO parquet in sources or datalake
    with patch("src.managers.storage_manager.StorageManager.get_datalake_base_path", return_value="/tmp/nonexistent_base_dir"), \
         patch("src.managers.storage_manager.StorageManager.get_datalake_golden_path", return_value="/tmp/nonexistent_golden_dir"), \
         patch("os.path.exists", side_effect=lambda p: True if "test_map" in str(p) else False):
        phase = OptimizationPhase(mock_app_state)
        errors = []
        phase.error_occurred.connect(lambda msg: errors.append(msg))
        
        success = phase.start()
        assert success is False
        assert len(errors) == 1
        assert "Historical Parquet Dataset (.parquet) is MANDATORY" in errors[0]


def test_optimization_phase_resolves_parquet_from_app_state(mock_app_state, sample_parquet):
    # Add parquet as a data source
    parquet_src = DataSource(
        id="hist_base",
        name="Parquet Base",
        source_type=SourceType.PARQUET,
        connection_string=sample_parquet,
        is_local=False,
        status=SourceStatus.ACTIVE,
    )
    mock_app_state.add_data_source(parquet_src)
    
    phase = OptimizationPhase(mock_app_state)
    resolved = phase._resolve_parquet_path()
    assert resolved == sample_parquet


def test_optimization_phase_resolves_parquet_from_storage_manager(mock_app_state, sample_parquet, tmp_path):
    # StorageManager datalake/base contains sample_parquet
    with patch("src.managers.storage_manager.StorageManager.get_datalake_base_path", return_value=os.path.dirname(sample_parquet)):
        phase = OptimizationPhase(mock_app_state)
        resolved = phase._resolve_parquet_path()
        assert resolved is not None
        assert resolved.endswith(".parquet")


def test_optimizer_service_raises_on_missing_parquet():
    service = OptimizerService()
    with patch.object(service, "checkpoint_file", "/tmp/nonexistent_checkpoint_file.pth"):
        with pytest.raises(ValueError, match="No User Parquet File provided"):
            service.run(map_file_path=None, history_file_path=None)


def test_database_handler_registers_datasource_on_import(mock_app_state, sample_parquet):
    mock_controller = MagicMock()
    mock_controller.app_state = mock_app_state
    
    events = []
    def event_emitter(name, data):
        events.append((name, data))
        
    class MockImporter:
        def __init__(self, storage=None):
            self.on_progress = None
            self.on_log = None
            self.on_finished = None
            
        def execute_import(self, path):
            if self.on_finished:
                self.on_finished(True, "Imported successfully")

    handler = DatabaseCommandHandler(
        controller=mock_controller,
        event_emitter=event_emitter,
        importer_factory=lambda storage: MockImporter(storage)
    )
    
    responses = []
    msg = IpcMessage(action="import_parquet", payload={"path": sample_parquet}, id="req-1")
    handler.handle_import_parquet(msg, lambda ok, res=None, error=None: responses.append((ok, res, error)))
    
    assert len(responses) == 1
    assert responses[0][0] is True
    
    # Verify DataSource was registered in app_state
    sources = mock_app_state.get_all_data_sources()
    parquet_sources = [s for s in sources if s.source_type == SourceType.PARQUET]
    assert len(parquet_sources) == 1
    assert parquet_sources[0].id == "historical_base"
