# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# File: tests/unit/test_linguist_pinn.py

import pytest
import torch
import numpy as np
from unittest.mock import MagicMock, patch

from src.models.neuro_symbolic import NeuroSymbolicModel
from src.agents.linguist_agent import LinguistAgent
from src.services.linguist_service import LinguistService
from src.domain.app_state import AppState
from src.domain.entities import DataSource, SourceType, SourceStatus


def test_neuro_symbolic_pinn_residuals():
    """Verifies that NeuroSymbolicModel computes differentiable PINN residuals."""
    with patch("src.models.neuro_symbolic.AutoModel.from_pretrained") as MockAutoModel, \
         patch("src.models.neuro_symbolic.AutoConfig.from_pretrained") as MockAutoConfig:

        mock_config = MagicMock()
        mock_config.hidden_size = 64
        MockAutoConfig.return_value = mock_config

        mock_transformer = MagicMock()
        mock_output = MagicMock()
        mock_output.last_hidden_state = torch.randn(2, 5, 64)
        mock_transformer.return_value = mock_output
        MockAutoModel.return_value = mock_transformer

        model = NeuroSymbolicModel(model_name="mock-model", freeze_transformer=True, latent_dim=32)

        input_ids = torch.randint(0, 1000, (2, 5))
        attention_mask = torch.ones((2, 5))

        recon, orig, residuals = model(input_ids, attention_mask)

        assert recon.shape == (2, 5, 64)
        assert orig.shape == (2, 5, 64)
        assert "loss_bounds" in residuals
        assert "loss_kinematics" in residuals
        assert "loss_conservation" in residuals
        assert "total_physics_loss" in residuals
        assert residuals["total_physics_loss"].item() >= 0.0


def test_linguist_agent_train_and_inference_pinn():
    """Verifies that LinguistAgent trains and runs inference with PINN physics checks."""
    with patch("src.agents.linguist_agent.AutoTokenizer.from_pretrained") as MockTokenizer, \
         patch("src.models.neuro_symbolic.AutoModel.from_pretrained") as MockAutoModel, \
         patch("src.models.neuro_symbolic.AutoConfig.from_pretrained") as MockAutoConfig:

        mock_config = MagicMock()
        mock_config.hidden_size = 64
        MockAutoConfig.return_value = mock_config

        mock_transformer = MagicMock()
        mock_output = MagicMock()
        mock_output.last_hidden_state = torch.randn(1, 5, 64)
        mock_transformer.return_value = mock_output
        MockAutoModel.return_value = mock_transformer

        mock_tok_inst = MockTokenizer.return_value
        mock_tok_inst.return_value = {
            "input_ids": torch.randint(0, 1000, (1, 5)),
            "attention_mask": torch.ones((1, 5))
        }

        agent = LinguistAgent(model_name="mock-model")

        # Train step with numerical batch
        batch = [10.0, 12.0, 14.0, 15.0, 16.0]
        loss = agent.train_step(batch)
        assert isinstance(loss, float)
        assert loss >= 0.0

        # Inference
        result = agent.inference({"text": "Speed is 50 km/h, flow is 1200 veh/h"})
        assert "is_valid" in result
        assert "physics_residual" in result
        assert "error_score" in result


def test_linguist_service_promotes_on_5_samples():
    """Verifies that LinguistService promotes a valid source at 5 samples."""
    app_state = MagicMock(spec=AppState)
    ingestion = MagicMock()
    pipeline = MagicMock()
    ingestion.get_pipeline.return_value = pipeline
    agent_factory = MagicMock()

    src = DataSource(id="src_1", name="Sensor 1", source_type=SourceType.API, is_local=True, status=SourceStatus.QUARANTINE)
    app_state.get_all_data_sources.return_value = [src]

    # Buffer has 5 samples
    pipeline.has_enough_data.return_value = True
    pipeline.get_quarantine_data.return_value = [10.0, 12.0, 14.0, 15.0, 16.0]

    mock_linguist = MagicMock()
    mock_linguist.train_step.return_value = 0.02  # Learned with low PINN loss
    mock_linguist.inference.return_value = {"is_valid": True, "is_anomaly": False, "physics_residual": 0.01}
    agent_factory.get_or_create_linguist.return_value = mock_linguist
    agent_factory.get_or_create_specialist.return_value = MagicMock()

    service = LinguistService(app_state, ingestion, agent_factory)
    service.run_check()

    assert src.status == SourceStatus.ACTIVE
    pipeline.promote_to_active.assert_called_once_with("src_1")
