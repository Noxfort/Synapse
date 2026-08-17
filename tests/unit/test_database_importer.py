# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems

import os
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication

from src.services.database_importer import DatabaseImporter
from ui.wizards.import_wizard import ImportWizard, IntroPage, ConfigPage, ProcessingPage

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


def test_import_wizard_no_target_interval(qapp):
    """Verify that ImportWizard does NOT expose target interval / spin_freq fields."""
    wizard = ImportWizard()
    config_page = wizard.page_config
    
    # Verify spin_freq and target_freq are absent
    assert not hasattr(config_page, "spin_freq")
    assert not hasattr(wizard, "target_freq")
    assert wizard.field("target_freq") is None
    
    wizard.close()


def test_import_wizard_parquet_inspection(qapp, valid_parquet_file):
    """Verify that ConfigPage inspects and displays rich metadata from Parquet."""
    wizard = ImportWizard()
    wizard.source_path = valid_parquet_file
    
    config_page = wizard.page_config
    config_page.initializePage()
    
    items = [config_page.list_tables.item(i).text() for i in range(config_page.list_tables.count())]
    all_text = "\n".join(items)
    
    assert "valid_traffic.parquet" in all_text
    assert "Total Rows" in all_text
    assert "Time Column" in all_text
    assert "timestamp" in all_text
    assert "Historical span requirement met" in all_text
    assert "Identified Sources/Sensors" in all_text
    
    wizard.close()


def test_import_wizard_rejects_db_in_inspection(qapp, tmp_path):
    """Verify that ConfigPage displays an error if a non-parquet file is selected."""
    db_file = tmp_path / "test.db"
    db_file.write_text("sqlite dummy")
    
    wizard = ImportWizard()
    wizard.source_path = str(db_file)
    
    config_page = wizard.page_config
    config_page.initializePage()
    
    items = [config_page.list_tables.item(i).text() for i in range(config_page.list_tables.count())]
    all_text = "\n".join(items)
    
    assert "Unsupported file format" in all_text
    assert ".parquet" in all_text
    
    wizard.close()
