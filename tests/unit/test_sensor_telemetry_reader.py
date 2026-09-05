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
# File: tests/unit/test_sensor_telemetry_reader.py
# Author: Gabriel Moraes
# Date: 2026-09-04

"""
Unit tests for SensorTelemetryReader queries and SQL pushdown aggregation.
"""

from src.repositories.sensor_dictionary_repo import SensorDictionaryRepository
from src.repositories.sensor_telemetry_writer import SensorTelemetryWriter
from src.repositories.sensor_telemetry_reader import SensorTelemetryReader


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
