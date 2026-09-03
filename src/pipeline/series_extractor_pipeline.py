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
# File: src/pipeline/series_extractor_pipeline.py
# Author: Gabriel Moraes
# Date: 2026-08-20

from typing import Any, List, Optional, Set, Union
import numpy as np
from src.interfaces.quarantine import ISeriesExtractorPipeline


class SeriesExtractorPipeline(ISeriesExtractorPipeline):
    """
    Intelligent Schema-Aware Pipeline for extracting and sanitizing 1D numeric time-series
    from heterogeneous sensor payloads (Computer Vision detection lists, nested JSON APIs,
    discrete event streams, and raw scalars).
    """

    # Priority keys for traffic measurements (in order of priority)
    PRIMARY_TRAFFIC_KEYS = [
        "currentspeed_kmh", "freeflowspeed_kmh", "currentSpeed", "freeFlowSpeed",
        "speed", "velocidade", "vel", "kmh", "speedkmh", "estimated_speed_kmh", "speed_kmh",
        "currentFlow", "flow", "fluxo", "volume", "q", "field_7", "field_8",
        "vehicle_count", "counted_in_frame", "count", "contagem", "cars", "veic",
        "occupancy", "density", "densidade", "rho", "occ",
        "reading", "value", "val", "delay", "delay_seconds"
    ]

    # Keys that represent object/detection lists in computer vision / camera payloads
    DETECTION_LIST_KEYS = [
        "recognitions", "jams", "detections", "vehicles", "objects", "boxes",
        "tracks", "detected_objects", "targets", "plates", "items"
    ]

    # Explicit blacklist of ID, timestamp, and metadata keys that must never be treated as measurements
    IGNORE_KEYS: Set[str] = {
        "packet_id", "sensor_id", "device_id", "segmentid", "segment_id",
        "track_id", "frame_id", "camera_id", "node_id", "edge_id", "id",
        "timestamp", "starttimemillis", "endtimemillis", "created_at", "updated_at",
        "time", "date", "lat", "lon", "latitude", "longitude", "status", "version"
    }

    def __init__(self, traffic_keys: Optional[List[str]] = None):
        self.traffic_keys = traffic_keys or self.PRIMARY_TRAFFIC_KEYS

    def extract(self, data_chunk: List[Any]) -> np.ndarray:
        """
        Extracts a clean 1D float32 NumPy array from any arbitrary payload list.
        
        Args:
            data_chunk: List of raw items from sensor ingestion buffer.
            
        Returns:
            np.ndarray: 1D array of float32 values.
        """
        if not data_chunk:
            return np.array([], dtype=np.float32)

        values = []
        for item in data_chunk:
            values.append(self._parse_item(item))

        return np.array(values, dtype=np.float32)

    def _parse_item(self, item: Any) -> float:
        """Parses a single item into a float measurement with recursive schema resolution."""
        if isinstance(item, (int, float)):
            return float(item)

        if isinstance(item, dict):
            # 1. Check for Computer Vision detection lists or event lists (e.g. cameras, jams)
            for det_k in self.DETECTION_LIST_KEYS:
                if det_k in item and isinstance(item[det_k], (list, tuple)):
                    det_list = item[det_k]
                    if len(det_list) > 0 and isinstance(det_list[0], dict):
                        speeds = []
                        for d in det_list:
                            if not isinstance(d, dict):
                                continue
                            s = d.get("speed", d.get("speedKMH", d.get("speed_kmh")))
                            if s is None and "attributes" in d and isinstance(d["attributes"], dict):
                                s = d["attributes"].get("estimated_speed_kmh", d["attributes"].get("speed"))
                            if s is not None:
                                try:
                                    speeds.append(float(s))
                                except (ValueError, TypeError):
                                    pass
                        if speeds:
                            return float(np.mean(speeds))
                    return float(len(det_list))

            # 2. Check prioritized primary traffic keys (case-insensitive)
            item_lower = {str(k).lower(): (k, v) for k, v in item.items()}
            for target_k in self.traffic_keys:
                target_lower = target_k.lower()
                if target_lower in item_lower:
                    _, v = item_lower[target_lower]
                    res = self._extract_value(v)
                    if res is not None:
                        return res

            # 3. Check for nested dictionary structures (e.g. TomTom flowSegmentData)
            for k, v in item.items():
                if str(k).lower() in self.IGNORE_KEYS:
                    continue
                if isinstance(v, dict):
                    nested_res = self._parse_item(v)
                    if nested_res != 0.0:
                        return nested_res

            # 4. Fallback: Scan dict values ignoring metadata/IDs
            for k, v in item.items():
                if str(k).lower() in self.IGNORE_KEYS:
                    continue
                res = self._extract_value(v)
                if res is not None:
                    return res

            return 0.0

        if isinstance(item, (list, tuple)):
            if len(item) == 0:
                return 0.0
            # If it's a list of dicts (e.g. detections list directly)
            if isinstance(item[0], dict):
                return float(len(item))
            if isinstance(item[0], (int, float)):
                return float(item[0])
            if isinstance(item[0], str):
                try:
                    return float(item[0])
                except ValueError:
                    return 0.0
            return float(len(item))

        if isinstance(item, str):
            try:
                return float(item)
            except ValueError:
                return 0.0

        return 0.0

    def _extract_value(self, val: Any) -> Optional[float]:
        """Safely extracts a numeric float from scalar or string value."""
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            try:
                # Discard timestamp-like or UUID-like strings
                if len(val) > 20 or "-" in val and len(val) > 10:
                    return None
                return float(val)
            except ValueError:
                return None
        if isinstance(val, (list, tuple)):
            return float(len(val))
        return None
