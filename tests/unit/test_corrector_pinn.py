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
# File: tests/unit/test_corrector_pinn.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import pytest
import torch
import numpy as np

from src.models.pi_dvae_tcn import PIDVAETCN
from src.agents.corrector_agent import CorrectorAgent
from src.physics.traffic_loss import TrafficPhysicsLoss


def test_pi_dvae_tcn_forward_pass_and_shapes():
    """Verifies that PIDVAETCN forward pass produces matching output shapes."""
    batch_size = 4
    channels = 3
    seq_len = 16
    hidden_channels = 32
    latent_channels = 16

    model = PIDVAETCN(
        input_channels=channels,
        hidden_channels=hidden_channels,
        latent_channels=latent_channels,
        kernel_size=3
    )

    x = torch.randn(batch_size, channels, seq_len)
    recon, mu, logvar = model(x)

    assert recon.shape == (batch_size, channels, seq_len)
    assert mu.shape == (batch_size, latent_channels, seq_len)
    assert logvar.shape == (batch_size, latent_channels, seq_len)


def test_pi_dvae_tcn_forward_with_residuals():
    """Verifies that forward pass can return physics residuals directly."""
    model = PIDVAETCN(input_channels=3, hidden_channels=16, latent_channels=8)
    x = torch.rand(2, 3, 10)
    recon, mu, logvar, residuals = model(x, return_physics_residuals=True)

    assert recon.shape == (2, 3, 10)
    assert "total_physics_loss" in residuals
    assert residuals["total_physics_loss"].item() >= 0.0


def test_pi_dvae_tcn_physics_residuals_computation():
    """Verifies that TrafficPhysicsLoss produces all physical loss terms."""
    physics_engine = TrafficPhysicsLoss(max_acceleration=5.0)

    # Mock traffic state: flow (q), speed (v), density (rho)
    # Batch=2, Channels=3, Seq_Len=10
    q = torch.tensor([[[100.0, 105.0, 110.0, 115.0, 120.0, 125.0, 130.0, 135.0, 140.0, 145.0],
                       [50.0, 51.0, 52.0, 53.0, 54.0, 55.0, 56.0, 57.0, 58.0, 59.0],
                       [2.0, 2.05, 2.11, 2.16, 2.22, 2.27, 2.32, 2.36, 2.41, 2.45]]])

    residuals = physics_engine.compute_losses(q)

    assert "loss_bounds" in residuals
    assert "loss_kinematics" in residuals
    assert "loss_smooth" in residuals
    assert "loss_conservation" in residuals
    assert "total_physics_loss" in residuals

    assert residuals["total_physics_loss"].item() >= 0.0
    assert residuals["loss_bounds"].item() == 0.0  # All values are strictly positive


def test_pi_dvae_tcn_kinematic_penalty_on_unphysical_acceleration():
    """Verifies that an unphysical jump in speed generates higher kinematic loss."""
    physics_engine = TrafficPhysicsLoss(max_acceleration=5.0)

    # 1. Smooth physically viable speed sequence (gradual acceleration: +1 m/s per step)
    smooth_speed = torch.tensor([[[20.0, 21.0, 22.0, 23.0, 24.0, 25.0]]])
    res_smooth = physics_engine.compute_losses(smooth_speed)

    # 2. Unphysical jump (e.g. glitch: 20 -> 90 -> 10 m/s in single timesteps, dv/dt = 70 > a_max)
    glitched_speed = torch.tensor([[[20.0, 90.0, 10.0, 95.0, 15.0, 100.0]]])
    res_glitched = physics_engine.compute_losses(glitched_speed)

    assert res_smooth["loss_kinematics"].item() == 0.0
    assert res_glitched["loss_kinematics"].item() > 0.0
    assert res_glitched["total_physics_loss"].item() > res_smooth["total_physics_loss"].item()


def test_corrector_agent_train_step_with_pinn():
    """Verifies that CorrectorAgent trains smoothly with PINN loss."""
    agent = CorrectorAgent(input_dim=3, hidden_dim=32, latent_dim=16, physics_weight=0.1)

    # Synthetic batch of traffic sequences: [Batch=8, Seq_Len=20, Features=3]
    batch = np.random.uniform(10.0, 80.0, (8, 20, 3)).astype(np.float32)

    initial_loss = agent.train_step(batch)
    assert isinstance(initial_loss, float)
    assert not np.isnan(initial_loss)
    assert not np.isinf(initial_loss)
    assert initial_loss < 1e5


def test_corrector_agent_denoise_forward():
    """Verifies CorrectorAgent denoising reconstruction."""
    agent = CorrectorAgent(input_dim=3, hidden_dim=32, latent_dim=16)

    # Sequence with noise
    noisy_seq = np.random.uniform(10.0, 50.0, (20, 3)).astype(np.float32)
    denoised_seq = agent.denoise(noisy_seq)

    assert denoised_seq.shape == (20, 3)
    assert not np.isnan(denoised_seq).any()


def test_corrector_trainer_dae_explicit_corruption():
    """Verifies that CorrectorTrainer configures and executes explicit DAE noise injection."""
    from src.trainer.corrector_trainer import CorrectorTrainer

    model = PIDVAETCN(input_channels=2, hidden_channels=16, latent_channels=8)
    trainer = CorrectorTrainer(
        model=model,
        learning_rate=1e-3,
        physics_weight=0.05,
        noise_std=0.10,
        spike_prob=0.05
    )

    assert trainer.noise_std == 0.10
    assert trainer.spike_prob == 0.05

    batch = np.random.uniform(10.0, 50.0, (4, 16, 2)).astype(np.float32)
    loss = trainer.train_step(batch)

    assert isinstance(loss, float)
    assert not np.isnan(loss)
    assert not np.isinf(loss)
    assert loss < 1e5

