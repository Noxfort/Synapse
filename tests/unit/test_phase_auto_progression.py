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
# File: tests/unit/test_phase_auto_progression.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from PyQt6.QtWidgets import QApplication

from src.domain.app_state import AppState
from src.domain.entities import DataSource, SourceType
from src.managers.storage_manager import StorageManager
from src.controllers.system_controller import SystemController
from src.phases.optimization_phase import OptimizationPhase
from src.handlers.system_handler import SystemCommandHandler
from src.ipc.ipc_protocol import IpcMessage




@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def create_fake_phase0_artifact(storage_mgr: StorageManager):
    """Creates a dummy best_hparams.pth checkpoint file."""
    ckpt_path = Path(storage_mgr.get_checkpoint_path()) / "best_hparams.pth"
    ckpt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ckpt_path, "wb") as f:
        f.write(b"FAKE_TORCH_MODEL_CHECKPOINT_DATA")
    return ckpt_path


def create_fake_phase1_artifacts(storage_mgr: StorageManager):
    """Creates dummy DataLake parquet files, ontology, schedule, and auditor checkpoints."""
    base_file = Path(storage_mgr.get_datalake_base_path()) / "base_data.parquet"
    base_file.parent.mkdir(parents=True, exist_ok=True)
    with open(base_file, "wb") as f:
        f.write(b"PARQUET_BASE")

    golden_file = Path(storage_mgr.get_datalake_golden_path()) / "golden_data.parquet"
    golden_file.parent.mkdir(parents=True, exist_ok=True)
    with open(golden_file, "wb") as f:
        f.write(b"PARQUET_GOLDEN")

    config_dir = Path(storage_mgr.get_config_path())
    config_dir.mkdir(parents=True, exist_ok=True)

    safetensors = config_dir / "ontology.safetensors"
    with open(safetensors, "wb") as f:
        f.write(b"SAFETENSORS_DATA")

    peak_sched = config_dir / "peak_schedule.json"
    with open(peak_sched, "w") as f:
        f.write('{"morning_peak": 8, "evening_peak": 18}')

    auditor_ckpt = config_dir / "auditor_calibrated.pth"
    with open(auditor_ckpt, "wb") as f:
        f.write(b"AUDITOR_CHECKPOINT")


def test_storage_manager_phase_detection(tmp_path):
    """Verifies that StorageManager accurately identifies Phase 0 and Phase 1 artifacts."""
    sm = StorageManager()
    # Override root to tmp_path
    sm.project_root = tmp_path / "Synapse"
    sm.checkpoint_dir = sm.project_root / "Checkpoint"
    sm.datalake_dir = sm.project_root / "datalake"
    sm.base_dir = sm.datalake_dir / "base"
    sm.golden_dir = sm.datalake_dir / "golden"
    sm._ensure_structure()

    assert sm.has_phase0_artifacts() is False
    assert sm.has_phase1_artifacts() is False

    create_fake_phase0_artifact(sm)
    assert sm.has_phase0_artifacts() is True
    assert sm.has_phase1_artifacts() is False

    create_fake_phase1_artifacts(sm)
    assert sm.has_phase0_artifacts() is True
    assert sm.has_phase1_artifacts() is True


def test_system_controller_auto_phase_sync(tmp_path):
    """Tests that SystemController automatically synchronizes phase state based on storage."""
    sm = StorageManager()
    sm.project_root = tmp_path / "Synapse"
    sm.checkpoint_dir = sm.project_root / "Checkpoint"
    sm.datalake_dir = sm.project_root / "datalake"
    sm.base_dir = sm.datalake_dir / "base"
    sm.golden_dir = sm.datalake_dir / "golden"
    sm._ensure_structure()

    app_state = AppState()
    fenix = MagicMock()
    phases = {
        "optimization": MagicMock(),
        "bootstrap": MagicMock(),
        "runtime": MagicMock(),
    }

    sc = SystemController(app_state, sm, phases, fenix)

    # 1. No artifacts -> Start at Phase 0
    assert sc.sync_completed_phases() == "optimization"
    assert "optimization" not in sc._completed_phases
    assert "bootstrap" not in sc._completed_phases

    # 2. Add Phase 0 artifact -> Advance to Phase 1
    create_fake_phase0_artifact(sm)
    assert sc.sync_completed_phases() == "bootstrap"
    assert "optimization" in sc._completed_phases
    assert "bootstrap" not in sc._completed_phases

    # 3. Add Phase 1 artifacts -> Advance to Phase 2 (Live Operation)
    create_fake_phase1_artifacts(sm)
    assert sc.sync_completed_phases() == "runtime"
    assert "optimization" in sc._completed_phases
    assert "bootstrap" in sc._completed_phases


