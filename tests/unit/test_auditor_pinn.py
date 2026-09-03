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
# File: tests/unit/test_auditor_pinn.py
# Author: Gabriel Moraes
# Date: 2026-03-02

import pytest
import torch
import numpy as np

from src.models.wavelet_ae_occ import WaveletSpectralAE, WaveletAEOCC
from src.agents.auditor_agent import AuditorAgent
from src.physics.traffic_loss import TrafficPhysicsLoss


def test_wavelet_ae_occ_pinn_forward_and_residuals():
    """Verifies that WaveletSpectralAE produces spectral and time reconstruction and calculates PINN residuals via TrafficPhysicsLoss."""
    input_len = 32
    batch_size = 4
    model = WaveletSpectralAE(input_len=input_len, J=2, Q=1, latent_dim=16)
    physics_engine = TrafficPhysicsLoss(max_acceleration=5.0)
    
    # Random normal input
    x = torch.rand(batch_size, input_len)
    
    feats, z, rec_feats, time_recon = model(x, return_time_recon=True)
    physics_res = physics_engine.compute_losses(time_recon, orig_x=x)
    
    assert z.shape == (batch_size, 16)
    assert rec_feats.shape == feats.shape
    assert time_recon.shape == (batch_size, input_len)
    assert isinstance(physics_res, dict)
    assert "total_physics_loss" in physics_res
    assert "loss_bounds" in physics_res
    assert "loss_kinematics" in physics_res
    assert "loss_smooth" in physics_res
    assert "loss_conservation" in physics_res
    assert physics_res["total_physics_loss"] >= 0.0


def test_wavelet_ae_occ_backward_compatibility_mode():
    """Verifies that return_time_recon=False returns the classic 3-tuple."""
    input_len = 32
    model = WaveletSpectralAE(input_len=input_len, J=2, latent_dim=16)
    x = torch.rand(2, input_len)
    
    out = model(x, return_time_recon=False)
    assert isinstance(out, tuple)
    assert len(out) == 3
    feats, z, rec_feats = out
    assert feats.shape == rec_feats.shape


def test_auditor_agent_train_step_with_pinn():
    """Verifies that AuditorAgent trains smoothly with PINN loss terms."""
    input_len = 32
    agent = AuditorAgent(
        input_len=input_len,
        J=2,
        latent_dim=16,
        learning_rate=1e-3,
        physics_weight=0.5,
        enable_pinn=True
    )
    
    # Train step on dummy batch
    batch = torch.rand(8, input_len) * 50.0  # Positive traffic flow values
    loss = agent.train_step(batch)
    
    assert isinstance(loss, float)
    assert np.isfinite(loss)
    assert agent.pipeline.calibrator.center_initialized is True
    assert agent.pipeline.calibrator.threshold > 0.0


def test_auditor_agent_inference_detailed_payload():
    """Verifies inference returns rich physics and spectral diagnostics."""
    input_len = 32
    agent = AuditorAgent(input_len=input_len, J=2, latent_dim=16, physics_weight=0.5)
    
    # Warm up / initialize center
    warmup_batch = torch.rand(4, input_len) * 30.0
    agent.train_step(warmup_batch)
    
    sample = torch.rand(1, input_len) * 30.0
    result = agent.inference({"signature": sample})
    
    assert isinstance(result, dict)
    assert "is_anomaly" in result
    assert "score" in result
    assert "threshold" in result
    assert "spectral_residual" in result
    assert "time_residual" in result
    assert "compactness_dist" in result
    assert "physics_residual" in result
    assert "physics_details" in result
    assert "bounds_loss" in result["physics_details"]
    assert "kinematics_loss" in result["physics_details"]
    assert result["status"] == "audited"


def test_auditor_agent_physics_violation_sensitivity():
    """Verifies that physical violations (e.g. sharp unphysical spikes) yield higher physics residuals."""
    input_len = 32
    agent = AuditorAgent(input_len=input_len, J=2, latent_dim=16, max_acceleration=2.0, physics_weight=1.0)
    
    # Smooth physically plausible pattern (sine wave with positive baseline)
    t = torch.linspace(0, 3.14, input_len)
    smooth_signal = (torch.sin(t) * 10.0 + 20.0).unsqueeze(0)
    
    # Unphysical pattern: extreme oscillating spike violating max_acceleration and bounds
    spiky_signal = smooth_signal.clone()
    spiky_signal[0, 15] = 500.0  # Impossible teleportation / acceleration
    spiky_signal[0, 16] = -200.0 # Negative vehicle count violation
    
    # Train on smooth data to calibrate center and threshold
    for _ in range(5):
        agent.train_step(smooth_signal + torch.randn_like(smooth_signal) * 0.1)
        
    res_smooth = agent.inference({"signature": smooth_signal})
    res_spiky = agent.inference({"signature": spiky_signal})
    
    # Spiky signal should have a higher total score
    assert res_spiky["score"] > res_smooth["score"]
