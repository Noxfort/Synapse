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
# File: tests/unit/test_fuser_deeponet.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import pytest
import torch
import numpy as np

from src.models.pi_deeponet import PIDeepONet
from src.factories.fuser_model_factory import FuserModelFactory
from src.pipeline.fusion_pipeline import FusionPipeline
from src.agents.fuser_agent import FuserAgent
from src.trainer.fuser_trainer import FuserTrainer


def test_fuser_model_factory_creates_deeponet():
    """Verify FuserModelFactory instantiates PIDeepONet inside the composite module dict."""
    composite = FuserModelFactory.create_composite_model(
        num_variates=4,
        seq_len=20,
        pred_len=1,
        d_model=32,
        spatial_dim=16,
        coord_dim=2,
        p_latent=32
    )

    assert "deeponet" in composite
    assert isinstance(composite["deeponet"], PIDeepONet)
    assert composite["deeponet"].sensor_dim == 4
    assert composite["deeponet"].coord_dim == 2


def test_fusion_pipeline_execute_operator_continuous_queries():
    """Verify FusionPipeline executes continuous operator queries on arbitrary street coordinates."""
    pipeline = FuserModelFactory.create_fusion_pipeline(
        num_variates=4,
        seq_len=10,
        pred_len=1,
        d_model=32,
        spatial_dim=16,
        coord_dim=2,
        p_latent=32
    )

    # 1. Provide 4-sensor historical observations [SeqLen=10, NumSensors=4]
    current_history = np.random.randn(10, 4).astype(np.float32)

    # 2. Query 76 street coordinates in 2D space (x, y)
    query_coords = np.random.uniform(0.0, 1000.0, size=(76, 2)).astype(np.float32)

    # 3. Execute Operator
    fields, residuals = pipeline.execute_operator(
        current_history=current_history,
        query_coords=query_coords,
        return_physics_residual=True
    )

    assert fields.shape == (76, 3), f"Expected (76, 3) for [density, speed, flow], got {fields.shape}"
    # Physical fields must be strictly non-negative
    assert (fields[:, 0] >= 0.0).all(), "Density must be non-negative"
    assert (fields[:, 1] >= 0.0).all(), "Speed must be non-negative"
    assert (fields[:, 2] >= 0.0).all(), "Flow must be non-negative"

    assert "conservation_residual" in residuals
    assert residuals["conservation_residual"] >= 0.0


def test_fuser_agent_fuse_operator_orchestration():
    """Verify FuserAgent orchestrates DeepONet operator calls."""
    agent = FuserAgent(
        num_variates=4,
        seq_len=12,
        d_model=32,
        spatial_dim=16
    )

    history = np.random.randn(12, 4).astype(np.float32)
    coords = np.random.uniform(0.0, 500.0, size=(10, 2)).astype(np.float32)

    # Test via direct fuse_operator method
    fields = agent.fuse_operator(history, query_coords=coords)
    assert fields.shape == (10, 3)

    # Test via unified inference entry point
    inference_result = agent.inference({
        "x_temporal": history,
        "query_coords": coords
    })
    assert isinstance(inference_result, np.ndarray)
    assert inference_result.shape == (10, 3)


def test_fuser_trainer_train_step_with_deeponet_loss():
    """Verify FuserTrainer trains composite architecture optimizing both MSE and DeepONet physics loss."""
    composite = FuserModelFactory.create_composite_model(
        num_variates=4,
        seq_len=8,
        pred_len=1,
        d_model=16,
        spatial_dim=8,
        p_latent=16
    )

    trainer = FuserTrainer(
        composite_model=composite,
        learning_rate=0.001,
        spatial_dim=8,
        physics_weight=0.1
    )

    batch_x = torch.randn(4, 8, 4)
    batch_y = torch.randn(4, 1, 4)

    loss = trainer.train_step((batch_x, batch_y))
    assert isinstance(loss, float)
    assert loss > 0.0
