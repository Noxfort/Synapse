# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# File: src/repositories/telemetry_maintenance.py
# Author: Gabriel Moraes
# Date: 2026-09-02

import os
import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine

logger = logging.getLogger("Synapse.TelemetryMaintenance")


class TelemetryMaintenance:
    """
    Handles data retention, hourly rollup consolidation, and safe table purging
    in memory-safe daily chunks. Ported and adapted from CARINA FluidDynamicsMaintenance.
    """

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
            logger.error(f"[TelemetryMaintenance] Failed to load synapse_telemetry_queries.json: {e}")
        return {}

    def _get_query(self, query_key: str) -> str:
        q_obj = self._queries.get(query_key, {})
        if isinstance(q_obj, str):
            return q_obj
        return q_obj.get("postgres", q_obj.get(self.engine.db_type, ""))

    def consolidate_and_purge_old_data(self, keep_hours: int = 48, batch_days: int = 1):
        """
        Consolidates raw sensor telemetry older than `keep_hours` into synapse_sensor_hourly_summary
        and purges raw rows in non-blocking daily chunks to eliminate table locks and WAL bloat.
        """
        conn = self.engine.get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            sql_min = self._get_query("get_min_collected_before")
            cursor.execute(sql_min, (keep_hours,))
            row = cursor.fetchone()
            if not row or not row[0]:
                return
            min_ts = row[0]

            sql_cutoff = self._get_query("get_cutoff_timestamp_interval")
            cursor.execute(sql_cutoff, (keep_hours,))
            cutoff_ts = cursor.fetchone()[0]

            sql_next_batch = self._get_query("get_next_batch_timestamp")
            sql_consolidate = self._get_query("consolidate_sensor_hourly_summary")
            sql_purge = self._get_query("purge_consolidated_window")

            current_start = min_ts
            while current_start < cutoff_ts:
                cursor.execute(sql_next_batch, (current_start, batch_days))
                current_end = min(cursor.fetchone()[0], cutoff_ts)

                # 1. Consolidate into Hourly Summary
                cursor.execute(sql_consolidate, (current_start, current_end))

                # 2. Purge raw rows for this window
                cursor.execute(sql_purge, (current_start, current_end))
                conn.commit()
                logger.info(f"[TelemetryMaintenance] Consolidated & purged telemetry window {current_start} to {current_end}.")

                if current_end >= cutoff_ts:
                    break
                current_start = current_end

            # 3. Post-purge anti-bloat maintenance (VACUUM ANALYZE)
            if self.engine.db_type == "postgres":
                try:
                    conn.commit()
                    old_autocommit = getattr(conn, "autocommit", False)
                    conn.autocommit = True
                    cursor.execute("VACUUM ANALYZE synapse_sensor_telemetry_raw;")
                    conn.autocommit = old_autocommit
                    logger.info("[TelemetryMaintenance] Executed VACUUM ANALYZE on synapse_sensor_telemetry_raw.")
                except Exception as ve:
                    logger.debug(f"[TelemetryMaintenance] VACUUM ANALYZE notice: {ve}")
        except Exception as e:
            logger.error(f"[TelemetryMaintenance] Error during consolidation & purge: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            conn.close()
