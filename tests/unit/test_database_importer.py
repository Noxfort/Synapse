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
# File: tests/unit/test_database_importer.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import os
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock
from src.services.database_importer import DatabaseImporter

@pytest.fixture(scope="module")
def qapp():
    """Ensure a single QApplication instance exists for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

@pytest.fixture
def temp_datalake(tmp_path):
    """Provides a mocked StorageManager pointing to a clean temp directory."""
    base_dir = tmp_path / "datalake" / "base"
    base_dir.mkdir(parents=True, exist_ok=True)
    
    mock_sm = MagicMock()
    mock_sm.get_datalake_base_path.return_value = str(base_dir)
    return mock_sm, base_dir

@pytest.fixture
def valid_parquet_file(tmp_path):
    """Creates a temporary .parquet file with 10 calendar days of traffic data."""
    file_path = tmp_path / "valid_traffic.parquet"
    
    # 10 days of hourly timestamps
    timestamps = pd.date_range(start="2026-01-01 00:00", end="2026-01-10 23:00", freq="1h")
    df = pd.DataFrame({
        "timestamp": timestamps,
        "sensor_id": ["sensor_01"] * (len(timestamps) // 2) + ["sensor_02"] * (len(timestamps) - len(timestamps) // 2),
        "speed_val": np.random.uniform(20.0, 80.0, size=len(timestamps)),
        "flow_val": np.random.uniform(100.0, 1500.0, size=len(timestamps)),
    })
    df.to_parquet(file_path, engine="pyarrow")
    return str(file_path)

@pytest.fixture
def short_span_parquet_file(tmp_path):
    """Creates a temporary .parquet file with only 2 calendar days (insufficient)."""
    file_path = tmp_path / "short_span.parquet"
    
    timestamps = pd.date_range(start="2026-01-01 00:00", end="2026-01-02 23:00", freq="1h")
    df = pd.DataFrame({
        "timestamp": timestamps,
        "sensor_id": "sensor_01",
        "speed_val": np.random.uniform(20.0, 80.0, size=len(timestamps)),
    })
    df.to_parquet(file_path, engine="pyarrow")
    return str(file_path)


def test_database_importer_parquet_success(temp_datalake, valid_parquet_file):
    """Test importing a valid parquet file copies it directly to datalake base."""
    mock_sm, base_dir = temp_datalake
    importer = DatabaseImporter(storage_manager=mock_sm)
    
    results = []
    importer.import_finished.connect(lambda success, msg: results.append((success, msg)))
    
    importer.execute_import(valid_parquet_file)
    
    assert len(results) == 1
    success, msg = results[0]
    assert success is True
    assert "Import Successful" in msg
    
    target_file = base_dir / "base_v1.parquet"
    assert target_file.exists()
    assert target_file.stat().st_size > 0


def test_database_importer_insufficient_span(temp_datalake, short_span_parquet_file):
    """Test importing a parquet file with fewer than 7 days fails validation."""
    mock_sm, base_dir = temp_datalake
    importer = DatabaseImporter(storage_manager=mock_sm)
    
    results = []
    importer.import_finished.connect(lambda success, msg: results.append((success, msg)))
    
    importer.execute_import(short_span_parquet_file)
    
    assert len(results) == 1
    success, msg = results[0]
    assert success is False
    assert "at least 7 days" in msg


def test_database_importer_rejects_non_parquet(temp_datalake, tmp_path):
    """Test importing non-parquet files (.db, .csv) is explicitly rejected."""
    mock_sm, base_dir = temp_datalake
    importer = DatabaseImporter(storage_manager=mock_sm)
    
    db_file = tmp_path / "legacy_test.db"
    db_file.write_text("dummy sqlite content")
    
    results = []
    importer.import_finished.connect(lambda success, msg: results.append((success, msg)))
    
    importer.execute_import(str(db_file))
    
    assert len(results) == 1
    success, msg = results[0]
    assert success is False
    assert "Unsupported file format" in msg
    assert ".parquet" in msg


def test_database_importer_nonexistent_file(temp_datalake):
    """Test importing a nonexistent file path fails gracefully."""
    mock_sm, _ = temp_datalake
    importer = DatabaseImporter(storage_manager=mock_sm)
    
    results = []
    importer.import_finished.connect(lambda success, msg: results.append((success, msg)))
    
    importer.execute_import("/non/existent/path.parquet")
    
    assert len(results) == 1
    success, msg = results[0]
    assert success is False
    assert "File not found" in msg


def test_database_importer_direct_callbacks(temp_datalake, valid_parquet_file):
    """Test DatabaseImporter invoking direct callbacks (for headless execution)."""
    mock_sm, base_dir = temp_datalake
    importer = DatabaseImporter(storage_manager=mock_sm)
    
    progress_updates = []
    log_messages = []
    finished_results = []
    
    importer.on_progress = lambda p: progress_updates.append(p)
    importer.on_log = lambda m: log_messages.append(m)
    importer.on_finished = lambda ok, m: finished_results.append((ok, m))
    
    importer.execute_import(valid_parquet_file)
    
    assert len(progress_updates) >= 4
    assert 100 in progress_updates
    assert len(finished_results) == 1
    assert finished_results[0][0] is True
    assert (base_dir / "base_v1.parquet").exists()