def test_system_controller_auto_jump_from_phase0_to_phase2(tmp_path):
    """Tests that if Phase 0 completes (or skips) and Phase 1 artifacts already exist, it jumps to Phase 2."""
    sm = StorageManager()
    sm.project_root = tmp_path / "Synapse"
    sm.checkpoint_dir = sm.project_root / "Checkpoint"
    sm.datalake_dir = sm.project_root / "datalake"
    sm.base_dir = sm.datalake_dir / "base"
    sm.golden_dir = sm.datalake_dir / "golden"
    sm._ensure_structure()

    create_fake_phase1_artifacts(sm)

    app_state = AppState()
    fenix = MagicMock()
    phases = {
        "optimization": MagicMock(),
        "bootstrap": MagicMock(),
        "runtime": MagicMock(),
    }

    sc = SystemController(app_state, sm, phases, fenix)

    bootstrap_finished_emitted = []
    optimization_finished_emitted = []
    sc.bootstrap_finished.connect(lambda: bootstrap_finished_emitted.append(True))
    sc.optimization_finished.connect(lambda: optimization_finished_emitted.append(True))

    # Trigger completion of Phase 0
    sc._on_optimization_finished()

    # Since Phase 1 artifacts already exist, it should automatically emit bootstrap_finished (jump to Phase 2)
    assert bootstrap_finished_emitted == [True]
    assert optimization_finished_emitted == []
    assert "optimization" in sc._completed_phases
    assert "bootstrap" in sc._completed_phases


def test_optimization_phase_intelligent_skip(tmp_path):
    """Verifies that OptimizationPhase skips processing if best_hparams.pth already exists."""
    app_state = AppState()

    map_file = str(tmp_path / "test.net.xml")
    with open(map_file, "w") as f:
        f.write("<net></net>")
    app_state.set_map_source_path(map_file)

    # Add required live local + global sources
    app_state.add_data_source(DataSource(
        id="src_local",
        name="Camera 1",
        source_type=SourceType.API,
        connection_string="http://cam.local",
        is_local=True
    ))
    app_state.add_data_source(DataSource(
        id="src_global",
        name="Waze API",
        source_type=SourceType.API,
        connection_string="http://waze.local",
        is_local=False
    ))

    opt_phase = OptimizationPhase(app_state)

    finished_signals = []
    opt_phase.optimization_finished.connect(lambda: finished_signals.append(True))

    # Mock checkpoint file existence
    with patch("os.path.exists", side_effect=lambda p: True if "best_hparams.pth" in str(p) or str(p) == map_file else False), \
         patch("os.path.getsize", return_value=1024):
        success = opt_phase.start()
        assert success is True
        assert finished_signals == [True]
        assert opt_phase.opt_thread is None  # Thread was skipped cleanly


def test_system_status_auto_sets_phase(tmp_path):
    """Verifies that SystemCommandHandler automatically reports IDLE_ONLINE based on disk artifacts on boot."""
    sm = StorageManager()
    sm.project_root = tmp_path / "Synapse"
    sm.checkpoint_dir = sm.project_root / "Checkpoint"
    sm.datalake_dir = sm.project_root / "datalake"
    sm.base_dir = sm.datalake_dir / "base"
    sm.golden_dir = sm.datalake_dir / "golden"
    sm._ensure_structure()

    create_fake_phase0_artifact(sm)
    create_fake_phase1_artifacts(sm)

    app_state = AppState()
    fenix = MagicMock()
    phases = {
        "optimization": MagicMock(),
        "bootstrap": MagicMock(),
        "runtime": MagicMock(),
    }

    sc = SystemController(app_state, sm, phases, fenix)

    mock_controller = MagicMock()
    mock_controller.app_state = app_state
    mock_controller.system = sc

    handler = SystemCommandHandler(mock_controller)
    status_response = handler.handle_get_system_status(IpcMessage(action="get_system_status"))

    # Since both Phase 0 & 1 artifacts exist, phase should be IDLE_ONLINE (Phase 2)
    assert status_response["phase"] == "IDLE_ONLINE"
    assert "optimization" in status_response["completed_phases"]
    assert "bootstrap" in status_response["completed_phases"]

