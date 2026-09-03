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
# File: src/node/node_state.py
# Author: Gabriel Moraes
# Date: 2026-08-19

import time
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class NodeState:
    """
    Encapsulates all mutable runtime state and metadata of a Traffic Node.
    Follows Single Responsibility Principle (SRP) by decoupling state tracking from execution pipelines.
    """
    source_id: str
    last_value: float = 0.0
    last_loss: float = 0.008
    last_psi: float = 0.012
    last_timestamp: float = field(default_factory=time.time)
    last_embedding: np.ndarray = field(default_factory=lambda: np.zeros(32))
    steps_processed: int = 0
    fallback_steps: int = 0
    updated_this_cycle: bool = False
    is_validated: bool = False
    is_rejected: bool = False

    def mark_updated(self) -> None:
        """Flags that this node received or processed a sensor reading in the current cycle."""
        self.updated_this_cycle = True

    def reset_cycle(self) -> None:
        """Resets the cycle update flag at the end of a cycle tick."""
        self.updated_this_cycle = False

    def increment_fallback(self) -> None:
        """Increments the count of consecutive synthetic fallback steps."""
        self.fallback_steps += 1

    def reset_fallback(self) -> None:
        """Resets the synthetic fallback step counter upon sensor recovery."""
        self.fallback_steps = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serializes internal state for checkpointing and telemetry."""
        return {
            "source_id": self.source_id,
            "last_value": self.last_value,
            "last_timestamp": self.last_timestamp,
            "steps_processed": self.steps_processed,
            "fallback_steps": self.fallback_steps,
            "is_validated": self.is_validated,
            "is_rejected": self.is_rejected
        }

    def from_dict(self, state_dict: Dict[str, Any]) -> None:
        """Restores state attributes from a dictionary checkpoint."""
        if not isinstance(state_dict, dict):
            return
        self.steps_processed = state_dict.get("steps_processed", self.steps_processed)
        self.fallback_steps = state_dict.get("fallback_steps", self.fallback_steps)
        self.is_validated = state_dict.get("is_validated", self.is_validated)
        self.is_rejected = state_dict.get("is_rejected", self.is_rejected)
        self.last_value = state_dict.get("last_value", self.last_value)
        self.last_timestamp = state_dict.get("last_timestamp", self.last_timestamp)
