# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# File: tests/unit/test_domain_factories.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import pytest
import torch

from src.factories.agent_registry import AgentRegistry
from src.factories.auditor_factory import AuditorFactory
from src.factories.imputer_factory import ImputerFactory
from src.factories.corrector_factory import CorrectorFactory
from src.factories.specialist_factory import SpecialistFactory
from src.factories.coordinator_factory import CoordinatorFactory
from src.factories.linguist_factory import LinguistFactory
from src.factories.jurist_factory import JuristFactory
from src.factories.agent_factory import AgentFactory

from src.agents.auditor_agent import AuditorAgent
from src.agents.imputer_agent import ImputerAgent
from src.agents.corrector_agent import CorrectorAgent
from src.agents.specialist_agent import SpecialistAgent
from src.agents.coordinator_agent import CoordinatorAgent
from src.agents.linguist_agent import LinguistAgent
from src.agents.jurist_agent import JuristAgent


def test_agent_registry_lifecycle():
    """Verifies that AgentRegistry stores, retrieves, checks, and removes agent instances correctly."""
    registry = AgentRegistry()
    assert registry.get("sensor_1", "auditor") is None
    assert registry.has("sensor_1", "auditor") is False

    mock_agent = "MockAuditorInstance"
    registry.register("sensor_1", "auditor", mock_agent)

    assert registry.has("sensor_1", "auditor") is True
    assert registry.get("sensor_1", "auditor") == mock_agent

    registry.remove("sensor_1", "auditor")
    assert registry.has("sensor_1", "auditor") is False
    assert registry.get("sensor_1", "auditor") is None


def test_individual_domain_factories():
    """Verifies that each dedicated domain factory builds the respective agent properly."""
    config = {
        "auditor": {"input_len": 32, "J": 2, "latent_dim": 16},
        "imputer": {"seq_len": 16, "patch_len": 4, "stride": 2, "d_model": 32},
        "corrector": {"hidden_dim": 16, "latent_dim": 8},
        "specialist": {"num_levels": 2, "base_channel": 16},
        "coordinator": {"hidden_channels": 16, "heads": 2},
        "jurist": {"model_id": "dummy_model_id"}
    }

    auditor = AuditorFactory.create(config, input_len=32)
    assert isinstance(auditor, AuditorAgent)
    assert auditor.pipeline is not None
    assert auditor.trainer is not None

    imputer = ImputerFactory.create(config, feature_dim=2)
    assert isinstance(imputer, ImputerAgent)
    assert imputer.pipeline is not None

    corrector = CorrectorFactory.create(config, input_dim=1)
    assert isinstance(corrector, CorrectorAgent)
    assert corrector.pipeline is not None

    specialist = SpecialistFactory.create(config, input_dim=1, output_dim=16)
    assert isinstance(specialist, SpecialistAgent)
    assert specialist.pipeline is not None

    coordinator = CoordinatorFactory.create(config, input_dim=16, hidden_dim=16, output_dim=16)
    assert isinstance(coordinator, CoordinatorAgent)
    assert coordinator.pipeline is not None

    jurist = JuristFactory.create(config)
    assert isinstance(jurist, JuristAgent)


def test_agent_factory_generic_dispatcher():
    """Verifies that AgentFactory.create() acts as an extensible dispatcher (OCP)."""
    config = {"auditor": {"input_len": 32, "J": 2, "latent_dim": 16}}
    agent = AgentFactory.create("auditor", config=config, input_len=32)
    assert isinstance(agent, AuditorAgent)


def test_agent_factory_stateful_caching_via_registry():
    """Verifies that AgentFactory get_or_create methods use AgentRegistry properly."""
    factory = AgentFactory(config={"auditor": {"input_len": 32, "J": 2, "latent_dim": 16}})
    
    agent1 = factory.get_or_create_auditor("cam_01")
    assert isinstance(agent1, AuditorAgent)

    # Calling again should retrieve the exact same instance from registry
    agent2 = factory.get_or_create_auditor("cam_01")
    assert agent1 is agent2
