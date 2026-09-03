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
# File: src/services/historical_manager.py
# Author: Gabriel Moraes
# Date: 2026-02-28

from datetime import datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING
import numpy as np

from PyQt6.QtCore import QObject
from src.utils.logging_setup import logger

# Import the new MEH specialized engines
from src.meh.data_loader import HistoricalDataLoader
from src.meh.fallback_engine import FallbackEngine
from src.meh.playback_engine import PlaybackEngine

# Lazy Type Hinting to prevent circular imports
if TYPE_CHECKING:
    from src.domain.app_state import AppState

class HistoricalManager(QObject):
    """
    Facade/Orchestrator for the Historical and MEH (Historical State Module) subsystems.
    
    Responsibilities:
    - Delegates I/O and Analytics to HistoricalDataLoader.
    - Delegates Level 1/2 Temporal Fallback logic to FallbackEngine.
    - Delegates sequential Simulation to PlaybackEngine.
    - Formats the flat MEH payload into KSE Edge-specific payloads.
    """

    def __init__(self, app_state: 'AppState'):
        super().__init__()
        self.app_state = app_state
        
        # Instantiate the specialized MEH engines (SOLID Principles)
        self.loader = HistoricalDataLoader()
        self.fallback_engine = FallbackEngine(self.loader)
        self.playback_engine = PlaybackEngine(self.loader)
        
        # Attempt immediate load upon initialization
        self.load_data()

    def load_data(self) -> bool:
        """
        Orchestrates the loading of data and the building of MEH profiles.
        """
        logger.info("[HistoricalManager] Starting data load sequence...")
        success = self.loader.load()
        
        if success:
            self.fallback_engine.build_profiles()
            self.playback_engine.reset()
            if self.app_state:
                self.app_state.is_meh_ready = True
            return True
            
        return False

    # =========================================================================
    # KSE INTERFACE (The Connector)
    # =========================================================================

    def get_current_state_prediction(self) -> Dict[str, dict]:
        """
        Called by KSEManager when real-time sensors fail.
        Returns a structured dictionary {edge_id: {speed, density, queue}} 
        representing the expected traffic for the current moment.
        
        V2: Falls back to sensor profiles when no edges are configured.
        """
        now = datetime.now()
        
        # 1. Get Flat Data from the MEH Fallback Engine
        flat_data = self.get_meh_state(now)
        
        # 2. Structure Data for KSE (Map flat columns to Edges)
        result = {}
        
        K_JAM = 125.0
        VEH_EFFECTIVE_LEN = 7.5

        if self.app_state:
            edges = self.app_state.get_all_edges()
            
            if edges:
                # Normal path: map data to edges
                for edge in edges:
                    v_free = getattr(edge, "max_speed", 13.89)
                    edge_len = getattr(edge, "length", 100.0)
                    edge_lanes = getattr(edge, "lanes", 1)
                    max_capacity = max(1, int((edge_len / VEH_EFFECTIVE_LEN) * edge_lanes))

                    # DEFAULT VALUES (Safety Baseline)
                    density_val = 15.0
                    speed_val = v_free
                    queue_val = 0.0
                    
                    # INTELLIGENT MAPPING
                    speed_key = f"{edge.id}_speed"
                    density_key = f"{edge.id}_density"
                    queue_key = f"{edge.id}_queue"
                    
                    if speed_key in flat_data:
                        speed_val = float(flat_data[speed_key])
                    if density_key in flat_data:
                        density_val = float(flat_data[density_key])
                    if queue_key in flat_data:
                        queue_val = float(flat_data[queue_key])
                    else:
                        # Greenshields & HCM Queue Model
                        congestion_ratio = max(0.0, 1.0 - (speed_val / v_free))
                        density_ratio = density_val / K_JAM
                        queue_val = congestion_ratio * density_ratio * max_capacity
                        if getattr(edge, "signal_group_id", -1) != -1:
                            queue_val = max(queue_val, density_ratio * min(6, max_capacity))
                    
                    occupancy_val = min(0.98, max(0.02, density_val / K_JAM))
                    speed_val = max(1.0, min(v_free * 1.1, speed_val))
                    density_val = min(K_JAM, max(0.5, density_val))
                    
                    edge_stats = {
                        "speed": speed_val,
                        "density": density_val,
                        "queue": int(round(min(max_capacity, max(0, queue_val)))),
                        "occupancy": occupancy_val
                    }
                    
                    result[edge.id] = edge_stats
            elif flat_data:
                # Fallback path: No edges configured, use flat sensor data directly
                for sensor_id in self.fallback_engine.sensor_profiles.keys():
                    d_val = float(flat_data.get(f"{sensor_id}_density", flat_data.get("density", 15.0)))
                    s_val = float(flat_data.get(f"{sensor_id}_speed", flat_data.get("speed", 13.89)))
                    q_val = float(flat_data.get(f"{sensor_id}_queue", flat_data.get("queue", 0.0)))
                    if q_val <= 0.0 and (s_val < 10.0 or d_val > 25.0):
                        q_val = max(1.0, (1.0 - s_val / 13.89) * (d_val / K_JAM) * 15)
                    result[sensor_id] = {
                        "speed": s_val,
                        "density": d_val,
                        "queue": int(round(q_val)),
                        "occupancy": min(0.98, max(0.02, d_val / K_JAM)),
                    }
                
                # If still empty, create at least one entry from the raw flat data
                if not result and flat_data:
                    d_val = float(flat_data.get("density", 15.0))
                    result["synthetic_edge"] = {
                        "speed": float(flat_data.get("speed", 40.0)),
                        "density": d_val,
                        "queue": int(round(float(flat_data.get("queue", 1.0)))),
                        "occupancy": min(1.0, max(0.05, d_val / 100.0)),
                    }
                
        return result

    def get_exact_reading(self, sensor_id: str, target_timestamp: float, tolerance: float = 0.25) -> Optional[float]:
        """
        Per-sensor temporal lookup in the Golden Database.
        Delegated to the DataLoader for actual I/O.
        
        Called by TrafficNode.ghost_step() to find historical data
        for a specific sensor at the current time-of-day.
        
        Args:
            sensor_id: The sensor/node ID (matches parquet sensor_id column).
            target_timestamp: Unix epoch timestamp (time.time()).
            tolerance: Maximum time-of-day difference in seconds.
            
        Returns:
            Float value if a historical match exists, None otherwise.
        """
        return self.loader.get_exact_reading(sensor_id, target_timestamp, tolerance)

    def get_hierarchical_reading(
        self,
        sensor_id: str,
        target_timestamp: float,
        level_tolerances: Optional[Dict[str, float]] = None
    ) -> Optional[float]:
        """
        Hierarchical Multi-Tier Temporal Resolution (Seconds -> Minutes -> Weekday -> Hour -> Mean).
        Delegated to HistoricalDataLoader (SRP).
        """
        return self.loader.get_hierarchical_reading(sensor_id, target_timestamp, level_tolerances)

    # =========================================================================
    # MEH INTERFACE (Level 3 Fallback - Temporal Lookup)
    # =========================================================================

    def get_meh_state(self, target_time: datetime) -> Dict[str, Any]:
        """
        Delegates the temporal lookup to the Fallback Engine.
        If the Fallback Engine cannot resolve, degrades to Playback Engine.
        """
        state = self.fallback_engine.get_fallback_state(target_time)
        if not state:
            logger.warning("[HistoricalManager] MEH Fallback failed, degrading to Playback Simulation.")
            return self.get_next_playback_frame()
        return state

    # =========================================================================
    # SIMULATION / PLAYBACK INTERFACE (Sequential)
    # =========================================================================

    def get_next_playback_frame(self) -> Dict[str, float]:
        """Delegates to Playback Engine."""
        return self.playback_engine.get_next_frame()

    def reset_playback(self):
        """Delegates to Playback Engine."""
        self.playback_engine.reset()

    # =========================================================================
    # ANALYTICAL INTERFACE (Statistics)
    # =========================================================================

    def get_expected_value(self, metric_name: str) -> float:
        """Delegates to Data Loader."""
        return self.loader.get_expected_value(metric_name)

    def get_context_window(self, window_size: int = 60) -> np.ndarray:
        """Delegates to Data Loader."""
        return self.loader.get_context_window(window_size)

    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        """Delegates to Data Loader."""
        return self.loader.stats_cache

    @property
    def columns(self) -> List[str]:
        return self.loader.columns

    @property
    def is_ready(self) -> bool:
        return self.loader.is_loaded
