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
# File: tests/unit/test_kse_warmup.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import pytest
import time
import numpy as np
from unittest.mock import MagicMock, patch

from src.managers.kse_manager import KSEManager
from src.domain.app_state import AppState
from src.domain.entities import DataSource, SourceType, SourceStatus
from src.node.traffic_node import TrafficNode
from src.memory.temporal_memory import TemporalMemory
from src.agents.specialist_agent import SpecialistAgent


@pytest.fixture
def mock_app_state():
    app_state = MagicMock(spec=AppState)
    app_state.get_all_nodes.return_value = []
    app_state.get_all_edges.return_value = []
    return app_state


def test_traffic_node_validation_at_sample_1():
    """Verifies that a sensor with low loss converges and validates on sample 1."""
    memory = TemporalMemory(feature_dim=1, max_len=60)
    agent = MagicMock(spec=SpecialistAgent)
    agent.train.return_value = 0.02  # Low loss (< 0.15)
    agent.predict.return_value = np.zeros(32)

    kse = MagicMock()
    kse_snap = MagicMock(p=10.0, v=0.0, a=0.0, confidence=1.0)
    kse.get_kinetic_snapshot.return_value = kse_snap

    graph_mgr = MagicMock()
    app_state = MagicMock()
    src = DataSource(id="src_local_1", name="Cam 1", source_type=SourceType.API, is_local=True, status=SourceStatus.QUARANTINE)
    app_state.get_all_data_sources.return_value = [src]
    app_state.get_element_for_source.return_value = "node_1"
    graph_mgr.app_state = app_state

    node = TrafficNode("node_1", memory, agent, MagicMock(), kse, graph_manager=graph_mgr)

    res = node.step(15.0)

    assert node.steps_processed == 1
    assert node.is_validated is True
    assert node.is_rejected is False
    assert res["status"] == "Active"
    assert res["ready"] is True
    assert src.status == SourceStatus.ACTIVE


def test_traffic_node_rejection_after_10_samples():
    """Verifies that a sensor that cannot learn after 10 samples is rejected/discarded."""
    memory = TemporalMemory(feature_dim=1, max_len=60)
    agent = MagicMock(spec=SpecialistAgent)
    agent.train.return_value = 0.85  # High loss (> 0.15)
    agent.predict.return_value = np.zeros(32)

    kse = MagicMock()
    kse_snap = MagicMock(p=10.0, v=0.0, a=0.0, confidence=1.0)
    kse.get_kinetic_snapshot.return_value = kse_snap

    graph_mgr = MagicMock()
    app_state = MagicMock()
    src = DataSource(id="src_local_1", name="Cam 1", source_type=SourceType.API, is_local=True, status=SourceStatus.QUARANTINE)
    app_state.get_all_data_sources.return_value = [src]
    app_state.get_element_for_source.return_value = "node_1"
    graph_mgr.app_state = app_state

    node = TrafficNode("node_1", memory, agent, MagicMock(), kse, graph_manager=graph_mgr)

    # 10 samples with high loss
    for i in range(1, 11):
        res = node.step(float(i * 10))
        assert node.is_validated is False
        assert node.is_rejected is False
        assert "Calibrando" in res["status"]

    # 11th step triggers rejection
    res11 = node.step(110.0)
    assert node.is_rejected is True
    assert res11["status"] == "Rejected"
    assert res11["rejected"] is True
    assert src.status == SourceStatus.REJECTED


def test_kse_transmission_gate_requires_both_local_and_global(mock_app_state):
    """
    Verifies that KSEManager only transmits to CARINA when at least 1 LOCAL
    and 1 GLOBAL sensor are ACTIVE.
    """
    with patch("src.managers.kse_manager.MEHBridge") as MockMEHBridge, \
         patch("src.managers.kse_manager.PacketBuilder") as MockPacketBuilder:

        mock_bridge_instance = MockMEHBridge.return_value
        mock_bridge_instance.load_baseline.return_value = {"edge_1": {"flow": 10.0}}
        mock_bridge_instance.refresh_if_needed.return_value = None

        MockPacketBuilder.build.return_value = {"test_packet": True}
        MockPacketBuilder.extrapolate.return_value = {"test_packet": True}

        # Setup sources in app_state
        src_local = DataSource(id="src_1", name="Camera 1", source_type=SourceType.API, is_local=True, status=SourceStatus.QUARANTINE)
        src_global = DataSource(id="src_2", name="Waze API", source_type=SourceType.API, is_local=False, status=SourceStatus.QUARANTINE)
        mock_app_state.get_all_data_sources.return_value = [src_local, src_global]

        manager = KSEManager(mock_app_state)
        emitted_packets = []
        manager.data_ready_for_transmission.connect(lambda p: emitted_packets.append(p))

        manager.start()
        manager.min_window_ms = 0.0

        # Case 1: Both quarantine -> No transmission
        manager.sync_with_reality({"node_1": {"value": 10.0}})
        manager._check_elastic_window()
        assert len(emitted_packets) == 0
        assert manager.is_warmup_complete is False

        # Case 2: Only local active -> No transmission
        src_local.status = SourceStatus.ACTIVE
        manager.sync_with_reality({"node_1": {"value": 10.0}})
        manager._check_elastic_window()
        assert len(emitted_packets) == 0
        assert manager.is_warmup_complete is False

        # Case 3: Both local and global active -> Transmission unlocked!
        src_global.status = SourceStatus.ACTIVE
        manager.last_transmission_time = 0.0
        manager.sync_with_reality({"node_1": {"value": 10.0}})
        manager._check_elastic_window()

        assert manager.is_warmup_complete is True
        assert manager._has_valid_data is True
        assert len(emitted_packets) > 0, "Transmission should unlock when both Local and Global are Active"

        manager.stop()
