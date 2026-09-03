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
# File: src/pipeline/corrector_pipeline.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
import numpy as np
import logging
from typing import Any, Optional
from torch.amp import autocast

from src.models.pi_vae_tcn import PIVAETCN
from src.utils.normalization import TensorNormalizer

logger = logging.getLogger("Synapse.CorrectorPipeline")


class CorrectorPipeline:
    """
    Dedicated Neural Pipeline for Physics-Informed Denoising and Golden Dataset Generation.
    Encapsulates PI-VAE-TCN execution with dynamic Z-Score normalization.
    """

    def __init__(
        self,
        model: Optional[PIVAETCN] = None,
        input_dim: int = 1,
        hidden_dim: int = 64,
        latent_dim: int = 32,
        kernel_size: int = 3,
        max_acceleration: float = 10.0,
        device: Optional[torch.device] = None,
        **kwargs: Any
    ):
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")

        if model is not None:
            self.model = model
        else:
            self.model = PIVAETCN(
                input_channels=input_dim,
                hidden_channels=hidden_dim,
                latent_channels=latent_dim,
                kernel_size=kernel_size,
                max_acceleration=max_acceleration
            )

        self.model.to(self.device)

    def to(self, device: Any) -> 'CorrectorPipeline':
        self.device = torch.device(device) if isinstance(device, str) else device
        self.model.to(self.device)
        return self

    def correct(self, input_data: Any, batch_size: int = 128) -> np.ndarray:
        """
        Performs inference with dynamic Z-score normalization and AMP.
        """
        self.model.eval()
        original_dim = len(input_data.shape)

        data = input_data
        single_sample_2d = False
        if original_dim == 2:
            if data.shape[1] == self.model.input_channels and self.model.input_channels > 1:
                data = np.expand_dims(np.transpose(data, (1, 0)), axis=0)
                single_sample_2d = True
            else:
                data = np.expand_dims(data, axis=1)
        elif original_dim == 3:
            data = np.transpose(data, (0, 2, 1))

        dataset_size = data.shape[0]
        reconstructed_results = []
        device_type = self.device.type if self.device.type != 'mps' else 'cpu'

        try:
            x_tensor_cpu = torch.tensor(data, dtype=torch.float32)

            with torch.no_grad():
                for i in range(0, dataset_size, batch_size):
                    batch_x = x_tensor_cpu[i:i + batch_size].to(self.device)
                    batch_x_norm, mean, std = TensorNormalizer.zscore_norm(batch_x, seq_dim=2)

                    with autocast(device_type=device_type, enabled=(self.device.type == 'cuda')):
                        recon_x_norm, mu, logvar = self.model(batch_x_norm)

                    recon_x = TensorNormalizer.zscore_denorm(recon_x_norm.float(), mean, std)
                    reconstructed_results.append(recon_x.cpu().numpy())

                    del batch_x, batch_x_norm, recon_x, recon_x_norm, mu, logvar
                    if self.device.type == 'cuda':
                        torch.cuda.empty_cache()

            final_reconstruction = np.concatenate(reconstructed_results, axis=0)

            if single_sample_2d:
                final_reconstruction = np.transpose(final_reconstruction[0], (1, 0))
            elif original_dim == 2:
                final_reconstruction = np.squeeze(final_reconstruction, axis=1)
            elif original_dim == 3:
                final_reconstruction = np.transpose(final_reconstruction, (0, 2, 1))

            return final_reconstruction

        except Exception as e:
            logger.error(f"[CorrectorPipeline] Error during inference: {str(e)}")
            raise
