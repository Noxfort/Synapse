# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# File: src/repositories/sensor_dictionary_repo.py
# Author: Gabriel Moraes
# Date: 2026-09-02

import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Any

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine

logger = logging.getLogger("Synapse.SensorDictionaryRepo")


class SensorDictionaryRepository:
    """
    Normalizes long string sensor IDs into 4-byte integers (sensor_int_id)
    with bidirectional in-memory RAM caching for sub-millisecond lookups.
    """

    def __init__(self, engine: 'DatabaseEngine'):
        self.engine = engine
        self._str_to_int: Dict[str, int] = {}
        self._int_to_str: Dict[int, str] = {}
        self._preload_cache()

    def _preload_cache(self):
        """Preloads existing sensor mappings from database on startup."""
        conn = self.engine.get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT sensor_int_id, sensor_str_id FROM sensor_dictionary;")
            rows = cursor.fetchall()
            for int_id, str_id in rows:
                self._str_to_int[str_id] = int_id
                self._int_to_str[int_id] = str_id
            logger.info(f"[SensorDictionaryRepo] Loaded {len(self._str_to_int)} sensors into RAM cache.")
        except Exception as e:
            logger.warning(f"[SensorDictionaryRepo] Could not preload cache: {e}")
        finally:
            conn.close()

    def get_or_create(self, sensor_str_id: str, conn: Optional[Any] = None) -> int:
        """
        Returns integer ID for sensor string ID.
        Checks in-memory cache first (< 0.001 ms). If missing, queries or inserts into DB.
        """
        if not sensor_str_id:
            return 0
        if sensor_str_id in self._str_to_int:
            return self._str_to_int[sensor_str_id]

        local_conn = conn or self.engine.get_connection()
        if not local_conn:
            return 0
        try:
            cursor = local_conn.cursor()
            param_placeholder = "%s" if self.engine.db_type == "postgres" else "?"
            cursor.execute(
                f"SELECT sensor_int_id FROM sensor_dictionary WHERE sensor_str_id = {param_placeholder};",
                (sensor_str_id,)
            )
            row = cursor.fetchone()
            if row:
                int_id = row[0]
            else:
                if self.engine.db_type == "postgres":
                    cursor.execute(
                        "INSERT INTO sensor_dictionary (sensor_str_id) VALUES (%s) RETURNING sensor_int_id;",
                        (sensor_str_id,)
                    )
                    int_id = cursor.fetchone()[0]
                else:
                    cursor.execute(
                        "INSERT INTO sensor_dictionary (sensor_str_id) VALUES (?);",
                        (sensor_str_id,)
                    )
                    int_id = cursor.lastrowid
                local_conn.commit()

            self._str_to_int[sensor_str_id] = int_id
            self._int_to_str[int_id] = sensor_str_id
            return int_id
        except Exception as e:
            logger.error(f"[SensorDictionaryRepo] Failed to get/create ID for '{sensor_str_id}': {e}")
            return 0
        finally:
            if conn is None and local_conn:
                local_conn.close()

    def get_str_id(self, sensor_int_id: int) -> Optional[str]:
        """Returns string ID from numeric ID, with RAM cache fallback."""
        if sensor_int_id in self._int_to_str:
            return self._int_to_str[sensor_int_id]

        conn = self.engine.get_connection()
        if not conn:
            return None
        try:
            cursor = conn.cursor()
            param = "%s" if self.engine.db_type == "postgres" else "?"
            cursor.execute(f"SELECT sensor_str_id FROM sensor_dictionary WHERE sensor_int_id = {param};", (sensor_int_id,))
            row = cursor.fetchone()
            if row:
                str_id = row[0]
                self._str_to_int[str_id] = sensor_int_id
                self._int_to_str[sensor_int_id] = str_id
                return str_id
            return None
        except Exception as e:
            logger.error(f"[SensorDictionaryRepo] Error resolving str_id for {sensor_int_id}: {e}")
            return None
        finally:
            conn.close()

    def bulk_get_or_create(self, sensor_str_ids: List[str]) -> Dict[str, int]:
        """Resolves a list of sensor IDs efficiently using cache + single batch query."""
        results = {}
        missing = []
        for sid in sensor_str_ids:
            if sid in self._str_to_int:
                results[sid] = self._str_to_int[sid]
            else:
                missing.append(sid)

        if not missing:
            return results

        conn = self.engine.get_connection()
        if not conn:
            return results
        try:
            for sid in missing:
                results[sid] = self.get_or_create(sid, conn=conn)
        finally:
            conn.close()
        return results
