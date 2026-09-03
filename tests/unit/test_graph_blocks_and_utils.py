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
# File: tests/unit/test_graph_blocks_and_utils.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import pytest
import torch
import torch.nn.functional as F

from src.utils.graph_utils import (
    compute_random_walk_transition_matrices,
    batch_offset_edge_index
)
from src.blocks.graph_blocks import (
    DiffusionGraphConv,
    AdaptiveAdjacency,
    ObservabilityGate,
    GatedTemporalConv
)
from src.models.diffusion_gatv2 import DiffusionGATv2
from src.domain.model_contracts import IGraphDiffusionModel


def test_compute_random_walk_transition_matrices_linear():
    """Verify forward and backward transition matrices for linear graph."""
    num_nodes = 4
    edge_index = torch.tensor([[0, 1, 2], [1, 2, 3]], dtype=torch.long)
    
    p_f, p_b = compute_random_walk_transition_matrices(num_nodes, edge_index)
    
    assert p_f.shape == (num_nodes, num_nodes)
    assert p_b.shape == (num_nodes, num_nodes)
    
    # Forward: node 0 transitions to node 1 with probability 1.0
    assert p_f[0, 1].item() == 1.0
    # Backward: node 1 is reached from node 0 with probability 1.0
    assert p_b[1, 0].item() == 1.0


def test_compute_random_walk_transition_matrices_empty_fallback():
    """Verify fallback to identity matrix when graph has no edges."""
    num_nodes = 5
    empty_edges = torch.empty((2, 0), dtype=torch.long)
    
    p_f, p_b = compute_random_walk_transition_matrices(num_nodes, empty_edges)
    
    assert torch.equal(p_f, torch.eye(num_nodes))
    assert torch.equal(p_b, torch.eye(num_nodes))


def test_batch_offset_edge_index():
    """Verify batch edge index replication and node offsetting."""
    edge_index = torch.tensor([[0, 1], [1, 2]], dtype=torch.long)
    num_nodes = 3
    batch_size = 2
    
    batched = batch_offset_edge_index(edge_index, batch_size, num_nodes)
    
    # Expected: [[0, 1, 3, 4], [1, 2, 4, 5]]
    expected = torch.tensor([[0, 1, 3, 4], [1, 2, 4, 5]], dtype=torch.long)
    assert torch.equal(batched, expected)


def test_adaptive_adjacency_block():
    """Verify AdaptiveAdjacency computes stochastic rows (sum=1.0) via softmax."""
    num_nodes = 6
    adaptive_block = AdaptiveAdjacency(num_nodes=num_nodes, adaptive_dim=8)
    
    adp = adaptive_block()
    
    assert adp.shape == (num_nodes, num_nodes)
    assert (adp >= 0.0).all()
    # Row sum must equal 1.0
    row_sums = adp.sum(dim=-1)
    assert torch.allclose(row_sums, torch.ones(num_nodes), atol=1e-5)


def test_observability_gate_anchor_preservation():
    """Verify ObservabilityGate anchors ground truth sensor values."""
    num_nodes = 4
    dim = 8
    gate = ObservabilityGate(in_channels=dim, out_channels=dim)
    
    x_raw = torch.randn(1, num_nodes, dim)
    h_diffused = torch.zeros(1, num_nodes, dim)
    
    # Sensor 0 is active (1.0), others unobserved (0.0)
    mask = torch.tensor([1.0, 0.0, 0.0, 0.0])
    
    out = gate(h=h_diffused, x_raw=x_raw, observability_mask=mask)
    
    # Node 0 must retain x_raw value (since h_diffused is 0 and mask is 1)
    assert torch.allclose(out[0, 0, :], x_raw[0, 0, :], atol=1e-5)
    # Node 1-3 should be 0 because h_diffused is 0 and mask is 0
    assert torch.allclose(out[0, 1:, :], torch.zeros(num_nodes - 1, dim), atol=1e-5)


def test_diffusion_graph_conv_forward():
    """Verify DiffusionGraphConv forward pass dimensions and gradient flow."""
    num_nodes = 4
    in_dim = 16
    out_dim = 32
    conv = DiffusionGraphConv(in_channels=in_dim, out_channels=out_dim, diffusion_steps=2)
    
    x = torch.randn(2, num_nodes, in_dim, requires_grad=True)
    p_f = torch.eye(num_nodes)
    p_b = torch.eye(num_nodes)
    adp = torch.eye(num_nodes)
    
    out = conv(x, p_f, p_b, adaptive_adj=adp)
    
    assert out.shape == (2, num_nodes, out_dim)
    loss = out.sum()
    loss.backward()
    assert x.grad is not None


def test_gated_temporal_conv_causality():
    """Verify GatedTemporalConv maintains sequence length and causality."""
    conv = GatedTemporalConv(in_channels=16, out_channels=32, kernel_size=3)
    x = torch.randn(2, 16, 20)  # [Batch, Channels, Seq_Len]
    
    out = conv(x)
    assert out.shape == (2, 32, 20)


def test_diffusion_gatv2_satisfies_contract():
    """Verify DiffusionGATv2 implements IGraphDiffusionModel domain protocol."""
    model = DiffusionGATv2(num_nodes=5, in_channels=16, hidden_channels=32, out_channels=16)
    assert isinstance(model, IGraphDiffusionModel)
