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
# File: src/agents/base_agent.py
# Author: Gabriel Moraes
# Date: 2025-12-25

import torch
import torch.nn as nn
from abc import ABC, abstractmethod
from typing import Any

# Import Interface for type checking compliance
from src.interfaces.agents import IAgent
from src.utils.logging_setup import get_logger

logger = get_logger("BaseAgent")

# FIX V3: BaseAgent agora herda de nn.Module.
# Isso unifica a interface de 'to()', 'cuda()', 'cpu()', 'state_dict()'
# e resolve conflitos de MRO (Method Resolution Order) e dispositivos.
class BaseAgent(nn.Module, ABC, IAgent):
    """
    Abstract Base Class for Neural Inference Agents in SYNAPSE.
    
    SOLID Architecture (Segregated Interfaces & Liskov Compliance):
    - [SRP] Manages device movement (CPU/GPU) and forward inference contract.
    - [LSP] Inference-only agents (e.g. LLM Jurist) do not require artificial training stubs.
    - [ISP] Base interface enforces only inference; training contract is extended by BaseTrainableAgent.
    - [DIP] Supports both Inheritance (self is model) and Composition (self has model).
    """

    def __init__(self, model: nn.Module = None, name: str = "UnknownAgent"):
        # Inicializa o nn.Module primeiro (Crucial para registro de parâmetros)
        super().__init__()
        
        self.name = name
        self.device = torch.device("cpu")
        
        # Gestão de Modelo (Herança vs Composição)
        # Se um modelo externo for passado e não for nós mesmos, armazenamos.
        if model is not None and model is not self:
            self._external_model = model
            # Registra como submódulo para que .to() funcione automaticamente
            self.add_module("_external_model_ref", model)
        else:
            self._external_model = None

    @property
    def model(self) -> nn.Module:
        """
        Retorna o modelo ativo.
        """
        if self._external_model:
            return self._external_model
        return self

    def to(self, *args, **kwargs):
        """
        Sobrescreve .to() nativo do PyTorch para garantir que 'self.device' 
        seja atualizado em cascata tanto para herança quanto para composição.
        """
        # Extrai o device do args/kwargs se presente
        device = None
        for arg in args:
            if isinstance(arg, (torch.device, str)):
                device = torch.device(arg)
                break
        if "device" in kwargs:
            device = torch.device(kwargs["device"])
            
        if device is not None:
            self.device = device
        
        # 1. Move a própria estrutura (nn.Module base)
        super().to(*args, **kwargs)
        
        # 2. Se houver composição (modelo externo), move ele também
        if self._external_model:
            self._external_model.to(*args, **kwargs)
            
        return self

    def load_weights(self, path: str):
        """Standard interface for loading model state."""
        try:
            # Carrega no dispositivo configurado
            checkpoint = torch.load(path, map_location=self.device)
            self.model.load_state_dict(checkpoint)
        except Exception:
            # Otimização: Evitar print excessivo em loops de optuna
            pass

    def save_weights(self, path: str):
        """Standard interface for saving model state."""
        try:
            torch.save(self.model.state_dict(), path)
        except Exception as e:
            logger.error(f"[{self.name}] Failed to save weights: {e}")

    @abstractmethod
    def inference(self, input_data: Any) -> Any:
        """Primary inference method."""
        pass
    
    def train_step(self, batch_data: Any) -> float:
        """
        Optional training step returning loss.
        Default implementation for inference-only agents returns 0.0 (LSP-safe).
        """
        return 0.0


class BaseTrainableAgent(BaseAgent):
    """
    Contract for Neural Agents that execute self-contained local optimization steps.
    """
    @abstractmethod
    def train_step(self, batch_data: Any) -> float:
        """Single training step returning loss."""
        pass
