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
# File: tests/unit/test_xai_solid_architecture.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import pytest
import torch
import torch.nn as nn
from unittest.mock import MagicMock

from src.interfaces.xai import (
    IXAIStrategy,
    IXAIStrategyRegistry,
    IXAIExplainer,
    IXAIReporter
)
from src.strategies.xai_strategies import (
    AuditorXAIStrategy,
    TCNXAIStrategy,
    FuserXAIStrategy,
    XAIStrategyRegistry
)
from src.services.xai_explainer_service import CaptumExplainerService
from src.services.xai_reporter_service import XAIReporterService
from src.workers.xai_worker import XAIWorker


def test_xai_interfaces_and_protocols_compliance():
    """Verifies that all concrete implementations strictly satisfy their protocol contracts."""
    registry = XAIStrategyRegistry()
    assert isinstance(registry, IXAIStrategyRegistry)

    auditor_strat = AuditorXAIStrategy()
    assert isinstance(auditor_strat, IXAIStrategy)

    tcn_strat = TCNXAIStrategy()
    assert isinstance(tcn_strat, IXAIStrategy)

    fuser_strat = FuserXAIStrategy()
    assert isinstance(fuser_strat, IXAIStrategy)

    explainer = CaptumExplainerService()
    assert isinstance(explainer, IXAIExplainer)

    reporter = XAIReporterService(auto_load_jurist=False)
    assert isinstance(reporter, IXAIReporter)


def test_auditor_xai_strategy_execution():
    """Verifies AuditorXAIStrategy wrapper preparation, execution, and fallback text generation."""
    strategy = AuditorXAIStrategy()
    device = torch.device("cpu")
    input_vec = [10.0, 20.0, 30.0, 40.0]

    wrapper = strategy.prepare_wrapper(input_vec, {}, device)
    assert callable(wrapper)

    dummy_tensor = torch.tensor([input_vec], dtype=torch.float32, device=device)
    loss = wrapper(dummy_tensor)
    assert isinstance(loss, torch.Tensor)
    assert loss.shape == (1, 1)

    text = strategy.generate_fallback_text(
        delta=0.005,
        sig_map={"Sensor_0": 0.45, "Sensor_1": 0.12},
        attr_list=[0.45, 0.12, 0.0, 0.0]
    )
    assert "Auditoria Zero-Trust" in text
    assert "0.0050" in text
    assert "Sensor_0" in text


def test_tcn_xai_strategy_execution():
    """Verifies TCNXAIStrategy wrapper preparation and fallback text."""
    strategy = TCNXAIStrategy()
    device = torch.device("cpu")
    input_vec = [1.0, 2.0, 3.0, 4.0, 5.0]

    wrapper = strategy.prepare_wrapper(input_vec, {"feature_dim": 1}, device)
    assert callable(wrapper)

    dummy_tensor = torch.tensor([input_vec], dtype=torch.float32, device=device)
    out = wrapper(dummy_tensor)
    assert isinstance(out, torch.Tensor)
    assert out.shape == (1, 1)

    text = strategy.generate_fallback_text(
        delta=0.01,
        sig_map={"TCN [t-0]": 0.8},
        attr_list=[0.8]
    )
    assert "Análise Temporal de Sensor (TCN)" in text


def test_fuser_xai_strategy_execution():
    """Verifies FuserXAIStrategy wrapper preparation and fallback text."""
    strategy = FuserXAIStrategy()
    device = torch.device("cpu")
    input_vec = [1.0, 2.0, 3.0]

    wrapper = strategy.prepare_wrapper(input_vec, {"feature_names": ["A", "B", "C"]}, device)
    assert callable(wrapper)

    dummy_tensor = torch.tensor([input_vec], dtype=torch.float32, device=device)
    out = wrapper(dummy_tensor)
    assert isinstance(out, torch.Tensor)
    assert out.shape == (1, 1)

    text = strategy.generate_fallback_text(
        delta=0.02,
        sig_map={"NodeA": 0.3},
        attr_list=[0.3, 0.1, 0.0]
    )
    assert "Fusão Espaço-Temporal" in text


