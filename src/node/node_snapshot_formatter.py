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
# File: src/node/node_snapshot_formatter.py
# Author: Gabriel Moraes
# Date: 2026-08-19

from typing import Dict, Any, Optional
from src.interfaces.node import IPhysicsEngine, INodeSnapshotFormatter


class NodeSnapshotFormatter:
    """
    Constructs standardized telemetry, physics diagnostics, and step reports for traffic nodes.
    Follows Single Responsibility Principle (SRP) by isolating DTO / dict formatting.
    """

    @staticmethod
    def _extract_physics_report(physics_engine: Optional[IPhysicsEngine]) -> Dict[str, Any]:
        """Extracts kinetic state variables from the physics engine."""
        if physics_engine is None or not hasattr(physics_engine, "get_kinetic_snapshot"):
            return {}
        
        kse_snapshot = physics_engine.get_kinetic_snapshot()
        if kse_snapshot is None:
            return {}

        return {
            "position": getattr(kse_snapshot, "p", 0.0),
            "velocity": getattr(kse_snapshot, "v", 0.0),
            "acceleration": getattr(kse_snapshot, "a", 0.0),
            "confidence": getattr(kse_snapshot, "confidence", 1.0)
        }

    def format_step_report(
        self,
        source_id: str,
        status: str,
        value: float,
        loss: float,
        embedding: Any,
        is_ready: bool,
        steps: int,
        physics_engine: Optional[IPhysicsEngine] = None
    ) -> Dict[str, Any]:
        """Formats the result dictionary for a successful real-measurement step."""
        return {
            "source_id": source_id,
            "status": status,
            "type": "real",
            "ready": is_ready,
            "loss": loss,
            "embedding": embedding,
            "value": value,
            "physics": self._extract_physics_report(physics_engine),
            "steps": steps
        }

    def format_ghost_report(
        self,
        source_id: str,
        method_used: str,
        value: float,
        embedding: Any,
        fallback_steps: int,
        physics_engine: Optional[IPhysicsEngine] = None
    ) -> Dict[str, Any]:
        """Formats the result dictionary for a synthetic imputation step (sensor dropout)."""
        return {
            "source_id": source_id,
            "status": f"Fallback: {method_used}",
            "type": "synthetic",
            "ready": True,
            "loss": 0.0,
            "embedding": embedding,
            "value": value,
            "physics": self._extract_physics_report(physics_engine),
            "fallback_count": fallback_steps
        }

    def format_rejected_report(
        self,
        source_id: str,
        value: float,
        loss: float = 0.0
    ) -> Dict[str, Any]:
        """Formats the result dictionary for a rejected sensor reading."""
        return {
            "source_id": source_id,
            "status": "Rejected",
            "ready": False,
            "loss": loss,
            "value": value,
            "rejected": True
        }
