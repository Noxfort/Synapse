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
# File: tests/unit/test_meh_modular_loader.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import pytest
import os
import pandas as pd
import numpy as np
import torch
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.meh.data_reader import DataLakeReader
from src.meh.data_preprocessor import DatasetPreprocessor
from src.meh.sensor_catalog import SensorCatalog
from src.meh.metrics_cache import HistoricalMetricsCache
from src.meh.temporal_query import TemporalQueryEngine
from src.meh.data_loader import HistoricalDataLoader


# =========================================================================
# 1. DataLakeReader Tests (SRP / DIP)
# =========================================================================

def test_data_lake_reader_missing_files(tmp_path):
    storage_mock = MagicMock()
    storage_mock.get_datalake_golden_path.return_value = str(tmp_path / "lake" / "gold")
    
    reader = DataLakeReader(storage_manager=storage_mock)
    
    # Missing files return safe defaults
    raw_df = reader.read_golden_parquet()
    assert raw_df is None
    
    ontology = reader.read_ontology()
    assert ontology == {}
    
    data, ont = reader.read_all()
    assert data is None
    assert ont == {}


def test_data_lake_reader_loads_parquet(tmp_path):
    storage_mock = MagicMock()
    lake_dir = tmp_path / "lake" / "gold"
    lake_dir.mkdir(parents=True)
    storage_mock.get_datalake_golden_path.return_value = str(lake_dir)
    
    parquet_path = lake_dir / "golden_v1.parquet"
    dummy_df = pd.DataFrame({"sensor_id": ["s1", "s2"], "speed": [50.0, 60.0]})
    dummy_df.to_parquet(parquet_path)
    
    reader = DataLakeReader(storage_manager=storage_mock)
    loaded_df = reader.read_golden_parquet()
    
    assert loaded_df is not None
    assert len(loaded_df) == 2
    assert list(loaded_df["sensor_id"]) == ["s1", "s2"]


# =========================================================================
# 2. DatasetPreprocessor Tests (SRP)
# =========================================================================

def test_dataset_preprocessor_capping_and_downcast():
    preprocessor = DatasetPreprocessor(max_rows=100)
    
    # Create 150 rows with float64 and int64
    large_df = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=150, freq="min"),
        "float_val": np.random.rand(150),
        "int_val": np.arange(150, dtype=np.int64)
    })
    
    processed = preprocessor.process(large_df)
    
    # Must cap to 100 rows
    assert len(processed) == 100
    # Downcasted types
    assert processed["float_val"].dtype == np.float32
    assert processed["int_val"].dtype.kind in ('i', 'u')
    # Time index properly set
    assert processed.index.name == "time_idx"


# =========================================================================
# 3. SensorCatalog Tests (SRP / ISP)
# =========================================================================

def test_sensor_catalog_discovery():
    catalog = SensorCatalog()
    df = pd.DataFrame({
        "device_id": ["dev_1", "dev_2", "dev_1", "dev_3"],
        "speed": [40.0, 50.0, 42.0, 60.0]
    })
    catalog.build(df)
    
    assert catalog.group_column == "device_id"
    assert catalog.sensor_ids == ["dev_1", "dev_2", "dev_3"]
    
    # Test per-sensor data filtering
    sensor_df = catalog.get_sensor_data(df, "dev_1")
    assert len(sensor_df) == 2
    assert set(sensor_df["device_id"]) == {"dev_1"}


def test_sensor_catalog_fallback_to_global():
    catalog = SensorCatalog()
    df = pd.DataFrame({
        "speed": [40.0, 50.0],
        "flow": [100.0, 200.0]
    })
    catalog.build(df)
    
    assert catalog.group_column is None
    assert catalog.sensor_ids == ["global_sensor"]
    assert catalog.get_sensor_data(df, "any_sensor") is df


# =========================================================================
# 4. HistoricalMetricsCache Tests (SRP)
# =========================================================================

def test_metrics_cache_computations():
    metrics = HistoricalMetricsCache()
    df = pd.DataFrame({
        "speed": [10.0, 20.0, 30.0],
        "flow": [100.0, 200.0, 300.0]
    })
    metrics.compute(df)
    
    assert metrics.get_expected_value("speed") == pytest.approx(20.0)
    assert metrics.get_expected_value("flow") == pytest.approx(200.0)
    assert metrics.get_expected_value("unknown_metric") == 0.0
    
    stats = metrics.get_stats("speed")
    assert stats["mean"] == pytest.approx(20.0)
    assert stats["min"] == pytest.approx(10.0)
    assert stats["max"] == pytest.approx(30.0)
    assert stats["std"] == pytest.approx(10.0)


# =========================================================================
# 5. TemporalQueryEngine & Hierarchical MEH Tests
# =========================================================================

def test_temporal_query_engine_context_window():
    engine = TemporalQueryEngine()
    df = pd.DataFrame({"speed": [10.0, 20.0, 30.0]})
    
    window = engine.get_context_window(df, window_size=5)
    assert window.shape == (5, 1)
    # Check zero padding on top
    assert window[0, 0] == 0.0
    assert window[1, 0] == 0.0
    assert window[2, 0] == 10.0
    assert window[3, 0] == 20.0
    assert window[4, 0] == 30.0


def test_temporal_query_engine_hierarchical():
    engine = TemporalQueryEngine()
    catalog = SensorCatalog()
    metrics = HistoricalMetricsCache()
    
    base_ts = 1755500000.0
    base_dt = datetime.fromtimestamp(base_ts)
    
    df = pd.DataFrame([
        {"sensor_id": "sensor_x", "speed": 65.0, "timestamp": pd.Timestamp(base_dt)},
    ])
    catalog.build(df)
    metrics.compute(df)
    
    # 1. Level 1: exact second match within 10s
    val = engine.get_hierarchical_reading(df, catalog, metrics, "sensor_x", base_ts + 3.0)
    assert val == pytest.approx(65.0)
    
    # 2. Exact reading
    val_exact = engine.get_exact_reading(df, catalog, metrics, "sensor_x", base_ts, tolerance=0.1)
    assert val_exact == pytest.approx(65.0)


# =========================================================================
# 6. HistoricalDataLoader Facade Tests (DIP, OCP, Retrocompatibility)
# =========================================================================

def test_facade_injection_and_orchestration():
    mock_reader = MagicMock()
    mock_preprocessor = MagicMock()
    mock_catalog = MagicMock()
    mock_metrics = MagicMock()
    mock_query = MagicMock()
    
    dummy_raw = pd.DataFrame({"speed": [1.0, 2.0]})
    dummy_clean = pd.DataFrame({"speed": [1.0, 2.0]})
    mock_reader.read_all.return_value = (dummy_raw, {"concept": torch.tensor([1.0])})
    mock_preprocessor.process.return_value = dummy_clean
    
    loader = HistoricalDataLoader(
        reader=mock_reader,
        preprocessor=mock_preprocessor,
        catalog=mock_catalog,
        metrics=mock_metrics,
        query_engine=mock_query
    )
    
    success = loader.load()
    assert success is True
    assert loader.is_loaded is True
    
    # Verify pipeline was called in order
    mock_reader.read_all.assert_called_once()
    mock_preprocessor.process.assert_called_once_with(dummy_raw)
    mock_catalog.build.assert_called_once_with(dummy_clean)
    mock_metrics.compute.assert_called_once_with(dummy_clean)
