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
# File: src/meh/data_loader.py
# Author: Gabriel Moraes
# Date: 2026-02-28

import time
from typing import Optional, Dict, List
import pandas as pd
import numpy as np
import torch

from src.managers.storage_manager import StorageManager
from src.utils.logging_setup import logger
from src.meh.data_reader import DataLakeReader
from src.meh.data_preprocessor import DatasetPreprocessor
from src.meh.sensor_catalog import SensorCatalog
from src.meh.metrics_cache import HistoricalMetricsCache
from src.meh.temporal_query import TemporalQueryEngine


class HistoricalDataLoader:
    """
    Façade & Orchestrator Pattern (SOLID-compliant).
    Coordinates specialized MEH subcomponents:
      - DataLakeReader: Disk I/O (Parquet & Safetensors)
      - DatasetPreprocessor: Normalization, capping & memory optimization
      - SensorCatalog: Sensor discovery and per-sensor filtering
      - HistoricalMetricsCache: Statistical profile and expected values
      - TemporalQueryEngine: Cascading hierarchical temporal resolution
    """
    MAX_ROWS = DatasetPreprocessor.TIME_COL_CANDIDATES
    SENSOR_ID_CANDIDATES = SensorCatalog.SENSOR_ID_CANDIDATES

    def __init__(
        self,
        reader: Optional[DataLakeReader] = None,
        preprocessor: Optional[DatasetPreprocessor] = None,
        catalog: Optional[SensorCatalog] = None,
        metrics: Optional[HistoricalMetricsCache] = None,
        query_engine: Optional[TemporalQueryEngine] = None,
        storage_manager: Optional[StorageManager] = None
    ):
        # Injected or default specialized components
        self.reader = reader or DataLakeReader(storage_manager=storage_manager)
        self.preprocessor = preprocessor or DatasetPreprocessor()
        self.catalog = catalog or SensorCatalog()
        self.metrics = metrics or HistoricalMetricsCache()
        self.query_engine = query_engine or TemporalQueryEngine()

        # Public state & paths (backward-compatible)
        self.storage = self.reader.storage
        self.gold_path = self.reader.gold_path
        self.config_path = self.reader.config_path

        self.data: Optional[pd.DataFrame] = None
        self.ontology: Dict[str, torch.Tensor] = {}
        self.is_loaded: bool = False

    @property
    def stats_cache(self) -> Dict[str, Dict[str, float]]:
        return self.metrics.stats_cache

    @stats_cache.setter
    def stats_cache(self, value: Dict[str, Dict[str, float]]):
        self.metrics.stats_cache = value

    @property
    def group_column(self) -> Optional[str]:
        return self.catalog.group_column

    @group_column.setter
    def group_column(self, value: Optional[str]):
        self.catalog.group_column = value

    @property
    def sensor_ids(self) -> List[str]:
        return self.catalog.sensor_ids

    @sensor_ids.setter
    def sensor_ids(self, value: List[str]):
        self.catalog.sensor_ids = value

    def load(self) -> bool:
        """Orchestrates loading data from disk into memory."""
        try:
            # 1. Read Raw Data & Ontology from Disk
            raw_data, self.ontology = self.reader.read_all()
            if raw_data is None:
                self.is_loaded = False
                return False

            # 2. Preprocess, Downcast & Index
            self.data = self.preprocessor.process(raw_data)

            # 3. Build Sensor Catalog
            self._build_sensor_catalog()

            # 4. Calculate Historical Metrics
            self._calculate_statistics()

            self.is_loaded = True
            time.sleep(0.01)  # Final GIL yield before moving on

            mem_mb = self.data.memory_usage(deep=True).sum() / (1024 * 1024)
            logger.info(
                f"[HistoricalDataLoader] ✅ Loaded Golden History: {len(self.data)} records "
                f"({mem_mb:.1f} MB RAM). Sensors detected: {len(self.sensor_ids)}."
            )
            return True

        except Exception as e:
            logger.error(f"[HistoricalDataLoader] ❌ Failed to load dataset: {str(e)}")
            import traceback
            traceback.print_exc()
            self.is_loaded = False
            return False

    def _calculate_statistics(self):
        """Calculates Mean/Std/Min/Max for all numeric columns."""
        if not self.is_loaded and self.data is None:
            return
        self.metrics.compute(self.data)

    def _build_sensor_catalog(self):
        """Detects the sensor grouping column and builds a catalog of distinct sensor IDs."""
        self.catalog.build(self.data)

    def get_context_window(self, window_size: int = 60) -> np.ndarray:
        """Returns the last N records from history to serve as a 'warm start' buffer."""
        return self.query_engine.get_context_window(self.data, window_size=window_size)

    def get_expected_value(self, metric_name: str) -> float:
        """Returns the historical mean for a specific metric."""
        return self.metrics.get_expected_value(metric_name)

    def get_sensor_data(self, sensor_id: str) -> Optional[pd.DataFrame]:
        """Returns only the rows for a specific sensor."""
        return self.catalog.get_sensor_data(self.data, sensor_id)

    def get_hierarchical_reading(
        self,
        sensor_id: str,
        target_timestamp: float,
        level_tolerances: Optional[Dict[str, float]] = None
    ) -> Optional[float]:
        """
        Hierarchical Multi-Tier Temporal Resolution (MEH Cascading Lookup):
        - Level 1 (Seconds): Exact match within +/- 10s.
        - Level 2 (Minutes): Match within +/- 15min (900s).
        - Level 3 (Day-of-Week & Hour): Match for same weekday at same hour (+/- 1h).
        - Level 4 (Global Daily Hour): Match for same hour on any day.
        - Level 5 (Sensor Profile / Regional Mean): Sensor's historical expected mean.
        """
        return self.query_engine.get_hierarchical_reading(
            df=self.data,
            catalog=self.catalog,
            metrics=self.metrics,
            sensor_id=sensor_id,
            target_timestamp=target_timestamp,
            level_tolerances=level_tolerances
        )

    def get_exact_reading(
        self,
        sensor_id: str,
        target_timestamp: float,
        tolerance: float = 0.25
    ) -> Optional[float]:
        """Per-sensor temporal lookup with fallback to cascading resolution."""
        return self.query_engine.get_exact_reading(
            df=self.data,
            catalog=self.catalog,
            metrics=self.metrics,
            sensor_id=sensor_id,
            target_timestamp=target_timestamp,
            tolerance=tolerance
        )

    @property
    def columns(self) -> List[str]:
        if self.data is not None:
            return list(self.data.columns)
        return []
