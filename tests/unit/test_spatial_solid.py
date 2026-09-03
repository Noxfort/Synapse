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
# File: tests/unit/test_spatial_solid.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import pytest
import torch
import numpy as np
from unittest.mock import MagicMock

from src.domain.entities import MapEdge, MapNode
from src.domain.model_contracts import IGraphSampler, ISpatialGraphMutator
from src.interfaces.trainers import ICartographerTrainer
from src.services.graph_sampler import BfsGraphSampler
from src.services.spatial_graph_mutator import SpatialGraphMutator
from src.services.line_graph_builder import LineGraphBuilder
from src.models.sinkhorn_cross_attention import SinkhornCrossAttention
from src.trainer.cartographer_trainer import CartographerTrainer
from src.optimization.strategies_spatial import SpatialStrategies


@pytest.fixture
def sample_road_network():
    """Builds a small 10-edge grid network for testing."""
    nodes = [
        MapNode(id=f"n{i}", x=float(i % 3) * 100.0, y=float(i // 3) * 100.0, node_type="junction")
        for i in range(9)
    ]
    edges = [
        MapEdge(id="e0", from_node="n0", to_node="n1", shape=[(0.0, 0.0), (100.0, 0.0)], weight=100.0),
        MapEdge(id="e1", from_node="n1", to_node="n2", shape=[(100.0, 0.0), (200.0, 0.0)], weight=100.0),
        MapEdge(id="e2", from_node="n0", to_node="n3", shape=[(0.0, 0.0), (0.0, 100.0)], weight=100.0),
        MapEdge(id="e3", from_node="n1", to_node="n4", shape=[(100.0, 0.0), (100.0, 100.0)], weight=100.0),
        MapEdge(id="e4", from_node="n2", to_node="n5", shape=[(200.0, 0.0), (200.0, 100.0)], weight=100.0),
        MapEdge(id="e5", from_node="n3", to_node="n4", shape=[(0.0, 100.0), (100.0, 100.0)], weight=100.0),
        MapEdge(id="e6", from_node="n4", to_node="n5", shape=[(100.0, 100.0), (200.0, 100.0)], weight=100.0),
        MapEdge(id="e7", from_node="n3", to_node="n6", shape=[(0.0, 100.0), (0.0, 200.0)], weight=100.0),
        MapEdge(id="e8", from_node="n4", to_node="n7", shape=[(100.0, 100.0), (100.0, 200.0)], weight=100.0),
        MapEdge(id="e9", from_node="n5", to_node="n8", shape=[(200.0, 100.0), (200.0, 200.0)], weight=100.0),
        MapEdge(id="e10", from_node="n6", to_node="n7", shape=[(0.0, 200.0), (100.0, 200.0)], weight=100.0),
        MapEdge(id="e11", from_node="n7", to_node="n8", shape=[(100.0, 200.0), (200.0, 200.0)], weight=100.0),
    ]
    return edges, nodes


def test_bfs_graph_sampler_contract_and_expansion(sample_road_network):
    """Test BfsGraphSampler satisfies IGraphSampler and samples connected components."""
    edges, nodes = sample_road_network
    sampler = BfsGraphSampler()
    assert isinstance(sampler, IGraphSampler)

    # Sample a subgraph of 5-8 edges
    sub_edges, sub_nodes = sampler.sample_subgraph(edges, nodes, min_edges=5, max_edges=8)
    assert len(sub_edges) >= 5
    assert len(sub_edges) <= 8
    assert len(sub_nodes) > 0

    # Ensure all sampled edges have their nodes included in sub_nodes
    sub_node_ids = {n.id for n in sub_nodes}
    for e in sub_edges:
        assert e.from_node in sub_node_ids
        assert e.to_node in sub_node_ids


def test_bfs_graph_sampler_edge_cases():
    """Test BfsGraphSampler handles empty or minimal edge collections gracefully."""
    sampler = BfsGraphSampler()
    empty_edges, empty_nodes = sampler.sample_subgraph([], [])
    assert empty_edges == []
    assert empty_nodes == []

    small_edge = [MapEdge(id="e0", from_node="n0", to_node="n1", shape=[(0, 0), (1, 1)])]
    small_node = [MapNode(id="n0", x=0, y=0, node_type="j"), MapNode(id="n1", x=1, y=1, node_type="j")]
    res_edges, res_nodes = sampler.sample_subgraph(small_edge, small_node, min_edges=5)
    assert len(res_edges) == 1
    assert len(res_nodes) == 2


def test_spatial_graph_mutator_contract_and_jitter(sample_road_network):
    """Test SpatialGraphMutator satisfies ISpatialGraphMutator and generates valid mutants."""
    edges, _ = sample_road_network
    mutator = SpatialGraphMutator()
    assert isinstance(mutator, ISpatialGraphMutator)

    mutants, surviving = mutator.mutate(edges, noise_scale=10.0, drop_prob=0.2)

    assert len(mutants) == len(surviving)
    assert len(mutants) >= 3  # Minimum guarantee
    assert len(mutants) <= len(edges)

    for m in mutants:
        assert m.id.startswith("mut_")
        assert len(m.shape) >= 2


def test_spatial_graph_mutator_empty():
    """Test SpatialGraphMutator with empty edge input."""
    mutator = SpatialGraphMutator()
    mutants, surviving = mutator.mutate([])
    assert mutants == []
    assert surviving == []


def test_cartographer_trainer_step(sample_road_network):
    """Test CartographerTrainer performs mixed-precision training steps (SRP & DIP)."""
    edges, nodes = sample_road_network
    source = LineGraphBuilder.build_from_edges(edges[:5], nodes)
    mutant = LineGraphBuilder.build_from_edges(edges[:4], nodes)

    if source is None or mutant is None:
        pytest.skip("PyG not available for LineGraphBuilder.")

    gt = torch.zeros(source.num_nodes, mutant.num_nodes)
    for i in range(min(source.num_nodes, mutant.num_nodes)):
        gt[i, i] = 1.0

    model = SinkhornCrossAttention(raw_dim=11, d_model=16, n_heads=2, n_gat_layers=1, sinkhorn_iters=3)
    trainer = CartographerTrainer(model=model, learning_rate=1e-3, device=torch.device('cpu'))

    assert isinstance(trainer, ICartographerTrainer)

    loss = trainer.train_step(source, mutant, gt)
    assert isinstance(loss, float)
    assert loss >= 0.0
    assert not np.isnan(loss)


def test_spatial_strategies_dependency_injection(sample_road_network):
    """Test SpatialStrategies with injected mock sampler and mutator (OCP & DIP)."""
    edges, nodes = sample_road_network
    graph_data = {'edges': edges, 'nodes': nodes}

    # Mock trial
    mock_trial = MagicMock()
    mock_trial.number = 0
    mock_trial.params = {}
    mock_trial.suggest_categorical.side_effect = lambda name, choices: choices[0]
    mock_trial.suggest_int.side_effect = lambda name, low, high: low
    mock_trial.suggest_float.side_effect = lambda name, low, high, **kw: low
    mock_trial.should_prune.return_value = False
    mock_trial.report.return_value = None

    # Mock Sampler & Mutator
    mock_sampler = MagicMock(spec=IGraphSampler)
    mock_sampler.sample_subgraph.return_value = (edges[:5], nodes)

    mock_mutator = MagicMock(spec=ISpatialGraphMutator)
    mock_mutator.mutate.return_value = (edges[:4], list(range(4)))

    loss = SpatialStrategies.cartographer_strategy(
        trial=mock_trial,
        graph_data=graph_data,
        device=torch.device('cpu'),
        max_epochs=1,
        min_epochs=1,
        n_subgraphs_per_epoch=2,
        sampler=mock_sampler,
        mutator=mock_mutator
    )

    assert isinstance(loss, float)
    assert mock_sampler.sample_subgraph.called
    assert mock_mutator.mutate.called


def test_spatial_strategies_backward_compatible_delegates(sample_road_network):
    """Ensure deprecated static helpers delegate to new services cleanly."""
    edges, nodes = sample_road_network
    sub_edges, sub_nodes = SpatialStrategies._random_subgraph(edges, nodes, min_edges=5, max_edges=8)
    assert len(sub_edges) >= 5

    mutants, perm = SpatialStrategies._create_mutation(sub_edges, noise_scale=5.0)
    assert len(mutants) == len(perm)


def test_task_registry_cartographer_integration(sample_road_network, monkeypatch):
    """Verify TaskRegistry seamlessly builds and executes Cartographer tasks."""
    from src.optimization.task_registry import TaskRegistry

    edges, nodes = sample_road_network
    univ_data = np.random.randn(200, 4).astype(np.float32)

    # Mock MapService so _prepare_cartographer succeeds
    mock_ms = MagicMock()
    mock_ms.load_network.return_value = True
    mock_ms.edges = edges
    mock_ms.nodes = nodes
    monkeypatch.setattr("src.optimization.task_registry.MapService", lambda: mock_ms)

    tasks = TaskRegistry.build_tasks(
        univ_data=univ_data,
        map_graph=None,
        map_file_path="mock_map.net.xml.gz",
        device=torch.device('cpu')
    )

    cart_task = next((t for t in tasks if t.name == "cartographer"), None)
    assert cart_task is not None
    assert cart_task.enabled is True
    assert "Cartographer" in cart_task.label

