# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# File: src/engine/tensor_builder.py

import torch
import numpy as np
import torch.nn.functional as F
from typing import Dict, Any, Tuple

from src.utils.logging_setup import logger
from src.managers.graph_manager import GraphManager

class TensorBuilder:
    """
    Responsible for dynamically extracting and shaping Graph state features into PyTorch Tensors.
    Adheres to the Single Responsibility Principle (SRP) by isolating data casting from Business Logic.
    
    Refactored V3 (Diffusion & PINN Support):
    - Extracts Observability Mask (M in {0, 1}^N) for dynamic anchor calibration.
    - Extracts Global Velocity vectors for macroscopic boundary conditioning.
    """
    
    def __init__(self, device: torch.device, coordinator_model: Any, graph_manager: GraphManager):
        self.device = device
        self.graph_manager = graph_manager
        
        # Determine expected dimension via Introspection (Decoupled from Engine)
        self.expected_dim = self._inspect_dimension(coordinator_model)

    def _inspect_dimension(self, coordinator_model: Any) -> int:
        """Dynamically looks at the GAT model to cast padding constraints."""
        expected_dim = 32  # DEFAULTS TO 32 (TCN Latent Dim)
        try:
            if hasattr(coordinator_model, 'conv1'):
                in_channels = coordinator_model.conv1.in_channels
                if isinstance(in_channels, tuple):
                    expected_dim = in_channels[0]
                elif isinstance(in_channels, int):
                    expected_dim = in_channels
                logger.info(f"[TensorBuilder] Extracted Expected Input Dim = {expected_dim}")
            else:
                logger.warning(f"[TensorBuilder] Unknown Coordinator structure. Using default dim={expected_dim}.")
        except Exception as e:
            logger.warning(f"[TensorBuilder] Dimension inspection failed: {e}. Defaulting to {expected_dim}.")
            
        return expected_dim

    def prepare_tensors(self, snapshot: Dict[str, Any]) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Transforms raw node data into uniformly padded tensors, observability masks, and global velocities safely.
        """
        ordered_ids = self.graph_manager.get_ordered_node_ids()
        
        features_list = []
        history_list = []
        mask_list = []
        global_vel_list = []
        
        for nid in ordered_ids:
            node_data = snapshot.get(nid, {}) if snapshot else {}
            
            # Observability Mask (1.0 = Ground truth live sensor, 0.0 = Virtual/Synthesized node)
            is_real = (node_data.get("type") == "real") or (node_data.get("status") == "Active")
            mask_list.append(1.0 if is_real else 0.0)
            
            # Global Velocity for node
            node_val = node_data.get("value", 0.0)
            global_vel_list.append(float(node_val) if isinstance(node_val, (int, float)) else 0.0)
            
            # Spatial Embedding (X)
            final_emb = torch.zeros(self.expected_dim)
            
            if node_data and "embedding" in node_data:
                emb = node_data["embedding"]
                
                if isinstance(emb, np.ndarray):
                    emb_tensor = torch.from_numpy(emb).float()
                elif isinstance(emb, list):
                    emb_tensor = torch.tensor(emb, dtype=torch.float)
                elif isinstance(emb, torch.Tensor):
                    emb_tensor = emb.float()
                else:
                    emb_tensor = torch.zeros(self.expected_dim)

                if emb_tensor.ndim > 1:
                    emb_tensor = emb_tensor.view(-1)
                
                current_dim = emb_tensor.shape[0]
                
                if current_dim == self.expected_dim:
                    final_emb = emb_tensor
                elif current_dim < self.expected_dim:
                    padding = self.expected_dim - current_dim
                    final_emb = F.pad(emb_tensor, (0, padding), "constant", 0)
                else:
                    final_emb = emb_tensor[:self.expected_dim]
                    
            features_list.append(final_emb)

            # Temporal History
            node_obj = self.graph_manager.get_node(nid)
            if node_obj:
                hist = node_obj.memory.get_numpy().flatten()
                target_len = 60 # Match Fuser seq_len
                if len(hist) < target_len:
                    pad = np.zeros(target_len - len(hist))
                    hist = np.concatenate((pad, hist))
                elif len(hist) > target_len:
                    hist = hist[-target_len:]
                history_list.append(hist)
            else:
                history_list.append(np.zeros(60))

        if not features_list:
            raise ValueError("No data available for tensor construction.")

        x_spatial = torch.stack(features_list).to(self.device) 
        
        if hasattr(self.graph_manager, 'edge_index') and self.graph_manager.edge_index is not None:
            edge_index = self.graph_manager.edge_index.to(self.device)
        else:
            edge_index = torch.empty((2, 0), dtype=torch.long).to(self.device)

        x_temporal_np = np.stack(history_list).T 
        x_temporal = torch.from_numpy(x_temporal_np).float().to(self.device)
        
        observability_mask = torch.tensor(mask_list, dtype=torch.float, device=self.device)
        global_velocities = torch.tensor(global_vel_list, dtype=torch.float, device=self.device)
        
        return x_spatial, edge_index, x_temporal, observability_mask, global_velocities
