# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# File: src/repositories/sensor_telemetry_reader.py
# Author: Gabriel Moraes
# Date: 2026-09-02

import os
import json
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Dict, Optional, Any, Generator

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine

logger = logging.getLogger("Synapse.SensorTelemetryReader")


class SensorTelemetryReader:
    """
    Handles read queries, streaming batch queries with server-side cursors,
    and pushdown aggregations for sensor telemetry data.
    Ported and adapted from CARINA FluidDynamicsReader.
    """

    SAMPLE_COLUMNS = [
        "sensor_str_id", "sensor_int_id", "flow_rate", "speed", "occupancy",
        "sample_count", "status", "collected_at", "scenario_name"
    ]

    AGGREGATED_COLUMNS = [
        "sensor_int_id", "avg_speed", "min_speed", "avg_flow", "avg_occupancy",
        "total_volume", "total_samples"
    ]

    def __init__(self, engine: 'DatabaseEngine'):
        self.engine = engine
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self._queries = self._load_queries()

    def _load_queries(self) -> dict:
        try:
            json_path = os.path.join(self.project_root, "config", "synapse_telemetry_queries.json")
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"[SensorTelemetryReader] Failed to load synapse_telemetry_queries.json: {e}")
        return {}

    def _get_query(self, query_key: str, dialect_variant: Optional[str] = None) -> str:
        q_obj = self._queries.get(query_key, {})
        if isinstance(q_obj, str):
            return q_obj
        if dialect_variant and dialect_variant in q_obj:
            return q_obj[dialect_variant]
        return q_obj.get(self.engine.db_type, q_obj.get("sqlite", ""))

    def query_telemetry_history(self, limit_seconds: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieves sensor telemetry samples from database."""
        conn = self.engine.get_connection()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            if limit_seconds is not None:
                cutoff_dt = datetime.now() - timedelta(seconds=limit_seconds)
                sql = self._get_query("query_telemetry_history")
                param = cutoff_dt if self.engine.db_type == "postgres" else cutoff_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                cursor.execute(sql, (param,))
            else:
                sql = self._get_query("query_telemetry_history", "all")
                cursor.execute(sql)

            return [dict(zip(self.SAMPLE_COLUMNS, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"[SensorTelemetryReader] Error querying telemetry history: {e}")
            return []
        finally:
            conn.close()

    def query_telemetry_history_batches(
        self,
        limit_seconds: Optional[int] = None,
        batch_size: int = 50000
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """
        Streams batches of sensor telemetry using a named server-side cursor (PostgreSQL)
        or fetchmany (SQLite) to avoid RAM Out-of-Memory (OOM) errors.
        Falls back to synapse_sensor_hourly_summary if raw table is empty.
        """
        conn = self.engine.get_connection()
        if not conn:
            return
        try:
            if self.engine.db_type == "postgres":
                cursor = conn.cursor(name='synapse_server_cursor')
                cursor.itersize = batch_size
            else:
                cursor = conn.cursor()

            if limit_seconds is not None:
                cutoff_dt = datetime.now() - timedelta(seconds=limit_seconds)
                sql = self._get_query("query_telemetry_history")
                param = cutoff_dt if self.engine.db_type == "postgres" else cutoff_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                cursor.execute(sql, (param,))
            else:
                sql = self._get_query("query_telemetry_history", "all")
                cursor.execute(sql)

            has_data = False
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                has_data = True
                yield [dict(zip(self.SAMPLE_COLUMNS, row)) for row in rows]

            # Fallback to hourly summary if raw table had no rows
            if not has_data:
                logger.info("[SensorTelemetryReader] synapse_sensor_telemetry_raw is empty. Falling back to hourly summary.")
                if self.engine.db_type == "postgres" and hasattr(cursor, 'close'):
                    try:
                        cursor.close()
                    except Exception:
                        pass
                cursor = conn.cursor()
                if limit_seconds is not None:
                    cutoff_dt = datetime.now() - timedelta(seconds=limit_seconds)
                    query = self._get_query("fallback_history_batches")
                    param = cutoff_dt if self.engine.db_type == "postgres" else cutoff_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                    cursor.execute(query, (param,))
                else:
                    query = self._get_query("fallback_history_batches", "all")
                    cursor.execute(query)

                summary_cols = ["sensor_int_id", "flow_rate", "speed", "occupancy", "sample_count", "collected_at"]
                while True:
                    rows = cursor.fetchmany(batch_size)
                    if not rows:
                        break
                    yield [dict(zip(summary_cols, row)) for row in rows]
        except Exception as e:
            logger.error(f"[SensorTelemetryReader] Error streaming telemetry history batches: {e}")
        finally:
            conn.close()

    def query_aggregated_telemetry(self, limit_seconds: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Executes a Pushdown Aggregation Query directly on PostgreSQL/SQLite (GROUP BY sensor_int_id).
        """
        conn = self.engine.get_connection()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            if limit_seconds is not None:
                cutoff_dt = datetime.now() - timedelta(seconds=limit_seconds)
                sql = self._get_query("query_telemetry_aggregated")
                param = cutoff_dt if self.engine.db_type == "postgres" else cutoff_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                cursor.execute(sql, (param,))
            else:
                sql = self._get_query("query_telemetry_aggregated", "postgres_all" if self.engine.db_type == "postgres" else "sqlite_all")
                cursor.execute(sql)

            return [dict(zip(self.AGGREGATED_COLUMNS, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"[SensorTelemetryReader] Error querying aggregated telemetry: {e}")
            return []
        finally:
            conn.close()
