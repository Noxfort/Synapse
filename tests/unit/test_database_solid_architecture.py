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
# File: tests/unit/test_database_solid_architecture.py
# Author: Gabriel Moraes
# Date: 2026-09-04

# Unit tests for the SOLID decoupled Database Architecture (Flat structure).

import os
import tempfile
import pytest

from src.database.db_interfaces import IConnectionProvider, ISettingsManager, ISchemaMigrator
from src.database.db_settings_manager import DatabaseSettingsManager
from src.database.db_connectors import PostgresConnector, create_connector
from src.database.db_migrator import DatabaseMigrator
from src.database.db_engine import DatabaseEngine


def test_solid_interfaces_protocol_conformance():
    """Verifies that concrete classes satisfy their respective Protocol contracts."""
    settings_mgr = DatabaseSettingsManager()
    assert isinstance(settings_mgr, ISettingsManager)

    migrator = DatabaseMigrator()
    assert isinstance(migrator, ISchemaMigrator)

    pg_conn = PostgresConnector()
    assert isinstance(pg_conn, IConnectionProvider)


def test_database_settings_manager_isolation():
    """Tests DatabaseSettingsManager operations on an isolated temporary settings.ini."""
    with tempfile.NamedTemporaryFile(suffix=".ini", delete=False) as tf:
        temp_ini = tf.name

    try:
        mgr = DatabaseSettingsManager(settings_path=temp_ini)

        # 1. Database settings
        mgr.save_database_settings({
            "db_type": "postgres",
            "host": "db.test.local",
            "port": 5433,
            "user": "test_user",
            "password": "test_password",
            "dbname": "test_db",
            "schema": "test_schema",
            "connected": "true"
        })

        db_cfg = mgr.load_database_settings()
        assert db_cfg["db_type"] == "postgres"
        assert db_cfg["host"] == "db.test.local"
        assert db_cfg["port"] == 5433
        assert db_cfg["user"] == "test_user"
        assert db_cfg["dbname"] == "test_db"
        assert db_cfg["schema"] == "test_schema"
        assert db_cfg["connected"] is True

        # 2. Telemetry settings (isolated from DB)
        mgr.save_telemetry_settings(ip="10.0.0.1", host="broker.test", port=1884, connected=True)
        telem_cfg = mgr.load_telemetry_settings()
        assert telem_cfg["ip"] == "10.0.0.1"
        assert telem_cfg["host"] == "broker.test"
        assert telem_cfg["port"] == 1884
        assert telem_cfg["connected"] is True
    finally:
        if os.path.exists(temp_ini):
            try:
                os.remove(temp_ini)
            except Exception:
                pass


def test_sqlite_discontinuation_rejection():
    """Verifies that attempting to configure SQLite raises a ValueError."""
    with pytest.raises(ValueError, match="Synapse opera estritamente com PostgreSQL"):
        create_connector(custom_config={"db_type": "sqlite"})


def test_postgres_connector_circuit_breaker():
    """Tests PostgresConnector circuit breaker when fatal authentication error occurs."""
    connector = PostgresConnector(
        host="invalid-non-existent-host.local",
        port=9999,
        user="test_usr",
        password="bad_pwd"
    )
    assert connector.db_type == "postgres"
    assert connector._fatal_db_error is False

    # Simulate fatal authentication flag
    connector._fatal_db_error = True
    assert connector.get_connection() is None

    connector.reset_circuit_breaker()
    assert connector._fatal_db_error is False


def test_database_migrator_with_mock_schema():
    """Tests DatabaseMigrator executing PostgreSQL schema DDL with rollback resilience."""
    connector = PostgresConnector(schema="schema_synapse_test")
    conn = connector.get_connection()
    assert conn is not None
    try:
        migrator = DatabaseMigrator()

        mock_queries = {
            "postgres": {
                "tables": [
                    "CREATE TABLE IF NOT EXISTS test_tbl1 (id SERIAL PRIMARY KEY);",
                    "CREATE TABLE INVALID SYNTAX ERROR HERE;",
                    "CREATE TABLE IF NOT EXISTS test_tbl2 (id SERIAL PRIMARY KEY);"
                ],
                "indexes": [
                    "CREATE INDEX IF NOT EXISTS idx_fail ON non_existent(c);",
                    "CREATE INDEX IF NOT EXISTS idx_ok ON test_tbl1(id);"
                ],
                "migrations": []
            }
        }

        migrator.initialize_schema(
            conn=conn,
            db_type="postgres",
            schema_name="schema_synapse_test",
            schema_config=mock_queries
        )

        cursor = conn.cursor()
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'schema_synapse_test';")
        tables = {row[0] for row in cursor.fetchall()}
        assert "test_tbl1" in tables
        assert "test_tbl2" in tables

        # Clean up test tables
        cursor.execute("DROP TABLE IF EXISTS test_tbl1, test_tbl2 CASCADE;")
        conn.commit()
    finally:
        conn.close()


def test_database_engine_dependency_injection():
    """Tests DatabaseEngine composing injected components (DIP)."""
    class MockPostgresConnector:
        def __init__(self):
            self.db_type = "postgres"
            self._fatal_db_error = False
        def get_connection(self):
            return "mock_connection"
        def reset_circuit_breaker(self):
            pass

    custom_connector = MockPostgresConnector()
    custom_migrator = DatabaseMigrator()
    custom_settings = DatabaseSettingsManager()

    engine = DatabaseEngine(
        connector=custom_connector,
        settings_manager=custom_settings,
        migrator=custom_migrator,
        auto_init=False
    )

    assert engine.connector is custom_connector
    assert engine.migrator is custom_migrator
    assert engine.settings_manager is custom_settings
    assert engine.db_type == "postgres"
    assert engine.get_connection() == "mock_connection"
