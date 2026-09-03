# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# File: src/database/database_manager.py
# Author: Gabriel Moraes
# Date: 2026-09-02

import logging
from typing import Optional, List, Dict, Any, Generator
import pandas as pd

from src.database.db_engine import DatabaseEngine
from src.database.synapse_telemetry_worker import SynapseTelemetryWorker
from src.repositories.sensor_dictionary_repo import SensorDictionaryRepository
from src.repositories.sensor_telemetry_writer import SensorTelemetryWriter
from src.repositories.sensor_telemetry_reader import SensorTelemetryReader
from src.repositories.telemetry_maintenance import TelemetryMaintenance
from src.repositories.golden_history_repo import GoldenHistoryRepository
from src.repositories.cloud_vault_repo import CloudVaultRepository
from src.repositories.episodic_audit_repo import EpisodicAuditRepository

logger = logging.getLogger("Synapse.DatabaseManager")


class DatabaseManager:
    """
    Facade Pattern (Unit of Work).
    Unified point of interaction for all SYNAPSE database operations.
    Delegates calls to specialized repositories respecting SOLID (SRP).
    Ported and adapted from CARINA DatabaseManager.
    """

    def __init__(
        self,
        engine: Optional[DatabaseEngine] = None,
        auto_start_worker: bool = True,
        custom_config: Optional[Dict[str, Any]] = None
    ):
        # 1. Central Engine
        self.engine = engine or DatabaseEngine(custom_config=custom_config)

        # 2. Specialized Repositories
        self.dictionary_repo = SensorDictionaryRepository(self.engine)
        self.telemetry_writer = SensorTelemetryWriter(self.engine, self.dictionary_repo)
        self.telemetry_reader = SensorTelemetryReader(self.engine)
        self.maintenance = TelemetryMaintenance(self.engine)
        self.golden_repo = GoldenHistoryRepository(self.engine, self.dictionary_repo)
        self.cloud_vault_repo = CloudVaultRepository(self.engine)
        self.audit_repo = EpisodicAuditRepository(self.engine, self.dictionary_repo)

        # 3. Non-blocking Async Telemetry Worker
        self.telemetry_worker = SynapseTelemetryWorker(self.telemetry_writer)
        if auto_start_worker:
            self.telemetry_worker.start()

        self.current_session_id: Optional[int] = None

    # =========================================================================
    # TELEMETRY INGESTION (LIVE STREAMING)
    # =========================================================================

    def push_telemetry(
        self,
        sensor_id: str,
        speed: float,
        flow_rate: float,
        occupancy: float,
        status: int = 2,
        scenario_name: str = "default",
        collected_at: Optional[Any] = None
    ) -> bool:
        """Ultra-fast non-blocking push (< 0.001 ms) into telemetry worker queue."""
        return self.telemetry_worker.push_telemetry(
            sensor_id=sensor_id,
            speed=speed,
            flow_rate=flow_rate,
            occupancy=occupancy,
            status=status,
            scenario_name=scenario_name,
            collected_at=collected_at
        )

    def insert_telemetry_batch(self, samples: List[Dict[str, Any]], force_flush_delta: bool = False):
        """Direct batch insertion with Delta Compression and dictionary normalization."""
        self.telemetry_writer.insert_telemetry_batch(samples, force_flush_delta=force_flush_delta)

    # =========================================================================
    # TELEMETRY QUERIES & STREAMING
    # =========================================================================

    def query_telemetry_history(self, limit_seconds: Optional[int] = None) -> List[Dict[str, Any]]:
        return self.telemetry_reader.query_telemetry_history(limit_seconds=limit_seconds)

    def query_telemetry_history_batches(
        self,
        limit_seconds: Optional[int] = None,
        batch_size: int = 50000
    ) -> Generator[List[Dict[str, Any]], None, None]:
        return self.telemetry_reader.query_telemetry_history_batches(
            limit_seconds=limit_seconds,
            batch_size=batch_size
        )

    def query_aggregated_telemetry(self, limit_seconds: Optional[int] = None) -> List[Dict[str, Any]]:
        return self.telemetry_reader.query_aggregated_telemetry(limit_seconds=limit_seconds)

    # =========================================================================
    # GOLDEN DATASET (100% INTACT / MEH LOOKUPS)
    # =========================================================================

    def ingest_golden_dataframe(self, df: pd.DataFrame, version: str = "v1") -> bool:
        """Loads Golden Dataset na íntegra (zero data loss) via high-speed COPY."""
        return self.golden_repo.ingest_dataframe(df, version=version)

    def get_golden_exact_reading(
        self,
        sensor_id: str,
        target_timestamp: float,
        tolerance_sec: float = 10.0,
        version: str = "v1"
    ) -> Optional[Dict[str, float]]:
        return self.golden_repo.get_exact_reading(
            sensor_id=sensor_id,
            target_timestamp=target_timestamp,
            tolerance_sec=tolerance_sec,
            version=version
        )

    def get_golden_cyclical_reading(
        self,
        sensor_id: str,
        target_timestamp: float,
        version: str = "v1"
    ) -> Optional[Dict[str, float]]:
        return self.golden_repo.get_cyclical_reading(
            sensor_id=sensor_id,
            target_timestamp=target_timestamp,
            version=version
        )

    # =========================================================================
    # CLOUD VAULT (NEURAL CHECKPOINT BACKUP)
    # =========================================================================

    def sync_file_to_vault(self, filepath: str, base_dir: str) -> bool:
        return self.cloud_vault_repo.sync_file_to_vault(filepath, base_dir)

    def sync_all_files_to_vault(self, base_dir: str):
        self.cloud_vault_repo.sync_all_files_to_vault(base_dir)

    def restore_file_from_vault(self, relative_path: str, target_filepath: str) -> bool:
        return self.cloud_vault_repo.restore_file_from_vault(relative_path, target_filepath)

    def restore_all_files_from_vault(self, base_dir: str) -> int:
        return self.cloud_vault_repo.restore_all_files_from_vault(base_dir)

    # =========================================================================
    # EPISODIC AUDIT & XAI
    # =========================================================================

    def record_audit_episode(
        self,
        sensor_id: str,
        anomaly_score: float,
        physics_residual: float,
        state_vector: Optional[List[float]] = None,
        xai_verdict: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        return self.audit_repo.record_episode(
            sensor_id=sensor_id,
            anomaly_score=anomaly_score,
            physics_residual=physics_residual,
            state_vector=state_vector,
            xai_verdict=xai_verdict,
            metadata=metadata
        )

    def get_hardest_physics_violations(self, top_k: int = 20) -> List[Dict[str, Any]]:
        return self.audit_repo.get_hardest_violations(top_k=top_k)

    # =========================================================================
    # MAINTENANCE & ROLLUP
    # =========================================================================

    def consolidate_and_purge_old_data(self, keep_hours: int = 48, batch_days: int = 1):
        self.maintenance.consolidate_and_purge_old_data(keep_hours=keep_hours, batch_days=batch_days)

    # =========================================================================
    # OPERATION SESSIONS
    # =========================================================================

    def start_operation_session(self) -> Optional[int]:
        """Registers an operational session start_time."""
        conn = self.engine.get_connection()
        if not conn:
            return None
        try:
            cursor = conn.cursor()
            if self.engine.db_type == "postgres":
                cursor.execute("""
                    INSERT INTO operation_sessions (start_time, status)
                    VALUES (CURRENT_TIMESTAMP, 'EM_OPERACAO')
                    RETURNING session_id;
                """)
                sid = cursor.fetchone()[0]
            else:
                cursor.execute("INSERT INTO operation_sessions (status) VALUES ('EM_OPERACAO');")
                sid = cursor.lastrowid
            conn.commit()
            self.current_session_id = sid
            return sid
        except Exception as e:
            logger.error(f"[DatabaseManager] Failed to start operation session: {e}")
            return None
        finally:
            conn.close()

    def end_operation_session(self, status: str = 'FINALIZADO_NORMAL', error_msg: Optional[str] = None) -> bool:
        """Updates operational session end_time and status."""
        if not self.current_session_id:
            return False
        conn = self.engine.get_connection()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            param = "%s" if self.engine.db_type == "postgres" else "?"
            cursor.execute(f"""
                UPDATE operation_sessions
                SET end_time = CURRENT_TIMESTAMP, status = {param}, error_message = {param}
                WHERE session_id = {param};
            """, (status, error_msg, self.current_session_id))
            conn.commit()
            self.current_session_id = None
            return True
        except Exception as e:
            logger.error(f"[DatabaseManager] Failed to end session: {e}")
            return False
        finally:
            conn.close()

    # =========================================================================
    # LIFECYCLE
    # =========================================================================

    def stop(self):
        """Stops the telemetry background worker and flushes any pending samples."""
        if hasattr(self, 'telemetry_worker') and self.telemetry_worker:
            self.telemetry_worker.stop()
