# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# File: src/repositories/episodic_audit_repo.py
# Author: Gabriel Moraes
# Date: 2026-09-02

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List, Dict, Any

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine
    from src.repositories.sensor_dictionary_repo import SensorDictionaryRepository

logger = logging.getLogger("Synapse.EpisodicAuditRepo")


class EpisodicAuditRepository:
    """
    Repository for persisting physics-informed invariant violations (LWR / PINN residuals),
    auditor vetoes, and legal-grade XAI verdicts from JuristAgent into PostgreSQL.
    """

    def __init__(self, engine: 'DatabaseEngine', dictionary_repo: 'SensorDictionaryRepository'):
        self.engine = engine
        self.dictionary_repo = dictionary_repo

    def record_episode(
        self,
        sensor_id: str,
        anomaly_score: float,
        physics_residual: float,
        state_vector: Optional[List[float]] = None,
        xai_verdict: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """Records an anomalous traffic episode or physical continuity violation."""
        conn = self.engine.get_connection()
        if not conn:
            return None

        sensor_int = self.dictionary_repo.get_or_create(sensor_id, conn=conn)
        vec_json = json.dumps(state_vector or [])
        meta_json = json.dumps(metadata or {})
        now = datetime.now()

        try:
            cursor = conn.cursor()
            if self.engine.db_type == "postgres":
                cursor.execute("""
                    INSERT INTO audit_physics_episodes (
                        recorded_at, sensor_str_id, sensor_int_id, anomaly_score,
                        physics_residual, state_vector, xai_verdict, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb)
                    RETURNING id;
                """, (now, str(sensor_id), sensor_int, float(anomaly_score), float(physics_residual), vec_json, xai_verdict, meta_json))
                ep_id = cursor.fetchone()[0]
            else:
                cursor.execute("""
                    INSERT INTO audit_physics_episodes (
                        recorded_at, sensor_str_id, sensor_int_id, anomaly_score,
                        physics_residual, state_vector, xai_verdict, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """, (now.isoformat(), str(sensor_id), sensor_int, float(anomaly_score), float(physics_residual), vec_json, xai_verdict, meta_json))
                ep_id = cursor.lastrowid

            conn.commit()
            return ep_id
        except Exception as e:
            logger.error(f"[EpisodicAuditRepo] Error recording episode: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return None
        finally:
            conn.close()

    def get_hardest_violations(self, top_k: int = 20) -> List[Dict[str, Any]]:
        """Retrieves top-K episodes with highest physics residual for Experience Replay / Calibration."""
        conn = self.engine.get_connection()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            param = "%s" if self.engine.db_type == "postgres" else "?"
            cursor.execute(f"""
                SELECT id, recorded_at, sensor_str_id, anomaly_score, physics_residual,
                       state_vector, xai_verdict, metadata
                FROM audit_physics_episodes
                ORDER BY physics_residual DESC
                LIMIT {param};
            """, (top_k,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                results.append({
                    "id": r[0],
                    "recorded_at": r[1],
                    "sensor_id": r[2],
                    "anomaly_score": float(r[3]),
                    "physics_residual": float(r[4]),
                    "state_vector": json.loads(r[5]) if isinstance(r[5], str) else r[5],
                    "xai_verdict": r[6],
                    "metadata": json.loads(r[7]) if isinstance(r[7], str) else r[7]
                })
            return results
        except Exception as e:
            logger.error(f"[EpisodicAuditRepo] Error querying hardest violations: {e}")
            return []
        finally:
            conn.close()
