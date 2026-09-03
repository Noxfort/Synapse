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
# File: tests/unit/test_trainers_solid.py
# Author: Gabriel Moraes
# Date: 2026-08-28

import pytest
import torch
import numpy as np

# Base Protocols
from src.interfaces.base import IStepTrainable, IDeviceMovable, ITrainable

# Domain Trainer Protocols
from src.interfaces.trainers import (
    IAuditorTrainer,
    IImputerTrainer,
    ICorrectorTrainer,
    ISpecialistTrainer,
    ILinguistTrainer,
    ICoordinatorTrainer,
    IFuserTrainer,
    ICartographerTrainer
)

# Pipelines & Factories for cleanly wired components
from src.pipeline.auditor_pipeline import AuditorPipeline
from src.pipeline.imputer_pipeline import ImputerPipeline
from src.pipeline.corrector_pipeline import CorrectorPipeline
from src.pipeline.specialist_pipeline import SpecialistPipeline
from src.pipeline.coordinator_pipeline import CoordinatorPipeline
from src.factories.fuser_model_factory import FuserModelFactory

# Concrete Trainer Implementations
from src.trainer.auditor_trainer import AuditorTrainer
from src.trainer.imputer_trainer import ImputerTrainer
from src.trainer.corrector_trainer import CorrectorTrainer
from src.trainer.specialist_trainer import SpecialistTrainer
from src.trainer.coordinator_trainer import CoordinatorTrainer
from src.trainer.fuser_trainer import FuserTrainer
from src.trainer.cartographer_trainer import CartographerTrainer

# Cartographer Domain Entities
from src.domain.entities import MapEdge, MapNode
from src.services.line_graph_builder import LineGraphBuilder
from src.models.sinkhorn_cross_attention import SinkhornCrossAttention


@pytest.fixture
def sample_road_network():
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
    ]
    return edges, nodes


def test_base_protocol_hierarchy():
    """Verifies that ITrainable is backward-compatible with IStepTrainable."""
    assert ITrainable is IStepTrainable


def test_cartographer_trainer_solid_and_lsp(sample_road_network):
    """
    Verifies that CartographerTrainer adheres to SOLID:
    - ISP: Implements ICartographerTrainer, IStepTrainable, IDeviceMovable.
    - LSP: Can be invoked with either 3 separate args or a single packed batch tuple.
    - DIP: Injected model dependencies and protocol compliance.
    """
    edges, nodes = sample_road_network
    source = LineGraphBuilder.build_from_edges(edges[:5], nodes)
    mutant = LineGraphBuilder.build_from_edges(edges[:4], nodes)

    if source is None or mutant is None:
        pytest.skip("PyG not available for LineGraphBuilder.")

    gt = torch.zeros(source.num_nodes, mutant.num_nodes)
    for i in range(min(source.num_nodes, mutant.num_nodes)):
        gt[i, i] = 1.0

    model = SinkhornCrossAttention(raw_dim=11, d_model=16, n_heads=2, n_gat_layers=1, sinkhorn_iters=2)
    trainer = CartographerTrainer(model=model, learning_rate=1e-3, device=torch.device("cpu"))

    # Protocol type checks
    assert isinstance(trainer, ICartographerTrainer)
    assert isinstance(trainer, IStepTrainable)
    assert isinstance(trainer, IDeviceMovable)

    # Device movable test
    moved = trainer.to("cpu")
    assert moved is trainer

    # LSP Mode 1: 3 explicit positional arguments
    loss1 = trainer.train_step(source, mutant, gt)
    assert isinstance(loss1, float)
    assert loss1 >= 0.0

    # LSP Mode 2: Unified batch tuple (generic IStepTrainable caller)
    loss2 = trainer.train_step((source, mutant, gt))
    assert isinstance(loss2, float)
    assert loss2 >= 0.0

    # Error handling for missing required components
    with pytest.raises(ValueError):
        trainer.train_step(source)


