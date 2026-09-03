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
# File: src/infrastructure/json_source_storage.py
# Author: Gabriel Moraes
# Date: 2026-08-28

import json
import os
from typing import Dict, List, Optional, Tuple
from src.domain.entities import DataSource, SourceType, SourceStatus
from src.interfaces.sources import ISourceStorage
from src.utils.logging_setup import get_logger

logger = get_logger("JsonSourceStorage")


class JsonSourceStorage(ISourceStorage):
    """
    Handles JSON file serialization, deserialization, and filesystem I/O for data sources and map topology.
    (SRP: Isolated persistence responsibility).
    """

    @classmethod
    def get_default_path(cls) -> str:
        home = os.path.expanduser("~")
        docs = os.path.join(home, "Documentos")
        if not os.path.exists(docs):
            docs = os.path.join(home, "Documents")
        return os.path.join(docs, "Synapse", "config", "sources.json")

    def __init__(self, file_path: Optional[str] = None):
        self.file_path = file_path or self.get_default_path()

    def serialize_source(self, src: DataSource) -> dict:
        """Convert a DataSource to a JSON-safe dict."""
        return {
            "id": src.id,
            "name": src.name,
            "source_type": src.source_type.value if isinstance(src.source_type, SourceType) else str(src.source_type),
            "connection_string": src.connection_string,
            "is_local": src.is_local,
            "status": src.status.value if isinstance(src.status, SourceStatus) else str(src.status),
            "lat": src.lat,
            "lon": src.lon,
            "semantic_type": src.semantic_type,
            "inferred_unit": src.inferred_unit,
            "confidence_score": src.confidence_score,
            "metadata": src.metadata if isinstance(src.metadata, dict) else {},
        }

    def deserialize_source(self, data: dict) -> DataSource:
        """Reconstruct a DataSource from a saved dict."""
        source_type = SourceType.API
        for st in SourceType:
            if st.value == data.get("source_type"):
                source_type = st
                break

        raw_status = data.get("status", "Quarantine")
        status = SourceStatus.QUARANTINE
        if raw_status in (SourceStatus.ACTIVE.value, "Active", "active"):
            status = SourceStatus.ACTIVE
        elif raw_status in (SourceStatus.FALLBACK.value, "Fallback", "fallback"):
            status = SourceStatus.FALLBACK
        elif raw_status in (SourceStatus.QUARANTINE.value, "Quarantine", "quarantine"):
            status = SourceStatus.QUARANTINE

        return DataSource(
            id=data["id"],
            name=data["name"],
            source_type=source_type,
            connection_string=data.get("connection_string", ""),
            is_local=data.get("is_local", True),
            status=status,
            lat=data.get("lat", 0.0),
            lon=data.get("lon", 0.0),
            semantic_type=data.get("semantic_type"),
            inferred_unit=data.get("inferred_unit"),
            confidence_score=data.get("confidence_score", 0.0),
            metadata=data.get("metadata", {}),
        )

    def save(
        self,
        data_sources: Dict[str, DataSource],
        associations: Dict[str, List[str]],
        map_path: Optional[str] = None
    ) -> bool:
        """Persist current sources, associations, and map path to JSON."""
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            payload = {
                "map_path": map_path,
                "sources": [
                    self.serialize_source(s) for s in data_sources.values()
                    if "Historical" not in s.name
                ],
                "associations": associations,
            }
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.warning(f"[JsonSourceStorage] Failed to save sources: {e}")
            return False

    def load(self) -> Tuple[Dict[str, DataSource], Dict[str, List[str]], Optional[str]]:
        """Restore sources, associations, and map path from JSON (if file exists)."""
        sources: Dict[str, DataSource] = {}
        associations: Dict[str, List[str]] = {}
        map_path: Optional[str] = None

        if not os.path.exists(self.file_path):
            return sources, associations, map_path

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                payload = json.load(f)

            map_path = payload.get("map_path")

            loaded_count = 0
            for src_data in payload.get("sources", []):
                raw_status = src_data.get("status", "")
                if raw_status in ("Rejected", "rejected"):
                    continue

                source = self.deserialize_source(src_data)
                sources[source.id] = source
                loaded_count += 1

            associations = payload.get("associations", {})
            if loaded_count > 0 or map_path:
                logger.info(
                    f"[JsonSourceStorage] ♻️ Restored {loaded_count} source(s) and map '{map_path}' from disk."
                )

        except Exception as e:
            logger.warning(f"[JsonSourceStorage] Failed to load sources: {e}")

        return sources, associations, map_path
