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
# File: src/database/db_engine.py
# Author: Gabriel Moraes
# Date: 2026-09-04
# Description: High-level database orchestrator and facade conforming to SOLID principles.

import os
import logging
from typing import Any, Optional, Dict

from src.database.db_interfaces import IConnectionProvider, ISettingsManager, ISchemaMigrator
from src.database.db_settings_manager import DatabaseSettingsManager
from src.database.db_connectors import create_connector, PostgresConnector
from src.database.db_migrator import DatabaseMigrator

logger = logging.getLogger("Synapse.DatabaseEngine")


class DatabaseEngine:
    """
    Central facade and orchestrator for the Synapse Database Layer.
    Adheres to SOLID principles:
    - Single Responsibility (SRP): Delegates connection logic, settings I/O, and DDL migrations.
    - Open/Closed (OCP): Works with any IConnectionProvider or ISchemaMigrator implementation.
    - Dependency Inversion (DIP): Depends on abstract contracts and supports dependency injection.
    """

    def __init__(
        self,
        db_name: str = "banco_de_dados_noxfort",
        custom_config: Optional[Dict[str, Any]] = None,
        auto_init: bool = True,
        connector: Optional[IConnectionProvider] = None,
        settings_manager: Optional[ISettingsManager] = None,
        migrator: Optional[ISchemaMigrator] = None
    ):
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.settings_path = os.path.join(self.project_root, "config", "settings.ini")

        # 1. Injected or default settings manager
        self.settings_manager = settings_manager or DatabaseSettingsManager(settings_path=self.settings_path)

        # 2. Injected or factory-created connection provider
        self.connector = connector or create_connector(
            custom_config=custom_config,
            settings_mgr=self.settings_manager,
            db_name=db_name
        )

        # 3. Injected or default schema migrator
        self.migrator = migrator or DatabaseMigrator()

        if auto_init:
            self._initialize_db()
            logger.info(f"[DB_ENGINE] Central Engine Initialized. DB: {self.db_type}")

    @property
    def db_type(self) -> str:
        """Returns current database dialect ('postgres')."""
        return self.connector.db_type

    @property
    def db_path(self) -> str:
        """Deprecated SQLite path property; always empty in PostgreSQL."""
        return ""

    @db_path.setter
    def db_path(self, value: str) -> None:
        """Deprecated SQLite path setter (no-op)."""
        pass

    @property
    def db_name_pg(self) -> str:
        if hasattr(self.connector, "dbname"):
            return getattr(self.connector, "dbname")
        return ""

    @property
    def db_schema(self) -> str:
        if hasattr(self.connector, "schema"):
            return getattr(self.connector, "schema")
        return "public"

    @property
    def _fatal_db_error(self) -> bool:
        return getattr(self.connector, "_fatal_db_error", False)

    @_fatal_db_error.setter
    def _fatal_db_error(self, value: bool) -> None:
        if hasattr(self.connector, "_fatal_db_error"):
            setattr(self.connector, "_fatal_db_error", value)

    def get_connection(self) -> Optional[Any]:
        """Provides an active database connection via the configured connector."""
        return self.connector.get_connection()

    def reset_circuit_breaker(self) -> None:
        """Resets the fatal error circuit breaker on the connector."""
        self.connector.reset_circuit_breaker()

    def close(self) -> None:
        """Closes all connections and releases connection pool resources."""
        if hasattr(self.connector, "close"):
            self.connector.close()

    def load_database_settings(self) -> Dict[str, Any]:
        """Delegates database settings retrieval to the settings manager."""
        return self.settings_manager.load_database_settings()

    def save_settings_to_ini(self, config_dict: Dict[str, Any]) -> None:
        """Delegates connection settings persistence to the settings manager."""
        self.settings_manager.save_database_settings(config_dict)

    def load_telemetry_settings(self) -> Dict[str, Any]:
        """Delegates telemetry settings retrieval to the settings manager."""
        return self.settings_manager.load_telemetry_settings()

    def save_telemetry_settings(self, ip: str, host: str, port: int, connected: bool) -> None:
        """Delegates telemetry settings persistence to the settings manager."""
        self.settings_manager.save_telemetry_settings(ip, host, port, connected)

    def _load_schema_config(self) -> Dict[str, Any]:
        """Helper to expose schema configuration for test inspection or monkeypatching."""
        if hasattr(self.migrator, "_load_schema_config"):
            return getattr(self.migrator, "_load_schema_config")()
        return {}

    def _initialize_db(self) -> None:
        """Executes table creation, column migrations, and index generation."""
        conn = self.get_connection()
        if not conn:
            return
        try:
            custom_schema = self._load_schema_config()
            self.migrator.initialize_schema(
                conn=conn,
                db_type=self.db_type,
                schema_name=self.db_schema,
                schema_config=custom_schema
            )
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
