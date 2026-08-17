# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems

import pytest
import torch
import numpy as np

from src.models.pi_vae_tcn import PIVAETCN
from src.models.pinn_traffic_flow import PINNTrafficFlow
from src.models.neuro_symbolic import NeuroSymbolicModel
from src.models.itransformer import iTransformer
from src.models.itransformer_lite import iTransformerLite
from src.models.patch_tst import PatchTST
from src.models.diffusion_gatv2 import DiffusionGATv2
from src.models.gatv2_lite import SpatialGAT
from src.models.wavelet_ae_occ import WaveletAEOCC
from src.models.tcn_ae import TCNAE, TemporalConvNet

from src.agents.corrector_agent import CorrectorAgent
from src.agents.linguist_agent import LinguistAgent
from src.agents.peak_classifier_agent import PeakClassifierAgent
from src.agents.imputer_agent import ImputerAgent
from src.agents.fuser_agent import FuserAgent
from src.agents.auditor_agent import AuditorAgent
from src.utils.batch_inference import BatchInferenceEngine


def test_tf32_flags_enabled():
    """Verifies that TF32 is allowed for matmul and cuDNN when CUDA is available."""
    import src  # Loads global __init__.py configuration
    if torch.cuda.is_available():
        assert torch.backends.cuda.matmul.allow_tf32 is True
        assert torch.backends.cudnn.allow_tf32 is True


def test_corrector_agent_amp_train_and_inference():
    """Verifies CorrectorAgent (PI-VAE-TCN) runs training and inference with AMP."""
    agent = CorrectorAgent(input_dim=3, hidden_dim=32, latent_dim=16)
    assert hasattr(agent, "scaler")

    # Train step
    batch = np.random.uniform(10.0, 80.0, (4, 16, 3)).astype(np.float32)
    loss = agent.train_step(batch)
    assert isinstance(loss, float)
    assert not np.isnan(loss)
    assert not np.isinf(loss)

    # Inference step
    data_2d = np.random.uniform(10.0, 80.0, (32, 3)).astype(np.float32)
    recon_2d = agent.inference(data_2d)
    assert recon_2d.shape == data_2d.shape
    assert not np.isnan(recon_2d).any()


def test_linguist_agent_amp_train_and_inference():
    """Verifies LinguistAgent (NeuroSymbolic TCN-PINN) runs with AMP and GradScaler."""
    agent = LinguistAgent(learning_rate=1e-4)
    assert hasattr(agent, "scaler")

    # Inference
    result = agent.inference({"text": "Traffic flow is 1200 veh/h at 60 km/h."})
    assert "is_valid" in result
    assert "error_score" in result
    assert "physics_residual" in result
    assert isinstance(result["is_valid"], bool)

    # Train step
    loss = agent.train_step(["Sensor report: speed is 45 km/h with high density."])
    assert isinstance(loss, float)
    assert not np.isnan(loss)
    assert not np.isinf(loss)


def test_imputer_agent_amp_impute():
    """Verifies ImputerAgent (PatchTST) imputation runs with AMP without NaNs."""
    agent = ImputerAgent(feature_dim=2, seq_len=16, d_model=32, n_heads=2, n_layers=1)
    
    data = np.random.uniform(20.0, 60.0, (48, 2)).astype(np.float32)
    data[5:10, 0] = np.nan
    data[20:25, 1] = np.nan

    imputed = agent.impute(data)
    assert imputed.shape == data.shape
    assert not np.isnan(imputed).any()


def test_batch_inference_engine_amp():
    """Verifies BatchInferenceEngine runs with use_amp=True."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    engine = BatchInferenceEngine(device=device, batch_size=16, use_amp=True)

    model = torch.nn.Sequential(
        torch.nn.Linear(4, 16),
        torch.nn.ReLU(),
        torch.nn.Linear(16, 4)
    )

    data = np.random.randn(100, 4).astype(np.float32)
    output = engine.run(model, data, seq_len=8)
    assert output.shape == data.shape
    assert not np.isnan(output).any()


def test_fuser_agent_amp_integration():
    """Verifies FuserAgent executes PINNTrafficFlow and Diffusion with AMP."""
    agent = FuserAgent(num_variates=3, seq_len=12, spatial_dim=16)

    x_temporal = np.random.randn(12, 3).astype(np.float32)
    output = agent.inference({"x_temporal": x_temporal})
    assert output.shape == (3,)
    assert not np.isnan(output).any()
