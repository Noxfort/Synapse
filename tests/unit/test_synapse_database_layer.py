# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# Unit tests for the high-performance Synapse Database & Repositories Layer.

import os
import time
import tempfile
import pandas as pd
import pytest

from src.database.db_engine import DatabaseEngine
from src.database.database_manager import DatabaseManager
from src.repositories.sensor_dictionary_repo import SensorDictionaryRepository
from src.repositories.sensor_telemetry_writer import SensorTelemetryWriter
from src.repositories.sensor_telemetry_reader import SensorTelemetryReader
from src.repositories.telemetry_maintenance import TelemetryMaintenance
from src.repositories.golden_history_repo import GoldenHistoryRepository
from src.repositories.cloud_vault_repo import CloudVaultRepository
from src.repositories.episodic_audit_repo import EpisodicAuditRepository


@pytest.fixture
def temp_db_engine():
    """Provides a fresh isolated DatabaseEngine running SQLite for fast testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_path = tf.name

    custom_cfg = {
        "db_type": "sqlite",
        "db_name": os.path.basename(temp_path)
    }
    engine = DatabaseEngine(db_name=os.path.basename(temp_path), custom_config=custom_cfg)
    engine.db_path = temp_path
    engine._initialize_db()

    yield engine

    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except Exception:
            pass


def test_db_engine_initialization_and_tables(temp_db_engine):
    """Verifies that schema_queries.json tables and indexes are created automatically."""
    conn = temp_db_engine.get_connection()
    assert conn is not None

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}

    expected_tables = {
        "sensor_dictionary",
        "synapse_sensor_telemetry_raw",
        "synapse_sensor_hourly_summary",
        "synapse_golden_history",
        "cloud_file_vault",
        "audit_physics_episodes",
        "operation_sessions"
    }
    for t in expected_tables:
        assert t in tables, f"Expected table '{t}' was not created by DatabaseEngine."

    conn.close()


def test_sensor_dictionary_caching(temp_db_engine):
    """Verifies string to integer normalization and RAM caching."""
    repo = SensorDictionaryRepository(temp_db_engine)

    # First lookup should insert
    id1 = repo.get_or_create("sensor_loop_av_paulista_01")
    assert id1 > 0

    # Second lookup should hit RAM cache
    id2 = repo.get_or_create("sensor_loop_av_paulista_01")
    assert id1 == id2

    # Reverse lookup
    str_name = repo.get_str_id(id1)
    assert str_name == "sensor_loop_av_paulista_01"

    # Bulk lookup
    bulk = repo.bulk_get_or_create(["sensor_loop_av_paulista_01", "sensor_radar_reboucas_02"])
    assert len(bulk) == 2
    assert bulk["sensor_loop_av_paulista_01"] == id1
    assert bulk["sensor_radar_reboucas_02"] > 0


def test_delta_compression_engine(temp_db_engine):
    """Verifies that repeated identical telemetry states increment sample_count rather than creating rows."""
    dict_repo = SensorDictionaryRepository(temp_db_engine)
    writer = SensorTelemetryWriter(temp_db_engine, dict_repo)

    # 10 identical samples for the same sensor
    samples = [
        {"sensor_id": "sensor_a", "speed": 45.0, "flow_rate": 120.0, "occupancy": 0.15, "status": 2}
        for _ in range(10)
    ]

    writer.insert_telemetry_batch(samples, force_flush_delta=True)

    conn = temp_db_engine.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(sample_count) FROM synapse_sensor_telemetry_raw WHERE sensor_str_id = 'sensor_a';")
    row = cursor.fetchone()
    row_count = row[0]
    total_samples = row[1]

    # Delta compression should result in exactly 1 row with sample_count = 10!
    assert row_count == 1, f"Expected 1 delta-compressed row, got {row_count}"
    assert total_samples == 10, f"Expected sample_count = 10, got {total_samples}"

    # Now add a changed metric (e.g. speed drops to 15.0)
    writer.insert_telemetry_batch([
        {"sensor_id": "sensor_a", "speed": 15.0, "flow_rate": 250.0, "occupancy": 0.65, "status": 2}
    ], force_flush_delta=True)

    cursor.execute("SELECT COUNT(*) FROM synapse_sensor_telemetry_raw WHERE sensor_str_id = 'sensor_a';")
    new_row_count = cursor.fetchone()[0]
    assert new_row_count == 2
    conn.close()


def test_telemetry_reader_and_pushdown_aggregation(temp_db_engine):
    """Verifies query history and pushdown aggregations."""
    dict_repo = SensorDictionaryRepository(temp_db_engine)
    writer = SensorTelemetryWriter(temp_db_engine, dict_repo)
    reader = SensorTelemetryReader(temp_db_engine)

    writer.insert_telemetry_batch([
        {"sensor_id": "sensor_b", "speed": 40.0, "flow_rate": 100.0, "occupancy": 0.20},
        {"sensor_id": "sensor_b", "speed": 60.0, "flow_rate": 200.0, "occupancy": 0.30},
    ], force_flush_delta=True)

    # Simple history
    history = reader.query_telemetry_history()
    assert len(history) >= 2

    # Pushdown aggregation
    agg = reader.query_aggregated_telemetry()
    assert len(agg) >= 1
    sensor_b_agg = next(a for a in agg if a["sensor_int_id"] == dict_repo.get_or_create("sensor_b"))
    assert sensor_b_agg["avg_speed"] == 50.0
    assert sensor_b_agg["min_speed"] == 40.0


def test_golden_dataset_intact_ingestion(temp_db_engine):
    """Verifies that the Golden Dataset is ingested 100% na íntegra (zero data loss)."""
    dict_repo = SensorDictionaryRepository(temp_db_engine)
    golden_repo = GoldenHistoryRepository(temp_db_engine, dict_repo)

    now = time.time()
    # Create high-precision golden sample
    df = pd.DataFrame([
        {"sensor_id": "golden_sensor_1", "timestamp": now - 3600, "speed": 45.32, "flow_rate": 152.8, "occupancy": 0.182},
        {"sensor_id": "golden_sensor_1", "timestamp": now - 1800, "speed": 48.71, "flow_rate": 160.1, "occupancy": 0.195},
        {"sensor_id": "golden_sensor_1", "timestamp": now, "speed": 50.00, "flow_rate": 170.0, "occupancy": 0.210},
    ])

    success = golden_repo.ingest_dataframe(df, version="v1")
    assert success is True

    # Check exact reading at target timestamp
    exact = golden_repo.get_exact_reading("golden_sensor_1", target_timestamp=now, tolerance_sec=15.0)
    assert exact is not None
    assert abs(exact["speed"] - 50.0) < 0.01
    assert abs(exact["flow_rate"] - 170.0) < 0.01

    # Check global sensor profile
    profile = golden_repo.get_sensor_profile("golden_sensor_1")
    assert profile is not None
    expected_avg_speed = (45.32 + 48.71 + 50.00) / 3.0
    assert abs(profile["speed"] - expected_avg_speed) < 0.05


def test_cloud_vault_repository(temp_db_engine):
    """Verifies syncing and restoring neural checkpoints from PostgreSQL/SQLite BLOB."""
    vault = CloudVaultRepository(temp_db_engine)

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create a mock checkpoint file
        mock_ckpt = os.path.join(tmp_dir, "models", "best_hparams.pth")
        os.makedirs(os.path.dirname(mock_ckpt), exist_ok=True)
        dummy_content = b"SYNAPSE_NEURAL_WEIGHTS_VERSION_2_PAYLOAD_TEST_12345"
        with open(mock_ckpt, "wb") as f:
            f.write(dummy_content)

        # Sync to vault
        synced = vault.sync_file_to_vault(mock_ckpt, tmp_dir)
        assert synced is True

        # Fetch bytes directly
        content = vault.fetch_file_from_vault("models/best_hparams.pth")
        assert content == dummy_content

        # Restore into another location
        restore_path = os.path.join(tmp_dir, "restored", "best_hparams.pth")
        restored = vault.restore_file_from_vault("models/best_hparams.pth", restore_path)
        assert restored is True
        assert os.path.exists(restore_path)
        with open(restore_path, "rb") as f:
            assert f.read() == dummy_content


def test_episodic_audit_repository(temp_db_engine):
    """Verifies recording physics violations and retrieving hardest episodes."""
    dict_repo = SensorDictionaryRepository(temp_db_engine)
    audit_repo = EpisodicAuditRepository(temp_db_engine, dict_repo)

    ep_id1 = audit_repo.record_episode(
        sensor_id="sensor_loop_01",
        anomaly_score=0.88,
        physics_residual=12.45,
        state_vector=[35.0, 42.0, 120.0],
        xai_verdict="Violação de conservação de fluxo LWR detectada na via JK.",
        metadata={"cause": "shockwave"}
    )
    assert ep_id1 is not None

    ep_id2 = audit_repo.record_episode(
        sensor_id="sensor_loop_02",
        anomaly_score=0.95,
        physics_residual=28.10,
        state_vector=[10.0, 15.0, 80.0],
        xai_verdict="Sensor travado em valor anômalo com resíduo crítico.",
        metadata={"cause": "stuck_sensor"}
    )
    assert ep_id2 is not None

    hardest = audit_repo.get_hardest_violations(top_k=5)
    assert len(hardest) == 2
    # The highest residual (28.10) must be first
    assert hardest[0]["physics_residual"] == 28.10
    assert hardest[0]["sensor_id"] == "sensor_loop_02"


def test_database_manager_facade_and_async_worker(temp_db_engine):
    """Verifies DatabaseManager orchestrating the async worker and operational sessions."""
    db_mgr = DatabaseManager(engine=temp_db_engine, auto_start_worker=True)

    # Start session
    sid = db_mgr.start_operation_session()
    assert sid is not None

    # Push telemetry to async worker
    for i in range(5):
        db_mgr.push_telemetry(
            sensor_id="sensor_async",
            speed=55.0,
            flow_rate=180.0,
            occupancy=0.22
        )

    # Allow worker thread to drain or stop gracefully
    time.sleep(0.6)
    db_mgr.stop()

    # End session
    ended = db_mgr.end_operation_session(status="FINALIZADO_NORMAL")
    assert ended is True

    # Verify telemetry was flushed to database
    history = db_mgr.query_telemetry_history()
    async_samples = [h for h in history if h["sensor_str_id"] == "sensor_async"]
    assert len(async_samples) >= 1
    assert sum(s["sample_count"] for s in async_samples) == 5
