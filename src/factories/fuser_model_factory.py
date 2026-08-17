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
# File: src/factories/fuser_model_factory.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch.nn as nn
from src.models.itransformer import iTransformer
from src.models.diffusion_gatv2 import DiffusionGATv2
from src.models.pinn_traffic_flow import PINNTrafficFlow
from src.services.fusion_pipeline import FusionPipeline


class FuserModelFactory:
    """
    Fabricator for the Fuser's neural components and pipelines (DIP/IoC).
    
    Adheres to Dependency Inversion Principle (DIP):
    - Decouples concrete PyTorch model construction from the FuserAgent orchestrator.
    - Encapsulates hyperparameter wiring across DiffusionGATv2, PINNTrafficFlow, and iTransformer.
    """

    @staticmethod
    def create_fusion_pipeline(
        num_variates: int = 10,
        seq_len: int = 60,
        pred_len: int = 1,
        d_model: int = 64,
        n_heads: int = 4,
        layers: int = 2,
        spatial_dim: int = 32
    ) -> FusionPipeline:
        """
        Instantiates DiffusionGATv2, PINNTrafficFlow, and iTransformer and returns a configured FusionPipeline.
        """
        composite_dict = FuserModelFactory.create_composite_model(
            num_variates=num_variates,
            seq_len=seq_len,
            pred_len=pred_len,
            d_model=d_model,
            n_heads=n_heads,
            layers=layers,
            spatial_dim=spatial_dim
        )
        return FusionPipeline(
            diffusion_model=composite_dict["diffusion"],
            pinn_model=composite_dict["pinn"],
            temporal_model=composite_dict["itransformer"],
            spatial_dim=spatial_dim
        )

    @staticmethod
    def create_composite_model(
        num_variates: int = 10,
        seq_len: int = 60,
        pred_len: int = 1,
        d_model: int = 64,
        n_heads: int = 4,
        layers: int = 2,
        spatial_dim: int = 32
    ) -> nn.ModuleDict:
        """
        Creates the coupled neural architecture required by the Fuser pipeline.
        
        Returns:
            nn.ModuleDict with 'itransformer', 'diffusion', and 'pinn' sub-modules.
        """
        effective_pred_len = 1

        # 1. Primary Inverted Transformer Model
        itrans_model = iTransformer(
            num_variates=num_variates,
            seq_len=seq_len,
            pred_len=effective_pred_len,
            d_model=d_model,
            n_heads=n_heads,
            e_layers=layers,
            spatial_dim=spatial_dim
        )

        # 2. Diffusion Graph WaveNet Model
        diffusion_model = DiffusionGATv2(
            num_nodes=num_variates,
            in_channels=spatial_dim,
            hidden_channels=64,
            out_channels=spatial_dim,
            diffusion_steps=2,
            gat_heads=2
        )

        # 3. Physics-Informed (PINN) Traffic Flow Model
        pinn_model = PINNTrafficFlow(
            in_channels=spatial_dim,
            hidden_dim=64
        )

        return nn.ModuleDict({
            "itransformer": itrans_model,
            "diffusion": diffusion_model,
            "pinn": pinn_model
        })
