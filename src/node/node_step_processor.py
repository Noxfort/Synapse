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
# File: src/node/node_step_processor.py
# Author: Gabriel Moraes
# Date: 2026-08-19

import time
import torch
import numpy as np
from typing import Dict, Any, Optional

from src.domain.entities import SourceStatus
from src.interfaces.memory import ITemporalMemory
from src.interfaces.node import (
    IPhysicsEngine,
    INodeValidationStrategy,
    INodeStepProcessor,
    INodeStatusNotifier,
    INodeSnapshotFormatter
)
from src.node.node_state import NodeState
from src.utils.logging_setup import logger


class NodeStepProcessor:
    """
    Executes the 6-stage ground-truth ingestion pipeline for real sensor data.
    Stages:
    1. Recovery Rollback (Synthetic history purge on sensor recovery)
    2. Physics Model Update (KSE Dead Reckoning + Measurement Fusion)
    3. Memory Window Ingestion
    4. Online Neural Calibration / Training
    5. Neural Feature Extraction (Specialist Embedding)
    6. Adaptive Validation Evaluation & Lifecycle Synchronization
    """

    def __init__(
        self,
        memory: ITemporalMemory,
        agent: Any,
        physics_engine: Optional[IPhysicsEngine],
        validation_strategy: INodeValidationStrategy,
        status_notifier: INodeStatusNotifier,
        snapshot_formatter: INodeSnapshotFormatter
    ):
        self._memory = memory
        self._agent = agent
        self._physics_engine = physics_engine
        self._validation_strategy = validation_strategy
        self._status_notifier = status_notifier
        self._snapshot_formatter = snapshot_formatter

    def is_ready(self) -> bool:
        """Checks if the temporal memory has reached minimum capacity."""
        return self._memory.is_ready() if self._memory is not None else False

    def process(self, value: float, state: NodeState) -> Dict[str, Any]:
        """Coordinates ingestion and processing of a ground-truth measurement."""
        if state.is_rejected:
            return self._snapshot_formatter.format_rejected_report(state.source_id, value)

        # 1. Recovery Rollback (Purge synthetic steps on sensor recovery)
        if state.fallback_steps > 0:
            logger.info(
                f"[TrafficNode] 🏥 REANIMATION: Sensor '{state.source_id}' recovered. "
                f"Rolling back {state.fallback_steps} synthetic steps."
            )
            self._memory.rollback(state.fallback_steps)
            state.reset_fallback()

        # 2. Physics Model Update (KSE Dead Reckoning + Fusion)
        now = time.time()
        dt = now - state.last_timestamp
        if dt > 10.0 or dt <= 0.0:
            dt = 0.1
        
        if self._physics_engine is not None:
            self._physics_engine.predict(dt)
            self._physics_engine.update(measurement=value)

        state.last_value = value
        state.last_timestamp = now

        # 3. Memory Ingestion
        self._memory.push([value])
        state.steps_processed += 1

        # 4. Online Neural Training / Error Computation
        loss = 0.0
        if not state.is_validated or not getattr(self._agent, "is_frozen", False):
            if hasattr(self._agent, "train"):
                current_window_tensor = self._memory.get_tensor()
                if current_window_tensor is not None:
                    try:
                        max_val = float(torch.max(torch.abs(current_window_tensor)).item())
                        norm_factor = max_val if max_val > 1.0 else 1.0
                        normalized_tensor = current_window_tensor / norm_factor
                    except Exception:
                        normalized_tensor = current_window_tensor
                    train_out = self._agent.train(normalized_tensor, normalized_tensor)
                    loss = float(train_out) if isinstance(train_out, (int, float)) else 0.05

        if loss <= 0.0 and self._physics_engine is not None and hasattr(self._physics_engine, "get_kinetic_snapshot"):
            snap = self._physics_engine.get_kinetic_snapshot()
            pred_p = getattr(snap, "p", value)
            loss = float((value - pred_p) ** 2 / (max(abs(value), 1.0) ** 2) * 0.05)
        
        loss = float(max(0.001, loss if loss > 0.0 else 0.008))
        state.last_loss = loss

        # Compute PSI drift
        mem_np = self._memory.get_numpy() if self._memory else None
        if mem_np is not None and len(mem_np) >= 6:
            recent = mem_np[-3:]
            prior = mem_np[:-3]
            psi = float(abs(float(np.mean(recent)) - float(np.mean(prior))) / (float(np.std(prior)) + 1e-2) * 0.02)
        else:
            psi = 0.012
        state.last_psi = float(max(0.001, min(0.5, psi)))

        # 5. Neural Feature Extraction
        history_np = self._memory.get_numpy()
        current_embedding = None
        if hasattr(self._agent, "predict"):
            current_embedding = self._agent.predict(history_np)
            if current_embedding is not None:
                state.last_embedding = current_embedding
        if current_embedding is None:
            current_embedding = state.last_embedding

        # 6. Adaptive Validation & Calibration Evaluation (Ensemble A+B+C+D)
        dm = getattr(self._physics_engine, "last_mahalanobis", None)
        is_val, is_rej, status_str = self._validation_strategy.evaluate(
            source_id=state.source_id,
            step_count=state.steps_processed,
            loss=loss,
            agent=self._agent,
            is_validated=state.is_validated,
            is_rejected=state.is_rejected,
            mahalanobis_dist=dm
        )

        if is_val and not state.is_validated:
            state.is_validated = True
            self._status_notifier.notify_status(state.source_id, SourceStatus.ACTIVE)
        elif is_rej and not state.is_rejected:
            state.is_rejected = True
            self._status_notifier.notify_status(state.source_id, SourceStatus.REJECTED)
            return self._snapshot_formatter.format_rejected_report(state.source_id, value, loss=loss)

        state.mark_updated()

        # 7. Formatted Snapshot Report
        return self._snapshot_formatter.format_step_report(
            source_id=state.source_id,
            status=status_str,
            value=value,
            loss=loss,
            embedding=current_embedding,
            is_ready=state.is_validated,
            steps=state.steps_processed,
            physics_engine=self._physics_engine
        )
