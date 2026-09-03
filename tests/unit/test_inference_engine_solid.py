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
# File: tests/unit/test_inference_engine_solid.py
# Author: Gabriel Moraes
# Date: 2026-08-30

import pytest
import numpy as np
import torch
from unittest.mock import MagicMock

from src.domain.entities import SourceStatus
from src.engine.gating_policy import SourceGatingPolicy
from src.engine.forecast_imputer import ForecastImputer
from src.engine.data_flow_router import DataFlowRouter
from src.engine.inference_engine import InferenceEngine


def test_gating_policy_frozen_when_missing_sources():
    policy = SourceGatingPolicy(linguist_throttle_cycles=5)
    app_state = MagicMock()

    # Only 1 local active source, 0 global
    src_local = MagicMock(id="s1", is_local=True, status=SourceStatus.ACTIVE)
    app_state.get_all_data_sources.return_value = [src_local]

    eval_res = policy.evaluate(app_state, cycle_count=1)
    assert eval_res.is_frozen is True
    assert eval_res.active_local == 1
    assert eval_res.active_global == 0
    assert eval_res.has_quarantine is False


def test_gating_policy_unfrozen_when_local_and_global_active():
    policy = SourceGatingPolicy(linguist_throttle_cycles=5)
    app_state = MagicMock()

    src_local = MagicMock(id="s1", is_local=True, status=SourceStatus.ACTIVE)
    src_global = MagicMock(id="s2", is_local=False, status=SourceStatus.ACTIVE)
    app_state.get_all_data_sources.return_value = [src_local, src_global]

    eval_res = policy.evaluate(app_state, cycle_count=2)
    assert eval_res.is_frozen is False
    assert eval_res.active_local == 1
    assert eval_res.active_global == 1
    assert eval_res.should_trigger_linguist is False


def test_gating_policy_immediate_linguist_trigger_on_quarantine():
    policy = SourceGatingPolicy(linguist_throttle_cycles=5)
    app_state = MagicMock()

    src_quarantine = MagicMock(id="s1", is_local=True, status=SourceStatus.QUARANTINE)
    app_state.get_all_data_sources.return_value = [src_quarantine]

    eval_res = policy.evaluate(app_state, cycle_count=1)
    assert eval_res.has_quarantine is True
    assert eval_res.should_trigger_linguist is True


def test_forecast_imputer_propagates_to_unobserved_nodes():
    imputer = ForecastImputer()
    graph_manager = MagicMock()
    graph_manager.get_ordered_node_ids.return_value = ["N1", "N2"]

    node_n1 = MagicMock()
    node_n1.state.last_value = 0.0
    node_n2 = MagicMock()
    node_n2.state.last_value = 25.0

    graph_manager.get_node.side_effect = lambda nid: node_n1 if nid == "N1" else node_n2

    snapshot = {
        "N1": {"value": 0.0},
        "N2": {"value": 25.0}
    }

    forecast = np.array([[18.5, 30.0]])
    imputer.impute(forecast, snapshot, graph_manager)

    # N1 was 0.0 (unobserved), so it receives the predicted value 18.5
    assert snapshot["N1"]["value"] == 18.5
    assert node_n1.state.last_value == 18.5

    # N2 was 25.0 (observed > 0), so it remains unchanged
    assert snapshot["N2"]["value"] == 25.0
    assert node_n2.state.last_value == 25.0


def test_data_flow_router_processes_payload():
    app_state = MagicMock()
    graph_manager = MagicMock()
    src_mock = MagicMock(id="sensor_1", latest_value=0.0, last_update=0.0)
    app_state.get_all_data_sources.return_value = [src_mock]

    router = DataFlowRouter(app_state=app_state, graph_manager=graph_manager)

    emitted_data = []
    router.data_processed.connect(lambda p: emitted_data.append(p))

    # Test numeric dict payload
    router.handle_data_flow("sensor_1", {"value": 42.5})

    assert src_mock.latest_value == 42.5
    graph_manager.update_node_memory.assert_called_once_with("sensor_1", 42.5, raw_payload={"value": 42.5})
    assert len(emitted_data) == 1
    assert emitted_data[0]["id"] == "sensor_1"
    assert emitted_data[0]["raw"] == 42.5


def test_inference_engine_pure_orchestrator_flow():
    app_state = MagicMock()
    graph_manager = MagicMock()
    snapshot_builder = MagicMock()
    processor = MagicMock()
    gating_policy = MagicMock()
    forecast_imputer = MagicMock()
    ingestion = MagicMock()

    # Configure active gating
    gating_eval = MagicMock(is_frozen=False, should_trigger_linguist=False)
    gating_policy.evaluate.return_value = gating_eval

    # Configure snapshot & processor
    snapshot_builder.gather_snapshot.return_value = {"N1": {"value": 10.0}}
    processor.run_logic.return_value = ({"forecast": [12.0], "alert_event": None}, None)

    engine = InferenceEngine(
        app_state=app_state,
        graph_manager=graph_manager,
        snapshot_builder=snapshot_builder,
        processor=processor,
        gating_policy=gating_policy,
        forecast_imputer=forecast_imputer,
        ingestion=ingestion
    )

    emitted_results = []
    engine.global_cycle_results.connect(lambda r: emitted_results.append(r))

    engine.run_global_cycle()

    # Verify orchestration sequence
    ingestion.check_global_fetch.assert_called_once()
    gating_policy.evaluate.assert_called_once()
    snapshot_builder.gather_snapshot.assert_called_once()
    processor.run_logic.assert_called_once_with({"N1": {"value": 10.0}})
    forecast_imputer.impute.assert_called_once()
    assert len(emitted_results) == 1
    assert "sensor_snapshot" in emitted_results[0]
