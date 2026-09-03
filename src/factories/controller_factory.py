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
# File: src/factories/controller_factory.py
# Author: Gabriel Moraes
# Date: 2026-08-19

"""
Controller Factory & Composition Root (SOLID: SRP & DIP).

Centralizes the assembly and dependency injection of the entire controller hierarchy.
Decouples MainController from knowing concrete details of sub-controllers, services, and storage.
"""

from typing import Optional, Dict, Any, TYPE_CHECKING

from src.domain.app_state import AppState
from src.managers.storage_manager import StorageManager
from src.services.fenix_service import FenixService
from src.services.telemetry_service import TelemetryService
from src.factories.phase_factory import PhasePipelineFactory
from src.controllers.project_controller import ProjectController
from src.controllers.system_controller import SystemController
from src.controllers.view_controller import ViewController
from src.interfaces.controllers import (
    ISystemController,
    IProjectController,
    IViewController,
    ITelemetryService
)

if TYPE_CHECKING:
    from src.main_controller import MainController


class ControllerFactory:
    """
    Composition Root factory that builds the MainController with injected dependencies.
    """

    @classmethod
    def create_main_controller(
        cls,
        app_state: Optional[AppState] = None,
        storage: Optional[StorageManager] = None,
        telemetry_service: Optional[ITelemetryService] = None,
        system_ctrl: Optional[ISystemController] = None,
        project_ctrl: Optional[IProjectController] = None,
        view_ctrl: Optional[IViewController] = None,
        custom_phases: Optional[Dict[str, Any]] = None
    ) -> 'MainController':
        """
        Assembles all domain, storage, service, and controller dependencies
        and constructs a fully wired MainController facade.
        """
        # Lazy import of MainController to avoid circular import issues
        from src.main_controller import MainController

        state = app_state if app_state is not None else AppState()
        storage_mgr = storage if storage is not None else StorageManager()
        telemetry = telemetry_service if telemetry_service is not None else TelemetryService()

        # Build sub-controllers if not explicitly provided
        if project_ctrl is None:
            project_ctrl = ProjectController(state, storage_mgr)

        if view_ctrl is None:
            view_ctrl = ViewController()

        fenix = FenixService(storage_mgr, state)
        if system_ctrl is None:
            phases = PhasePipelineFactory.create_pipeline(state, fenix, custom_phases)
            system_ctrl = SystemController(state, storage_mgr, phases, fenix)

        return MainController(
            system_ctrl=system_ctrl,
            project_ctrl=project_ctrl,
            view_ctrl=view_ctrl,
            telemetry_service=telemetry,
            app_state=state,
            storage=storage_mgr,
            fenix_service=fenix
        )
