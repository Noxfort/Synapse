# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# File: src/repositories/sensor_telemetry_writer.py
# Author: Gabriel Moraes
# Date: 2026-09-02

import io
import logging
from datetime import datetime
from typing import TYPE_CHECKING, List, Dict, Tuple, Any

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine
    from src.repositories.sensor_dictionary_repo import SensorDictionaryRepository

logger = logging.getLogger("Synapse.SensorTelemetryWriter")


class SensorTelemetryWriter:
    """
    Handles batch insertions, Delta Compression, and Sensor Dictionary lookups
    for streaming sensor telemetry. Ported and adapted from CARINA FluidDynamicsWriter.
    """

    def __init__(self, engine: 'DatabaseEngine', dictionary_repo: 'SensorDictionaryRepository'):
        self.engine = engine
        self.dictionary_repo = dictionary_repo
        # Cache for delta compression: sensor_str_id -> (last_sample_dict, state_key_tuple)
        self._last_sensor_samples: Dict[str, Tuple[Dict[str, Any], Tuple]] = {}

    def _apply_delta_compression(self, samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Aggregates consecutive identical telemetry samples per sensor to reduce database rows by up to 98%.
        Increments sample_count when metrics are unchanged within float tolerance.
        """
        compressed = []
        for s in samples:
            sensor_id = str(s.get('sensor_id') or s.get('sensor_str_id', 'unknown'))
            speed = round(float(s.get('speed', 0.0)), 2)
            flow = round(float(s.get('flow_rate', s.get('flow', 0.0))), 2)
            occ = round(float(s.get('occupancy', 0.0)), 2)
            status = int(s.get('status', 2))
            scenario = str(s.get('scenario_name', 'default'))

            key = (sensor_id, speed, flow, occ, status, scenario)

            if sensor_id in self._last_sensor_samples:
                prev_sample, prev_key = self._last_sensor_samples[sensor_id]
                if prev_key == key:
                    # Unchanged state: increment sample count and update last timestamp
                    prev_sample['sample_count'] = prev_sample.get('sample_count', 1) + int(s.get('sample_count', 1))
                    prev_sample['collected_at'] = s.get('collected_at', prev_sample.get('collected_at'))
                    continue
                else:
                    compressed.append(prev_sample)

            new_sample = dict(s)
            new_sample['sensor_str_id'] = sensor_id
            new_sample['sample_count'] = int(new_sample.get('sample_count', 1))
            self._last_sensor_samples[sensor_id] = (new_sample, key)

        return compressed

    def flush_pending_delta_samples(self) -> List[Dict[str, Any]]:
        """Drains the in-memory delta cache (e.g. at shutdown or scenario change)."""
        pending = [sample for sample, _ in self._last_sensor_samples.values()]
        self._last_sensor_samples.clear()
        return pending

    def insert_telemetry_batch(self, samples: List[Dict[str, Any]], force_flush_delta: bool = False):
        """
        Batch-inserts sensor telemetry using real-time Delta Compression and Dictionary IDs.
        """
        if not samples:
            return

        conn = self.engine.get_connection()
        if not conn:
            return

        try:
            # 1. Delta Compression
            compressed_samples = self._apply_delta_compression(samples)
            if force_flush_delta:
                compressed_samples.extend(self.flush_pending_delta_samples())

            if not compressed_samples:
                return

            cursor = conn.cursor()
            now = datetime.now()

            # 2. Build rows with resolved numeric sensor IDs
            rows = []
            for s in compressed_samples:
                str_id = s.get('sensor_str_id') or s.get('sensor_id') or 'unknown'
                int_id = self.dictionary_repo.get_or_create(str_id, conn=conn)
                c_at = s.get('collected_at') or now
                if self.engine.db_type != "postgres" and hasattr(c_at, "strftime"):
                    c_at = c_at.strftime("%Y-%m-%d %H:%M:%S")
                rows.append((
                    c_at,
                    s.get('scenario_name', 'default'),
                    str_id,
                    int_id,
                    float(s.get('flow_rate', s.get('flow', 0.0))),
                    float(s.get('speed', 0.0)),
                    float(s.get('occupancy', 0.0)),
                    int(s.get('sample_count', 1)),
                    int(s.get('status', 2))
                ))

            # 3. High-Speed Bulk Insert
            if self.engine.db_type == "postgres":
                copied = False
                try:
                    # High-throughput streaming COPY protocol (~50k rows/s)
                    buf = io.StringIO()
                    for r in rows:
                        c_at_val, scen, s_str, s_int, flow, spd, occ, cnt, stat = r
                        ts_str = c_at_val.isoformat() if hasattr(c_at_val, "isoformat") else str(c_at_val)
                        clean_scen = str(scen).replace('\t', ' ').replace('\n', ' ')
                        clean_str = str(s_str).replace('\t', ' ').replace('\n', ' ')
                        buf.write(f"{ts_str}\t{clean_scen}\t{clean_str}\t{s_int}\t{flow}\t{spd}\t{occ}\t{cnt}\t{stat}\n")
                    buf.seek(0)
                    cursor.copy_from(
                        buf,
                        "synapse_sensor_telemetry_raw",
                        columns=(
                            "collected_at", "scenario_name", "sensor_str_id", "sensor_int_id",
                            "flow_rate", "speed", "occupancy", "sample_count", "status"
                        )
                    )
                    copied = True
                except Exception as copy_err:
                    logger.debug(f"[SensorTelemetryWriter] Streaming COPY notice: {copy_err}, falling back to execute_values.")

                if not copied:
                    try:
                        from psycopg2.extras import execute_values
                        query = """
                            INSERT INTO synapse_sensor_telemetry_raw (
                                collected_at, scenario_name, sensor_str_id, sensor_int_id,
                                flow_rate, speed, occupancy, sample_count, status
                            ) VALUES %s;
                        """
                        execute_values(cursor, query, rows, page_size=1000)
                    except Exception:
                        sql = """
                            INSERT INTO synapse_sensor_telemetry_raw (
                                collected_at, scenario_name, sensor_str_id, sensor_int_id,
                                flow_rate, speed, occupancy, sample_count, status
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """
                        cursor.executemany(sql, rows)
            else:
                sql = """
                    INSERT INTO synapse_sensor_telemetry_raw (
                        collected_at, scenario_name, sensor_str_id, sensor_int_id,
                        flow_rate, speed, occupancy, sample_count, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """
                cursor.executemany(sql, rows)

            conn.commit()
            logger.debug(f"[SensorTelemetryWriter] Inserted {len(rows)} compressed telemetry samples.")
        except Exception as e:
            logger.error(f"[SensorTelemetryWriter] Error inserting telemetry batch: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            conn.close()
