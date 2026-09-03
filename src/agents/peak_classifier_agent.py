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
# File: src/agents/peak_classifier_agent.py
# Author: Gabriel Moraes
# Date: 2026-03-02

import logging
import numpy as np
import torch
import torch.nn as nn
from torch.amp import autocast, GradScaler

# SYNAPSE Local Models
from src.models.itransformer_lite import iTransformerLite
from src.models.pino_traffic import SpectralFeatureExtractor

# SYNAPSE Pipelines (SRP Extraction)
from src.pipeline.peak_pipeline import ColumnDiscovery, PeakPipeline

logger = logging.getLogger(__name__)


class PeakClassifierAgent(nn.Module):
    """
    Peak Classifier Agent (Extrator de Sazonalidade).
    
    Refactored V2 (SOLID):
    - Column discovery delegated to ColumnDiscovery service.
    - Pipeline execution delegated to PeakPipeline service.
    - Uses Fourier SpectralFeatureExtractor (PINO block) for robust frequency domain feature extraction.
    """

    def __init__(self, itransformer_config: dict, timesnet_config: dict, output_path: str = "peak_schedule.json"):
        super(PeakClassifierAgent, self).__init__()
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.output_path = output_path
        
        # --- VRAM Protection: Force safe chunk size ---
        self.chunk_size = 2048
        itransformer_config['seq_len'] = self.chunk_size
        itransformer_config['pred_len'] = self.chunk_size
        timesnet_config['seq_len'] = self.chunk_size
        timesnet_config['pred_len'] = self.chunk_size
        timesnet_config.setdefault('enc_in', 1)
        
        # Neural Models
        self.itransformer = iTransformerLite(
            num_sensors=itransformer_config.get('num_variates', 2),
            d_model=itransformer_config.get('d_model', 32),
            n_heads=itransformer_config.get('n_heads', 2)
        ).to(self.device)
        self.itransformer.eval()
        
        timesnet_config.pop("num_kernels", None)
        self.timesnet = SpectralFeatureExtractor(**timesnet_config).to(self.device)
        
        # Auxiliary Classifier Head for HPO Tuning
        self.hpo_classifier = nn.Linear(timesnet_config.get('enc_in', 1), 1).to(self.device)
        self.criterion = nn.BCEWithLogitsLoss()
        
        self.optimizer = torch.optim.Adam([
            {'params': self.timesnet.parameters()},
            {'params': self.hpo_classifier.parameters()}
        ], lr=timesnet_config.get('learning_rate', 1e-3))
        self.scaler = GradScaler('cuda' if torch.cuda.is_available() else 'cpu')

        # --- Services (SRP) ---
        self._column_discovery = ColumnDiscovery()
        self._pipeline = PeakPipeline(
            itransformer=self.itransformer,
            timesnet=self.timesnet,
            device=self.device,
            chunk_size=self.chunk_size
        )

    def train_step(self, x_windows: np.ndarray, y_labels: np.ndarray) -> float:
        """
        Forward/backward pass for HPO Hyperparameter Tuning with AMP.
        """
        self.train()
        
        x_tensor = torch.tensor(x_windows, dtype=torch.float32).to(self.device)
        y_tensor = torch.tensor(y_labels, dtype=torch.float32).view(-1, 1).to(self.device)
        
        if len(x_tensor.shape) == 2:
            x_tensor = x_tensor.unsqueeze(-1).expand(-1, -1, 2)
            
        self.optimizer.zero_grad()
        device_type = self.device.type if self.device.type != 'mps' else 'cpu'
        
        with autocast(device_type=device_type, enabled=(self.device.type == 'cuda')):
            with torch.no_grad():
                stress_signal = self.itransformer(x_tensor)
                
            timesnet_features = self.timesnet(stress_signal)
            pooled_features = timesnet_features.mean(dim=1)
            
            logits = self.hpo_classifier(pooled_features)
            loss = self.criterion(logits, y_tensor)
        
        if not torch.isfinite(loss):
            self.scaler.update()
            return 1e6
            
        self.scaler.scale(loss).backward()
        self.scaler.unscale_(self.optimizer)
        torch.nn.utils.clip_grad_norm_(self.parameters(), max_norm=1.0)
        self.scaler.step(self.optimizer)
        self.scaler.update()
        
        return loss.item()

    def process_and_classify(self, historical_df):
        """
        Main pipeline execution (Orchestration Only).
        Delegates column discovery and pipeline execution to services.
        """
        logger.info("Starting Peak Classification Pipeline...")
        
        # 1. Semantic Column Discovery (Delegated)
        available_cols = historical_df.columns.tolist()
        vol_col, spd_col = self._column_discovery.discover(available_cols)
        
        logger.info(f"🧠 Semantic NLP identified '{vol_col}' as Volume/Flow.")
        logger.info(f"🧠 Semantic NLP identified '{spd_col}' as Speed/Velocity.")
        
        # 2. Pipeline Execution (Delegated)
        return self._pipeline.run(historical_df, vol_col, spd_col, self.output_path)
