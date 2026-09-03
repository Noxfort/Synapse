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
# File: tests/unit/test_packet_builder.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import pytest
from unittest.mock import MagicMock
from src.kse.packet_builder import PacketBuilder
from src.domain.entities import MapEdge


def test_packet_builder_with_app_state_edges():
    """Verify that PacketBuilder builds full network packets using edges from app_state."""
    edge1 = MapEdge(
        id="edge_1",
        from_node="node_A",
        to_node="node_B",
        shape=[(0.0, 0.0), (100.0, 0.0)],
        length=100.0,
        lanes=2,
        max_speed=13.89,
    )
    edge2 = MapEdge(
        id="edge_2",
        from_node="node_B",
        to_node="node_C",
        shape=[(100.0, 0.0), (200.0, 0.0)],
        length=150.0,
        lanes=1,
        max_speed=13.89,
    )

    mock_app_state = MagicMock()
    mock_app_state.get_all_edges.return_value = [edge1, edge2]

    data = {
        "edge_1": {"density": 25.0, "speed": 12.0, "physics": {"v": 11.5}},
        "node_B": {"value": 30.0, "physics": {"v": 10.0}},
    }

    packet = PacketBuilder.build(data, source="realtime", app_state=mock_app_state)

    assert packet is not None
    assert packet["source"] == "realtime"
    assert len(packet["traffic"]) == 2

    edge1_data = next(t for t in packet["traffic"] if t["edge_id"] == "edge_1")
    assert edge1_data["density"] == 25.0
    assert edge1_data["speed"] == 11.5

    edge2_data = next(t for t in packet["traffic"] if t["edge_id"] == "edge_2")
    assert edge2_data["density"] == 30.0
    assert edge2_data["speed"] == 10.0


def test_packet_builder_fallback_when_no_edges():
    """Verify fallback path when app_state is None or has no edges."""
    data = {
        "sensor_1": {"density": 20.0, "speed": 10.0},
        "sensor_2": {"value": 15.0},
    }

    packet_no_app_state = PacketBuilder.build(data, source="realtime", app_state=None)
    assert packet_no_app_state is not None
    assert len(packet_no_app_state["traffic"]) == 2

    mock_app_state = MagicMock()
    mock_app_state.get_all_edges.return_value = []
    packet_empty_edges = PacketBuilder.build(data, source="kse_dead_reckoning", app_state=mock_app_state)
    assert packet_empty_edges is not None
    assert packet_empty_edges["source"] == "kse_dead_reckoning"
    assert len(packet_empty_edges["traffic"]) == 2


def test_packet_builder_empty_data():
    """Verify that empty data returns None."""
    assert PacketBuilder.build({}, source="realtime", app_state=None) is None


def test_packet_builder_queue_calculation_when_congested():
    """Verify that congested edges or cyclic signals produce non-zero vehicle queues."""
    edge = MapEdge(
        id="edge_congested",
        from_node="node_A",
        to_node="node_B",
        shape=[(0.0, 0.0), (300.0, 0.0)],
        length=300.0,
        lanes=3,
        max_speed=13.89,  # ~50 km/h
        signal_group_id=1,
    )
    mock_app_state = MagicMock()
    mock_app_state.get_all_edges.return_value = [edge]

    # Edge with high density (75.0 veh/km) and low speed (2.5 m/s)
    data = {
        "edge_congested": {"density": 75.0, "speed": 2.5}
    }

    packet = PacketBuilder.build(data, source="realtime", app_state=mock_app_state)
    assert packet is not None
    edge_data = packet["traffic"][0]
    assert edge_data["queue"] > 0
    assert edge_data["occupancy"] > 0.10


def test_packet_builder_kmh_speed_conversion():
    """Verify that speed values in km/h (>35.0) are converted to m/s."""
    edge = MapEdge(
        id="edge_express",
        from_node="node_A",
        to_node="node_B",
        shape=[(0.0, 0.0), (500.0, 0.0)],
        length=500.0,
        lanes=2,
        max_speed=27.78,  # 100 km/h in m/s
    )
    mock_app_state = MagicMock()
    mock_app_state.get_all_edges.return_value = [edge]

    # Sensor reports 72.0 km/h
    data = {
        "edge_express": {"density": 20.0, "speed": 72.0}
    }

    packet = PacketBuilder.build(data, source="realtime", app_state=mock_app_state)
    assert packet is not None
    edge_data = packet["traffic"][0]
    # 72 km/h / 3.6 = 20.0 m/s
    assert abs(edge_data["speed"] - 20.0) < 0.1


def test_json_lines_logger_and_carina_dumps(tmp_path, monkeypatch):
    """Verify that JsonLinesLogger creates valid JSONL files and logs data properly."""
    import json
    from src.utils.debug_logger import JsonLinesLogger

    monkeypatch.setattr("src.utils.debug_logger.get_log_dir", lambda: tmp_path)

    logger = JsonLinesLogger("test_subfolder", "test_prefix")
    test_data = {"test_key": "test_val", "number": 42}
    logger.log(test_data)
    logger.close()

    assert logger.file_path is not None
    assert logger.file_path.exists()

    with open(logger.file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    assert len(lines) == 1
    loaded = json.loads(lines[0])
    assert loaded["test_key"] == "test_val"
    assert loaded["number"] == 42

