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
# File: src/services/fuser_trainer.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
import torch.nn as nn
import torch.optim as optim
from typing import Optional, Any
from torch.amp import autocast, GradScaler
from src.domain.interfaces import IFuserTrainer
from src.utils.convergence_tracker import MarginalConvergenceTracker


class FuserTrainer(IFuserTrainer):
    """
    Dedicated training service for the Fuser neural pipeline.
    
    Adheres to Single Responsibility Principle (SRP):
    - Encapsulates optimizer, gradient scaling, and physics loss balancing.
    - Manages training loops, batch iterations, and early stopping convergence.
    """

    def __init__(
        self,
        composite_model: nn.Module,
        learning_rate: float = 0.0001,
        spatial_dim: int = 32,
        physics_weight: float = 0.05,
        optimizer: Optional[optim.Optimizer] = None,
        criterion: Optional[nn.Module] = None
    ):
        self.model = composite_model
        self.spatial_dim = spatial_dim
        self.physics_weight = physics_weight
        
        self.optimizer = optimizer or optim.Adam(self.model.parameters(), lr=learning_rate)
        self.scaler = GradScaler('cuda' if torch.cuda.is_available() else 'cpu')
        self.criterion = criterion or nn.MSELoss()

    def _get_current_device(self) -> torch.device:
        """Introspects the model to find its actual physical device."""
        try:
            return next(self.model.parameters()).device
        except StopIteration:
            return torch.device("cpu")

    def train_step(self, batch_data: Any, cached_edge_index: Optional[torch.Tensor] = None) -> float:
        """
        Unified training step optimizing iTransformer, Diffusion, and PINN physics loss.
        """
        self.model.train()
        device = self._get_current_device()
        
        # Unpack inputs
        if isinstance(batch_data, (tuple, list)):
            inputs = batch_data[0].to(device)
            targets = batch_data[1].to(device)
            edge_index = batch_data[2].to(device) if len(batch_data) > 2 else cached_edge_index
        else:
            inputs, targets = batch_data, batch_data
            inputs = inputs.to(device)
            targets = targets.to(device)
            edge_index = cached_edge_index
            
        if edge_index is None:
            edge_index = torch.empty((2, 0), dtype=torch.long, device=device)
        else:
            edge_index = edge_index.to(device)
            
        self.optimizer.zero_grad()
        device_type = device.type if device.type != 'mps' else 'cpu'
        
        diffusion = self.model["diffusion"] if isinstance(self.model, nn.ModuleDict) else getattr(self.model, "diffusion")
        pinn = self.model["pinn"] if isinstance(self.model, nn.ModuleDict) else getattr(self.model, "pinn")
        itransformer = self.model["itransformer"] if isinstance(self.model, nn.ModuleDict) else getattr(self.model, "itransformer")

        with autocast(device_type=device_type, enabled=(device.type == 'cuda')):
            # Forward through diffusion
            batch_size, seq_len, num_nodes = inputs.shape
            dummy_spatial = torch.zeros((batch_size, num_nodes, self.spatial_dim), device=device)
            
            diff_spatial, _ = diffusion(dummy_spatial, edge_index)
            refined_spatial, metrics = pinn(diff_spatial, edge_index)
            
            # Forward through iTransformer
            outputs = itransformer(inputs, spatial_context=refined_spatial)
            
            # Shape alignment
            batch_size, pred_len, num_variates = outputs.shape
            if targets.dim() == 2: 
                targets = targets.view(batch_size, 1, num_variates)
            elif targets.dim() == 3 and targets.size(1) != pred_len:
                targets = targets[:, -pred_len:, :]
                
            loss_mse = self.criterion(outputs, targets)
            loss_physics = metrics.get("physics_residual", 0.0)
            
            # Combined Loss (Data fidelity + Physical consistency)
            total_loss = loss_mse + self.physics_weight * loss_physics

        self.scaler.scale(total_loss).backward()
        self.scaler.step(self.optimizer)
        self.scaler.update()
        
        return total_loss.item()

    def train(
        self,
        inputs: torch.Tensor,
        targets: torch.Tensor,
        epochs: int = 100,
        batch_size: int = 16,
        cached_edge_index: Optional[torch.Tensor] = None,
        tracker: Optional[MarginalConvergenceTracker] = None,
        use_dynamic_convergence: bool = True
    ) -> float:
        """
        Executes complete training epochs with dynamic convergence tracking.
        """
        dataset_size = inputs.size(0)
        
        if tracker is None and use_dynamic_convergence:
            tracker = MarginalConvergenceTracker(
                min_epochs=5,
                max_epochs=epochs,
                patience=4,
                min_delta=1e-4,
                restore_best_weights=True
            )

        max_loops = tracker.max_epochs if tracker else epochs
        target_model = self.model["itransformer"] if isinstance(self.model, nn.ModuleDict) and "itransformer" in self.model else self.model

        last_avg_loss = 0.0
        for epoch in range(max_loops):
            epoch_loss = 0.0
            permutation = torch.randperm(dataset_size)
            
            for i in range(0, dataset_size, batch_size):
                indices = permutation[i : i + batch_size]
                batch_x = inputs[indices]
                batch_y = targets[indices]
                
                loss = self.train_step((batch_x, batch_y), cached_edge_index=cached_edge_index)
                epoch_loss += loss
            
            avg_loss = epoch_loss / max(1, (dataset_size // batch_size))
            last_avg_loss = avg_loss
            
            if (epoch + 1) % 5 == 0 or epoch == 0:
                print(f"[FuserTrainer] Epoch [{epoch+1}] Total Loss: {avg_loss:.4f}")
            
            if tracker and tracker.step(epoch, avg_loss, model=target_model):
                print(f"[FuserTrainer] 🛑 Converged at epoch {epoch+1} ({tracker.stop_reason}) | Best Loss: {tracker.best_loss:.4f}")
                break

        return last_avg_loss
