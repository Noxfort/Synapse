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
# File: src/memory/spatiotemporal_memory.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
import numpy as np
from collections import deque
from typing import Dict, List, Optional, Union, Tuple


class SpatioTemporalMemory:
    """
    Spatio-Temporal Continuous State Buffer.
    
    Synchronizes temporal time series across all spatial nodes in a traffic network.
    
    Features:
    - Maintains a sliding temporal window of length `max_len` for every node.
    - Generates 3D/4D PyTorch Tensors: [Batch, Num_Nodes, Seq_Len, Features] or [Num_Nodes, Seq_Len, Features].
    - Computes observability masks [Num_Nodes] for selective sensor masking (anchoring ground truth vs virtual nodes).
    - Supports node-level updates, batch updates, and physical rollbacks.
    """

    def __init__(
        self,
        node_ids: List[str],
        feature_dim: int,
        max_len: int = 60,
        device: Optional[torch.device] = None
    ):
        """
        Args:
            node_ids: List of unique node identifiers (intersections/edges).
            feature_dim: Dimension of features per node per timestep (e.g. 1 for flow, 3 for flow/speed/density).
            max_len: Sliding window capacity (sequence length).
            device: Default compute device for tensor export.
        """
        self.node_ids = list(node_ids)
        self.feature_dim = feature_dim
        self.max_len = max_len
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.id_to_idx: Dict[str, int] = {nid: i for i, nid in enumerate(self.node_ids)}
        self.num_nodes: int = len(self.node_ids)
        
        # Per-node temporal buffers
        self.buffers: Dict[str, deque] = {
            nid: deque(maxlen=max_len) for nid in self.node_ids
        }
        
        # Track last update timestamp/step to determine active observability
        self.active_status: Dict[str, bool] = {nid: False for nid in self.node_ids}

    def update_node(self, node_id: str, features: Union[List[float], np.ndarray, float]) -> bool:
        """
        Pushes a new timestep for a specific node.
        """
        if node_id not in self.id_to_idx:
            return False

        if isinstance(features, (int, float)):
            clean_feats = [float(features)]
        elif isinstance(features, np.ndarray):
            clean_feats = features.flatten().tolist()
        elif isinstance(features, list):
            clean_feats = [float(f) for f in features]
        else:
            clean_feats = [0.0] * self.feature_dim

        # Ensure correct dimension
        if len(clean_feats) < self.feature_dim:
            clean_feats += [0.0] * (self.feature_dim - len(clean_feats))
        elif len(clean_feats) > self.feature_dim:
            clean_feats = clean_feats[:self.feature_dim]

        self.buffers[node_id].append(clean_feats)
        self.active_status[node_id] = True
        return True

    def update_all(self, state_matrix: Union[np.ndarray, torch.Tensor]) -> None:
        """
        Pushes a single timestep simultaneously for all nodes.
        
        Args:
            state_matrix: Array/Tensor of shape [Num_Nodes, Features]
        """
        if isinstance(state_matrix, torch.Tensor):
            state_matrix = state_matrix.detach().cpu().numpy()
            
        for nid, idx in self.id_to_idx.items():
            if idx < state_matrix.shape[0]:
                self.update_node(nid, state_matrix[idx])

    def is_warmed_up(self, min_fraction: float = 1.0) -> bool:
        """
        Checks whether at least `min_fraction` of nodes have reached the full `max_len` window.
        """
        if not self.node_ids:
            return False
        warmed = sum(1 for b in self.buffers.values() if len(b) >= self.max_len)
        return (warmed / self.num_nodes) >= min_fraction

    def get_observability_mask(self, device: Optional[torch.device] = None) -> torch.Tensor:
        """
        Generates a binary observability mask tensor: [Num_Nodes]
        (1.0 = Observed Ground Truth Sensor, 0.0 = Unobserved / Stale Virtual Node).
        """
        target_device = device or self.device
        mask = [1.0 if self.active_status.get(nid, False) and len(self.buffers[nid]) > 0 else 0.0 for nid in self.node_ids]
        return torch.tensor(mask, dtype=torch.float32, device=target_device)

    def get_tensor(self, batch_first: bool = True, device: Optional[torch.device] = None) -> torch.Tensor:
        """
        Assembles and returns the full Spatio-Temporal Tensor.
        
        Returns:
            tensor: [Batch=1, Num_Nodes, Seq_Len, Features] if batch_first else [Num_Nodes, Seq_Len, Features]
        """
        target_device = device or self.device
        matrix = np.zeros((self.num_nodes, self.max_len, self.feature_dim), dtype=np.float32)
        
        for nid, idx in self.id_to_idx.items():
            buf = self.buffers[nid]
            if len(buf) > 0:
                buf_array = np.array(buf, dtype=np.float32)
                # Align to right (latest timesteps)
                matrix[idx, -len(buf):, :] = buf_array
                
        tensor = torch.tensor(matrix, dtype=torch.float32, device=target_device)
        if batch_first:
            return tensor.unsqueeze(0)
        return tensor

    def get_spatial_snapshot(self, device: Optional[torch.device] = None) -> torch.Tensor:
        """
        Returns the most recent spatial snapshot across all nodes: [Num_Nodes, Features].
        """
        target_device = device or self.device
        snapshot = np.zeros((self.num_nodes, self.feature_dim), dtype=np.float32)
        
        for nid, idx in self.id_to_idx.items():
            buf = self.buffers[nid]
            if len(buf) > 0:
                snapshot[idx] = np.array(buf[-1], dtype=np.float32)
                
        return torch.tensor(snapshot, dtype=torch.float32, device=target_device)

    def get_temporal_series(self, node_id: str) -> Optional[np.ndarray]:
        """
        Returns the temporal sequence for a specific node: [Current_Len, Features].
        """
        if node_id not in self.buffers or len(self.buffers[node_id]) == 0:
            return None
        return np.array(self.buffers[node_id], dtype=np.float32)

    def rollback(self, steps: int) -> None:
        """
        Rolls back the last N steps across all node buffers for error recovery.
        """
        for buf in self.buffers.values():
            for _ in range(min(steps, len(buf))):
                buf.pop()

    def clear(self) -> None:
        """Resets all node buffers and active states."""
        for buf in self.buffers.values():
            buf.clear()
        for nid in self.node_ids:
            self.active_status[nid] = False
