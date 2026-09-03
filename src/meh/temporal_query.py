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
# File: src/meh/temporal_query.py
# Author: Gabriel Moraes
# Date: 2026-02-28

from datetime import datetime
from typing import Dict, Optional
import numpy as np
import pandas as pd

from src.meh.sensor_catalog import SensorCatalog
from src.meh.metrics_cache import HistoricalMetricsCache


class TemporalQueryEngine:
    """
    Single Responsibility: Temporal lookup algorithms, cascading hierarchical
    resolution (5 MEH tiers), exact tolerance matching, and context window buffers.
    """

    def get_context_window(self, df: Optional[pd.DataFrame], window_size: int = 60) -> np.ndarray:
        """Returns the last N records from history to serve as a 'warm start' buffer."""
        if df is None or df.empty:
            return np.zeros((window_size, 1))

        numeric_df = df.select_dtypes(include=[np.number])
        data_values = numeric_df.values

        current_len = len(data_values)
        if current_len == 0:
            return np.zeros((window_size, 1))

        if current_len < window_size:
            padding = np.zeros((window_size - current_len, data_values.shape[1]))
            return np.vstack([padding, data_values])

        return data_values[-window_size:]

    def get_hierarchical_reading(
        self,
        df: Optional[pd.DataFrame],
        catalog: SensorCatalog,
        metrics: HistoricalMetricsCache,
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
        if df is None or df.empty:
            return None

        sensor_df = catalog.get_sensor_data(df, sensor_id)
        if sensor_df is None or sensor_df.empty:
            # Level 5 fallback: global expected value
            return metrics.get_expected_value(f"{sensor_id}_speed") or metrics.get_expected_value("speed")

        numeric_cols = [c for c in sensor_df.select_dtypes(include=[np.number]).columns
                        if c not in ['_day_of_week', '_seconds_since_midnight']]
        if not numeric_cols:
            return None
        val_col = numeric_cols[0]

        target_dt = datetime.fromtimestamp(target_timestamp)
        target_seconds = target_dt.hour * 3600 + target_dt.minute * 60 + target_dt.second
        target_dow = target_dt.weekday()
        target_hour = target_dt.hour

        if 'timestamp' not in sensor_df.columns:
            return float(sensor_df[val_col].mean())

        ts_col = sensor_df['timestamp']
        row_seconds = ts_col.dt.hour * 3600 + ts_col.dt.minute * 60 + ts_col.dt.second
        sec_diff = (row_seconds - target_seconds).abs()

        # --- LEVEL 1: Seconds Proximity (<= 10s) ---
        sec_tol = (level_tolerances or {}).get("seconds", 10.0)
        min_sec_diff = sec_diff.min()
        if min_sec_diff <= sec_tol:
            best_idx = sec_diff.idxmin()
            return float(sensor_df.loc[best_idx, val_col])

        # --- LEVEL 2: Minutes Proximity (<= 15 min / 900s) ---
        min_tol = (level_tolerances or {}).get("minutes", 900.0)
        if min_sec_diff <= min_tol:
            best_idx = sec_diff.idxmin()
            return float(sensor_df.loc[best_idx, val_col])

        # --- LEVEL 3: Same Day-of-Week & Same Hour (+/- 1h) ---
        dow_mask = (ts_col.dt.dayofweek == target_dow) & ((ts_col.dt.hour - target_hour).abs() <= 1)
        dow_df = sensor_df.loc[dow_mask]
        if not dow_df.empty:
            dow_sec_diff = sec_diff.loc[dow_df.index]
            best_idx = dow_sec_diff.idxmin()
            return float(dow_df.loc[best_idx, val_col])

        # --- LEVEL 4: Same Hour Across Any Day (+/- 1h) ---
        hour_mask = (ts_col.dt.hour - target_hour).abs() <= 1
        hour_df = sensor_df.loc[hour_mask]
        if not hour_df.empty:
            hour_sec_diff = sec_diff.loc[hour_df.index]
            best_idx = hour_sec_diff.idxmin()
            return float(hour_df.loc[best_idx, val_col])

        # --- LEVEL 5: Sensor Mean / Profile Fallback ---
        sensor_mean = float(sensor_df[val_col].mean())
        if not np.isnan(sensor_mean):
            return sensor_mean

        return metrics.get_expected_value(val_col)

    def get_exact_reading(
        self,
        df: Optional[pd.DataFrame],
        catalog: SensorCatalog,
        metrics: HistoricalMetricsCache,
        sensor_id: str,
        target_timestamp: float,
        tolerance: float = 0.25
    ) -> Optional[float]:
        """
        Per-sensor temporal lookup with strict tolerance fallback to cascading.
        """
        if df is None or df.empty:
            return None

        sensor_df = catalog.get_sensor_data(df, sensor_id)
        if sensor_df is None or sensor_df.empty:
            return self.get_hierarchical_reading(df, catalog, metrics, sensor_id, target_timestamp)

        if 'timestamp' in sensor_df.columns:
            target_dt = datetime.fromtimestamp(target_timestamp)
            target_seconds = target_dt.hour * 3600 + target_dt.minute * 60 + target_dt.second
            ts_col = sensor_df['timestamp']
            row_seconds = ts_col.dt.hour * 3600 + ts_col.dt.minute * 60 + ts_col.dt.second
            diff = (row_seconds - target_seconds).abs()
            min_diff = diff.min()

            if min_diff <= tolerance:
                best_idx = diff.idxmin()
                row = sensor_df.loc[best_idx]
                numeric_cols = [c for c in sensor_df.select_dtypes(include=[np.number]).columns
                                if c not in ['_day_of_week', '_seconds_since_midnight']]
                if numeric_cols:
                    return float(row[numeric_cols[0]])

        return self.get_hierarchical_reading(df, catalog, metrics, sensor_id, target_timestamp)
