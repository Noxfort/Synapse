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
# File: tests/unit/test_main_controller_solid.py
# Author: Gabriel Moraes
# Date: 2026-08-19

import pytest
from unittest.mock import MagicMock

from PyQt6.QtWidgets import QApplication

from src.main_controller import MainController
from src.factories.controller_factory import ControllerFactory
from src.factories.phase_factory import PhasePipelineFactory
from src.services.telemetry_service import TelemetryService
from src.domain.app_state import AppState
from src.managers.storage_manager import StorageManager
from src.interfaces.controllers import (
    ISystemController,
    IProjectController,
    IViewController,
    ITelemetryService
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_controller_factory_creation(qapp):
    """Verifies ControllerFactory builds and wires a complete MainController."""
    state = AppState()
    storage = StorageManager()
    telemetry = TelemetryService()
    
    controller = ControllerFactory.create_main_controller(
        app_state=state,
        storage=storage,
        telemetry_service=telemetry
    )
    
    assert controller.app_state is state
    assert controller.storage is storage
    assert controller.telemetry is telemetry
    assert controller.system is not None
    assert controller.project is not None
    assert controller.view is not None
    assert isinstance(controller.system, ISystemController)
    assert isinstance(controller.project, IProjectController)
    assert isinstance(controller.view, IViewController)
    assert isinstance(controller.telemetry, ITelemetryService)


def test_main_controller_pure_orchestration(qapp):
    """Verifies that MainController is a pure orchestrator relying on injected protocols (DIP & SRP)."""
    mock_system = MagicMock(spec=ISystemController)
    mock_project = MagicMock(spec=IProjectController)
    mock_view = MagicMock(spec=IViewController)
    mock_telemetry = MagicMock(spec=ITelemetryService)
    mock_state = MagicMock(spec=AppState)
    mock_storage = MagicMock(spec=StorageManager)

    controller = MainController(
        system_ctrl=mock_system,
        project_ctrl=mock_project,
        view_ctrl=mock_view,
        telemetry_service=mock_telemetry,
        app_state=mock_state,
        storage=mock_storage
    )

    assert controller.system is mock_system
    assert controller.project is mock_project
    assert controller.view is mock_view
    assert controller.telemetry is mock_telemetry

    # Test high-level orchestration: start_optimization_flow
    mock_system.start_optimization.return_value = True
    result = controller.start_optimization_flow()
    assert result is True
    mock_system.start_optimization.assert_called_once()
    mock_view.on_optimization_started.assert_called_once()

    # Test high-level orchestration: shutdown
    controller.shutdown()
    mock_system.stop_online_operation.assert_called_once()
    mock_telemetry.report_shutdown.assert_called_once()


def test_telemetry_service_error_and_shutdown(qapp):
    """Verifies telemetry incident and shutdown behavior."""
    mock_client = MagicMock()
    mock_client.enabled = True
    telemetry = TelemetryService(monitor_client=mock_client)

    telemetry.report_error("Sensor disconnection detected")
    mock_client.report_incident.assert_called_with(
        category="SOFTWARE",
        level="CRITICAL",
        message="Sensor disconnection detected"
    )


def test_phase_pipeline_factory_extension(qapp):
    """Verifies PhasePipelineFactory creates default phases and accepts custom ones (OCP)."""
    state = AppState()
    mock_fenix = MagicMock()
    
    pipeline = PhasePipelineFactory.create_pipeline(state, mock_fenix)
    assert "optimization" in pipeline
    assert "bootstrap" in pipeline
    assert "runtime" in pipeline

    # Test OCP extension
    custom_phase = MagicMock()
    extended_pipeline = PhasePipelineFactory.create_pipeline(
        state, mock_fenix, custom_phases={"analytics": custom_phase}
    )
    assert "analytics" in extended_pipeline
    assert extended_pipeline["analytics"] is custom_phase
