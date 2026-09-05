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
# File: tests/unit/test_database_manager.py
# Author: Gabriel Moraes
# Date: 2026-09-04

"""
Unit tests for DatabaseManager facade orchestration, operational sessions lifecycle,
and non-blocking async telemetry worker flushing.
"""

from src.database.database_manager import DatabaseManager


def test_database_manager_facade_and_async_worker(temp_db_engine):
    """Verifies DatabaseManager orchestrating the async worker and operational sessions."""
    db_mgr = DatabaseManager(engine=temp_db_engine, auto_start_worker=True)

    # Start session
    sid = db_mgr.start_operation_session()
    assert sid is not None

    # Push telemetry to async worker
    for _ in range(5):
        db_mgr.push_telemetry(
            sensor_id="sensor_async",
            speed=55.0,
            flow_rate=180.0,
            occupancy=0.22
        )

    # Stop worker gracefully, which flushes queued items deterministically without sleep
    db_mgr.stop()

    # End session
    ended = db_mgr.end_operation_session(status="FINALIZADO_NORMAL")
    assert ended is True

    # Verify telemetry was flushed to database
    history = db_mgr.query_telemetry_history()
    async_samples = [h for h in history if h["sensor_str_id"] == "sensor_async"]
    assert len(async_samples) >= 1
    assert sum(s["sample_count"] for s in async_samples) == 5