def test_auditor_trainer_solid_protocols():
    """Verifies AuditorTrainer protocol compliance."""
    pipeline = AuditorPipeline(input_len=32, J=2, latent_dim=16)
    trainer = AuditorTrainer(model=pipeline.model, device=torch.device("cpu"))

    assert isinstance(trainer, IAuditorTrainer)
    assert isinstance(trainer, IStepTrainable)
    assert isinstance(trainer, IDeviceMovable)

    trainer.to("cpu")
    dummy_x = torch.randn(2, 32)
    loss = trainer.train_step(dummy_x)
    assert isinstance(loss, float)


def test_imputer_trainer_solid_protocols():
    """Verifies ImputerTrainer protocol compliance."""
    pipeline = ImputerPipeline(feature_dim=2, seq_len=16, patch_len=4, stride=2, d_model=32)
    trainer = ImputerTrainer(model=pipeline.model, device=torch.device("cpu"))

    assert isinstance(trainer, IImputerTrainer)
    assert isinstance(trainer, IStepTrainable)
    assert isinstance(trainer, IDeviceMovable)

    trainer.to("cpu")
    dummy_x = torch.randn(2, 16, 2)
    loss = trainer.train_step(dummy_x)
    assert isinstance(loss, float)


def test_corrector_trainer_solid_protocols():
    """Verifies CorrectorTrainer protocol compliance."""
    pipeline = CorrectorPipeline(input_dim=1, hidden_dim=16, latent_dim=8, kernel_size=3)
    trainer = CorrectorTrainer(model=pipeline.model, device=torch.device("cpu"))

    assert isinstance(trainer, ICorrectorTrainer)
    assert isinstance(trainer, IStepTrainable)
    assert isinstance(trainer, IDeviceMovable)

    trainer.to("cpu")
    dummy_x = torch.randn(4, 10)
    loss = trainer.train_step(dummy_x)
    assert isinstance(loss, float)


def test_specialist_trainer_solid_protocols():
    """Verifies SpecialistTrainer protocol compliance."""
    pipeline = SpecialistPipeline(input_dim=1, output_dim=16, num_channels=[8, 16])
    trainer = SpecialistTrainer(model=pipeline.model, input_dim=1, output_dim=16, device=torch.device("cpu"))

    assert isinstance(trainer, ISpecialistTrainer)
    assert isinstance(trainer, IStepTrainable)
    assert isinstance(trainer, IDeviceMovable)

    trainer.to("cpu")
    dummy_x = torch.randn(2, 20, 1)
    dummy_y = torch.randn(2, 16)
    loss = trainer.train_step((dummy_x, dummy_y))
    assert isinstance(loss, float)


def test_coordinator_trainer_solid_protocols():
    """Verifies CoordinatorTrainer protocol compliance."""
    pipeline = CoordinatorPipeline(in_channels=16, hidden_channels=16, out_channels=16)
    trainer = CoordinatorTrainer(model=pipeline.model, device=torch.device("cpu"))

    assert isinstance(trainer, ICoordinatorTrainer)
    assert isinstance(trainer, IStepTrainable)
    assert isinstance(trainer, IDeviceMovable)

    trainer.to("cpu")
    x = torch.randn(3, 16)
    edge_index = torch.tensor([[0, 1], [1, 2]], dtype=torch.long)
    loss = trainer.train_step((x, edge_index, x))
    assert isinstance(loss, float)


def test_fuser_trainer_solid_protocols():
    """Verifies FuserTrainer protocol compliance."""
    pipeline = FuserModelFactory.create_fusion_pipeline(
        num_variates=4,
        seq_len=10,
        pred_len=1,
        d_model=16,
        n_heads=2,
        layers=1,
        spatial_dim=8
    )
    trainer = FuserTrainer(composite_model=pipeline.module_dict, spatial_dim=8)

    assert isinstance(trainer, IFuserTrainer)
    assert isinstance(trainer, IStepTrainable)
    assert isinstance(trainer, IDeviceMovable)

    trainer.to("cpu")
    dummy_x = torch.randn(2, 10, 4)
    dummy_y = torch.randn(2, 1, 4)
    loss = trainer.train_step((dummy_x, dummy_y))
    assert isinstance(loss, float)
