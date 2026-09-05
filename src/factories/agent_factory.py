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
# File: src/factories/agent_factory.py
# Author: Gabriel Moraes
# Date: 2026-08-17

from typing import Dict, Any, Optional

# Domain Agent Types
from src.agents.specialist_agent import SpecialistAgent
from src.agents.coordinator_agent import CoordinatorAgent
from src.agents.fuser_agent import FuserAgent
from src.agents.imputer_agent import ImputerAgent
from src.agents.corrector_agent import CorrectorAgent
from src.agents.peak_classifier_agent import PeakClassifierAgent
from src.agents.linguist_agent import LinguistAgent
from src.agents.auditor_agent import AuditorAgent
from src.agents.jurist_agent import JuristAgent
from src.agents.compass_agent import CompassAgent

# Dedicated Domain Factories (SOLID / OCP / DIP)
from src.factories.agent_registry import AgentRegistry
from src.factories.auditor_factory import AuditorFactory
from src.factories.imputer_factory import ImputerFactory
from src.factories.corrector_factory import CorrectorFactory
from src.factories.specialist_factory import SpecialistFactory
from src.factories.coordinator_factory import CoordinatorFactory
from src.factories.linguist_factory import LinguistFactory
from src.factories.jurist_factory import JuristFactory
from src.factories.compass_factory import CompassFactory
from src.factories.fuser_model_factory import FuserModelFactory
from src.services.dynamic_sensor_calibrator import DynamicSensorCalibrator


