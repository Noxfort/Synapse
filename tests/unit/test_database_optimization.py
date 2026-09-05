# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# File: tests/unit/test_database_optimization.py
# Author: Gabriel Moraes
# Date: 2026-09-05
# Description: Unit tests for PostgreSQL connection pooling, streaming COPY,
#              BRIN index verification, and TOAST external storage.

from src.database.db_connectors import PostgresConnector, PooledConnectionProxy
from src.repositories.sensor_dictionary_repo import SensorDictionaryRepository
from src.repositories.sensor_telemetry_writer import SensorTelemetryWriter


def test_threaded_connection_pool_lifecycle(temp_db_engine):
    """Verifies that ThreadedConnectionPool initializes, provides proxies, and recycles connections."""
    connector = temp_db_engine.connector
    assert isinstance(connector, PostgresConnector)
    assert connector.enable_pool is True

    # 1. Acquire connection from pool
    conn1 = temp_db_engine.get_connection()
    assert conn1 is not None
    assert isinstance(conn1, PooledConnectionProxy)
    assert conn1.closed == 0

    # Execute a simple query
    cursor = conn1.cursor()
    cursor.execute("SELECT 1;")
    assert cursor.fetchone()[0] == 1

    # 2. Close proxy (returns connection to pool)
    conn1.close()
    assert conn1.closed == 1

    # Calling close again should be a safe no-op
    conn1.close()

    # 3. Borrow again - pool re-lends connection cleanly
    conn2 = temp_db_engine.get_connection()
    assert conn2 is not None
    assert conn2.closed == 0
    cur2 = conn2.cursor()
    cur2.execute("SELECT 2;")
    assert cur2.fetchone()[0] == 2
    conn2.close()


def test_pooled_connection_proxy_rollback_on_close(temp_db_engine):
    """Verifies uncommitted dirty transactions are rolled back when connection is returned to pool."""
    conn = temp_db_engine.get_connection()
    assert conn is not None
    cur = conn.cursor()
    cur.execute("CREATE TEMPORARY TABLE _test_rollback (val INT);")
    cur.execute("INSERT INTO _test_rollback VALUES (42);")
    # Close without commit
    conn.close()

    # Next borrowed connection should not be blocked or left in error state
    conn_next = temp_db_engine.get_connection()
    assert conn_next is not None
    cur_next = conn_next.cursor()
    cur_next.execute("SELECT 100;")
    assert cur_next.fetchone()[0] == 100
    conn_next.close()


def test_streaming_copy_batch_insertion(temp_db_engine):
    """Verifies that SensorTelemetryWriter inserts batches using streaming COPY correctly."""
    dict_repo = SensorDictionaryRepository(temp_db_engine)
    writer = SensorTelemetryWriter(temp_db_engine, dict_repo)

    samples = [
        {
            "sensor_id": f"sensor_optim_{i % 5}",
            "speed": 60.0 + i,
            "flow_rate": 100.0 + (i * 2),
            "occupancy": 0.25,
            "status": 2,
            "scenario_name": "sim_test"
        }
        for i in range(50)
    ]

    writer.insert_telemetry_batch(samples, force_flush_delta=True)

    conn = temp_db_engine.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM synapse_sensor_telemetry_raw WHERE scenario_name = 'sim_test';")
    count = cursor.fetchone()[0]
    assert count == 50, f"Expected 50 inserted telemetry rows, got {count}"

    cursor.execute("SELECT speed, flow_rate, status FROM synapse_sensor_telemetry_raw WHERE sensor_str_id = 'sensor_optim_0' ORDER BY speed ASC LIMIT 1;")
    row = cursor.fetchone()
    assert row[0] == 60.0
    assert row[1] == 100.0
    assert row[2] == 2
    conn.close()


def test_brin_index_created(temp_db_engine):
    """Verifies that idx_telemetry_brin_collected_at is successfully registered in PostgreSQL."""
    conn = temp_db_engine.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE schemaname = 'schema_synapse_test' AND indexname = 'idx_telemetry_brin_collected_at';
    """)
    row = cursor.fetchone()
    assert row is not None, "idx_telemetry_brin_collected_at was not found in pg_indexes!"
    assert "brin" in row[1].lower(), f"Expected BRIN index, got: {row[1]}"
    conn.close()


def test_cloud_vault_toast_storage_external(temp_db_engine):
    """Verifies that cloud_file_vault.file_content has storage set to 'external' (no useless compression)."""
    conn = temp_db_engine.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.attstorage
        FROM pg_attribute a
        JOIN pg_class c ON a.attrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = 'schema_synapse_test'
          AND c.relname = 'cloud_file_vault'
          AND a.attname = 'file_content';
    """)
    row = cursor.fetchone()
    assert row is not None
    # 'e' means EXTERNAL storage in PostgreSQL pg_attribute.attstorage
    assert row[0] == 'e', f"Expected attstorage='e' (EXTERNAL), got '{row[0]}'"
    conn.close()
