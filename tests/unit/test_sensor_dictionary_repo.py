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
# File: tests/unit/test_sensor_dictionary_repo.py
# Author: Gabriel Moraes
# Date: 2026-09-04

"""
Unit tests for SensorDictionaryRepository string-to-integer normalization and RAM caching.
"""

from src.repositories.sensor_dictionary_repo import SensorDictionaryRepository


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
