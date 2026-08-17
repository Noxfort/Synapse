# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# File: tests/unit/test_pure_orchestrators.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import pytest
import torch
import numpy as np

# Domain Protocols
from src.domain.interfaces import (
    IAgent,
    IAuditorPipeline, IAuditorTrainer,
    IImputerPipeline, IImputerTrainer,
    ICorrectorPipeline, ICorrectorTrainer,
    ISpecialistPipeline, ISpecialistTrainer,
    ILinguistPipeline, ILinguistTrainer,
    ICoordinatorPipeline, ICoordinatorTrainer
)

# Refactored Facade Agents
from src.agents.auditor_agent import AuditorAgent
from src.agents.imputer_agent import ImputerAgent
from src.agents.corrector_agent import CorrectorAgent
from src.agents.specialist_agent import SpecialistAgent
from src.agents.linguist_agent import LinguistAgent
from src.agents.coordinator_agent import CoordinatorAgent
from src.agents.fuser_agent import FuserAgent

# Pipelines & Trainers
from src.services.auditor_pipeline import AuditorPipeline
from src.services.auditor_trainer import AuditorTrainer
from src.services.imputer_pipeline import ImputerPipeline
from src.services.imputer_trainer import ImputerTrainer
from src.services.corrector_pipeline import CorrectorPipeline
from src.services.corrector_trainer import CorrectorTrainer
from src.services.specialist_pipeline import SpecialistPipeline
from src.services.specialist_trainer import SpecialistTrainer
from src.services.linguist_pipeline import LinguistPipeline
from src.services.linguist_trainer import LinguistTrainer
from src.services.coordinator_pipeline import CoordinatorPipeline
from src.services.coordinator_trainer import CoordinatorTrainer

# Central Factory
from src.factories.agent_factory import AgentFactory


def test_auditor_pure_orchestrator_and_pipeline():
    """Verifies AuditorAgent facade delegation and standalone AuditorPipeline execution."""
    pipeline = AuditorPipeline(input_len=32, J=2, latent_dim=16)
    assert isinstance(pipeline, IAuditorPipeline)

    agent = AuditorAgent(pipeline=pipeline, input_len=32)
    assert isinstance(agent, IAgent)

    dummy_input = torch.randn(1, 32)
    result = agent.inference({"signature": dummy_input})
    assert isinstance(result, dict)
    assert "is_anomaly" in result
    assert "score" in result
    assert "status" in result
    assert result["status"] == "audited"

    loss = agent.train_step(dummy_input)
    assert isinstance(loss, float)


def test_imputer_pure_orchestrator_and_pipeline():
    """Verifies ImputerAgent facade delegation and standalone ImputerPipeline execution."""
    pipeline = ImputerPipeline(feature_dim=2, seq_len=16, patch_len=4, stride=2, d_model=32)
    assert isinstance(pipeline, IImputerPipeline)

    agent = ImputerAgent(pipeline=pipeline, feature_dim=2, seq_len=16)
    assert isinstance(agent, IAgent)

    # Sequence with NaNs
    seq = np.random.randn(32, 2).astype(np.float32)
    seq[5:10, 0] = np.nan
    reconstructed = agent.impute(seq)

    assert not np.isnan(reconstructed).any()
    assert reconstructed.shape == (32, 2)


def test_corrector_pure_orchestrator_and_pipeline():
    """Verifies CorrectorAgent facade delegation and standalone CorrectorPipeline execution."""
    pipeline = CorrectorPipeline(input_dim=1, hidden_dim=16, latent_dim=8, kernel_size=3)
    assert isinstance(pipeline, ICorrectorPipeline)

    agent = CorrectorAgent(pipeline=pipeline, input_dim=1)
    assert isinstance(agent, IAgent)

    batch_data = np.random.randn(8, 10).astype(np.float32)
    denoised = agent.inference(batch_data)
    assert denoised.shape == (8, 10)

    loss = agent.train_step(batch_data)
    assert isinstance(loss, float)


def test_specialist_pure_orchestrator_and_pipeline():
    """Verifies SpecialistAgent facade delegation and standalone SpecialistPipeline execution."""
    pipeline = SpecialistPipeline(input_dim=1, output_dim=16, num_channels=[8, 16])
    assert isinstance(pipeline, ISpecialistPipeline)

    agent = SpecialistAgent(pipeline=pipeline, input_dim=1, output_dim=16)
    assert isinstance(agent, IAgent)

    input_history = np.random.randn(30, 1).astype(np.float32)
    embedding = agent.predict(input_history)
    assert embedding.shape == (16,)

    loss = agent.train_step((torch.randn(4, 30, 1), torch.randn(4, 16)))
    assert isinstance(loss, float)


def test_coordinator_pure_orchestrator_and_pipeline():
    """Verifies CoordinatorAgent facade delegation and standalone CoordinatorPipeline execution."""
    pipeline = CoordinatorPipeline(in_channels=16, hidden_channels=16, out_channels=16)
    assert isinstance(pipeline, ICoordinatorPipeline)

    agent = CoordinatorAgent(pipeline=pipeline, in_channels=16, hidden_channels=16, out_channels=16)
    assert isinstance(agent, IAgent)

    num_nodes = 4
    x = torch.randn(num_nodes, 16)
    edge_index = torch.tensor([[0, 1, 2], [1, 2, 3]], dtype=torch.long)
    agent.set_topology(edge_index)

    out = agent.forward_pass(x)
    assert out.shape == (num_nodes, 16)


def test_agent_factory_pure_orchestrator_assembly():
    """Verifies AgentFactory builds correctly wired agents with dependency injection."""
    config = {
        "auditor": {"input_len": 32, "J": 2, "latent_dim": 16},
        "imputer": {"seq_len": 16, "patch_len": 4, "stride": 2, "d_model": 32},
        "corrector": {"hidden_dim": 16, "latent_dim": 8},
        "specialist": {"num_levels": 2, "base_channel": 16},
        "coordinator": {"hidden_channels": 16, "heads": 2}
    }

    auditor = AgentFactory.create_auditor(config, input_len=32)
    imputer = AgentFactory.create_imputer(config, feature_dim=2)
    corrector = AgentFactory.create_corrector(config, input_dim=1)
    specialist = AgentFactory.create_specialist(config, input_dim=1, output_dim=16)
    coordinator = AgentFactory.create_coordinator(config, input_dim=16, hidden_dim=16, output_dim=16)

    assert isinstance(auditor, AuditorAgent)
    assert isinstance(imputer, ImputerAgent)
    assert isinstance(corrector, CorrectorAgent)
    assert isinstance(specialist, SpecialistAgent)
    assert isinstance(coordinator, CoordinatorAgent)
