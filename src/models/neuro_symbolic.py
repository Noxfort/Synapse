# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Labs
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
# File: src/models/neuro_symbolic.py
# Author: Gabriel Moraes
# Date: 2026-08-17

from typing import Tuple, Dict, Optional, Any, Union
import torch
import torch.nn as nn
from transformers import AutoModel, AutoConfig

# Enable Tensor Cores globally for matrix multiplications and cuDNN operations
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True


class NeuroSymbolicModel(nn.Module):
    """
    Pure Neuro-Symbolic Neural Architecture for the Linguist Agent.
    
    Architecture:
    1. Semantic Backbone: Transformer (DistilRoBERTa) - Extracts language representations.
    2. Neural Reasoner: TCN Autoencoder compressing into bottleneck manifold.
    3. Physics Projection Head: Latent Space -> Physical State Projections [q (flow), v (speed), rho (density)].
    4. Semantic Decoder: Reconstructs original semantic embeddings.
    """

    def __init__(
        self,
        model_name: str = "distilroberta-base",
        freeze_transformer: bool = True,
        latent_dim: int = 64,
        transformer: Optional[nn.Module] = None,
        physics_loss_engine: Optional[Any] = None
    ):
        super(NeuroSymbolicModel, self).__init__()
        
        # 1. Semantic Backbone (Transformer - DIP support)
        if transformer is not None:
            self.transformer = transformer
            self.hidden_size = getattr(transformer.config, "hidden_size", 768)
        else:
            self.config = AutoConfig.from_pretrained(model_name)
            self.hidden_size = self.config.hidden_size
            self.transformer = AutoModel.from_pretrained(model_name)
        
        if freeze_transformer:
            for param in self.transformer.parameters():
                param.requires_grad = False
                
        # Optional Physics Engine reference for backward compatibility
        self.physics_engine = physics_loss_engine

        # 2. Neural Reasoner (TCN Autoencoder)
        self.encoder = nn.Sequential(
            nn.Conv1d(in_channels=self.hidden_size, out_channels=256, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.BatchNorm1d(256),
            nn.Conv1d(in_channels=256, out_channels=latent_dim, kernel_size=3, padding=1),
            nn.ReLU()
        )
        
        # Physics Head: Latent Space -> Physical State Projections [q (flow), v (speed), rho (density)]
        self.physics_head = nn.Sequential(
            nn.Conv1d(in_channels=latent_dim, out_channels=64, kernel_size=1),
            nn.ReLU(),
            nn.Conv1d(in_channels=64, out_channels=3, kernel_size=1)
        )
        
        # Decoder: Reconstruct original semantic embeddings
        self.decoder = nn.Sequential(
            nn.Conv1d(in_channels=latent_dim, out_channels=256, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.BatchNorm1d(256),
            nn.Conv1d(in_channels=256, out_channels=self.hidden_size, kernel_size=3, padding=1)
        )
        
        # Module Dict grouping
        self.ae = nn.ModuleDict({
            "encoder": self.encoder,
            "physics_head": self.physics_head,
            "decoder": self.decoder
        })

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        return_physics_residuals: bool = True
    ) -> Union[Tuple[torch.Tensor, torch.Tensor, torch.Tensor], Tuple[torch.Tensor, torch.Tensor, Dict[str, torch.Tensor]]]:
        """
        Forward pass through Transformer -> TCN Reasoner -> Physics Projection.
        
        Returns:
            reconstruction: Reconstructed semantic embeddings [Batch, SeqLen, HiddenDim]
            original_embeddings: Raw transformer embeddings [Batch, SeqLen, HiddenDim]
            physics_output: Projected states tensor or physical residuals dictionary
        """
        # 1. Get Semantic Embeddings
        with torch.set_grad_enabled(not self.transformer.training):
            outputs = self.transformer(input_ids=input_ids, attention_mask=attention_mask)
        
        original_embeddings = outputs.last_hidden_state
        
        # 2. Permute for 1D Conv: [Batch, Seq, Hidden] -> [Batch, Hidden, Seq]
        x = original_embeddings.permute(0, 2, 1)
        
        # 3. Latent Representation
        latent = self.encoder(x)
        
        # 4. Physics Projection
        physics_states = self.physics_head(latent)
        
        # 5. Decoder Pass
        reconstructed_x = self.decoder(latent)
        reconstruction = reconstructed_x.permute(0, 2, 1)
        
        if return_physics_residuals:
            from src.physics.traffic_loss import TrafficPhysicsLoss
            engine = self.physics_engine or TrafficPhysicsLoss(max_acceleration=10.0)
            physics_residuals = engine.compute_losses(physics_states)
            return reconstruction, original_embeddings, physics_residuals
            
        return reconstruction, original_embeddings, physics_states