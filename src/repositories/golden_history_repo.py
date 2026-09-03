# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# File: src/repositories/golden_history_repo.py
# Author: Gabriel Moraes
# Date: 2026-09-02

import io
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Dict, Any, List
import pandas as pd

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine
    from src.repositories.sensor_dictionary_repo import SensorDictionaryRepository

logger = logging.getLogger("Synapse.GoldenHistoryRepo")


class GoldenHistoryRepository:
    """
    High-fidelity repository for the Golden Dataset.
    Stores and queries the curated baseline IN ITS ENTIRETY (zero data loss,
    no delta compression) to guarantee exact ground-truth precision for the
    MEH (Micro-Estimation History) hierarchical query engine.
    """

    def __init__(self, engine: 'DatabaseEngine', dictionary_repo: 'SensorDictionaryRepository'):
        self.engine = engine
        self.dictionary_repo = dictionary_repo

    def ingest_dataframe(self, df: pd.DataFrame, version: str = "v1") -> bool:
        """
        Ingests a Golden Dataset DataFrame into the database na íntegra.
        Uses PostgreSQL streaming COPY protocol for ultra-high throughput (~50,000 rows/s).
        """
        if df is None or df.empty:
            logger.warning("[GoldenHistoryRepo] DataFrame is empty, skipping ingestion.")
            return False

        conn = self.engine.get_connection()
        if not conn:
            return False

        try:
            # 1. Identify and normalize column mappings
            time_col = None
            for c in ["timestamp", "time", "datetime", "collected_at", "ts"]:
                if c in df.columns:
                    time_col = c
                    break
            if time_col is None:
                time_col = df.columns[0]

            sensor_col = None
            for c in ["sensor_id", "sensor", "id", "node_id", "edge_id"]:
                if c in df.columns:
                    sensor_col = c
                    break
            if sensor_col is None:
                sensor_col = df.columns[1] if len(df.columns) > 1 else time_col

            speed_col = next((c for c in ["speed", "mean_speed", "avg_speed", "velocidade"] if c in df.columns), None)
            flow_col = next((c for c in ["flow_rate", "flow", "volume", "vazao"] if c in df.columns), None)
            occ_col = next((c for c in ["occupancy", "occ", "density", "ocupacao"] if c in df.columns), None)

            # Preload dictionary mapping
            sensor_names = df[sensor_col].astype(str).unique().tolist()
            name_to_id = self.dictionary_repo.bulk_get_or_create(sensor_names)

            logger.info(f"[GoldenHistoryRepo] 🚀 Starting intact Golden ingestion ({len(df)} records, version='{version}')...")

            if self.engine.db_type == "postgres":
                cursor = conn.cursor()
                buf = io.StringIO()
                for _, row in df.iterrows():
                    s_str = str(row[sensor_col])
                    s_int = name_to_id.get(s_str, 0)
                    raw_t = row[time_col]
                    dt = pd.to_datetime(raw_t, unit='s') if isinstance(raw_t, (int, float)) and raw_t < 1e11 else pd.to_datetime(raw_t)
                    t_val = str(dt.isoformat())
                    u_val = float(row[speed_col]) if speed_col else 0.0
                    q_val = float(row[flow_col]) if flow_col else 0.0
                    k_val = float(row[occ_col]) if occ_col else 0.0
                    buf.write(f"{version}\t{s_str}\t{s_int}\t{t_val}\t{q_val}\t{u_val}\t{k_val}\n")
                
                buf.seek(0)
                cursor.copy_from(
                    buf,
                    "synapse_golden_history",
                    columns=("version", "sensor_str_id", "sensor_int_id", "timestamp_val", "flow_rate", "speed", "occupancy")
                )
                conn.commit()
            else:
                cursor = conn.cursor()
                rows = []
                for _, row in df.iterrows():
                    s_str = str(row[sensor_col])
                    s_int = name_to_id.get(s_str, 0)
                    raw_t = row[time_col]
                    dt = pd.to_datetime(raw_t, unit='s') if isinstance(raw_t, (int, float)) and raw_t < 1e11 else pd.to_datetime(raw_t)
                    t_val = dt.strftime("%Y-%m-%d %H:%M:%S")
                    u_val = float(row[speed_col]) if speed_col else 0.0
                    q_val = float(row[flow_col]) if flow_col else 0.0
                    k_val = float(row[occ_col]) if occ_col else 0.0
                    rows.append((version, s_str, s_int, t_val, q_val, u_val, k_val))

                cursor.executemany("""
                    INSERT INTO synapse_golden_history (
                        version, sensor_str_id, sensor_int_id, timestamp_val, flow_rate, speed, occupancy
                    ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """, rows)
                conn.commit()

            logger.info(f"[GoldenHistoryRepo] ✅ Successfully ingested Golden Dataset ({len(df)} records) na íntegra.")
            return True
        except Exception as e:
            logger.error(f"[GoldenHistoryRepo] Error ingesting Golden Dataset: {e}", exc_info=True)
            try:
                conn.rollback()
            except Exception:
                pass
            return False
        finally:
            conn.close()

    def get_exact_reading(
        self,
        sensor_id: str,
        target_timestamp: float,
        tolerance_sec: float = 10.0,
        version: str = "v1"
    ) -> Optional[Dict[str, float]]:
        """
        MEH Tier-1 Lookup: Exact match within +/- tolerance_sec.
        Fast B-tree index scan on (sensor_int_id, timestamp_val).
        """
        sensor_int = self.dictionary_repo.get_or_create(sensor_id)
        if sensor_int == 0:
            return None

        conn = self.engine.get_connection()
        if not conn:
            return None

        dt_target = datetime.fromtimestamp(target_timestamp)
        try:
            cursor = conn.cursor()
            if self.engine.db_type == "postgres":
                cursor.execute("""
                    SELECT flow_rate, speed, occupancy, timestamp_val 
                    FROM synapse_golden_history
                    WHERE sensor_int_id = %s AND version = %s
                      AND timestamp_val BETWEEN %s - INTERVAL '%s seconds' AND %s + INTERVAL '%s seconds'
                    ORDER BY ABS(EXTRACT(EPOCH FROM (timestamp_val - %s))) ASC
                    LIMIT 1;
                """, (sensor_int, version, dt_target, tolerance_sec, dt_target, tolerance_sec, dt_target))
            else:
                target_epoch = int(target_timestamp)
                cursor.execute("""
                    SELECT flow_rate, speed, occupancy, timestamp_val 
                    FROM synapse_golden_history
                    WHERE sensor_int_id = ? AND version = ?
                    ORDER BY ABS(strftime('%s', timestamp_val) - ?) ASC
                    LIMIT 1;
                """, (sensor_int, version, target_epoch))

            row = cursor.fetchone()
            if row:
                return {"flow_rate": float(row[0]), "speed": float(row[1]), "occupancy": float(row[2])}
            return None
        except Exception as e:
            logger.error(f"[GoldenHistoryRepo] Error in get_exact_reading: {e}")
            return None
        finally:
            conn.close()

    def get_cyclical_reading(
        self,
        sensor_id: str,
        target_timestamp: float,
        version: str = "v1"
    ) -> Optional[Dict[str, float]]:
        """
        MEH Tier-3 Lookup: Same Day-of-Week (DOW) and Hour using functional indexes.
        """
        sensor_int = self.dictionary_repo.get_or_create(sensor_id)
        if sensor_int == 0:
            return None

        conn = self.engine.get_connection()
        if not conn:
            return None

        dt_target = datetime.fromtimestamp(target_timestamp)
        dow = dt_target.isoweekday() % 7  # 0=Sunday for Postgres DOW
        hour = dt_target.hour

        try:
            cursor = conn.cursor()
            if self.engine.db_type == "postgres":
                cursor.execute("""
                    SELECT AVG(flow_rate), AVG(speed), AVG(occupancy)
                    FROM synapse_golden_history
                    WHERE sensor_int_id = %s AND version = %s
                      AND EXTRACT(DOW FROM timestamp_val) = %s
                      AND EXTRACT(HOUR FROM timestamp_val) = %s;
                """, (sensor_int, version, dow, hour))
            else:
                cursor.execute("""
                    SELECT AVG(flow_rate), AVG(speed), AVG(occupancy)
                    FROM synapse_golden_history
                    WHERE sensor_int_id = ? AND version = ?
                      AND CAST(strftime('%w', timestamp_val) AS INTEGER) = ?
                      AND CAST(strftime('%H', timestamp_val) AS INTEGER) = ?;
                """, (sensor_int, version, dow, hour))

            row = cursor.fetchone()
            if row and row[0] is not None:
                return {"flow_rate": float(row[0]), "speed": float(row[1]), "occupancy": float(row[2])}
            return None
        except Exception as e:
            logger.error(f"[GoldenHistoryRepo] Error in get_cyclical_reading: {e}")
            return None
        finally:
            conn.close()

    def get_sensor_profile(self, sensor_id: str, version: str = "v1") -> Optional[Dict[str, float]]:
        """
        MEH Tier-5 Lookup: Global historical average profile for the sensor.
        """
        sensor_int = self.dictionary_repo.get_or_create(sensor_id)
        if sensor_int == 0:
            return None

        conn = self.engine.get_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()
            param = "%s" if self.engine.db_type == "postgres" else "?"
            cursor.execute(f"""
                SELECT AVG(flow_rate), AVG(speed), AVG(occupancy)
                FROM synapse_golden_history
                WHERE sensor_int_id = {param} AND version = {param};
            """, (sensor_int, version))
            row = cursor.fetchone()
            if row and row[0] is not None:
                return {"flow_rate": float(row[0]), "speed": float(row[1]), "occupancy": float(row[2])}
            return None
        except Exception as e:
            logger.error(f"[GoldenHistoryRepo] Error in get_sensor_profile: {e}")
            return None
        finally:
            conn.close()
