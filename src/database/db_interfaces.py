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
# File: src/database/db_interfaces.py
# Author: Gabriel Moraes
# Date: 2026-09-04
# Description: Abstract contracts and protocols for database connections,
#              settings, and schema migrations adhering to SOLID principles.

from typing import Any, Optional, Dict, Protocol, runtime_checkable


@runtime_checkable
class IConnectionProvider(Protocol):
    """Abstract protocol for database connection providers."""

    @property
    def db_type(self) -> str:
        """Returns the database dialect/type ('postgres')."""
        ...

    def get_connection(self) -> Optional[Any]:
        """Provides an active database connection or None on failure."""
        ...

    def reset_circuit_breaker(self) -> None:
        """Resets fatal error flags allowing retry attempts."""
        ...

    def close(self) -> None:
        """Closes all underlying connections or connection pools."""
        ...


@runtime_checkable
class ISettingsManager(Protocol):
    """Abstract protocol for database and telemetry settings persistence."""

    def load_database_settings(self) -> Dict[str, Any]:
        """Loads database configuration dictionary."""
        ...

    def save_database_settings(self, config_dict: Dict[str, Any]) -> None:
        """Persists updated database configuration."""
        ...

    def load_telemetry_settings(self) -> Dict[str, Any]:
        """Loads telemetry configuration dictionary."""
        ...

    def save_telemetry_settings(self, ip: str, host: str, port: int, connected: bool) -> None:
        """Persists telemetry configuration."""
        ...


@runtime_checkable
class ISchemaMigrator(Protocol):
    """Abstract protocol for schema creation, migrations, and indexing."""

    def initialize_schema(self, conn: Any, db_type: str, schema_name: str = "public") -> None:
        """Applies tables, migrations, and indexes to the target connection."""
        ...
