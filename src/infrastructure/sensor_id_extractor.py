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
# File: src/infrastructure/sensor_id_extractor.py
# Author: Gabriel Moraes
# Date: 2025-12-25

import re
from typing import Any, List, Optional, Set

from src.interfaces.sensor_gateway import ISensorIdExtractor


class _HybridExtractorDescriptor:
    """Enables extract to be called seamlessly on either class or instance."""

    def __get__(self, instance, owner):
        if instance is None:
            def _class_call(*args, **kwargs) -> str:
                return owner.extract_with_rules(*args, **kwargs)
            return _class_call

        def _instance_call(payload: Any, client_ip: str, request_path: str = "") -> str:
            return instance._extract_instance(payload, client_ip, request_path)
        return _instance_call


class SensorIdExtractor(ISensorIdExtractor):
    """
    Encapsulates sensor identifier discovery heuristics (SRP & OCP).
    Supports instance customization and backward-compatible classmethod calls.
    """

    DEFAULT_CANDIDATE_KEYS = [
        'source_id', 'sensorId', 'id', 'camera_id', 'deviceId', 'uuid', 'ip', 'sensor_id',
        'UnitID', 'StationID', 'DetectorID'
    ]

    DEFAULT_SUB_CONTAINERS = ['metadata', 'header', 'info', 'device']

    DEFAULT_GENERIC_URL_KEYWORDS = {
        "events", "webhook", "webhooks", "data", "api", "ingest", "sensor", "telemetry", "push", "post"
    }

    def __init__(
        self,
        candidate_keys: Optional[List[str]] = None,
        sub_containers: Optional[List[str]] = None,
        generic_url_keywords: Optional[Set[str]] = None,
    ):
        self.candidate_keys = candidate_keys or list(self.DEFAULT_CANDIDATE_KEYS)
        self.sub_containers = sub_containers or list(self.DEFAULT_SUB_CONTAINERS)
        self.generic_url_keywords = generic_url_keywords or set(self.DEFAULT_GENERIC_URL_KEYWORDS)

    @classmethod
    def normalize_id(cls, raw_id: str) -> str:
        """
        Normalizes sensor IDs like 'src_01', 'SRC_1', 'src_001' to 'src_1'.
        If not matching a zero-padded pattern, returns lower-case stripped string.
        """
        clean = raw_id.strip()
        match = re.match(r'^(src|sensor|cam|loop)_0*(\d+)$', clean, re.IGNORECASE)
        if match:
            prefix = match.group(1).lower()
            num = int(match.group(2))
            if prefix in ("src", "sensor", "cam", "loop"):
                return f"src_{num}"
        return clean.lower()

    @classmethod
    def extract_with_rules(
        cls,
        payload: Any,
        client_ip: str,
        request_path: str = "",
        candidate_keys: Optional[List[str]] = None,
        sub_containers: Optional[List[str]] = None,
        generic_url_keywords: Optional[Set[str]] = None,
    ) -> str:
        """Core extraction logic with configurable rules."""
        keys = candidate_keys or cls.DEFAULT_CANDIDATE_KEYS
        subs = sub_containers or cls.DEFAULT_SUB_CONTAINERS
        keywords = generic_url_keywords or cls.DEFAULT_GENERIC_URL_KEYWORDS

        # 1. URL Path Priority
        if request_path:
            clean_path = request_path.split("?")[0].strip().strip("/")
            if clean_path:
                segments = clean_path.split("/")
                # Search segments from right to left
                for seg in reversed(segments):
                    if seg:
                        norm = cls.normalize_id(seg)
                        if norm.startswith(("src_", "sensor_", "cam_", "loop_")):
                            return norm
                # If there's only 1 segment and it's not a generic API word
                if len(segments) == 1 and segments[0].lower() not in keywords:
                    return cls.normalize_id(segments[0])

        # 2. Payload Inspection Priority
        if isinstance(payload, dict):
            # Top level search
            for candidate in keys:
                for k, v in payload.items():
                    if k.lower() == candidate.lower() and v is not None:
                        return cls.normalize_id(str(v))

            # Nested search
            for sub in subs:
                sub_dict = payload.get(sub)
                if isinstance(sub_dict, dict):
                    for candidate in keys:
                        for k, v in sub_dict.items():
                            if k.lower() == candidate.lower() and v is not None:
                                return cls.normalize_id(str(v))

        # 3. Fallback to sanitized client IP
        clean_ip = client_ip.replace('.', '_').replace(':', '_')
        return f"device_{clean_ip}"

    def _extract_instance(self, payload: Any, client_ip: str, request_path: str = "") -> str:
        return self.extract_with_rules(
            payload=payload,
            client_ip=client_ip,
            request_path=request_path,
            candidate_keys=self.candidate_keys,
            sub_containers=self.sub_containers,
            generic_url_keywords=self.generic_url_keywords,
        )

    # Hybrid method: callable as SensorIdExtractor.extract(...) or extractor_instance.extract(...)
    extract = _HybridExtractorDescriptor()
