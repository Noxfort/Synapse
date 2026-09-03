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
# File: src/meh/data_preprocessor.py
# Author: Gabriel Moraes
# Date: 2026-02-28

import gc
import time
from typing import List, Optional
import numpy as np
import pandas as pd

from src.utils.logging_setup import logger


class DatasetPreprocessor:
    """
    Single Responsibility: DataFrame sanitization, memory optimization (downcasting),
    and datetime indexing for historical traffic datasets.
    """

    TIME_COL_CANDIDATES: List[str] = ['timestamp', 'event_timestamp', 'time', 'datetime', 'date']

    def __init__(self, max_rows: int = 500_000):
        self.max_rows = max_rows

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Sanitizes and optimizes a raw DataFrame."""
        if df is None or df.empty:
            return df

        processed_df = df.copy()

        # 1. Cap rows to prevent OOM
        original_len = len(processed_df)
        if original_len > self.max_rows:
            logger.warning(
                f"[DatasetPreprocessor] ⚠️ Dataset has {original_len} rows, "
                f"capping to {self.max_rows} most recent rows to save memory."
            )
            processed_df = processed_df.tail(self.max_rows).reset_index(drop=True)
            gc.collect()
            time.sleep(0.01)

        # 2. Downcast numeric columns to save RAM (float64 -> float32, int64 -> downcast)
        float_cols = processed_df.select_dtypes(include=['float64']).columns
        for col in float_cols:
            processed_df[col] = processed_df[col].astype(np.float32)

        int_cols = processed_df.select_dtypes(include=['int64']).columns
        for col in int_cols:
            processed_df[col] = pd.to_numeric(processed_df[col], downcast='integer')

        # 3. Detect and index timestamp column
        time_col = next((col for col in self.TIME_COL_CANDIDATES if col in processed_df.columns), None)
        if time_col:
            if time_col != 'timestamp':
                processed_df.rename(columns={time_col: 'timestamp'}, inplace=True)

            processed_df['timestamp'] = pd.to_datetime(processed_df['timestamp'])
            processed_df.set_index('timestamp', inplace=True, drop=False)
            processed_df.index.name = 'time_idx'
            processed_df.sort_index(inplace=True)

        return processed_df
