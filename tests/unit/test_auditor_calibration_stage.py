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
# File: tests/unit/test_auditor_calibration_stage.py
# Author: Gabriel Moraes
# Date: 2026-08-19

import os
import pytest
import torch
import numpy as np
import pandas as pd

from src.stages.auditor_calibration_stage import AuditorCalibrationStage
from src.agents.auditor_agent import AuditorAgent
from src.engine.neural_factory import NeuralFactory


def test_prepare_windows_with_nans(tmp_path):
    """Verifies that _prepare_windows cleans NaNs and creates valid sliding windows."""
    stage = AuditorCalibrationStage(str(tmp_path))
    
    # Create parquet with NaNs and infs
    golden_path = tmp_path / "golden.parquet"
    df = pd.DataFrame({
        "flow": [10.0, np.nan, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0] * 20,
        "speed": [50.0, 55.0, np.nan, 60.0, 65.0, 70.0, 75.0, 80.0] * 20,
        "density": [np.nan, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0] * 20,
    })
    df.to_parquet(golden_path)

    windows = stage._prepare_windows(str(golden_path))
    assert windows is not None
    assert isinstance(windows, np.ndarray)
    assert windows.shape[1] == stage.WINDOW_SIZE
    assert not np.isnan(windows).any()
    assert not np.isinf(windows).any()


def test_calibrate_threshold():
    """Verifies that _calibrate_threshold sets threshold on both calibrator and model."""
    stage = AuditorCalibrationStage("/tmp")
    agent = AuditorAgent(input_len=stage.WINDOW_SIZE, J=2, latent_dim=16)

    # Initialize hypersphere center with a dummy train step
    warmup_batch = torch.rand(8, stage.WINDOW_SIZE) * 50.0
    agent.train_step(warmup_batch)

    # Create dummy windows
    windows = np.random.uniform(10.0, 80.0, (32, stage.WINDOW_SIZE)).astype(np.float32)

    stage._calibrate_threshold(agent, windows)

    thresh_calibrator = agent.pipeline.calibrator.threshold
    thresh_model = agent.model.threshold

    assert isinstance(thresh_calibrator, float)
    assert thresh_calibrator > 0.0
    assert torch.is_tensor(thresh_model)
    assert pytest.approx(thresh_calibrator, abs=1e-5) == thresh_model.item()


def test_save_and_load_calibration_checkpoint(tmp_path):
    """Verifies checkpoint roundtrip between AuditorCalibrationStage and NeuralFactory."""
    stage = AuditorCalibrationStage(str(tmp_path))
    checkpoint_path = tmp_path / "auditor_calibrated.pth"

    agent = AuditorAgent(input_len=stage.WINDOW_SIZE, J=2, latent_dim=16)
    warmup_batch = torch.rand(8, stage.WINDOW_SIZE) * 50.0
    agent.train_step(warmup_batch)

    windows = np.random.uniform(10.0, 80.0, (16, stage.WINDOW_SIZE)).astype(np.float32)
    stage._calibrate_threshold(agent, windows)
    stage._save_checkpoint(agent, str(checkpoint_path))

    assert checkpoint_path.exists()
    assert checkpoint_path.stat().st_size > 0

    # Create fresh agent and factory
    fresh_agent = AuditorAgent(input_len=stage.WINDOW_SIZE, J=2, latent_dim=16)
    factory = NeuralFactory(weights_dir=str(tmp_path))
    factory._load_auditor_calibration(fresh_agent)

    # Verify state matches
    assert pytest.approx(fresh_agent.pipeline.calibrator.threshold, abs=1e-5) == agent.pipeline.calibrator.threshold
    assert pytest.approx(fresh_agent.model.threshold.item(), abs=1e-5) == agent.model.threshold.item()
    assert torch.allclose(fresh_agent.pipeline.calibrator.center.cpu(), agent.pipeline.calibrator.center.cpu())


def test_stage_execute_end_to_end(tmp_path):
    """Verifies complete execution of AuditorCalibrationStage on golden parquet."""
    stage = AuditorCalibrationStage(str(tmp_path))
    golden_path = tmp_path / "golden.parquet"
    checkpoint_path = tmp_path / "auditor_calibrated.pth"

    df = pd.DataFrame({
        f"col_{i}": np.random.uniform(5.0, 50.0, 200).astype(np.float32)
        for i in range(10)
    })
    df.to_parquet(golden_path)

    context = {
        "golden_path": str(golden_path),
        "auditor_checkpoint_path": str(checkpoint_path)
    }

    success = stage.execute(context)
    assert success is True
    assert checkpoint_path.exists()
    assert checkpoint_path.stat().st_size > 0

    # Re-executing with existing checkpoint should skip training quickly
    success_cached = stage.execute(context)
    assert success_cached is True
