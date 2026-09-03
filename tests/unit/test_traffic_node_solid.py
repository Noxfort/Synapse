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
# File: tests/unit/test_traffic_node_solid.py
# Author: Gabriel Moraes
# Date: 2026-08-18

import pytest
import numpy as np
from unittest.mock import MagicMock

from src.node.traffic_node import TrafficNode
from src.node.node_state import NodeState
from src.node.node_step_processor import NodeStepProcessor
from src.node.node_ghost_processor import NodeGhostProcessor
from src.node.node_status_notifier import NodeStatusNotifier
from src.node.node_snapshot_formatter import NodeSnapshotFormatter
from src.domain.entities import SourceStatus
from src.interfaces.memory import ITemporalMemory
from src.interfaces.node import (
    IPhysicsEngine,
    INodeValidationStrategy,
    INodeImputationStrategy
)
from src.strategies.node_validation_strategy import AdaptiveValidationStrategy
from src.strategies.node_imputation_strategy import HierarchicalImputationStrategy
from src.factories.node_factory import NodeFactory
from src.memory.temporal_memory import TemporalMemory
from src.kse.definitions import KineticState


def test_traffic_node_pure_orchestrator_step():
    """Verifies that TrafficNode orchestrates the pipeline and triggers status callback."""
    memory = MagicMock(spec=ITemporalMemory)
    memory.is_ready.return_value = True
    memory.get_tensor.return_value = MagicMock()
    memory.get_numpy.return_value = np.zeros((60, 1))

    agent = MagicMock()
    agent.train.return_value = 0.05
    agent.predict.return_value = np.ones(32)

    kse = MagicMock(spec=IPhysicsEngine)
    kse.get_kinetic_snapshot.return_value = KineticState(
        p=12.5, v=1.0, a=0.1, uncertainty=0.05, confidence=0.95
    )

    status_events = []
    def on_status_change(src_id: str, status: SourceStatus):
        status_events.append((src_id, status))

    val_strategy = MagicMock(spec=INodeValidationStrategy)
    val_strategy.evaluate.return_value = (True, False, "Active")

    imp_strategy = MagicMock(spec=INodeImputationStrategy)

    node = TrafficNode(
        source_id="node_test_1",
        memory=memory,
        agent=agent,
        physics_engine=kse,
        validation_strategy=val_strategy,
        imputation_strategy=imp_strategy,
        on_status_change=on_status_change
    )

    result = node.step(12.5)

    # Verification of pipeline orchestration
    kse.predict.assert_called_once()
    kse.update.assert_called_once_with(measurement=12.5)
    memory.push.assert_called_once_with([12.5])
    agent.train.assert_called_once()
    agent.predict.assert_called_once()
    val_strategy.evaluate.assert_called_once()

    assert node.is_validated is True
    assert result["ready"] is True
    assert result["status"] == "Active"
    assert result["value"] == 12.5
    assert len(status_events) == 1
    assert status_events[0] == ("node_test_1", SourceStatus.ACTIVE)


def test_traffic_node_ghost_step_delegation():
    """Verifies that TrafficNode delegates synthetic data resolution to imputation strategy."""
    memory = MagicMock(spec=ITemporalMemory)
    memory.is_ready.return_value = True
    memory.get_numpy.return_value = np.zeros((60, 1))

    agent = MagicMock()
    agent.predict.return_value = np.ones(32)

    kse = MagicMock(spec=IPhysicsEngine)
    kse.get_kinetic_snapshot.return_value = KineticState(
        p=20.0, v=0.0, a=0.0, uncertainty=0.1, confidence=0.9
    )

    imp_strategy = MagicMock(spec=INodeImputationStrategy)
    imp_strategy.impute.return_value = (20.0, "MEH (Hierarchical Match)")

    node = TrafficNode(
        source_id="node_test_2",
        memory=memory,
        agent=agent,
        physics_engine=kse,
        imputation_strategy=imp_strategy
    )

    result = node.ghost_step()

    imp_strategy.impute.assert_called_once()
    memory.push.assert_called_once_with([20.0])
    assert result["status"] == "Fallback: MEH (Hierarchical Match)"
    assert result["value"] == 20.0
    assert result["type"] == "synthetic"


def test_adaptive_validation_strategy_rules():
    """Tests 1-5-10 progressive validation rules in isolation."""
    strategy = AdaptiveValidationStrategy(loss_convergence_threshold=0.15, max_warmup_steps=10)
    agent = MagicMock()

    # Step 1 with low loss -> Converges
    is_val, is_rej, status = strategy.evaluate("src_1", step_count=1, loss=0.05, agent=agent, is_validated=False, is_rejected=False)
    assert is_val is True
    assert is_rej is False
    assert status == "Active"
    agent.freeze.assert_called_once()

    # Step 5 with high loss -> Calibrating
    is_val, is_rej, status = strategy.evaluate("src_2", step_count=5, loss=0.50, agent=agent, is_validated=False, is_rejected=False)
    assert is_val is False
    assert is_rej is False
    assert "Calibrando (5/10)" in status

    # Step 10 with high loss -> Still Calibrating (last chance)
    is_val, is_rej, status = strategy.evaluate("src_2", step_count=10, loss=0.50, agent=agent, is_validated=False, is_rejected=False)
    assert is_val is False
    assert is_rej is False
    assert "Calibrando (10/10)" in status

    # Step 11 with high loss -> Rejected
    is_val, is_rej, status = strategy.evaluate("src_2", step_count=11, loss=0.50, agent=agent, is_validated=False, is_rejected=False)
    assert is_val is False
    assert is_rej is True
    assert status == "Rejected"


