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
# File: src/services/linguist_pipeline.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
import numpy as np
import logging
from typing import Dict, Any, List, Optional
from transformers import AutoTokenizer
from torch.amp import autocast

from src.models.neuro_symbolic import NeuroSymbolicModel

logger = logging.getLogger("Synapse.LinguistPipeline")


class LinguistPipeline:
    """
    Dedicated Neural Pipeline for Semantic-Physical Validation and Contradiction Detection.
    Combines Transformer text embeddings, TCN autoencoding, and PINN physical checks.
    """

    def __init__(
        self,
        model: Optional[NeuroSymbolicModel] = None,
        model_name: str = "distilroberta-base",
        anomaly_threshold: float = 0.85,
        device: Optional[torch.device] = None,
        **kwargs: Any
    ):
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = model or NeuroSymbolicModel(model_name=model_name)
        self.model.to(self.device)

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.anomaly_threshold = anomaly_threshold

    def to(self, device: Any) -> 'LinguistPipeline':
        self.device = torch.device(device) if isinstance(device, str) else device
        self.model.to(self.device)
        return self

    def validate(self, input_data: Any) -> Dict[str, Any]:
        """
        Runs the semantic-physical anomaly detection loop using TCN-PINN.
        """
        self.model.eval()

        if isinstance(input_data, dict):
            text_claim = input_data.get("text", "")
        elif isinstance(input_data, list):
            text_claim = f"Sensor traffic stream: {input_data[:10]}"
        else:
            text_claim = str(input_data)

        inputs = self.tokenizer(
            text_claim,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=128
        )

        input_ids = inputs["input_ids"].to(self.device)
        attention_mask = inputs["attention_mask"].to(self.device)
        device_type = self.device.type if self.device.type != 'mps' else 'cpu'

        with torch.no_grad():
            with autocast(device_type=device_type, enabled=(self.device.type == 'cuda')):
                reconstruction, original, physics_residuals = self.model(input_ids, attention_mask)

            error = torch.nn.functional.mse_loss(reconstruction.float(), original.float(), reduction='none')
            mean_error = error.mean().item()
            physics_error = physics_residuals.get("total_physics_loss", torch.tensor(0.0)).item()

        is_valid = bool(mean_error < self.anomaly_threshold and physics_error < 0.5)

        return {
            "is_valid": is_valid,
            "is_anomaly": not is_valid,
            "error_score": mean_error,
            "physics_residual": physics_error,
            "semantic_vector": original.cpu().float().numpy()
        }

    def calibrate_threshold(self, validation_texts: List[str]) -> None:
        """
        Auto-adjusts the anomaly threshold based on a baseline distribution of normal logs.
        """
        if not validation_texts:
            logger.warning("[LinguistPipeline] No validation texts provided for calibration.")
            return

        self.model.eval()
        inputs = self.tokenizer(
            validation_texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=128
        )

        input_ids = inputs["input_ids"].to(self.device)
        attention_mask = inputs["attention_mask"].to(self.device)
        device_type = self.device.type if self.device.type != 'mps' else 'cpu'

        with torch.no_grad():
            with autocast(device_type=device_type, enabled=(self.device.type == 'cuda')):
                reconstruction, original, _ = self.model(input_ids, attention_mask)
                errors = torch.nn.functional.mse_loss(reconstruction.float(), original.float(), reduction='none')

            seq_errors = errors.mean(dim=(1, 2)).cpu().numpy()
            self.anomaly_threshold = float(np.percentile(seq_errors, 95))

        logger.info(f"[LinguistPipeline] New semantic threshold set to: {self.anomaly_threshold:.4f}")
