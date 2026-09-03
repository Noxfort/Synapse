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
# File: src/interfaces/quarantine.py
# Author: Gabriel Moraes
# Date: 2026-08-19

from typing import Any, List, Tuple, Protocol, runtime_checkable
import numpy as np


@runtime_checkable
class ISeriesExtractorPipeline(Protocol):
    """Contract for extracting and sanitizing 1D numeric time-series from raw sensor payloads."""
    def extract(self, data_chunk: List[Any]) -> np.ndarray:
        """Parses a chunk of raw heterogeneous data items into a 1D float32 NumPy array."""
        ...


@runtime_checkable
class ISemanticClassifier(Protocol):
    """Contract for inferring traffic semantic types, engineering units, and confidence scores."""
    def classify(self, source: Any, data_np: np.ndarray, data_chunk: List[Any]) -> Tuple[str, str, float]:
        """Returns a tuple containing (semantic_type, unit, confidence_score)."""
        ...


@runtime_checkable
class ISensorPhysicsValidator(Protocol):
    """Contract for verifying symbolic traffic invariants and Neuro-PINN physical consistency."""
    def validate(self, source: Any, data_np: np.ndarray, data_chunk: List[Any], agent: Any) -> bool:
        """Returns True if the sensor data complies with all physical laws and PINN thresholds."""
        ...


@runtime_checkable
class IKnowledgeTransfer(Protocol):
    """Contract for transferring neural representations (encoders/weights) between agents."""
    def transfer(self, source_agent: Any, target_agent: Any) -> bool:
        """Transfers learned feature representation from source agent to target agent."""
        ...


__all__ = [
    "ISeriesExtractorPipeline",
    "ISemanticClassifier",
    "ISensorPhysicsValidator",
    "IKnowledgeTransfer"
]
