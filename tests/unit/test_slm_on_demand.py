# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# File: tests/unit/test_slm_on_demand.py
# Author: Gabriel Moraes
# Date: 2026-09-03

import pytest
import torch
from unittest.mock import MagicMock, patch

from src.slm.device_manager import SLMDeviceManager
from src.slm.output_sanitizer import SLMOutputSanitizer
from src.slm.prompt_builder import SLMPromptBuilder
from src.agents.jurist_agent import JuristAgent
from src.services.xai_reporter_service import XAIReporterService


def test_slm_output_sanitizer():
    """Verifies that think blocks, emojis, backticks, and extra whitespace are stripped."""
    raw_output = (
        "```text\n<think>Raciocínio interno da SLM analisando tráfego...</think>```\n"
        "<think>Outra reflexão</think>\n"
        "Diagnóstico Operacional: Corredor operando em regime de capacidade máxima 🚗🚦.\n"
        "```"
    )
    sanitized = SLMOutputSanitizer.sanitize(raw_output)
    assert "<think>" not in sanitized
    assert "</think>" not in sanitized
    assert "🚗" not in sanitized
    assert "🚦" not in sanitized
    assert "Diagnóstico Operacional: Corredor operando em regime de capacidade máxima." in sanitized


def test_slm_prompt_builder():
    """Verifies prompt construction dynamically loaded from src/prompts/slm_prompts.json for all SYNAPSE targets."""
    # 1. Auditor Zero-Trust
    auditor_msgs = SLMPromptBuilder.build_xai_chat_messages(
        target="auditor",
        attribution_map={"Sensor_A1": 0.45, "Sensor_B2": 0.12},
        timestamp="2026-09-03 10:00:00"
    )
    assert len(auditor_msgs) == 2
    assert "Zero-Trust" in auditor_msgs[0]["content"]
    assert "Sensor_A1" in auditor_msgs[1]["content"]

    # 2. Local TCN Temporal
    tcn_msgs = SLMPromptBuilder.build_xai_chat_messages(
        target="tcn",
        attribution_map={"t-1": 0.6, "t-2": 0.3},
        timestamp="2026-09-03 10:00:00"
    )
    assert "Dinâmica Temporal" in tcn_msgs[0]["content"]

    # 3. Global Fuser GATv2
    fuser_msgs = SLMPromptBuilder.build_xai_chat_messages(
        target="fuser",
        attribution_map={"Junction_1": 0.7, "Junction_2": 0.2},
        timestamp="2026-09-03 10:00:00"
    )
    assert "Topologia" in fuser_msgs[0]["content"]

    # 4. Jurist Official Report
    jurist_msgs = SLMPromptBuilder.build_xai_chat_messages(
        target="jurist",
        attribution_map={"Violations": 1},
        timestamp="2026-09-03 10:00:00"
    )
    assert "Código de Trânsito Brasileiro" in jurist_msgs[0]["content"]


def test_slm_device_manager():
    """Verifies dynamic hardware detection."""
    # Explicit CPU
    dev, layers = SLMDeviceManager.resolve_device_settings(device="cpu")
    assert dev == "cpu"
    assert layers == 0

    # Auto mode
    dev_auto, layers_auto = SLMDeviceManager.resolve_device_settings(device="auto")
    assert dev_auto in ("gpu", "cpu")


def test_jurist_agent_on_demand_lifecycle():
    """Verifies that JuristAgent loads on-demand and unloads cleanly via JuristPipeline."""
    jurist = JuristAgent()
    assert jurist.is_loaded is False
    assert jurist.pipeline.model is None

    # Mock the internal GGUF model
    mock_model = MagicMock()
    mock_model.create_chat_completion.return_value = {
        "choices": [
            {
                "message": {
                    "content": "<think>pensando</think>Relatório Pericial: Tráfego fluido e seguro."
                }
            }
        ]
    }

    with patch("src.pipeline.jurist_pipeline.SLMModelLoader.load_model", return_value=mock_model):
        report = jurist.generate_report(
            tensor_data={"Sensor_1": 0.35},
            auto_unload=True
        )

        assert "<think>" not in report
        assert "Tráfego fluido e seguro." in report
        # Verify it automatically unloaded
        assert jurist.is_loaded is False
        assert jurist.pipeline.model is None


def test_reporter_service_on_demand_delegation():
    """Verifies XAIReporterService delegates to on-demand Jurist with auto_unload."""
    mock_jurist = MagicMock()
    mock_jurist.generate_report.return_value = "Síntese Oficial via SLM sob demanda"

    reporter = XAIReporterService(jurist=mock_jurist, auto_load_jurist=False)
    text = reporter.generate_report(
        target="fuser",
        attr_list=[0.8, 0.2],
        feature_names=["Fuser_1", "Fuser_2"],
        timestamp="2026-09-03 12:00:00",
        delta=0.001
    )

    assert text == "Síntese Oficial via SLM sob demanda"
    mock_jurist.generate_report.assert_called_once()
    assert mock_jurist.generate_report.call_args.kwargs.get("auto_unload") is True