def test_captum_explainer_service():
    """Verifies that CaptumExplainerService computes Integrated Gradients without UI dependencies."""
    explainer = CaptumExplainerService()
    device = torch.device("cpu")

    # Simple linear wrapper: sum(2 * x)
    def dummy_wrapper(inputs: torch.Tensor) -> torch.Tensor:
        return torch.sum(2.0 * inputs, dim=1).unsqueeze(1)

    input_vec = [1.0, 2.0, 3.0]
    attr_list, delta = explainer.compute_attributions(dummy_wrapper, input_vec, device)

    assert len(attr_list) == 3
    assert isinstance(delta, float)
    # For linear model 2*x with baseline 0, attributions should equal 2*x
    assert pytest.approx(attr_list[0], rel=1e-2) == 2.0
    assert pytest.approx(attr_list[1], rel=1e-2) == 4.0
    assert pytest.approx(attr_list[2], rel=1e-2) == 6.0


def test_reporter_service_with_and_without_jurist():
    """Verifies XAIReporterService fallback and delegation."""
    reporter = XAIReporterService(auto_load_jurist=False)
    strategy = AuditorXAIStrategy()

    # Fallback to strategy
    text = reporter.generate_report(
        target="auditor",
        attr_list=[0.5, 0.1],
        feature_names=["Sens1", "Sens2"],
        timestamp="2026-08-31T12:00:00",
        delta=0.001,
        strategy=strategy
    )
    assert "Auditoria Zero-Trust" in text
    assert "Sens1" in text

    # Mock Jurist Agent
    mock_jurist = MagicMock()
    mock_jurist.is_loaded = True
    mock_jurist.generate_report.return_value = "Jurist Semantic Explanation Test"

    reporter_with_jurist = XAIReporterService(jurist=mock_jurist, auto_load_jurist=False)
    report = reporter_with_jurist.generate_report(
        target="auditor",
        attr_list=[0.5, 0.1],
        feature_names=["Sens1", "Sens2"],
        timestamp="2026-08-31T12:00:00",
        delta=0.001,
        strategy=strategy
    )
    assert report == "Jurist Semantic Explanation Test"
    mock_jurist.generate_report.assert_called_once()

    # Unload
    reporter_with_jurist.unload_resources()
    mock_jurist.unload_resources.assert_called_once()
    assert reporter_with_jurist.jurist is None


def test_open_closed_principle_extensibility():
    """
    OCP Test: Validates that a brand new AI agent strategy can be registered and
    executed without changing a single line in XAIWorker or existing strategies.
    """
    registry = XAIStrategyRegistry(populate_defaults=True)

    class CustomAnomalyXAIStrategy(IXAIStrategy):
        def prepare_wrapper(self, input_vector, model_config, device):
            return lambda x: torch.sum(x * 3.0, dim=1).unsqueeze(1)

        def generate_fallback_text(self, delta, sig_map, attr_list):
            return f"Custom Anomaly Agent Analysis: Delta={delta:.2f}"

    custom_strategy = CustomAnomalyXAIStrategy()
    registry.register("custom_anomaly", custom_strategy)

    retrieved = registry.get("custom_anomaly")
    assert retrieved is custom_strategy

    device = torch.device("cpu")
    wrapper = retrieved.prepare_wrapper([1.0, 2.0], {}, device)
    out = wrapper(torch.tensor([[1.0, 2.0]], dtype=torch.float32))
    assert out.item() == 9.0  # (1*3 + 2*3) = 9.0


def test_xai_worker_facade_orchestration(qapp):
    """
    Verifies that XAIWorker acts as a clean facade, coordinates ephemeral tasks,
    and emits PyQt results asynchronously.
    """
    mock_explainer = MagicMock(spec=IXAIExplainer)
    mock_explainer.compute_attributions.return_value = ([0.1, 0.2, 0.3], 0.004)

    mock_reporter = MagicMock(spec=IXAIReporter)
    mock_reporter.generate_report.return_value = "Mocked Semantic Output"

    worker = XAIWorker(
        model_config={"feature_dim": 3},
        explainer=mock_explainer,
        reporter=mock_reporter,
        device=torch.device("cpu")
    )

    received_results = []
    worker.result_ready.connect(lambda res: received_results.append(res))

    worker.submit_request(
        target_type="auditor",
        input_vector=[1.0, 2.0, 3.0],
        feature_names=["f1", "f2", "f3"]
    )

    # Wait for the ephemeral thread to complete and process Qt event loop
    assert len(worker._active_tasks) == 1
    task = worker._active_tasks[0]
    task.wait(2000)
    qapp.processEvents()

    assert len(received_results) == 1
    result = received_results[0]
    assert result["type"] == "XAI_RESULT"
    assert result["target"] == "auditor"
    assert result["attributions"] == [0.1, 0.2, 0.3]
    assert result["convergence_delta"] == 0.004
    assert result["semantic_text"] == "Mocked Semantic Output"

    worker.unload_resources()
    mock_reporter.unload_resources.assert_called_once()
