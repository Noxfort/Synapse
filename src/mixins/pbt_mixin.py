# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# File: src/agents/mixins/pbt_mixin.py
# Author: Gabriel Moraes
# Date: 2026-04-26

import numpy as np
import torch.nn as nn
from typing import Dict, Any


class PBTMixin:
    """
    Single Responsibility: Population-Based Training primitives.
    
    Provides copy_from(), mutate(), get_state(), and set_state()
    for agents that participate in PBT optimization.
    
    Requirements on the host class:
    - self.model: nn.Module (or ModuleDict)
    - self.optimizer: torch.optim.Optimizer
    - self.learning_rate: float
    - self.dropout: float
    """

    def copy_from(self, other_agent: 'PBTMixin'):
        """Exploit Step: Copy weights and hyperparams from a better agent."""
        self.model.load_state_dict(other_agent.model.state_dict())
        self.learning_rate = other_agent.learning_rate
        self.dropout = other_agent.dropout

        for param_group in self.optimizer.param_groups:
            param_group['lr'] = self.learning_rate

        self.running_loss = 0.0
        self.steps = 0

    def mutate(self):
        """Explore Step: Randomly perturbate hyperparameters."""
        factor = np.random.choice([0.8, 1.2])
        self.learning_rate *= factor

        self.dropout += np.random.normal(0, 0.05)
        self.dropout = np.clip(self.dropout, 0.0, 0.5)

        for param_group in self.optimizer.param_groups:
            param_group['lr'] = self.learning_rate

        self._update_dropout_layers()

    def _update_dropout_layers(self):
        """Updates all dropout layers in the model to the current rate."""
        for m in self.model.modules():
            if isinstance(m, (nn.Dropout, nn.Dropout1d, nn.Dropout2d)):
                m.p = self.dropout

    def get_pbt_state(self) -> Dict[str, Any]:
        """Exports PBT-relevant state for checkpointing."""
        return {
            "agent_config": {
                "lr": self.learning_rate,
                "dropout": self.dropout
            }
        }

    def set_pbt_state(self, state: Dict[str, Any]):
        """Restores PBT-relevant state from checkpoint."""
        conf = state.get("agent_config", {})
        self.learning_rate = conf.get("lr", 0.001)
        self.dropout = conf.get("dropout", 0.2)

        for param_group in self.optimizer.param_groups:
            param_group['lr'] = self.learning_rate
        self._update_dropout_layers()
