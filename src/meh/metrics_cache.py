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
# File: src/meh/metrics_cache.py
# Author: Gabriel Moraes
# Date: 2026-02-28

from typing import Dict, Optional
import numpy as np
import pandas as pd


class HistoricalMetricsCache:
    """
    Single Responsibility: Statistical metric calculations and caching
    (Mean, Std, Min, Max) for historical datasets.
    """

    def __init__(self):
        self.stats_cache: Dict[str, Dict[str, float]] = {}

    def compute(self, df: Optional[pd.DataFrame]) -> None:
        """Calculates and caches Mean/Std/Min/Max for all numeric columns."""
        self.stats_cache.clear()
        if df is None or df.empty:
            return

        numeric_df = df.select_dtypes(include=[np.number])
        for col in numeric_df.columns:
            self.stats_cache[col] = {
                "mean": float(numeric_df[col].mean()),
                "std": float(numeric_df[col].std()) if len(numeric_df[col]) > 1 else 0.0,
                "min": float(numeric_df[col].min()),
                "max": float(numeric_df[col].max())
            }

    def get_expected_value(self, metric_name: str) -> float:
        """Returns the historical mean for a specific metric."""
        if metric_name in self.stats_cache:
            return self.stats_cache[metric_name].get("mean", 0.0)
        return 0.0

    def get_stats(self, metric_name: str) -> Optional[Dict[str, float]]:
        """Returns all cached statistics for a specific metric."""
        return self.stats_cache.get(metric_name)
