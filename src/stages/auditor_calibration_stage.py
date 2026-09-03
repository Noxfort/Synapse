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
from src.utils.convergence_tracker import MarginalConvergenceTracker


class AuditorCalibrationStage(BaseStage):
    """
    Auditor Calibration Stage — Cold-Start Elimination.
    
    Trains the AuditorAgent (WaveletAEOCC) on the Golden Dataset during
    the Offline Phase, so it enters the Online Phase fully calibrated.
    
    Pipeline Position: Runs AFTER ClassificationStage (requires golden_v1.parquet).
    
    Outputs:
    - auditor_calibrated.pth: Model weights + threshold + center
    """

    # Training Defaults (Dynamic Marginal Convergence)
    MAX_SAFETY_EPOCHS = 100
    MIN_EPOCHS = 5
    PATIENCE = 4
    MIN_DELTA = 1e-4
    SLOPE_THRESHOLD = 1e-4
    BATCH_SIZE = 64
    WINDOW_SIZE = 60  # Matches default seq_len used by NeuralFactory
    CALIBRATION_PERCENTILE = 99
    SAFETY_HEADROOM = 1.35
    MIN_THRESHOLD_FLOOR = 0.75

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

        self.log("[AuditorCalibrationStage] 🏋️ Training Auditor on Golden Dataset (Dynamic Marginal Convergence)...")

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

            # 3. Dynamic Training Loop
            tracker = MarginalConvergenceTracker(
                min_epochs=self.MIN_EPOCHS,
                max_epochs=self.MAX_SAFETY_EPOCHS,
                patience=self.PATIENCE,
                min_delta=self.MIN_DELTA,
                slope_threshold=self.SLOPE_THRESHOLD,
                restore_best_weights=True
            )

            self.log(f"[AuditorCalibrationStage] 🔄 Starting dynamic calibration (max={self.MAX_SAFETY_EPOCHS}, min={self.MIN_EPOCHS})...")
            
            for epoch in range(self.MAX_SAFETY_EPOCHS):
                if self.check_interruption():
                    return False

                epoch_losses = []
                indices = np.random.permutation(len(windows))

                for i in range(0, len(indices), self.BATCH_SIZE):
                    batch_idx = indices[i:i + self.BATCH_SIZE]
                    batch = torch.tensor(windows[batch_idx], dtype=torch.float32)
                    loss = agent.train_step(batch)
                    epoch_losses.append(loss)

                avg_loss = float(np.mean(epoch_losses))
                
                # Log telemetry
                if (epoch + 1) % 5 == 0 or epoch == 0:
                    self.log(f"[AuditorCalibrationStage]   Epoch {epoch+1} — Loss: {avg_loss:.6f}")

                # Check dynamic marginal convergence
                should_stop = tracker.step(epoch=epoch, loss=avg_loss, model=agent.model)

                # Dynamic progress scaling (80 to 90 range)
                progress_val = min(90, 80 + int(((epoch + 1) / max(20, epoch + 5)) * 10))
                self.progress(progress_val)

                if should_stop:
                    self.log(
                        f"[AuditorCalibrationStage] 🛑 Converged at epoch {epoch+1} "
                        f"({tracker.stop_reason}) | Best Loss: {tracker.best_loss:.6f}"
                    )
                    break

            # 4. Calibrate Threshold
            self.log("[AuditorCalibrationStage] 📐 Calibrating anomaly threshold (percentile 99 + safety headroom)...")
            self._calibrate_threshold(agent, windows)

            # 5. Save Checkpoint
            self._save_checkpoint(agent, checkpoint_path)

            thresh_val = float(agent.model.threshold.item() if isinstance(agent.model.threshold, torch.Tensor) else agent.model.threshold)
            self.log(f"[AuditorCalibrationStage] ✅ Auditor calibrated successfully!")
            self.log(f"[AuditorCalibrationStage] 📊 Final threshold: {thresh_val:.6f}")
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

        # Clean NaN/Inf in the dataframe
        df_clean = df[numeric_cols].ffill().bfill().fillna(0.0)
        data = df_clean.values.astype(np.float32)
        data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)

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
        device = getattr(agent.pipeline, "device", getattr(agent, "device", torch.device("cpu")))
        calibrator = getattr(agent.pipeline, "calibrator", getattr(agent.trainer, "calibrator", None))
        physics_engine = getattr(agent.pipeline, "physics_engine", getattr(agent.trainer, "physics_engine", None))
        physics_weight = getattr(agent.pipeline, "physics_weight", getattr(agent, "physics_weight", 0.5))
        enable_pinn = getattr(agent.pipeline, "enable_pinn", getattr(agent, "enable_pinn", True))

        all_scores = []

        with torch.no_grad():
            for i in range(0, len(windows), self.BATCH_SIZE):
                batch = torch.tensor(
                    windows[i:i + self.BATCH_SIZE], dtype=torch.float32
                ).to(device)

                from src.utils.normalization import TensorNormalizer
                batch = TensorNormalizer.sanitize(batch)
                batch, _, _ = TensorNormalizer.instance_norm(batch)
                batch = TensorNormalizer.sanitize(batch)

                feats, z, rec_feats, time_recon = agent.model(batch, return_time_recon=True)
                feats = feats.to(device)
                z = z.to(device)
                rec_feats = rec_feats.to(device)
                time_recon = time_recon.to(device)

                rec_err = torch.mean((rec_feats - feats) ** 2, dim=1)
                time_err = torch.mean((time_recon - batch) ** 2, dim=1)

                if calibrator is not None and calibrator.center is not None:
                    center = calibrator.center.to(device)
                    dist_center = torch.sum((z - center) ** 2, dim=1)
                else:
                    dist_center = torch.zeros(batch.shape[0], device=device)

                if physics_engine is not None and enable_pinn:
                    physics_res = physics_engine.compute_losses(time_recon, orig_x=batch)
                    phys_val = physics_res.get("total_physics_loss", torch.tensor(0.0, device=device))
                    if isinstance(phys_val, torch.Tensor):
                        phys_val = phys_val.to(device)
                else:
                    phys_val = torch.tensor(0.0, device=device)

                scores = rec_err + (0.5 * time_err) + (0.1 * dist_center) + (physics_weight * phys_val)
                all_scores.append(scores.cpu())

        if all_scores:
            all_scores = torch.cat(all_scores).numpy()
            valid_scores = all_scores[np.isfinite(all_scores)]
            if len(valid_scores) > 0:
                raw_pct = float(np.percentile(valid_scores, self.CALIBRATION_PERCENTILE))
                calibrated_threshold = max(self.MIN_THRESHOLD_FLOOR, raw_pct * self.SAFETY_HEADROOM)
            else:
                calibrated_threshold = self.MIN_THRESHOLD_FLOOR
        else:
            calibrated_threshold = self.MIN_THRESHOLD_FLOOR

        # Override threshold with the statistical one in calibrator and model
        if calibrator is not None:
            calibrator.threshold = calibrated_threshold
        agent.model.threshold = torch.tensor(calibrated_threshold)
        if hasattr(agent, "threshold"):
            agent.threshold = torch.tensor(calibrated_threshold)

    def _save_checkpoint(self, agent: AuditorAgent, checkpoint_path: str):
        """Saves the full calibrated state using CheckpointService pattern."""
        os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)

        calibrator = getattr(agent.pipeline, "calibrator", getattr(agent.trainer, "calibrator", None))
        center = calibrator.center if (calibrator and calibrator.center is not None) else getattr(agent.model, 'center', None)
        center_init = calibrator.center_initialized if calibrator else getattr(agent.model, 'center_initialized', False)
        threshold = calibrator.threshold if calibrator else getattr(agent.model, 'threshold', 0.5)
        if isinstance(threshold, torch.Tensor):
            threshold = threshold.item()

        state = {
            'model_state_dict': agent.model.state_dict(),
            'threshold': threshold,
            'center': center,
            'center_initialized': center_init,
            'input_len': getattr(agent.model, 'input_len', self.WINDOW_SIZE),
            'latent_dim': getattr(agent.model, 'latent_dim', 16),
        }

        # Atomic save (temp → move)
        temp_path = checkpoint_path + ".tmp"
        torch.save(state, temp_path)

        import shutil
        shutil.move(temp_path, checkpoint_path)

        self.log(f"[AuditorCalibrationStage] 💾 Checkpoint saved: {checkpoint_path}")
