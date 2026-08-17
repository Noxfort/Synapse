# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# File: tests/unit/test_physics_engine.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import pytest
import torch
import tempfile
import os

from src.physics.fundamental_diagrams import (
    GreenshieldsDiagram,
    UnderwoodDiagram,
    NewellDaganzoDiagram,
)
from src.physics.kinematics import (
    NonNegativityBoundsConstraint,
    KinematicAccelerationConstraint,
    TemporalSmoothnessConstraint,
)
from src.physics.continuum import (
    ContinuumConservation,
    SpatialGraphConservation,
)
from src.physics.traffic_loss import TrafficPhysicsLoss
from src.infrastructure.safetensors_repository import SafetensorsRepository
from src.strategies.semantic_clustering import CosineSemanticClusterer
from src.models.pinn_traffic_flow import PINNTrafficFlow
from src.models.pi_vae_tcn import PIVAETCN
from src.models.wavelet_ae_occ import WaveletAEOCC
from src.models.neuro_symbolic import NeuroSymbolicModel
from src.models.distilroberta import DistilRobertaSemanticExtractor


class TestFundamentalDiagrams:
    def test_greenshields(self):
        diag = GreenshieldsDiagram()
        k = torch.tensor([0.0, 60.0, 120.0])
        v_free = torch.tensor([60.0, 60.0, 60.0])
        k_jam = torch.tensor([120.0, 120.0, 120.0])
        
        q = diag.compute_flow(k, v_free, k_jam)
        v = diag.compute_speed(k, v_free, k_jam)
        
        assert q.shape == (3,)
        assert v[0].item() == pytest.approx(60.0, rel=1e-3)
        assert v[1].item() == pytest.approx(30.0, rel=1e-3)
        assert v[2].item() == pytest.approx(0.0, rel=1e-3)
        assert q[0].item() == pytest.approx(0.0, rel=1e-3)
        assert q[1].item() == pytest.approx(1800.0, rel=1e-3)
        assert q[2].item() == pytest.approx(0.0, rel=1e-3)

    def test_underwood(self):
        diag = UnderwoodDiagram()
        k = torch.tensor([0.0, 50.0])
        v_free = torch.tensor([60.0, 60.0])
        k_jam = torch.tensor([120.0, 120.0])
        
        q = diag.compute_flow(k, v_free, k_jam)
        assert q.shape == (2,)
        assert q[0].item() == pytest.approx(0.0, rel=1e-3)
        assert q[1].item() > 0.0

    def test_newell_daganzo(self):
        diag = NewellDaganzoDiagram()
        k = torch.tensor([10.0, 60.0, 110.0])
        v_free = torch.tensor([60.0, 60.0, 60.0])
        k_jam = torch.tensor([120.0, 120.0, 120.0])
        
        q = diag.compute_flow(k, v_free, k_jam)
        assert q.shape == (3,)
        assert (q >= 0.0).all()


class TestKinematicConstraints:
    def test_non_negativity_bounds(self):
        constraint = NonNegativityBoundsConstraint()
        positive_state = torch.tensor([1.0, 2.0, 3.0])
        negative_state = torch.tensor([-1.0, -2.0, 3.0])
        
        loss_pos = constraint.compute_residual(positive_state)
        loss_neg = constraint.compute_residual(negative_state)
        
        assert loss_pos.item() == 0.0
        assert loss_neg.item() > 0.0

    def test_kinematic_acceleration(self):
        constraint = KinematicAccelerationConstraint(max_acceleration=5.0, dt=1.0)
        smooth_vel = torch.tensor([[10.0, 12.0, 14.0, 16.0]])  # dv = 2.0 <= 5.0
        harsh_vel = torch.tensor([[10.0, 25.0, 10.0, 35.0]])   # dv = 15.0 > 5.0
        
        loss_smooth = constraint.compute_residual(smooth_vel)
        loss_harsh = constraint.compute_residual(harsh_vel)
        
        assert loss_smooth.item() == 0.0
        assert loss_harsh.item() > 0.0

    def test_temporal_smoothness(self):
        constraint = TemporalSmoothnessConstraint()
        constant_seq = torch.tensor([[5.0, 5.0, 5.0, 5.0]])
        noisy_seq = torch.tensor([[5.0, 15.0, -5.0, 20.0]])
        
        loss_const = constraint.compute_residual(constant_seq)
        loss_noisy = constraint.compute_residual(noisy_seq)
        
        assert loss_const.item() == 0.0
        assert loss_noisy.item() > 0.0


