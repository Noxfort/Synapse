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
# File: src/services/auditor_pipeline.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
import numpy as np
import logging
from typing import Dict, Any, Union, Optional
from torch.amp import autocast

from src.models.wavelet_ae_occ import WaveletSpectralAE, WaveletAEOCC
from src.strategies.deep_svdd_calibrator import DeepSVDDCalibrator
from src.physics.traffic_loss import TrafficPhysicsLoss
from src.utils.normalization import TensorNormalizer

logger = logging.getLogger("Synapse.AuditorPipeline")


class AuditorPipeline:
    """
    Dedicated Neural Pipeline for Security Auditing and Anomaly Detection.
    Encapsulates Wavelet Scattering Autoencoder, Deep SVDD Calibrator, and PINN physics evaluation.
    """

    def __init__(
        self,
        model: Optional[WaveletSpectralAE] = None,
        calibrator: Optional[DeepSVDDCalibrator] = None,
        physics_engine: Optional[TrafficPhysicsLoss] = None,
        input_len: int = 60,
        J: int = 2,
        Q: int = 1,
        latent_dim: int = 16,
        physics_weight: float = 0.5,
        max_acceleration: float = 10.0,
        enable_pinn: bool = True,
        device: Optional[torch.device] = None
    ):
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.physics_weight = physics_weight
        self.enable_pinn = enable_pinn

        if model is not None:
            self.model = model
        else:
            padded_len = 2 ** int(np.ceil(np.log2(input_len)) + 1)
            max_safe_j = int(np.log2(padded_len))
            if J > max_safe_j:
                safe_J = max(1, max_safe_j)
                if J > safe_J:
                    logger.info(f"[AuditorPipeline] Auto-adjusting J from {J} to {safe_J} for stability (padded_len={padded_len}).")
                J = safe_J

            self.model = WaveletSpectralAE(
                input_len=input_len,
                J=J,
                Q=Q,
                latent_dim=latent_dim
            )

        self.calibrator = calibrator or DeepSVDDCalibrator(latent_dim=latent_dim)
        self.physics_engine = physics_engine or TrafficPhysicsLoss(max_acceleration=max_acceleration)

        self.model.to(self.device)

    def to(self, device: Any) -> 'AuditorPipeline':
        self.device = torch.device(device) if isinstance(device, str) else device
        self.model.to(self.device)
        return self

    def audit(self, input_data: Union[Dict[str, Any], torch.Tensor]) -> Dict[str, Any]:
        """
        Reconstructs the embedding and signal to audit for anomalies (spectral, statistical, physical).
        """
        self.model.eval()

        if isinstance(input_data, dict):
            if "signature" in input_data:
                x = input_data["signature"]
            else:
                x = input_data.get('data') or input_data.get('window')

            if x is None:
                return {"error": "No data provided"}
            x = torch.tensor(x, dtype=torch.float32) if not isinstance(x, torch.Tensor) else x
        else:
            x = input_data if isinstance(input_data, torch.Tensor) else torch.tensor(input_data, dtype=torch.float32)

        x = x.to(self.device)
        if x.ndim == 1:
            x = x.unsqueeze(0)

        # Safety padding/trimming to match input_len
        if hasattr(self.model, 'input_len'):
            target_len = self.model.input_len
            sig_dim = x.shape[1]
            if sig_dim != target_len:
                if sig_dim < target_len:
                    import torch.nn.functional as F
                    x = F.pad(x, (0, target_len - sig_dim))
                else:
                    x = x[:, :target_len]

        # Instance Normalization (SRP)
        x, _, _ = TensorNormalizer.instance_norm(x)
        device_type = self.device.type if self.device.type != 'mps' else 'cpu'

        with torch.no_grad():
            with autocast(device_type=device_type, enabled=(self.device.type == 'cuda')):
                feats, z, rec_feats, time_recon = self.model(x, return_time_recon=True)

                rec_err = torch.mean((rec_feats - feats) ** 2, dim=1)
                time_err = torch.mean((time_recon - x) ** 2, dim=1)
                
                # Deep SVDD Anomaly Score
                dist_center, _ = self.calibrator.compute_anomaly_scores(z)
                
                # PINN Physics Loss
                physics_res = self.physics_engine.compute_losses(time_recon, orig_x=x)
                physics_loss = physics_res["total_physics_loss"] if self.enable_pinn else torch.tensor(0.0, device=x.device)

                total_score = rec_err + (0.5 * time_err) + (0.1 * dist_center) + (self.physics_weight * physics_loss)
                threshold = self.calibrator.threshold
                is_anomaly = total_score > threshold

        return {
            "is_anomaly": bool(is_anomaly.item() if is_anomaly.numel() == 1 else is_anomaly[0].item()),
            "score": float(total_score.mean().item()),
            "threshold": float(threshold),
            "spectral_residual": float(rec_err.mean().item()),
            "time_residual": float(time_err.mean().item()),
            "compactness_dist": float(dist_center.mean().item()),
            "physics_residual": float(physics_loss.mean().item()),
            "physics_details": {
                "bounds_loss": float(physics_res["loss_bounds"].item()),
                "kinematics_loss": float(physics_res["loss_kinematics"].item()),
                "smooth_loss": float(physics_res["loss_smooth"].item()),
                "conservation_loss": float(physics_res["loss_conservation"].item()),
            },
            "status": "audited"
        }
