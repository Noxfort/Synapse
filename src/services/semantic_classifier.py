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
# File: src/services/semantic_classifier.py
# Author: Gabriel Moraes
# Date: 2026-08-20

from typing import Any, List, Tuple, Optional
import numpy as np
from src.interfaces.quarantine import ISemanticClassifier
from src.domain.entities import DataSource


class SemanticClassifier(ISemanticClassifier):
    """
    Classifies traffic sensor semantics (semantic type, engineering unit, and confidence)
    based on metadata context, payload schema structure, and signal characteristics,
    independent of rigid numerical magnitude assumptions.
    """

    CAMERA_KEYWORDS = ["camera", "cam", "video", "cftv", "vis", "yolo", "det", "vision"]
    SPEED_KEYWORDS = ["speed", "vel", "radar", "tomtom", "gps", "kmh", "mph", "currentspeed"]
    FLOW_KEYWORDS = ["flow", "fluxo", "volume", "loop", "count", "veic", "waze", "currentflow"]
    DENSITY_KEYWORDS = ["density", "densidade", "occ", "occupancy", "rho"]

    def classify(
        self,
        source: DataSource,
        data_np: np.ndarray,
        data_chunk: Optional[List[Any]] = None
    ) -> Tuple[str, str, float]:
        """
        Infers semantic type, engineering unit, and confidence from sensor metadata and schema.
        
        Args:
            source: The DataSource entity.
            data_np: 1D NumPy array of numerical values.
            data_chunk: Optional raw payload chunk for structural schema inspection.
            
        Returns:
            Tuple[str, str, float]: (semantic_type, unit, confidence)
        """
        name_and_conn = f"{source.name} {source.id} {getattr(source, 'connection_string', '') or ''}".lower()

        # 1. Inspect Payload Structure if available
        if data_chunk and len(data_chunk) > 0:
            sample_item = data_chunk[0]
            if isinstance(sample_item, dict):
                # Computer Vision detections / objects
                if any(k in sample_item for k in ["detections", "vehicles", "objects", "boxes", "tracks"]):
                    return "Vehicle Count", "vehicles", 0.95
                # TomTom flowSegmentData with currentSpeed
                if "flowSegmentData" in sample_item:
                    nested = sample_item["flowSegmentData"]
                    if isinstance(nested, dict) and "currentSpeed" in nested:
                        return "Vehicle Speed", "km/h", 0.95
                # Direct keys
                if any(k in sample_item for k in ["currentSpeed", "speed", "velocidade"]):
                    return "Vehicle Speed", "km/h", 0.95
                if any(k in sample_item for k in ["currentFlow", "flow", "fluxo", "volume"]):
                    return "Traffic Flow", "veh/h", 0.95
                if any(k in sample_item for k in ["occupancy", "density", "densidade"]):
                    return "Traffic Density", "veh/km", 0.95
                if any(k in sample_item for k in ["vehicle_count", "counted_in_frame", "count"]):
                    return "Vehicle Count", "vehicles", 0.95

        # 2. Keyword analysis on sensor metadata
        if any(k in name_and_conn for k in self.CAMERA_KEYWORDS):
            return "Vehicle Count", "vehicles", 0.95
        if any(k in name_and_conn for k in self.SPEED_KEYWORDS):
            return "Vehicle Speed", "km/h", 0.95
        if any(k in name_and_conn for k in self.FLOW_KEYWORDS):
            return "Traffic Flow", "veh/h", 0.95
        if any(k in name_and_conn for k in self.DENSITY_KEYWORDS):
            return "Traffic Density", "veh/km", 0.95

        # 3. Fallback Heuristic
        mean_val = float(np.mean(data_np)) if len(data_np) > 0 else 0.0
        if mean_val > 150.0:
            return "Traffic Flow", "veh/h", 0.85
        elif 5.0 <= mean_val <= 150.0:
            return "Vehicle Speed", "km/h", 0.85
        else:
            return "Traffic State", "units", 0.80
