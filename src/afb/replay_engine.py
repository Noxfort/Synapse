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
from datetime import datetime
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np


class ReplayEngine:
    """
    Lightweight historical replay engine for the Autonomous Fallback Bridge.
    Pure CPU / Pandas / Numpy — Zero PyTorch / GPU dependency.
    """

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or os.path.join(
            os.path.expanduser("~"), "Documentos", "SYNAPSE_CORE", "data", "datalake", "golden", "golden_v1.parquet"
        )
        self.data: Optional[pd.DataFrame] = None
        self.sensor_ids: List[str] = []
        self.is_loaded = False
        self._load_data()

    def _load_data(self) -> bool:
        """Loads historical parquet dataset for replay."""
        if not os.path.exists(self.data_path):
            # Fallback path check
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
                self.sensor_ids = list(dict.fromkeys(self.data[group_col].dropna().unique().tolist()))
            else:
                self.sensor_ids = ['global_sensor']

            # Auto-detect timestamp column
            time_cols = ['timestamp', 'event_timestamp', 'time', 'datetime', 'date']
            time_col = next((c for c in time_cols if c in self.data.columns), None)
            if time_col:
                if time_col != 'timestamp':
                    self.data.rename(columns={time_col: 'timestamp'}, inplace=True)
                self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])

            self.is_loaded = True
            return True
        except Exception:
            self.is_loaded = False
            return False

    def get_replay_frame(self, target_timestamp: Optional[float] = None) -> Dict[str, Any]:
        """
        Retrieves the historical replay readings matching the target time of day.
        
        Args:
            target_timestamp: Epoch timestamp. If None, uses current time.time().
            
        Returns:
            Dictionary {sensor_id: {speed, density, queue, status, timestamp}}
        """
        ts = target_timestamp or time.time()
        target_dt = datetime.fromtimestamp(ts)
        target_seconds = target_dt.hour * 3600 + target_dt.minute * 60 + target_dt.second

        frame: Dict[str, Any] = {
            "_metadata": {
                "strategy": "AFB_REPLAY",
                "timestamp": ts,
                "time_of_day": target_dt.strftime("%H:%M:%S"),
                "is_fallback": True
            },
            "readings": {}
        }

        if not self.is_loaded or self.data is None or self.data.empty:
            # Synthetic safe baseline fallback if no file exists
            for sid in self.sensor_ids or ["sensor_fallback"]:
                frame["readings"][sid] = {
                    "speed": 40.0,
                    "density": 12.0,
                    "queue": 0.0,
                    "confidence": 0.50
                }
            return frame

        # Find closest match in time-of-day
        if 'timestamp' in self.data.columns:
            ts_col = self.data['timestamp']
            row_seconds = ts_col.dt.hour * 3600 + ts_col.dt.minute * 60 + ts_col.dt.second
            diff = (row_seconds - target_seconds).abs()
            best_idx = diff.idxmin()
            
            # Numeric columns
            numeric_cols = [c for c in self.data.select_dtypes(include=[np.number]).columns
                            if c not in ['_day_of_week', '_seconds_since_midnight']]
            
            matched_row = self.data.loc[best_idx]
            base_speed = float(matched_row[numeric_cols[0]]) if numeric_cols else 40.0
            
            for sid in self.sensor_ids:
                frame["readings"][sid] = {
                    "speed": base_speed,
                    "density": 10.0,
                    "queue": 0.0,
                    "confidence": 0.90,
                    "source": "synapse_historical_transmission"
                }
        else:
            for sid in self.sensor_ids:
                frame["readings"][sid] = {
                    "speed": 40.0,
                    "density": 10.0,
                    "queue": 0.0,
                    "confidence": 0.50
                }

        return frame
