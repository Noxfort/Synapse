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
# File: tests/unit/test_fuser_diffusion_pinn.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import pytest
import torch
import numpy as np

from src.models.diffusion_gatv2 import DiffusionGATv2, DiffusionGraphConv
from src.models.pino_traffic import PINOTrafficFlow1D
from src.agents.fuser_agent import FuserAgent


def test_diffusion_gatv2_single_sensor_extrapolation():
    """Test DiffusionGATv2 extrapolates across 6 nodes from a single observed sensor."""
    num_nodes = 6
    in_dim = 32
    out_dim = 32
    
    model = DiffusionGATv2(
        num_nodes=num_nodes,
        in_channels=in_dim,
        hidden_channels=32,
        out_channels=out_dim,
        diffusion_steps=2
    )
    
    # Graph topology: 0 -> 1 -> 2 -> 3 -> 4 -> 5 (Linear Corridor)
    edge_index = torch.tensor([
        [0, 1, 2, 3, 4],
        [1, 2, 3, 4, 5]
    ], dtype=torch.long)
    
    # Only node 0 has an active sensor, nodes 1-5 are unobserved (zeros)
    x = torch.zeros((1, num_nodes, in_dim))
    x[0, 0, :] = torch.randn(in_dim)  # Ground truth anchor at node 0
    
    # Observability mask: 1 for node 0, 0 for others
    mask = torch.tensor([1.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    
    out, adp_adj = model(x, edge_index=edge_index, observability_mask=mask)
    
    assert out.shape == (1, num_nodes, out_dim), f"Expected shape {(1, num_nodes, out_dim)}, got {out.shape}"
    assert adp_adj.shape == (num_nodes, num_nodes), "Adaptive adjacency should be N x N"
    
    # Unobserved nodes (1 to 5) must receive non-zero diffused energy from node 0
    diffused_norm = torch.norm(out[0, 1:, :], dim=-1)
    assert (diffused_norm > 0).all(), "Unobserved nodes should have non-zero extrapolated features."


def test_pino_traffic_flow_consistency():
    """Test PINOTrafficFlow1D computes valid density, speed, flow and continuity residuals."""
    num_nodes = 4
    in_dim = 32
    
    pinn = PINOTrafficFlow1D(in_channels=in_dim, hidden_dim=32)
    
    x = torch.randn((1, num_nodes, in_dim))
    edge_index = torch.tensor([[0, 1, 2], [1, 2, 3]], dtype=torch.long)
    global_vel = torch.tensor([50.0, 45.0, 40.0, 35.0]) # Macroscopic speeds
    
    refined_x, metrics = pinn(x, edge_index=edge_index, global_velocities=global_vel)
    
    assert refined_x.shape == (1, num_nodes, in_dim)
    assert "density" in metrics
    assert "speed" in metrics
    assert "flow" in metrics
    assert "physics_residual" in metrics
    
    # Physical variables must be strictly non-negative
    assert (metrics["density"] >= 0).all()
    assert (metrics["speed"] >= 0).all()
    assert (metrics["flow"] >= 0).all()
    assert metrics["physics_residual"].item() >= 0.0


def test_fuser_agent_full_hybrid_pipeline():
    """Test FuserAgent running Diffusion + PINN + iTransformer with dynamic calibration."""
    num_variates = 5
    seq_len = 60
    
    agent = FuserAgent(
        num_variates=num_variates,
        seq_len=seq_len,
        pred_len=1,
        d_model=64,
        spatial_dim=32
    )
    
    # Mock history: 60 time steps for 5 nodes
    current_history = np.random.randn(seq_len, num_variates).astype(np.float32)
    
    # Topology: Loop graph 0->1->2->3->4->0
    edge_index = torch.tensor([
        [0, 1, 2, 3, 4],
        [1, 2, 3, 4, 0]
    ], dtype=torch.long)
    agent.set_topology(edge_index)
    
    # Scenario A: 1 active sensor (node 0)
    mask_1 = np.array([1.0, 0.0, 0.0, 0.0, 0.0])
    global_vel = np.array([60.0, 60.0, 55.0, 50.0, 50.0])
    
    out_1 = agent.fuse_state(
        current_history=current_history,
        observability_mask=mask_1,
        global_velocities=global_vel,
        edge_index=edge_index
    )
    
    assert out_1.shape == (num_variates,), f"Expected {(num_variates,)}, got {out_1.shape}"
    assert np.isfinite(out_1).all(), "Output must contain finite real numbers."
    
    # Scenario B: Dynamic Calibration when 2nd sensor comes online (node 2)
    mask_2 = np.array([1.0, 0.0, 1.0, 0.0, 0.0])
    agent.update_observability(mask_2)
    
    out_2 = agent.fuse_state(
        current_history=current_history,
        observability_mask=mask_2,
        global_velocities=global_vel,
        edge_index=edge_index
    )
    
    assert out_2.shape == (num_variates,)
    assert np.isfinite(out_2).all()


def test_fuser_agent_backward_compatibility():
    """Test FuserAgent legacy call without mask or global velocities (backward compatibility)."""
    num_variates = 3
    seq_len = 60
    
    agent = FuserAgent(num_variates=num_variates, seq_len=seq_len, pred_len=1, d_model=32)
    
    current_history = np.random.randn(seq_len, num_variates).astype(np.float32)
    spatial_context = torch.randn(num_variates, 32)
    
    # Legacy invocation (only history and spatial context)
    output = agent.fuse_state(current_history, spatial_context=spatial_context)
    
    assert output is not None
    assert output.shape == (num_variates,)
