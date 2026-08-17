# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# File: tests/unit/test_fuser_solid.py

import pytest
import torch
import torch.nn as nn
import numpy as np
from unittest.mock import MagicMock

from src.agents.fuser_agent import FuserAgent
from src.domain.interfaces import ISensorCalibrator, IFusionPipeline
from src.services.dynamic_sensor_calibrator import DynamicSensorCalibrator
from src.services.fusion_pipeline import FusionPipeline
from src.services.fuser_trainer import FuserTrainer
from src.factories.fuser_model_factory import FuserModelFactory


def test_fuser_agent_pure_orchestrator_dependency_injection():
    """Test FuserAgent as pure orchestrator with mocked FusionPipeline and Calibrator (DIP & SRP)."""
    # 1. Mock Pipeline
    mock_pipeline = MagicMock(spec=IFusionPipeline)
    mock_pipeline.execute.return_value = np.array([42.0, 42.0, 42.0, 42.0], dtype=np.float32)

    # 2. Mock Calibrator
    mock_calibrator = MagicMock(spec=ISensorCalibrator)
    mock_calibrator.apply.side_effect = lambda raw_output, current_history, observability_mask: raw_output + 1.0

    # Instantiate pure orchestrator with injected dependencies
    orchestrator = FuserAgent(
        pipeline=mock_pipeline,
        calibrator=mock_calibrator,
        num_variates=4,
        seq_len=10
    )

    # Verify Inference Flow Orchestration
    current_history = np.random.randn(10, 4).astype(np.float32)
    result = orchestrator.fuse_state(current_history=current_history)

    assert result is not None
    assert result.shape == (4,)
    # Raw output was 42.0, calibrator added 1.0 -> result should be 43.0
    np.testing.assert_allclose(result, 43.0)
    assert mock_pipeline.execute.called
    assert mock_calibrator.apply.called


def test_fusion_pipeline_execution():
    """Verify FusionPipeline executes Diffusion -> PINN -> iTransformer cleanly."""
    pipeline = FuserModelFactory.create_fusion_pipeline(
        num_variates=4,
        seq_len=12,
        pred_len=1,
        d_model=32,
        spatial_dim=16
    )

    history = np.random.randn(12, 4).astype(np.float32)
    edge_index = torch.tensor([[0, 1, 2], [1, 2, 3]], dtype=torch.long)
    mask = np.array([1.0, 0.0, 1.0, 0.0])
    velocities = np.array([50.0, 45.0, 40.0, 35.0])

    raw_state = pipeline.execute(
        current_history=history,
        observability_mask=mask,
        global_velocities=velocities,
        edge_index=edge_index
    )

    assert raw_state is not None
    assert raw_state.shape == (4,)
    assert np.isfinite(raw_state).all()


def test_dynamic_sensor_calibrator_lifecycle():
    """Verify DynamicSensorCalibrator updates alpha and applies EMA bias correction."""
    calibrator = DynamicSensorCalibrator(num_variates=3, initial_alpha=0.05, max_alpha=0.2)
    assert calibrator.ema_bias.shape == (3,)
    
    # Active mask with 2 active sensors
    mask = np.array([1.0, 0.0, 1.0])
    calibrator.update_observability(mask)
    assert calibrator.calibration_cycles == 1
    assert calibrator.ema_alpha == 0.05 + 0.02

    # Apply calibration where sensor 0 has error (ground truth 50 vs predicted 45)
    history = np.array([[50.0, 0.0, 30.0]])
    raw_pred = np.array([45.0, 20.0, 30.0], dtype=np.float32)

    calibrated = calibrator.apply(raw_pred, history, observability_mask=mask)
    assert calibrated.shape == (3,)
    # Bias for node 0 should have adjusted upwards
    assert calibrator.ema_bias[0] > 0.0
    assert calibrated[0] > raw_pred[0]

    # Reset
    calibrator.reset()
    assert (calibrator.ema_bias == 0.0).all()
