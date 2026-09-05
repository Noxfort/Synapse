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
# File: tests/unit/test_database_engine.py
# Author: Gabriel Moraes
# Date: 2026-09-04

"""
Unit tests for DatabaseEngine lifecycle, table creation, auto_init flag,
and DDL execution error resilience.
"""

from src.database.db_engine import DatabaseEngine


def test_db_engine_initialization_and_tables(temp_db_engine):
    """Verifies that schema_queries.json tables and indexes are created automatically in PostgreSQL."""
    conn = temp_db_engine.get_connection()
    assert conn is not None

    cursor = conn.cursor()
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'schema_synapse_test';")
    tables = {row[0] for row in cursor.fetchall()}

    expected_tables = {
        "sensor_dictionary",
        "synapse_sensor_telemetry_raw",
        "synapse_sensor_hourly_summary",
        "synapse_golden_history",
        "cloud_file_vault",
        "audit_physics_episodes",
        "operation_sessions",
        "security_audit_logs",
        "synapse_users"
    }
    for t in expected_tables:
        assert t in tables, f"Expected table '{t}' was not created by DatabaseEngine."

    conn.close()


def test_database_engine_auto_init_flag():
    """Verifies that auto_init=False prevents _initialize_db from running automatically."""
    custom_cfg = {"db_type": "postgres", "schema": "schema_synapse_autoinit", "db_schema": "schema_synapse_autoinit"}
    
    # Ensure fresh schema
    engine_temp = DatabaseEngine(custom_config=custom_cfg, auto_init=False)
    conn = engine_temp.get_connection()
    assert conn is not None
    cur = conn.cursor()
    cur.execute("DROP SCHEMA IF EXISTS schema_synapse_autoinit CASCADE; CREATE SCHEMA schema_synapse_autoinit;")
    conn.commit()

    engine = DatabaseEngine(custom_config=custom_cfg, auto_init=False)

    # Tables should NOT be initialized yet
    conn = engine.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'schema_synapse_autoinit';")
    tables = {row[0] for row in cursor.fetchall()}
    assert len(tables) == 0
    conn.close()

    # Calling _initialize_db explicitly should initialize tables
    engine._initialize_db()
    conn = engine.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'schema_synapse_autoinit';")
    tables = {row[0] for row in cursor.fetchall()}
    assert "sensor_dictionary" in tables

    # Clean up schema
    cursor.execute("DROP SCHEMA IF EXISTS schema_synapse_autoinit CASCADE;")
    conn.commit()
    conn.close()


def test_database_engine_initialize_db_rollback_resilience(monkeypatch):
    """Verifies that an error in one index or table does not abort remaining statements in PostgreSQL."""
    custom_cfg = {"db_type": "postgres", "schema": "schema_synapse_test"}
    engine = DatabaseEngine(custom_config=custom_cfg, auto_init=False)

    mock_schema = {
        "postgres": {
            "tables": [
                "CREATE TABLE IF NOT EXISTS schema_synapse_test.t_valid1 (id SERIAL PRIMARY KEY);",
                "CREATE TABLE INVALID SYNTAX ERROR HERE;",
                "CREATE TABLE IF NOT EXISTS schema_synapse_test.t_valid2 (id SERIAL PRIMARY KEY);"
            ],
            "indexes": [
                "CREATE INDEX idx_invalid ON non_existent_table(col);",
                "CREATE INDEX IF NOT EXISTS idx_valid1 ON schema_synapse_test.t_valid1(id);"
            ],
            "migrations": []
        }
    }
    monkeypatch.setattr(engine, "_load_schema_config", lambda: mock_schema)
    engine._initialize_db()

    conn = engine.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'schema_synapse_test';")
    tables = {row[0] for row in cursor.fetchall()}
    assert "t_valid1" in tables
    assert "t_valid2" in tables

    cursor.execute("DROP TABLE IF EXISTS schema_synapse_test.t_valid1, schema_synapse_test.t_valid2 CASCADE;")
    conn.commit()
    conn.close()
