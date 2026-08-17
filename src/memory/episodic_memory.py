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
# File: src/memory/episodic_memory.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import time
import torch
import numpy as np
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field


@dataclass
class AnomalyEpisode:
    """Represents a recorded anomaly or physical violation episode."""
    timestamp: float
    sensor_id: str
    signature: np.ndarray
    anomaly_score: float
    physics_residual: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class EpisodicMemory:
    """
    Episodic Replay Buffer for Anomaly and Physics Invariant Violations.
    
    Responsibilities:
    - Stores high-loss edge cases and anomalous traffic episodes.
    - Provides prioritized and uniform mini-batch sampling for experience replay.
    - Tracks hard physical violations for fine-tuning PINN loss weights and calibrating thresholds.
    """

    def __init__(self, capacity: int = 1000, device: Optional[torch.device] = None):
        self.capacity = capacity
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.episodes: List[AnomalyEpisode] = []

    def record_episode(
        self,
        sensor_id: str,
        signature: Union[np.ndarray, torch.Tensor, List[float]],
        anomaly_score: float,
        physics_residual: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Stores a new anomalous episode into memory with FIFO eviction on capacity overflow.
        """
        if isinstance(signature, torch.Tensor):
            sig_array = signature.detach().cpu().numpy().astype(np.float32)
        elif isinstance(signature, list):
            sig_array = np.array(signature, dtype=np.float32)
        else:
            sig_array = np.asarray(signature, dtype=np.float32)

        episode = AnomalyEpisode(
            timestamp=time.time(),
            sensor_id=str(sensor_id),
            signature=sig_array,
            anomaly_score=float(anomaly_score),
            physics_residual=float(physics_residual),
            metadata=metadata or {}
        )

        if len(self.episodes) >= self.capacity:
            self.episodes.pop(0)

        self.episodes.append(episode)

    def sample_batch(
        self,
        batch_size: int,
        device: Optional[torch.device] = None
    ) -> Optional[Tuple[torch.Tensor, torch.Tensor]]:
        """
        Uniformly samples a batch of anomaly signatures and scores for retrain / calibration replay.
        
        Returns:
            signatures: [Batch, Sequence_Len] or [Batch, Channels, Sequence_Len]
            scores: [Batch]
        """
        if not self.episodes:
            return None

        target_device = device or self.device
        actual_size = min(batch_size, len(self.episodes))
        indices = np.random.choice(len(self.episodes), size=actual_size, replace=False)

        selected = [self.episodes[i] for i in indices]
        signatures = np.stack([ep.signature for ep in selected])
        scores = np.array([ep.anomaly_score for ep in selected], dtype=np.float32)

        return (
            torch.tensor(signatures, dtype=torch.float32, device=target_device),
            torch.tensor(scores, dtype=torch.float32, device=target_device)
        )

    def get_hardest_violations(self, top_k: int = 10) -> List[AnomalyEpisode]:
        """
        Returns the top-K episodes with the highest physical continuity / kinematic violation residual.
        """
        sorted_episodes = sorted(self.episodes, key=lambda e: e.physics_residual, reverse=True)
        return sorted_episodes[:top_k]

    def get_recent(self, n: int = 20) -> List[AnomalyEpisode]:
        """Returns the most recent N recorded episodes."""
        return self.episodes[-n:]

    def clear(self) -> None:
        """Clears all recorded episodes."""
        self.episodes.clear()

    def __len__(self) -> int:
        return len(self.episodes)


# Compatibility Alias
AnomalyMemory = EpisodicMemory
