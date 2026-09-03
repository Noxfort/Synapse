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
# File: tests/unit/test_node_manager_solid.py
# Author: Gabriel Moraes
# Date: 2026-08-28

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from src.managers.node_manager import NodeManager
from src.managers.storage_manager import StorageManager
from src.factories.node_factory import NodeFactory
from src.interfaces.node import (
    ITrafficNode,
    INodeCheckpointStorage,
    INodeFactory,
    INodeManager
)


def test_node_manager_protocol_conformance():
    """Validates that NodeManager and dependencies conform to runtime checkable protocols."""
    mock_storage = MagicMock(spec=INodeCheckpointStorage)
    mock_factory = MagicMock(spec=INodeFactory)
    
    manager = NodeManager(storage=mock_storage, node_factory=mock_factory)
    assert isinstance(manager, INodeManager)
    assert isinstance(mock_storage, INodeCheckpointStorage)
    assert isinstance(mock_factory, INodeFactory)
    assert isinstance(StorageManager(), INodeCheckpointStorage)


def test_node_manager_add_node_fresh():
    """Verifies adding a fresh node without existing checkpoint."""
    mock_storage = MagicMock(spec=INodeCheckpointStorage)
    mock_storage.load_node_checkpoint.return_value = None

    mock_node = MagicMock(spec=ITrafficNode)
    mock_node.source_id = "sensor_1"
    mock_node.is_ready = True

    mock_factory = MagicMock(spec=INodeFactory)
    mock_factory.create_node.return_value = mock_node

    manager = NodeManager(storage=mock_storage, node_factory=mock_factory)
    
    assert manager.add_node("sensor_1") is True
    assert manager.get_node("sensor_1") == mock_node
    assert "sensor_1" not in manager.probation_nodes
    assert manager.add_node("sensor_1") is False  # Duplicate rejection


def test_node_manager_add_node_restoration_and_probation():
    """Verifies restoring a node from checkpoint activates probation period."""
    mock_storage = MagicMock(spec=INodeCheckpointStorage)
    saved_state = {"source_id": "sensor_2", "steps_processed": 100}
    mock_storage.load_node_checkpoint.return_value = saved_state

    mock_node = MagicMock(spec=ITrafficNode)
    mock_node.source_id = "sensor_2"
    mock_node.is_ready = True

    mock_factory = MagicMock(spec=INodeFactory)
    mock_factory.create_node.return_value = mock_node

    manager = NodeManager(storage=mock_storage, node_factory=mock_factory, probation_duration=10.0)
    
    assert manager.add_node("sensor_2") is True
    mock_storage.load_node_checkpoint.assert_called_once_with("sensor_2")
    mock_node.set_state.assert_called_once_with(saved_state)
    assert "sensor_2" in manager.probation_nodes


def test_node_manager_update_node_with_probation_lifecycle():
    """Verifies update_node executes step and manages probation status transition."""
    mock_storage = MagicMock(spec=INodeCheckpointStorage)
    mock_storage.load_node_checkpoint.return_value = {"state": "restored"}

    mock_node = MagicMock(spec=ITrafficNode)
    mock_node.source_id = "sensor_prob"
    mock_node.step.side_effect = lambda val: {"status": "Normal", "loss": 0.02, "value": val}

    mock_factory = MagicMock(spec=INodeFactory)
    mock_factory.create_node.return_value = mock_node

    manager = NodeManager(storage=mock_storage, node_factory=mock_factory, probation_duration=2.0)
    manager.add_node("sensor_prob")

    # 1. Update while in probation -> status overridden
    res1 = manager.update_node("sensor_prob", 42.0)
    assert "Probation" in res1["status"]

    # 2. Simulate probation expiration
    manager.probation_nodes["sensor_prob"] = datetime.now() - timedelta(seconds=5)
    res2 = manager.update_node("sensor_prob", 43.0)
    assert "sensor_prob" not in manager.probation_nodes
    assert res2["status"] == "Normal"


def test_node_manager_trigger_fallback():
    """Verifies trigger_fallback invokes ghost_step on the target node."""
    mock_storage = MagicMock(spec=INodeCheckpointStorage)
    mock_storage.load_node_checkpoint.return_value = None

    mock_node = MagicMock(spec=ITrafficNode)
    mock_node.source_id = "sensor_fallback"
    mock_node.ghost_step.return_value = {"method_used": "Physics", "value": 15.0}

    mock_factory = MagicMock(spec=INodeFactory)
    mock_factory.create_node.return_value = mock_node

    manager = NodeManager(storage=mock_storage, node_factory=mock_factory)
    manager.add_node("sensor_fallback")

    # Non-existent node fallback
    assert manager.trigger_fallback("unknown_node", "timeout") is None

    # Existent node fallback
    res = manager.trigger_fallback("sensor_fallback", "Camera dropped frames")
    mock_node.ghost_step.assert_called_once()
    assert res["method_used"] == "Physics"
    assert res["value"] == 15.0


def test_node_manager_save_all_nodes():
    """Verifies saving state of all nodes delegates to injected storage."""
    mock_storage = MagicMock(spec=INodeCheckpointStorage)
    mock_storage.load_node_checkpoint.return_value = None
    mock_storage.save_node_checkpoint.return_value = True

    mock_node_1 = MagicMock(spec=ITrafficNode)
    mock_node_1.source_id = "s1"
    mock_node_1.get_state.return_value = {"state": 1}

    mock_node_2 = MagicMock(spec=ITrafficNode)
    mock_node_2.source_id = "s2"
    mock_node_2.get_state.return_value = {"state": 2}

    def fake_factory(source_id, **kwargs):
        return mock_node_1 if source_id == "s1" else mock_node_2

    manager = NodeManager(storage=mock_storage, node_factory=fake_factory)
    manager.add_node("s1")
    manager.add_node("s2")

    manager.save_all_nodes()
    mock_storage.save_node_checkpoint.assert_any_call("s1", {"state": 1})
    mock_storage.save_node_checkpoint.assert_any_call("s2", {"state": 2})
    assert mock_storage.save_node_checkpoint.call_count == 2


def test_node_manager_remove_node_and_accessors():
    """Verifies node removal and collection accessors."""
    mock_storage = MagicMock(spec=INodeCheckpointStorage)
    mock_storage.load_node_checkpoint.return_value = {"val": 1}

    mock_node_a = MagicMock(spec=ITrafficNode)
    mock_node_a.source_id = "a"
    mock_node_a.is_ready = True
    mock_node_a.agent = "agent_a"

    mock_node_b = MagicMock(spec=ITrafficNode)
    mock_node_b.source_id = "b"
    mock_node_b.is_ready = False
    mock_node_b.agent = "agent_b"

    def fake_factory(source_id, **kwargs):
        return mock_node_a if source_id == "a" else mock_node_b

    manager = NodeManager(storage=mock_storage, node_factory=fake_factory)
    manager.add_node("a")
    manager.add_node("b")

    assert manager.get_ready_nodes_ids() == ["a"]
    assert manager.get_agents_for_pbt() == {"a": "agent_a", "b": "agent_b"}
    assert len(manager.get_all_nodes()) == 2

    # Remove node
    manager.remove_node("a")
    assert manager.get_node("a") is None
    assert "a" not in manager.probation_nodes
    assert len(manager.get_all_nodes()) == 1
