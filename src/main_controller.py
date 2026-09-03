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
# File: src/main_controller.py
# Author: Gabriel Moraes
# Date: 2026-08-19

"""
Pure High-Level Orchestrator & Controller Aggregator (SOLID Architecture).

Adheres strictly to SOLID:
- [SRP] Zero direct object instantiation, zero telemetry logic, zero proxy signal repetition.
- [DIP] Injected with abstract protocols: ISystemController, IProjectController, IViewController, ITelemetryService.
- [ISP] Subsystems are segregated; callers connect directly to sub-controllers (system, project, view, telemetry).
- [OCP] Open to custom controllers, phases, and services injected via ControllerFactory.
"""

from typing import Optional, Any
from PyQt6.QtCore import QObject

from src.domain.app_state import AppState
from src.managers.storage_manager import StorageManager
from src.interfaces.controllers import (
    ISystemController,
    IProjectController,
    IViewController,
    ITelemetryService,
)


class MainController(QObject):
    """
    Pure High-Level Orchestrator & Controller Aggregator.
    Coordinates cross-cutting actions across System, Project, View, and Telemetry controllers.
    """

    def __init__(
        self,
        system_ctrl: ISystemController,
        project_ctrl: IProjectController,
        view_ctrl: IViewController,
        telemetry_service: ITelemetryService,
        app_state: AppState,
        storage: Optional[StorageManager] = None,
        fenix_service: Optional[Any] = None,
    ):
        super().__init__()
        self.system = system_ctrl
        self.project = project_ctrl
        self.view = view_ctrl
        self.telemetry = telemetry_service
        self.app_state = app_state
        self.storage = storage
        self.fenix_service = fenix_service

        # Backward compatibility aliases
        self.system_ctrl = self.system
        self.project_ctrl = self.project
        self.view_ctrl = self.view

        self._wire_internal_events()

    def _wire_internal_events(self):
        """Wires direct inter-controller notifications without intermediate proxy signals."""
        if hasattr(self.system, "log_message") and hasattr(self.view, "log"):
            self.system.log_message.connect(self.view.log)
        if hasattr(self.system, "status_message") and hasattr(self.view, "status"):
            self.system.status_message.connect(self.view.status)
        if hasattr(self.system, "error_occurred"):
            if hasattr(self.view, "error_alert"):
                self.system.error_occurred.connect(self.view.error_alert)
            self.system.error_occurred.connect(self.telemetry.report_error)

        if hasattr(self.project, "log_message") and hasattr(self.view, "log"):
            self.project.log_message.connect(self.view.log)
        if hasattr(self.project, "error_occurred"):
            if hasattr(self.view, "error_alert"):
                self.project.error_occurred.connect(self.view.error_alert)
            self.project.error_occurred.connect(self.telemetry.report_error)

        if hasattr(self.system, "online_system_started") and hasattr(self.view, "on_online_system_started"):
            self.system.online_system_started.connect(self.view.on_online_system_started)
        if hasattr(self.project, "project_loaded") and hasattr(self.view, "on_project_loaded"):
            self.project.project_loaded.connect(self.view.on_project_loaded)

    # --- High-Level Orchestration Flows (Cross-Subsystem Operations) ---
    def start_optimization_flow(self) -> bool:
        """Orchestrates starting optimization and notifying the view layer."""
        started = self.system.start_optimization()
        if started and hasattr(self.view, "on_optimization_started"):
            self.view.on_optimization_started()
        return bool(started)

    def shutdown(self):
        """Orchestrates graceful shutdown across all subsystems."""
        self.system.stop_online_operation()
        self.telemetry.report_shutdown()
