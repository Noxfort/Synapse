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
# File: src/afb/replay_engine.py
# Author: Gabriel Moraes
# Date: 2026-08-18

"""
AFB Replay Engine — Autonomous Fallback Bridge (Replay of Transmitted Data).

Single Responsibility:
Extracts and replays historical traffic data that Synapse already validated
and transmitted at the same time-of-day.
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
import pandas as pd
import numpy as np

logger = logging.getLogger("Synapse.AFB.ReplayEngine")


class ReplayEngine:
    """
    Historical replay engine for the Autonomous Fallback Bridge.
    Pure CPU / Pandas / Numpy — Zero PyTorch / GPU dependency.
    
    Extracts and replays historical traffic data that Synapse already validated
    and transmitted at the same time-of-day.
    
    Resolution Hierarchy (MEH-aligned 5 tiers):
    - Level 1: Seconds match (+/- 10s)
    - Level 2: Minutes proximity (+/- 15 min / 900s)
    - Level 3: Same day-of-week & same hour (+/- 1h)
    - Level 4: Same hour across any day (+/- 1h)
    - Level 5: Sensor expected mean / baseline
    """

    def __init__(
        self,
        data_path: Optional[str] = None,
        db_engine: Optional[Any] = None,
        telemetry_reader: Optional[Any] = None,
    ):
        self.data_path = data_path or os.path.join(
            os.path.expanduser("~"), "Documentos", "SYNAPSE_CORE", "data", "datalake", "golden", "golden_v1.parquet"
        )
        self.db_engine = db_engine
        self.telemetry_reader = telemetry_reader
        self.data: Optional[pd.DataFrame] = None
        self.sensor_ids: List[str] = []
        self.is_loaded = False
        self.source_type: str = "none"

        # 1. Try to load from database first (highest priority: Synapse's own validated transmissions)
        loaded = self._load_from_db()
        
        # 2. If DB is unavailable or empty, fallback to parquet file
        if not loaded:
            self._load_from_parquet()

    def _load_from_db(self) -> bool:
        """Loads historical transmissions directly from the PostgreSQL database."""
        try:
            # If no db_engine or telemetry_reader passed, attempt to instantiate default DatabaseEngine
            reader = self.telemetry_reader
            if reader is None:
                if self.db_engine is None:
                    try:
                        from src.database.db_engine import DatabaseEngine
                        self.db_engine = DatabaseEngine()
                    except Exception:
                        self.db_engine = None

                if self.db_engine is not None:
                    from src.repositories.sensor_telemetry_reader import SensorTelemetryReader
                    reader = SensorTelemetryReader(self.db_engine)

            if reader is not None:
                samples = reader.query_telemetry_history(limit_seconds=None)
                if samples:
                    df = pd.DataFrame(samples)
                    if not df.empty and "collected_at" in df.columns:
                        df["timestamp"] = pd.to_datetime(df["collected_at"])
                        
                        sensor_col = "sensor_str_id" if "sensor_str_id" in df.columns else "sensor_int_id"
                        if sensor_col in df.columns:
                            df["sensor_id"] = df[sensor_col].astype(str)
                            self.sensor_ids = list(dict.fromkeys(df["sensor_id"].dropna().unique().tolist()))
                        else:
                            df["sensor_id"] = "global_sensor"
                            self.sensor_ids = ["global_sensor"]

                        self.data = df
                        self.is_loaded = True
                        self.source_type = "database"
                        logger.info(f"[ReplayEngine] Loaded {len(df)} records for {len(self.sensor_ids)} sensors from database.")
                        return True
        except Exception as e:
            logger.debug(f"[ReplayEngine] Could not load telemetry from DB: {e}")

        return False

    def _load_from_parquet(self) -> bool:
        """Loads historical parquet dataset for replay as fallback."""
        if not os.path.exists(self.data_path):
            alt_path = os.path.join(os.getcwd(), "data", "datalake", "golden", "golden_v1.parquet")
            if os.path.exists(alt_path):
                self.data_path = alt_path
            else:
                return False

        try:
            self.data = pd.read_parquet(self.data_path)
            
            # Detect sensor column
            candidates = ['sensor_id', 'device_id', 'camera_id', 'source_id', 'id']
            group_col = next((c for c in candidates if c in self.data.columns), None)
            
            if group_col:
                self.data["sensor_id"] = self.data[group_col].astype(str)
                self.sensor_ids = list(dict.fromkeys(self.data["sensor_id"].dropna().unique().tolist()))
            else:
                self.data["sensor_id"] = 'global_sensor'
                self.sensor_ids = ['global_sensor']

            # Auto-detect timestamp column
            time_cols = ['timestamp', 'event_timestamp', 'time', 'datetime', 'date']
            time_col = next((c for c in time_cols if c in self.data.columns), None)
            if time_col:
                if time_col != 'timestamp':
                    self.data.rename(columns={time_col: 'timestamp'}, inplace=True)
                self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])

            self.is_loaded = True
            self.source_type = "parquet"
            logger.info(f"[ReplayEngine] Loaded {len(self.data)} records from parquet: {self.data_path}")
            return True
        except Exception as e:
            logger.warning(f"[ReplayEngine] Failed to load parquet dataset: {e}")
            self.is_loaded = False
            return False

    def get_replay_frame(self, target_timestamp: Optional[float] = None) -> Dict[str, Any]:
        """
        Retrieves historical replay readings matching the target time-of-day
        using the MEH 5-tier hierarchical resolution cascade.
        
        Args:
            target_timestamp: Epoch timestamp. If None, uses current time.time().
            
        Returns:
            Dictionary {sensor_id: {speed, density, queue, flow_rate, occupancy, confidence, source}}
        """
        ts = target_timestamp or time.time()
        target_dt = datetime.fromtimestamp(ts)
        target_seconds = target_dt.hour * 3600 + target_dt.minute * 60 + target_dt.second
        target_dow = target_dt.weekday()
        target_hour = target_dt.hour

        frame: Dict[str, Any] = {
            "_metadata": {
                "strategy": "AFB_DATABASE_REPLAY" if self.source_type == "database" else "AFB_REPLAY",
                "source": self.source_type,
                "timestamp": ts,
                "time_of_day": target_dt.strftime("%H:%M:%S"),
                "day_of_week": target_dow,
                "is_fallback": True,
                "resolution_tier": "tier_5_safe_baseline",
            },
            "readings": {}
        }

        # Safe baseline if no data available
        if not self.is_loaded or self.data is None or self.data.empty:
            for sid in self.sensor_ids or ["sensor_fallback"]:
                frame["readings"][sid] = {
                    "speed": 40.0,
                    "density": 12.0,
                    "queue": 0.0,
                    "flow_rate": 200.0,
                    "occupancy": 0.10,
                    "confidence": 0.50,
                    "source": "synthetic_baseline"
                }
            return frame

        dominant_tier = "tier_5_sensor_mean"

        for sid in self.sensor_ids:
            sensor_df = self.data[self.data["sensor_id"] == sid] if "sensor_id" in self.data.columns else self.data
            if sensor_df.empty:
                sensor_df = self.data

            reading, tier = self._resolve_sensor_reading(
                sensor_df, target_dt, target_seconds, target_dow, target_hour
            )
            frame["readings"][sid] = reading
            dominant_tier = tier

        frame["_metadata"]["resolution_tier"] = dominant_tier
        return frame

    def _resolve_sensor_reading(
        self,
        df: pd.DataFrame,
        target_dt: datetime,
        target_seconds: float,
        target_dow: int,
        target_hour: int,
    ) -> tuple[Dict[str, Any], str]:
        """
        Applies the 5-Tier Hierarchical Cascade on the given sensor DataFrame.
        """
        if "timestamp" not in df.columns:
            # Tier 5 directly
            mean_speed = float(df["speed"].mean()) if "speed" in df.columns else 40.0
            return {
                "speed": mean_speed,
                "density": 10.0,
                "queue": 0.0,
                "flow_rate": 200.0,
                "occupancy": 0.10,
                "confidence": 0.50,
                "source": "synapse_historical_mean"
            }, "tier_5_sensor_mean"

        ts_col = df["timestamp"]
        row_seconds = ts_col.dt.hour * 3600 + ts_col.dt.minute * 60 + ts_col.dt.second
        sec_diff = (row_seconds - target_seconds).abs()

        matched_row: Optional[pd.Series] = None
        tier = "tier_5_sensor_mean"
        confidence = 0.50

        # --- LEVEL 1: Exact Seconds Proximity (<= 10s) ---
        min_sec_diff = sec_diff.min()
        if min_sec_diff <= 10.0:
            best_idx = sec_diff.idxmin()
            matched_row = df.loc[best_idx]
            tier = "tier_1_seconds"
            confidence = 0.95

        # --- LEVEL 2: Minutes Proximity (<= 15 min / 900s) ---
        elif min_sec_diff <= 900.0:
            best_idx = sec_diff.idxmin()
            matched_row = df.loc[best_idx]
            tier = "tier_2_minutes"
            confidence = 0.85

        # --- LEVEL 3: Same Day-of-Week & Same Hour (+/- 1h) ---
        else:
            dow_mask = (ts_col.dt.dayofweek == target_dow) & ((ts_col.dt.hour - target_hour).abs() <= 1)
            dow_df = df.loc[dow_mask]
            if not dow_df.empty:
                dow_sec_diff = sec_diff.loc[dow_df.index]
                best_idx = dow_sec_diff.idxmin()
                matched_row = df.loc[best_idx]
                tier = "tier_3_weekday_hour"
                confidence = 0.75

            # --- LEVEL 4: Same Hour Across Any Day (+/- 1h) ---
            else:
                hour_mask = (ts_col.dt.hour - target_hour).abs() <= 1
                hour_df = df.loc[hour_mask]
                if not hour_df.empty:
                    hour_sec_diff = sec_diff.loc[hour_df.index]
                    best_idx = hour_sec_diff.idxmin()
                    matched_row = df.loc[best_idx]
                    tier = "tier_4_global_hour"
                    confidence = 0.65

        # Extract values from matched row or fall back to Level 5 mean
        if matched_row is not None:
            speed = float(matched_row["speed"]) if "speed" in matched_row and pd.notna(matched_row["speed"]) else 40.0
            flow_rate = float(matched_row["flow_rate"]) if "flow_rate" in matched_row and pd.notna(matched_row["flow_rate"]) else 200.0
            occupancy = float(matched_row["occupancy"]) if "occupancy" in matched_row and pd.notna(matched_row["occupancy"]) else 0.10
            density = float(matched_row["density"]) if "density" in matched_row and pd.notna(matched_row["density"]) else max(5.0, occupancy * 100.0)
            queue = float(matched_row["queue"]) if "queue" in matched_row and pd.notna(matched_row["queue"]) else 0.0
        else:
            # --- LEVEL 5: Sensor Mean Profile Fallback ---
            tier = "tier_5_sensor_mean"
            confidence = 0.50
            speed = float(df["speed"].mean()) if "speed" in df.columns and not df["speed"].dropna().empty else 40.0
            flow_rate = float(df["flow_rate"].mean()) if "flow_rate" in df.columns and not df["flow_rate"].dropna().empty else 200.0
            occupancy = float(df["occupancy"].mean()) if "occupancy" in df.columns and not df["occupancy"].dropna().empty else 0.10
            density = max(5.0, occupancy * 100.0)
            queue = 0.0

        reading = {
            "speed": speed,
            "density": density,
            "queue": queue,
            "flow_rate": flow_rate,
            "occupancy": occupancy,
            "confidence": confidence,
            "source": f"synapse_historical_{self.source_type}"
        }
        return reading, tier
