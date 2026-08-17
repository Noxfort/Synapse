# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# File: tests/unit/test_convergence_tracker.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import pytest
import torch
import torch.nn as nn
import numpy as np

from src.utils.convergence_tracker import MarginalConvergenceTracker

try:
    import optuna
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False


class SimpleLinearModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(10, 1)

    def forward(self, x):
        return self.fc(x)


class TestMarginalConvergenceTracker:

    def test_warmup_adherence(self):
        """Ensures that the tracker never stops before min_epochs even if loss is flat."""
        tracker = MarginalConvergenceTracker(
            min_epochs=5,
            max_epochs=20,
            patience=2,
            min_delta=1e-4,
            slope_threshold=1e-4
        )

        model = SimpleLinearModel()

        # Feed flat loss during warm-up
        for epoch in range(4):  # epochs 0, 1, 2, 3 (< min_epochs=5)
            stopped = tracker.step(epoch=epoch, loss=1.0, model=model)
            assert not stopped, f"Tracker stopped prematurely at epoch {epoch} during warm-up."

        # At epoch 4 (5th epoch), warm-up is completed and patience/slope can stop it
        stopped = tracker.step(epoch=4, loss=1.0, model=model)
        assert stopped, "Tracker should stop on flat loss once warm-up is fulfilled."

    def test_stop_on_patience_and_marginal_gain(self):
        """Verifies early stopping when loss improves by less than min_delta."""
        tracker = MarginalConvergenceTracker(
            min_epochs=3,
            max_epochs=50,
            patience=3,
            min_delta=0.01,
            restore_best_weights=True
        )
        model = SimpleLinearModel()

        # Decent improvements initially
        assert not tracker.step(0, 1.00, model)
        assert not tracker.step(1, 0.80, model)
        assert not tracker.step(2, 0.60, model)

        # Marginal gains (< min_delta=0.01)
        assert not tracker.step(3, 0.595, model)  # wait = 1
        assert not tracker.step(4, 0.594, model)  # wait = 2
        stopped = tracker.step(5, 0.593, model)   # wait = 3 == patience

        assert stopped
        assert tracker.best_loss == pytest.approx(0.60, abs=1e-3)
        assert tracker.best_epoch == 2
        assert "patience" in tracker.stop_reason or "slope" in tracker.stop_reason

    def test_restore_best_weights(self):
        """Ensures the best model weights are restored upon early stopping."""
        tracker = MarginalConvergenceTracker(
            min_epochs=3,
            max_epochs=20,
            patience=2,
            min_delta=0.05,
            restore_best_weights=True
        )
        model = SimpleLinearModel()

        # Set initial weight
        with torch.no_grad():
            model.fc.weight.fill_(1.0)
        
        # Step 0: loss 1.0 (best)
        tracker.step(0, 1.0, model)

        # Step 1: change weight to 2.0 and lower loss to 0.5 (new best!)
        with torch.no_grad():
            model.fc.weight.fill_(2.0)
        tracker.step(1, 0.5, model)

        # Step 2 & 3: change weight to 9.0 and worse loss (1.5, 2.0) -> triggers early stop
        with torch.no_grad():
            model.fc.weight.fill_(9.0)
        tracker.step(2, 1.5, model)
        stopped = tracker.step(3, 2.0, model)

        assert stopped
        # Model weight should be restored to 2.0 (the snapshot from step 1)
        assert torch.allclose(model.fc.weight, torch.tensor(2.0))

    def test_max_epochs_ceiling(self):
        """Verifies that the tracker stops strictly when reaching max_epochs."""
        tracker = MarginalConvergenceTracker(
            min_epochs=2,
            max_epochs=5,
            patience=10,  # huge patience so patience doesn't stop it
            slope_threshold=0.0,  # disable slope stop
            min_delta=0.0
        )
        model = SimpleLinearModel()

        for epoch in range(4):
            # Consistently improving loss
            stopped = tracker.step(epoch, 10.0 - epoch, model)
            assert not stopped

        # 5th epoch (epoch=4) reaches max_epochs=5
        stopped = tracker.step(4, 5.0, model)
        assert stopped
        assert tracker.stop_reason == "max_epochs_reached"

    def test_non_finite_loss_handling(self):
        """Ensures tracker safely stops on NaN or Inf loss."""
        tracker = MarginalConvergenceTracker(min_epochs=5, max_epochs=20)
        model = SimpleLinearModel()

        assert not tracker.step(0, 1.0, model)
        assert tracker.step(1, float("nan"), model)
        assert tracker.stop_reason == "nan_inf_loss"

    @pytest.mark.skipif(not OPTUNA_AVAILABLE, reason="Optuna not installed")
    def test_optuna_pruning_integration(self):
        """Tests integration with Optuna trial and pruning."""
        study = optuna.create_study(
            direction="minimize",
            pruner=optuna.pruners.ThresholdPruner(upper=1.0)
        )

        def objective(trial):
            tracker = MarginalConvergenceTracker(
                min_epochs=2,
                max_epochs=10,
                optuna_trial=trial,
                enable_pruning=True
            )
            # High loss should trigger ThresholdPruner
            tracker.step(0, 5.0)
            return tracker.best_loss

        with pytest.raises(optuna.TrialPruned):
            trial = study.ask()
            objective(trial)
