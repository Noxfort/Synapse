# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# File: tests/unit/test_isolated_llm_process.py
# Author: Gabriel Moraes
# Date: 2026-09-04

import pytest
import time
from unittest.mock import MagicMock, patch
from src.slm.process.isolated_jurist_manager import IsolatedJuristManager
from src.slm.process.llm_worker_process import LLMWorkerInstance


def test_llm_worker_instance_mock_inference():
    worker = LLMWorkerInstance(model_id="mock_model.gguf")
    assert worker.is_loaded is False

    # Simulate mock model
    mock_llm = MagicMock()
    mock_llm.create_chat_completion.return_value = {
        "choices": [{"message": {"content": "<think>pensamento pericial</think>Laudo pericial aprovado sem irregularidades."}}]
    }
    worker._model = mock_llm
    worker._is_loaded = True

    # Test report generation with output sanitization
    report_text = worker.generate_report({
        "tensor_data": {"fluxo": 120.0, "velocidade": 45.0},
        "target": "AUDITOR_XAI",
        "locale": "pt_BR",
        "auto_unload": False,
    })

    assert "Laudo pericial aprovado" in report_text
    assert "<think>" not in report_text
    assert "</think>" not in report_text

    # Test verdict generation
    verdict_text = worker.generate_verdict({
        "source_id": "sensor_det_01",
        "status": "NORMAL",
        "values": ["fluxo: 120"],
        "auto_unload": False,
    })
    assert "Laudo pericial aprovado" in verdict_text

    # Test unload
    res = worker.unload_resources()
    assert res["unloaded"] is True
    assert worker.is_loaded is False


def test_isolated_jurist_manager_lifecycle():
    manager = IsolatedJuristManager(model_id="test_model.gguf", command_timeout=5.0)
    assert manager.is_alive is False

    # Test that send_command handles simulated communication
    mock_conn = MagicMock()
    mock_conn.poll.return_value = True
    mock_conn.recv.return_value = {"id": "test_id", "success": True, "result": "pong"}

    manager._parent_conn = mock_conn
    mock_proc = MagicMock()
    mock_proc.is_alive.return_value = True
    manager._process = mock_proc

    with patch("uuid.uuid4", return_value="test_id"):
        res = manager.send_command("ping")
        assert res == "pong"

    # Test shutdown
    manager.shutdown()
    assert manager._parent_conn is None
    assert manager._process is None
    assert manager.is_alive is False
