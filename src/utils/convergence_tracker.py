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
# File: src/utils/convergence_tracker.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import copy
import logging
from typing import Optional, List, Dict, Any
import numpy as np
import torch

try:
    import optuna
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False

logger = logging.getLogger("Synapse.ConvergenceTracker")


class MarginalConvergenceTracker:
    """
    Two-Level Marginal Convergence and Early Stopping Tracker.
    
    Responsibilities:
    - Detects marginal gain plateaus using linear regression derivative (slope ≈ 0).
    - Tracks consecutive epochs without meaningful improvement (patience + min_delta).
    - Preserves and restores the best neural weights (state_dict deepcopy).
    - Integrates seamlessly with Optuna trials for automated intermediate reporting and pruning.
    - Prevents runaway training via a safety maximum epoch ceiling.
    """

    def __init__(
        self,
        min_epochs: int = 4,
        max_epochs: int = 50,
        patience: int = 4,
        min_delta: float = 1e-4,
        slope_threshold: float = 1e-4,
        window_size: int = 5,
        restore_best_weights: bool = True,
        optuna_trial: Optional[Any] = None,
        enable_pruning: bool = True
    ):
        """
        Args:
            min_epochs: Warm-up epochs before early stopping criteria can trigger.
            max_epochs: Upper safety limit of epochs to execute.
            patience: Number of consecutive epochs with < min_delta improvement to tolerate.
            min_delta: Minimum reduction in loss to qualify as a significant improvement.
            slope_threshold: Maximum absolute slope (dLoss/dt) over window to consider flat.
            window_size: Number of recent epochs used for linear regression slope calculation.
            restore_best_weights: Whether to restore model weights to the best recorded epoch.
            optuna_trial: Optional Optuna trial for reporting and pruning.
            enable_pruning: Whether to raise optuna.TrialPruned() if trial.should_prune() triggers.
        """
        self.min_epochs = max(1, min_epochs)
        self.max_epochs = max_epochs
        self.patience = patience
        self.min_delta = min_delta
        self.slope_threshold = slope_threshold
        self.window_size = max(2, window_size)
        self.restore_best_weights = restore_best_weights
        self.optuna_trial = optuna_trial
        self.enable_pruning = enable_pruning

        # Tracking State
        self.best_loss: float = float("inf")
        self.best_epoch: int = 0
        self.stopped_epoch: int = 0
        self.wait: int = 0
        self.best_weights: Optional[Dict[str, Any]] = None
        self.loss_history: List[float] = []
        self.early_stopped: bool = False
        self.stop_reason: str = ""

    def step(
        self,
        epoch: int,
        loss: float,
        model: Optional[torch.nn.Module] = None
    ) -> bool:
        """
        Processes an epoch's loss value, updates telemetry, and determines if training should stop.
        
        Args:
            epoch: Current epoch index (0-based or 1-based, consistently used).
            loss: Current loss value for this epoch.
            model: Optional PyTorch model for weight snapshotting.
            
        Returns:
            bool: True if training should stop immediately, False to continue.
            
        Raises:
            optuna.TrialPruned: If Optuna pruning is active and triggered.
        """
        # Defensive check against non-finite loss
        if not np.isfinite(loss):
            self.early_stopped = True
            self.stopped_epoch = epoch
            self.stop_reason = "nan_inf_loss"
            logger.warning(f"[ConvergenceTracker] ⚠️ Non-finite loss detected ({loss}) at epoch {epoch}. Stopping.")
            return True

        self.loss_history.append(float(loss))

        # ── 1. Optuna Reporting & Pruning (Level 1 Interlock) ──
        if self.optuna_trial is not None and OPTUNA_AVAILABLE:
            try:
                self.optuna_trial.report(loss, epoch)
                if self.enable_pruning and self.optuna_trial.should_prune():
                    self.early_stopped = True
                    self.stopped_epoch = epoch
                    self.stop_reason = "optuna_pruned"
                    logger.info(f"[ConvergenceTracker] ✂️ Optuna pruned trial at epoch {epoch} (loss={loss:.4f}).")
                    raise optuna.TrialPruned()
            except optuna.TrialPruned:
                raise
            except Exception as e:
                logger.debug(f"[ConvergenceTracker] Optuna report/prune check skipped: {e}")

        # ── 2. Best Model Tracking (Weights + Loss) ──
        if loss < (self.best_loss - self.min_delta):
            self.best_loss = loss
            self.best_epoch = epoch
            self.wait = 0
            if model is not None and self.restore_best_weights:
                try:
                    # Deep copy CPU tensors to avoid GPU memory leaks
                    self.best_weights = {
                        k: v.cpu().clone() for k, v in model.state_dict().items()
                    }
                except Exception as e:
                    logger.debug(f"[ConvergenceTracker] Failed to snapshot model weights: {e}")
        else:
            self.wait += 1

        # ── 3. Warm-up Period Check ──
        if (epoch + 1) < self.min_epochs:
            return False

        # ── 4. Patience / Marginal Improvement Check ──
        if self.wait >= self.patience:
            self.early_stopped = True
            self.stopped_epoch = epoch
            self.stop_reason = f"patience_exceeded (no improvement >= {self.min_delta} for {self.wait} epochs)"
            self._restore_weights(model)
            logger.info(
                f"[ConvergenceTracker] 🛑 Marginal gain plateau: stopped at epoch {epoch+1} "
                f"(best_loss={self.best_loss:.6f} at epoch {self.best_epoch+1})."
            )
            return True

        # ── 5. Mathematical Slope / Plateau Check (Derivada ≈ 0) ──
        if len(self.loss_history) >= self.window_size:
            recent = self.loss_history[-self.window_size:]
            x = np.arange(len(recent))
            try:
                slope, _ = np.polyfit(x, recent, 1)
                # If slope is nearly flat or positive (loss stopped descending)
                if abs(slope) < self.slope_threshold or (slope > 0 and self.wait >= 2):
                    self.early_stopped = True
                    self.stopped_epoch = epoch
                    self.stop_reason = f"slope_plateau (|slope|={abs(slope):.2e} < {self.slope_threshold:.2e})"
                    self._restore_weights(model)
                    logger.info(
                        f"[ConvergenceTracker] 🛑 Mathematical plateau (slope={slope:.2e}): "
                        f"stopped at epoch {epoch+1} (best_loss={self.best_loss:.6f})."
                    )
                    return True
            except Exception as e:
                logger.debug(f"[ConvergenceTracker] Slope calculation error: {e}")

        # ── 6. Safety Max Epochs Ceiling ──
        if (epoch + 1) >= self.max_epochs:
            self.early_stopped = True
            self.stopped_epoch = epoch
            self.stop_reason = "max_epochs_reached"
            self._restore_weights(model)
            logger.info(
                f"[ConvergenceTracker] 🏁 Safety ceiling reached: stopped at epoch {epoch+1} "
                f"(best_loss={self.best_loss:.6f})."
            )
            return True

        return False

    def _restore_weights(self, model: Optional[torch.nn.Module]):
        """Restores model weights to the best snapshot if available."""
        if model is not None and self.restore_best_weights and self.best_weights is not None:
            try:
                model.load_state_dict(self.best_weights)
                logger.debug(f"[ConvergenceTracker] 🔄 Restored best model weights from epoch {self.best_epoch+1}.")
            except Exception as e:
                logger.warning(f"[ConvergenceTracker] Failed to restore best weights: {e}")
