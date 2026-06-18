import pytest
import torch
import numpy as np
from src.agents.specialist_agent import SpecialistAgent
from src.agents.coordinator_agent import CoordinatorAgent
from src.agents.fuser_agent import FuserAgent
from src.agents.auditor_agent import AuditorAgent

def test_specialist_agent_shapes():
    """Test Specialist (TCN) handles correctly dimensioned numpy arrays."""
    # TrafficNode feeds numpy arrays from memory: [feature_dim, seq_len] -> typically passed as list/numpy
    agent = SpecialistAgent(input_dim=1, output_dim=32, num_channels=[16, 32])
    
    # Mock a traffic node memory array: e.g. 60 time steps, 1 feature
    input_history = np.random.randn(60, 1)
    
    # Inference is expected to return the final embedding of output_dim
    embedding = agent.predict(input_history)
    
    assert embedding is not None, "TCN embedding should not be None."
    assert isinstance(embedding, np.ndarray), "Should return a numpy array."
    # With shape [Batch, Channels, Seq] returning [:, -1], it should be (32,)
    assert embedding.shape == (32,), f"Expected shape (32,), got {embedding.shape}"

def test_coordinator_agent_forward_pass():
    """Test Coordinator (GATv2) handles spatial forward pass smoothly."""
    # We upgraded Coordinator to in_channels=32 earlier
    agent = CoordinatorAgent(in_channels=32, hidden_channels=32, out_channels=32)
    
    num_nodes = 5
    # Mock node features (embeddings from TCN)
    x = torch.randn((num_nodes, 32))
    
    # Mock edges: 0->1, 1->2, 2->3, 3->4
    edge_index = torch.tensor([
        [0, 1, 2, 3],
        [1, 2, 3, 4]
    ], dtype=torch.long)
    
    # Inject topology
    agent.set_topology(edge_index)
    
    # Run inference
    output = agent.inference({"x_spatial": x, "edge_index": edge_index})
    
    # Check dimensions [Num_Nodes, Out_Channels]
    assert output is not None
    assert output.shape == (num_nodes, 32), f"Expected {(num_nodes, 32)}, got {output.shape}"

def test_fuser_agent_cross_attention():
    """Test Fuser (iTransformer) properly fuses temporal history and spatial context."""
    num_variates = 3 # e.g. 3 active sensors
    agent = FuserAgent(num_variates=num_variates, seq_len=60, pred_len=1, d_model=64)
    
    # Mock temporal history matrix [seq_len, variates] for 3 sensors
    # So when unsqueezed it becomes [Batch, Seq_Len, Variates] -> [1, 60, 3]
    current_history = np.random.randn(60, num_variates)
    
    # Mock spatial context from GATv2 [nodes, channels]
    # GAT output has length equal to ALL map nodes (let's say 3 nodes were active)
    spatial_context = torch.randn(num_variates, 32)
    
    output = agent.fuse_state(current_history, spatial_context=spatial_context)
    
    assert output is not None
    # Outputs a flattened present state prediction vector [variates]
    assert output.shape == (num_variates,), f"Expected {(num_variates,)}, got {output.shape}"

def test_auditor_agent_anomaly_scoring():
    """Test Auditor (Wavelet + OCC) can score payloads without crashing."""
    # Uses power of 2 lengths internally
    agent = AuditorAgent(input_len=32, J=2, latent_dim=16)
    
    # Mock feature incoming from inference cycle 
    # (Typically the flattened sequence or the signature)
    # The agent applies normalization, so we must conform to expected sizes
    mock_payload = torch.randn(1, 32)
    
    result = agent.inference({"signature": mock_payload})
    
    assert isinstance(result, dict)
    assert "is_anomaly" in result
    assert "score" in result
    assert isinstance(result["score"], float)