def test_hierarchical_imputation_strategy_resolution():
    """Tests hierarchical historical DB match vs KSE physics projection."""
    strategy = HierarchicalImputationStrategy(tolerance=0.25)
    physics = MagicMock(spec=IPhysicsEngine)
    physics.get_kinetic_snapshot.return_value = KineticState(
        p=14.2, v=0.0, a=0.0, uncertainty=0.1, confidence=0.9
    )

    # 1. Historical Match
    hist_mgr = MagicMock()
    hist_mgr.get_hierarchical_reading.return_value = 35.0

    val, method = strategy.impute(
        source_id="src_1", timestamp=1000.0, dt=1.0, physics_engine=physics, historical_manager=hist_mgr
    )
    assert val == 35.0
    assert "Hierarchical Match" in method
    physics.update.assert_called_once_with(35.0)

    # 2. Data Hole (Fallback to KSE physics)
    hist_mgr_empty = MagicMock()
    hist_mgr_empty.get_hierarchical_reading.return_value = None
    hist_mgr_empty.get_exact_reading.return_value = None

    val2, method2 = strategy.impute(
        source_id="src_2", timestamp=1000.0, dt=1.0, physics_engine=physics, historical_manager=hist_mgr_empty
    )
    assert val2 == 14.2
    assert "KSE (Physics Projection)" in method2


def test_node_factory_and_state_persistence():
    """Tests NodeFactory assembly and full state get/set persistence."""
    node = NodeFactory.create_node(source_id="loop_sensor_42")

    assert node.source_id == "loop_sensor_42"
    assert node.memory is not None
    assert node.kse is not None
    assert node.agent is not None

    # Step to populate state
    node.step(18.0)
    state = node.get_state()

    assert state["source_id"] == "loop_sensor_42"
    assert state["steps_processed"] == 1
    assert "memory_buffer" in state
    assert "kse_state" in state
    assert "agent_state" in state

    # Restore in new node
    node2 = NodeFactory.create_node(source_id="loop_sensor_42")
    node2.set_state(state)

    assert node2.steps_processed == 1
    assert len(node2.memory) == 1


def test_node_state_isolated_methods():
    """Tests NodeState dataclass methods and serialization."""
    state = NodeState(source_id="sensor_abc")
    assert state.updated_this_cycle is False
    assert state.fallback_steps == 0

    state.mark_updated()
    assert state.updated_this_cycle is True

    state.reset_cycle()
    assert state.updated_this_cycle is False

    state.increment_fallback()
    state.increment_fallback()
    assert state.fallback_steps == 2

    state.reset_fallback()
    assert state.fallback_steps == 0

    d = state.to_dict()
    assert d["source_id"] == "sensor_abc"

    state.from_dict({"steps_processed": 50, "is_validated": True, "is_rejected": False})
    assert state.steps_processed == 50
    assert state.is_validated is True


def test_node_status_notifier_callback_and_app_state():
    """Tests NodeStatusNotifier with callback and AppState fallback."""
    events = []
    notifier = NodeStatusNotifier(on_status_change=lambda sid, st: events.append((sid, st)))
    notifier.notify_status("sensor_1", SourceStatus.ACTIVE)
    assert events == [("sensor_1", SourceStatus.ACTIVE)]


def test_node_snapshot_formatter():
    """Tests NodeSnapshotFormatter format methods."""
    formatter = NodeSnapshotFormatter()
    physics = MagicMock()
    physics.get_kinetic_snapshot.return_value = KineticState(p=10.0, v=2.0, a=0.5, uncertainty=0.1, confidence=0.99)

    step_rep = formatter.format_step_report(
        source_id="s1",
        status="Active",
        value=25.0,
        loss=0.01,
        embedding=np.zeros(16),
        is_ready=True,
        steps=10,
        physics_engine=physics
    )
    assert step_rep["source_id"] == "s1"
    assert step_rep["status"] == "Active"
    assert step_rep["physics"]["position"] == 10.0
    assert step_rep["physics"]["confidence"] == 0.99

    ghost_rep = formatter.format_ghost_report(
        source_id="s1",
        method_used="KSE",
        value=20.0,
        embedding=np.zeros(16),
        fallback_steps=2,
        physics_engine=physics
    )
    assert ghost_rep["type"] == "synthetic"
    assert ghost_rep["fallback_count"] == 2
