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
# File: tests/unit/test_sensor_telemetry_writer.py
# Author: Gabriel Moraes
# Date: 2026-09-04

"""
Unit tests for SensorTelemetryWriter delta compression and batch insertion.
"""

from src.repositories.sensor_dictionary_repo import SensorDictionaryRepository
from src.repositories.sensor_telemetry_writer import SensorTelemetryWriter


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
