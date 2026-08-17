# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems

import pytest
import torch
import torch.nn.functional as F
import numpy as np

from src.models.tcn_ae import TCNAE, TCNAEEncoder, TCNAEDecoder
from src.blocks.temporal_blocks import TemporalBlock, Chomp1d
from src.agents.specialist_agent import SpecialistAgent
from src.services.specialist_pipeline import SpecialistPipeline
from src.services.specialist_trainer import SpecialistTrainer


def test_tcn_ae_instantiation_and_parameter_count():
    """Verifies that the lightweight TCNAE has < 5,000 parameters (~20 KB)."""
    model = TCNAE(num_inputs=1, num_channels=[8, 16], latent_dim=32, kernel_size=2)
    total_params = sum(p.numel() for p in model.parameters())
    
    # Assert featherweight footprint (< 5,000 params)
    assert total_params < 5000, f"Expected < 5000 params, got {total_params}"
    assert model.latent_dim == 32
    assert model.num_inputs == 1


def test_tcn_ae_forward_and_shapes():
    """Verifies TCNAE input, latent embedding and reconstruction shapes."""
    batch_size = 4
    seq_len = 16
    channels = 1
    
    model = TCNAE(num_inputs=channels, num_channels=[8, 16], latent_dim=32)
    x = torch.randn(batch_size, channels, seq_len)
    
    # Test forward with embedding
    recon, embedding = model(x, return_embedding=True)
    assert recon.shape == (batch_size, channels, seq_len)
    assert embedding.shape == (batch_size, 32)
    
    # Test encode directly
    z = model.encode(x)
    assert z.shape == (batch_size, 32)
    
    # Test decode directly
    recon_direct = model.decode(z, seq_len=seq_len)
    assert recon_direct.shape == (batch_size, channels, seq_len)


def test_tcn_ae_multivariate_input():
    """Verifies TCNAE handles multivariate traffic signals (flow, speed, density)."""
    batch_size = 2
    seq_len = 12
    channels = 3
    
    model = TCNAE(num_inputs=channels, num_channels=[8, 16], latent_dim=32)
    x = torch.randn(batch_size, channels, seq_len)
    
    recon, embedding = model(x, return_embedding=True)
    assert recon.shape == (batch_size, channels, seq_len)
    assert embedding.shape == (batch_size, 32)


def test_tcn_ae_reconstruction_and_anomaly_detection():
    """Verifies that corrupted signals produce higher reconstruction error than clean signals."""
    torch.manual_seed(42)
    model = TCNAE(num_inputs=1, num_channels=[8, 16], latent_dim=32)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    
    # Train on simple sinusoidal signal for a few steps
    t = torch.linspace(0, 4 * np.pi, 20).unsqueeze(0).unsqueeze(0) # [1, 1, 20]
    clean_signal = torch.sin(t)
    
    for _ in range(30):
        optimizer.zero_grad()
        recon, _ = model(clean_signal)
        loss = F.mse_loss(recon, clean_signal)
        loss.backward()
        optimizer.step()
        
    model.eval()
    with torch.no_grad():
        clean_recon, _ = model(clean_signal)
        clean_error = F.mse_loss(clean_recon, clean_signal).item()
        
        # Corrupt signal with an extreme glitch/outlier
        corrupted_signal = clean_signal.clone()
        corrupted_signal[0, 0, 10] += 50.0  # Big spike anomaly
        
        corrupt_recon, _ = model(corrupted_signal)
        corrupt_error = F.mse_loss(corrupt_recon, corrupted_signal).item()
        
    assert corrupt_error > clean_error * 5.0, (
        f"Corrupt error ({corrupt_error:.4f}) should be significantly higher than clean ({clean_error:.4f})"
    )


def test_specialist_pipeline_freeze_and_unfreeze():
    """Verifies that SpecialistPipeline freeze() disables grad for all parameters and unfreeze() re-enables them."""
    pipeline = SpecialistPipeline(input_dim=1, output_dim=32, num_channels=[8, 16])
    
    # Initial state
    assert not pipeline.is_frozen
    assert all(p.requires_grad for p in pipeline.model.parameters())
    
    # Freeze
    pipeline.freeze()
    assert pipeline.is_frozen
    assert not any(p.requires_grad for p in pipeline.model.parameters())
    
    # Unfreeze
    pipeline.unfreeze()
    assert not pipeline.is_frozen
    assert all(p.requires_grad for p in pipeline.model.parameters())


def test_specialist_agent_integration_with_tcn_ae():
    """Verifies SpecialistAgent initialization, prediction and freeze lifecycle with TCNAE."""
    agent = SpecialistAgent(input_dim=1, output_dim=32, num_channels=[8, 16])
    
    # Predict with numpy sequence [SeqLen, 1]
    input_seq = np.random.randn(16, 1).astype(np.float32)
    embedding = agent.predict(input_seq)
    
    assert embedding is not None
    assert embedding.shape == (32,), f"Expected 32-dim vector, got shape {embedding.shape}"
    assert not np.isnan(embedding).any()
    
    # Train
    inputs = torch.randn(8, 16, 1)
    targets = torch.randn(8, 16, 1)
    loss = agent.train(inputs, targets, epochs=1)
    assert isinstance(loss, float)
    assert not np.isnan(loss)
    
    # Freeze
    agent.freeze()
    assert agent.is_frozen
    
    # Predict continues working seamlessly when frozen
    embedding_frozen = agent.predict(input_seq)
    assert embedding_frozen.shape == (32,)
