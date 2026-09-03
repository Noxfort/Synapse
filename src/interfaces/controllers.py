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
# File: src/interfaces/controllers.py
# Author: Gabriel Moraes
# Date: 2026-08-19

"""
Abstract Controller and Telemetry Interfaces (SOLID: DIP & ISP).

Defines runtime-checkable protocols for all sub-controllers and services,
allowing MainController to depend purely on abstractions rather than concrete types.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ISystemController(Protocol):
    """Contract for system lifecycle and engine operations."""
    
    def start_optimization(self) -> bool:
        """Starts the optimization phase."""
        ...

    def stop_optimization(self) -> None:
        """Stops the optimization phase."""
        ...

    def start_offline_bootstrap(self) -> None:
        """Starts offline bootstrap phase."""
        ...

    def stop_offline_bootstrap(self) -> None:
        """Stops offline bootstrap phase."""
        ...

    def start_online_operation(self) -> None:
        """Starts online runtime processing."""
        ...

    def stop_online_operation(self) -> None:
        """Stops online runtime processing."""
        ...

    def sync_completed_phases(self) -> str:
        """Synchronizes and returns the recommended active phase based on disk artifacts."""
        ...

    def detect_completed_phases(self) -> set:
        """Inspects disk artifacts to return the set of completed phase names."""
        ...


@runtime_checkable
class IProjectController(Protocol):
    """Contract for project file and data source persistence."""

    def create_new_project(self) -> None:
        """Creates a fresh project state."""
        ...

    def load_project(self, path: str) -> None:
        """Loads a project from a specified path."""
        ...

    def save_project(self, path: str) -> None:
        """Saves current project to a specified path."""
        ...

    def add_data_source(self, name: str, source_type: str, connection_string: str) -> None:
        """Registers a new data source into the project."""
        ...

    def remove_data_source(self, source_id: str) -> None:
        """Removes a data source by ID."""
        ...


@runtime_checkable
class IViewController(Protocol):
    """Contract for UI state transitions and view logging."""

    def log(self, message: str) -> None:
        """Appends a log message to the view stream."""
        ...

    def status(self, message: str) -> None:
        """Updates the status message."""
        ...

    def error_alert(self, message: str) -> None:
        """Notifies the view of an error."""
        ...

    def on_optimization_started(self) -> None:
        """Triggers UI layout for optimization."""
        ...

    def on_online_system_started(self) -> None:
        """Triggers UI layout for online operation."""
        ...

    def on_project_loaded(self) -> None:
        """Triggers UI layout when a project is loaded."""
        ...

    def set_map_view_mode(self, mode: str) -> None:
        """Sets the map visual rendering mode."""
        ...


@runtime_checkable
class ITelemetryService(Protocol):
    """Contract for telemetry, observability and incident reporting."""

    def init_telemetry(self, enabled: bool, host: str, port: int) -> None:
        """Initializes the telemetry client with connection parameters."""
        ...

    def reconfigure_telemetry(self, enabled: bool, host: str, port: int) -> None:
        """Reconfigures the active telemetry client."""
        ...

    def report_error(self, message: str) -> None:
        """Reports a critical software error incident."""
        ...

    def report_shutdown(self) -> None:
        """Reports application shutdown and ensures queue flush."""
        ...