class TestContinuumConservation:
    def test_continuum_conservation(self):
        conservation = ContinuumConservation()
        # q = rho * v -> 100 = 10 * 10
        q = torch.tensor([[100.0, 200.0]])
        v = torch.tensor([[10.0, 20.0]])
        rho = torch.tensor([[10.0, 10.0]])
        
        loss_perfect = conservation.compute_residual(q=q, v=v, rho=rho)
        assert loss_perfect.item() == pytest.approx(0.0, abs=1e-4)

        # Inconsistent
        q_bad = torch.tensor([[500.0, 500.0]])
        loss_bad = conservation.compute_residual(q=q_bad, v=v, rho=rho)
        assert loss_bad.item() > 0.0

    def test_spatial_graph_conservation(self):
        conservation = SpatialGraphConservation()
        flow = torch.tensor([[[100.0], [100.0]]])  # [Batch=1, Nodes=2, Channels=1]
        edge_index = torch.tensor([[0], [1]])      # 0 -> 1
        
        loss = conservation.compute_residual(flow, edge_index)
        assert loss.item() == 0.0


class TestTrafficPhysicsLossEngine:
    def test_integrated_loss_engine(self):
        engine = TrafficPhysicsLoss(max_acceleration=10.0)
        # 3-channel state: [Batch=2, Channels=3 (q, v, rho), SeqLen=24]
        state = torch.ones(2, 3, 24) * 10.0
        state[:, 0, :] = 100.0  # q = 100
        state[:, 1, :] = 10.0   # v = 10
        state[:, 2, :] = 10.0   # rho = 10 -> q = rho * v = 100
        
        losses = engine.compute_losses(state)
        assert "total_physics_loss" in losses
        assert "loss_bounds" in losses
        assert "loss_kinematics" in losses
        assert "loss_smooth" in losses
        assert "loss_conservation" in losses
        assert losses["total_physics_loss"].item() >= 0.0


class TestSafetensorsAndClustering:
    def test_safetensors_repository(self):
        repo = SafetensorsRepository()
        tensors = {"test_tensor": torch.randn(4, 4)}
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.safetensors")
            success = repo.save_tensors(tensors, path)
            assert success is True
            assert os.path.exists(path)
            
            loaded = repo.load_tensors(path)
            assert "test_tensor" in loaded
            assert loaded["test_tensor"].shape == (4, 4)

    def test_cosine_clusterer(self):
        clusterer = CosineSemanticClusterer(similarity_threshold=0.80)
        vec1 = torch.tensor([[1.0, 0.0, 0.0]])
        concept1, is_new1 = clusterer.match_or_create_concept(vec1, ["traffic jam"])
        assert is_new1 is True
        assert concept1 == "Semantic_Concept_1"
        
        # Similar vector -> should match existing concept
        vec2 = torch.tensor([[0.95, 0.05, 0.0]])
        concept2, is_new2 = clusterer.match_or_create_concept(vec2, ["heavy traffic"])
        assert is_new2 is False
        assert concept2 == concept1


class TestModelsRefactoredPINN:
    def test_pinn_traffic_flow_with_custom_diagram(self):
        custom_diagram = UnderwoodDiagram()
        model = PINNTrafficFlow(in_channels=32, fundamental_diagram=custom_diagram)
        x = torch.randn(2, 5, 32)
        edge_index = torch.tensor([[0, 1], [1, 2]])
        
        refined, metrics = model(x, edge_index=edge_index)
        assert refined.shape == (2, 5, 32)
        assert "physics_residual" in metrics

    def test_pivae_tcn_with_injected_physics(self):
        engine = TrafficPhysicsLoss(max_acceleration=8.0)
        model = PIVAETCN(input_channels=3, hidden_channels=16, latent_channels=8, physics_loss_engine=engine)
        x = torch.randn(2, 3, 24).abs()  # positive inputs
        recon, mu, logvar, residuals = model(x, return_physics_residuals=True)
        
        assert recon.shape == (2, 3, 24)
        assert "total_physics_loss" in residuals