class AgentFactory:
    """
    The Central Agent Fabricator Facade & Abstract Dispatcher.
    
    SOLID Architecture V7:
    - SRP: Acts strictly as a creational dispatcher/facade delegating to specialized domain factories.
    - OCP: Extensible via builder registry without modifying internal neural assembly.
    - DIP: Delegates sensor instance lifecycle to the dedicated AgentRegistry.
    """

    _domain_factories = {
        "auditor": AuditorFactory,
        "imputer": ImputerFactory,
        "corrector": CorrectorFactory,
        "specialist": SpecialistFactory,
        "coordinator": CoordinatorFactory,
        "linguist": LinguistFactory,
        "jurist": JuristFactory,
        "compass": CompassFactory,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None, registry: Optional[AgentRegistry] = None):
        """
        Args:
            config: Global system configuration dict.
            registry: Optional external AgentRegistry (DIP).
        """
        self.config = config or {}
        self.registry = registry or AgentRegistry()

    # --- Registry Delegations (Stateful / Lifecycle) ---

    def get_or_create_linguist(self, source_id: str) -> LinguistAgent:
        """Retrieves or creates LinguistAgent for a sensor source."""
        agent = self.registry.get(source_id, 'linguist')
        if agent is None:
            agent = self.create_linguist(self.config)
            self.registry.register(source_id, 'linguist', agent)
        return agent

    def release_linguist(self, source_id: str) -> None:
        """
        Explicitly deactivates and unregisters the ephemeral LinguistAgent for a sensor source,
        freeing GPU/RAM resources immediately after onboarding/teaching.
        """
        self.registry.remove(source_id, 'linguist')

    def get_or_create_compass(self, source_id: str) -> CompassAgent:
        """Retrieves or creates CompassAgent for a sensor source."""
        agent = self.registry.get(source_id, 'compass')
        if agent is None:
            agent = self.create_compass(self.config)
            self.registry.register(source_id, 'compass', agent)
        return agent

    def release_compass(self, source_id: str) -> None:
        """
        Explicitly deactivates and unregisters the ephemeral CompassAgent for a sensor source,
        freeing GPU/RAM resources immediately after directional reconciliation.
        """
        self.registry.remove(source_id, 'compass')

    def get_or_create_specialist(self, source_id: str) -> SpecialistAgent:
        """Retrieves or creates SpecialistAgent for a sensor source."""
        agent = self.registry.get(source_id, 'specialist')
        if agent is None:
            p_spec = self.config.get('specialist', {})
            input_dim = p_spec.get('input_dim', 1)
            output_dim = p_spec.get('output_dim', 1)
            agent = self.create_specialist(self.config, input_dim=input_dim, output_dim=output_dim)
            self.registry.register(source_id, 'specialist', agent)
        return agent

    def get_or_create_auditor(self, source_id: str) -> AuditorAgent:
        """Retrieves or creates AuditorAgent for a sensor source."""
        agent = self.registry.get(source_id, 'auditor')
        if agent is None:
            p_aud = self.config.get('auditor', {})
            input_len = p_aud.get('input_len', 60)
            agent = self.create_auditor(self.config, input_len=input_len)
            self.registry.register(source_id, 'auditor', agent)
        return agent

    def get_or_create_jurist(self, source_id: str) -> JuristAgent:
        """Retrieves or creates JuristAgent for a sensor source."""
        agent = self.registry.get(source_id, 'jurist')
        if agent is None:
            agent = self.create_jurist(self.config)
            self.registry.register(source_id, 'jurist', agent)
        return agent

    # --- Static Creational Dispatchers (Stateless) ---

    @classmethod
    def create(cls, agent_type: str, config: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
        """Generic Creational Dispatcher (OCP)."""
        cfg = config or {}
        key = agent_type.lower()
        factory = cls._domain_factories.get(key)
        if factory:
            return factory.create(config=cfg, **kwargs)
        if key == "fuser":
            return cls.create_fuser(cfg, **kwargs)
        if key in ("classifier", "peak_classifier"):
            return cls.create_classifier(cfg, **kwargs)
        raise ValueError(f"[AgentFactory] Unknown agent type: '{agent_type}'")

    @staticmethod
    def create_specialist(config: Dict[str, Any], input_dim: int = 1, output_dim: int = 32, **kwargs: Any) -> SpecialistAgent:
        return SpecialistFactory.create(config=config, input_dim=input_dim, output_dim=output_dim, **kwargs)

    @staticmethod
    def create_auditor(config: Dict[str, Any], input_len: int = 60, **kwargs: Any) -> AuditorAgent:
        return AuditorFactory.create(config=config, input_len=input_len, **kwargs)

    @staticmethod
    def create_imputer(config: Dict[str, Any], feature_dim: int = 4, **kwargs: Any) -> ImputerAgent:
        return ImputerFactory.create(config=config, feature_dim=feature_dim, **kwargs)

    @staticmethod
    def create_corrector(config: Dict[str, Any], input_dim: int = 1, **kwargs: Any) -> CorrectorAgent:
        return CorrectorFactory.create(config=config, input_dim=input_dim, **kwargs)

    @staticmethod
    def create_coordinator(config: Dict[str, Any], input_dim: int = 32, hidden_dim: int = 32, output_dim: int = 32, **kwargs: Any) -> CoordinatorAgent:
        return CoordinatorFactory.create(config=config, input_dim=input_dim, hidden_dim=hidden_dim, output_dim=output_dim, **kwargs)

    @staticmethod
    def create_linguist(config: Dict[str, Any], **kwargs: Any) -> LinguistAgent:
        return LinguistFactory.create(config=config, **kwargs)

    @staticmethod
    def create_jurist(config: Dict[str, Any], **kwargs: Any) -> JuristAgent:
        return JuristFactory.create(config=config, **kwargs)

    @staticmethod
    def create_compass(config: Dict[str, Any], **kwargs: Any) -> CompassAgent:
        return CompassFactory.create(config=config, **kwargs)

    @staticmethod
    def create_fuser(config: Dict[str, Any], num_variates: int = 10, seq_len: int = 60, pred_len: int = 1, **kwargs: Any) -> FuserAgent:
        p_fuser = config.get('fuser', {})
        d_model = p_fuser.get('d_model', 512)
        n_heads = p_fuser.get('n_heads', 8)
        layers = p_fuser.get('layers', 2)
        spatial_dim = p_fuser.get('spatial_dim', 32)

        pipeline = FuserModelFactory.create_fusion_pipeline(
            num_variates=num_variates,
            seq_len=seq_len,
            pred_len=pred_len,
            d_model=d_model,
            n_heads=n_heads,
            layers=layers,
            spatial_dim=spatial_dim
        )
        calibrator = DynamicSensorCalibrator(num_variates=num_variates)

        return FuserAgent(
            pipeline=pipeline,
            calibrator=calibrator,
            num_variates=num_variates,
            seq_len=seq_len,
            pred_len=pred_len
        )

    @staticmethod
    def create_classifier(config: Dict[str, Any], output_path: str = "peak_schedule.json", **kwargs: Any) -> PeakClassifierAgent:
        p_clf = config.get('classifier', {})
        itransformer_cfg = p_clf.get('itransformer', {
            'num_variates': kwargs.get('input_dim', 2),
            'd_model': p_clf.get('d_model', 32),
            'n_heads': p_clf.get('n_heads', 2)
        })
        timesnet_cfg = p_clf.get('timesnet', {
            'enc_in': p_clf.get('enc_in', 1),
            'c_out': p_clf.get('c_out', 1),
            'learning_rate': p_clf.get('lr', 1e-3)
        })
        return PeakClassifierAgent(
            itransformer_config=itransformer_cfg,
            timesnet_config=timesnet_cfg,
            output_path=output_path
        )
