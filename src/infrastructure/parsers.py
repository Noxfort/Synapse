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
# File: src/infrastructure/parsers.py
# Author: Gabriel Moraes
# Date: 2025-12-25

import csv
import io
import json
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.interfaces.sensor_gateway import IPayloadParser, IPolyglotPayloadParser


# =============================================================================
# PAYLOAD PARSING STRATEGIES (SRP & OCP)
# =============================================================================

class BasePayloadParser(ABC):
    """Abstract Strategy base class for sensor payload parsers."""

    @abstractmethod
    def can_parse(self, content_type: str, raw_body: str) -> bool:
        """Determines if this parser handles the given content type or body structure."""
        pass

    @abstractmethod
    def parse(self, raw_body: str) -> Optional[Dict[str, Any]]:
        """Parses the raw body into a normalized Python dictionary."""
        pass


class JsonPayloadParser(BasePayloadParser):
    """Strategy for JSON telemetry payloads."""

    def can_parse(self, content_type: str, raw_body: str) -> bool:
        return 'application/json' in content_type or raw_body.startswith('{') or raw_body.startswith('[')

    def parse(self, raw_body: str) -> Optional[Dict[str, Any]]:
        try:
            parsed = json.loads(raw_body)
            if isinstance(parsed, dict):
                return parsed
            elif isinstance(parsed, list):
                return {"items": parsed}
        except (json.JSONDecodeError, ValueError):
            pass
        return None


class XmlPayloadParser(BasePayloadParser):
    """Strategy for XML telemetry payloads (e.g. DATEX II / SOAP)."""

    def can_parse(self, content_type: str, raw_body: str) -> bool:
        return 'xml' in content_type or raw_body.startswith('<')

    def parse(self, raw_body: str) -> Optional[Dict[str, Any]]:
        try:
            root = ET.fromstring(raw_body)
            data = {}
            for child in root:
                data[child.tag] = child.text
            data.update(root.attrib)
            return data
        except ET.ParseError:
            return None


class CsvPayloadParser(BasePayloadParser):
    """Strategy for single-line CSV / Key-Value telemetry (Radars / Inductive loops)."""

    def can_parse(self, content_type: str, raw_body: str) -> bool:
        return ',' in raw_body or ';' in raw_body

    def parse(self, raw_body: str) -> Optional[Dict[str, Any]]:
        try:
            data = {}
            line = raw_body.replace(';', ',')

            if '=' in line:
                parts = line.split(',')
                for p in parts:
                    if '=' in p:
                        k, v = p.split('=', 1)
                        data[k.strip()] = v.strip()
            else:
                reader = csv.reader(io.StringIO(line))
                for row in reader:
                    for idx, val in enumerate(row):
                        data[f"field_{idx}"] = val

            return data if data else None
        except Exception:
            return None


class RawFallbackPayloadParser(BasePayloadParser):
    """Default fallback wrapper when no structured parser matched."""

    def can_parse(self, content_type: str, raw_body: str) -> bool:
        return True

    def parse(self, raw_body: str) -> Dict[str, Any]:
        return {"raw_content": raw_body, "format": "unknown"}


class PolyglotPayloadParser(IPolyglotPayloadParser):
    """
    Parser Registry & Dispatcher (OCP compliant).
    Open for new parser extensions without modifying ingestion handler.
    """

    def __init__(self, parsers: Optional[List[IPayloadParser]] = None):
        self._parsers: List[IPayloadParser] = parsers or [
            JsonPayloadParser(),
            XmlPayloadParser(),
            CsvPayloadParser(),
            RawFallbackPayloadParser(),
        ]

    def register_parser(self, parser: IPayloadParser, priority: int = 0) -> None:
        """Allows dynamic injection of new payload parsers."""
        self._parsers.insert(priority, parser)

    def parse(self, content_type: str, raw_body: str) -> Dict[str, Any]:
        """Dispatches parsing to the first matching strategy."""
        for parser in self._parsers:
            if parser.can_parse(content_type, raw_body):
                result = parser.parse(raw_body)
                if result is not None:
                    return result
        return {"raw_content": raw_body, "format": "unknown"}


def create_default_parser_registry() -> PolyglotPayloadParser:
    """Factory function for creating a fresh parser registry."""
    return PolyglotPayloadParser()
