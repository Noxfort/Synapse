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
# File: src/stages/auditor_calibration_stage.py
# Author: Gabriel Moraes
# Date: 2026-04-27

import os
import torch
import numpy as np
import pandas as pd
from typing import Dict, Any

from src.stages.base_stage import BaseStage
from src.agents.auditor_agent import AuditorAgent
from src.services.checkpoint_service import CheckpointService


class AuditorCalibrationStage(BaseStage):
    """
    Auditor Calibration Stage — Cold-Start Elimination.
    
    Trains the AuditorAgent (WaveletAEOCC) on the Golden Dataset during
    the Offline Phase, so it enters the Online Phase fully calibrated.
    
    Pipeline Position: Runs AFTER ClassificationStage (requires golden_v1.parquet).
    
    Outputs:
    - auditor_calibrated.pth: Model weights + threshold + center
    """

    # Training Defaults
    EPOCHS = 30
    BATCH_SIZE = 64
    WINDOW_SIZE = 60  # Matches default seq_len used by NeuralFactory
    CALIBRATION_PERCENTILE = 95

    def execute(self, shared_context: Dict[str, Any]) -> bool:
        """Trains the Auditor on golden data and saves calibrated checkpoint."""
        
        checkpoint_path = shared_context.get("auditor_checkpoint_path")
        golden_path = shared_context.get("golden_path")

        # ── SKIP LOCK ──
        if checkpoint_path and os.path.exists(checkpoint_path) and os.path.getsize(checkpoint_path) > 0:
            self.log("[AuditorCalibrationStage] 🏆 Calibrated checkpoint found. Skipping training.")
            self.progress(95)
            return True

        # ── VALIDATE GOLDEN ──
        if not golden_path or not os.path.exists(golden_path):
            self.log("[AuditorCalibrationStage] ⚠️ Golden dataset not found. Skipping calibration.")
            return True  # Non-fatal: system can still run with uncalibrated auditor

        if self.check_interruption():
            return False

        self.log("[AuditorCalibrationStage] 🏋️ Training Auditor on Golden Dataset...")

        try:
            # 1. Load & Prepare Data
            windows = self._prepare_windows(golden_path)
            if windows is None or len(windows) == 0:
                self.log("[AuditorCalibrationStage] ⚠️ No valid training windows. Skipping.")
                return True

            self.log(f"[AuditorCalibrationStage] 📊 Prepared {len(windows)} training windows (size={self.WINDOW_SIZE}).")

            # 2. Create Agent
            agent = AuditorAgent(
                input_len=self.WINDOW_SIZE,
                J=2, Q=1, latent_dim=16,
                learning_rate=1e-3
            )

            # 3. Training Loop
            self.log(f"[AuditorCalibrationStage] 🔄 Training for {self.EPOCHS} epochs (batch={self.BATCH_SIZE})...")
            
            for epoch in range(self.EPOCHS):
                if self.check_interruption():
                    return False

                epoch_losses = []
                indices = np.random.permutation(len(windows))

                for i in range(0, len(indices), self.BATCH_SIZE):
                    batch_idx = indices[i:i + self.BATCH_SIZE]
                    batch = torch.tensor(windows[batch_idx], dtype=torch.float32)
                    loss = agent.train_step(batch)
                    epoch_losses.append(loss)

                avg_loss = np.mean(epoch_losses)
                
                # Log every 5 epochs to avoid spam
                if (epoch + 1) % 5 == 0 or epoch == 0:
                    self.log(f"[AuditorCalibrationStage]   Epoch {epoch+1}/{self.EPOCHS} — Loss: {avg_loss:.6f}")

                # Progress: 80-90 range (leaving room for calibration + save)
                progress_val = 80 + int((epoch / self.EPOCHS) * 10)
                self.progress(progress_val)

            # 4. Calibrate Threshold
            self.log("[AuditorCalibrationStage] 📐 Calibrating anomaly threshold (percentile 95)...")
            self._calibrate_threshold(agent, windows)

            # 5. Save Checkpoint
            self._save_checkpoint(agent, checkpoint_path)

            self.log(f"[AuditorCalibrationStage] ✅ Auditor calibrated successfully!")
            self.log(f"[AuditorCalibrationStage] 📊 Final threshold: {agent.model.threshold.item():.6f}")
            self.progress(95)

            return True

        except Exception as e:
            self.log(f"[AuditorCalibrationStage] ❌ Calibration failed: {e}")
            import traceback
            traceback.print_exc()
            return True  # Non-fatal: don't break the pipeline

    def _prepare_windows(self, golden_path: str) -> np.ndarray:
        """
        Loads the Golden Dataset and creates sliding windows for training.
        
        Returns:
            np.ndarray of shape [N, WINDOW_SIZE] — flattened feature windows.
        """
        df = pd.read_parquet(golden_path)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if not numeric_cols:
            return None

        # Use all numeric columns, flatten each row into a single feature vector
        data = df[numeric_cols].values.astype(np.float32)

        # If total features per row >= WINDOW_SIZE, use rows directly
        if data.shape[1] >= self.WINDOW_SIZE:
            # Truncate to WINDOW_SIZE
            return data[:, :self.WINDOW_SIZE]

        # Otherwise, create sliding windows from each column independently
        windows = []
        for col_idx in range(data.shape[1]):
            series = data[:, col_idx]
            n_windows = len(series) - self.WINDOW_SIZE + 1
            if n_windows <= 0:
                continue
            for start in range(0, n_windows, self.WINDOW_SIZE // 2):  # 50% overlap
                end = start + self.WINDOW_SIZE
                if end > len(series):
                    break
                windows.append(series[start:end])

        if not windows:
            return None

        return np.array(windows, dtype=np.float32)

    def _calibrate_threshold(self, agent: AuditorAgent, windows: np.ndarray):
        """
        Runs validation on all training windows to set threshold = percentile 95.
        This replaces the arbitrary 0.5 default with a data-driven cutoff.
        """
        agent.model.eval()
        all_scores = []

        with torch.no_grad():
            for i in range(0, len(windows), self.BATCH_SIZE):
                batch = torch.tensor(
                    windows[i:i + self.BATCH_SIZE], dtype=torch.float32
                ).to(agent.device)

                from src.utils.normalization import TensorNormalizer
                batch, _, _ = TensorNormalizer.instance_norm(batch)

                feats, z, rec_feats = agent.model(batch)
                rec_err = torch.mean((rec_feats - feats) ** 2, dim=1)
                dist_center = torch.sum((z - agent.model.center) ** 2, dim=1)
                scores = rec_err + (0.1 * dist_center)
                all_scores.append(scores.cpu())

        all_scores = torch.cat(all_scores).numpy()
        calibrated_threshold = float(np.percentile(all_scores, self.CALIBRATION_PERCENTILE))

        # Override the EMA threshold with the statistical one
        agent.model.threshold = torch.tensor(calibrated_threshold)

    def _save_checkpoint(self, agent: AuditorAgent, checkpoint_path: str):
        """Saves the full calibrated state using CheckpointService pattern."""
        os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
        
        state = {
            'model_state_dict': agent.model.state_dict(),
            'threshold': agent.model.threshold,
            'center': agent.model.center,
            'center_initialized': agent.model.center_initialized,
            'input_len': agent.model.input_len,
            'latent_dim': agent.model.latent_dim,
        }
        
        # Atomic save (temp → move)
        temp_path = checkpoint_path + ".tmp"
        torch.save(state, temp_path)
        
        import shutil
        shutil.move(temp_path, checkpoint_path)
        
        self.log(f"[AuditorCalibrationStage] 💾 Checkpoint saved: {checkpoint_path}")
