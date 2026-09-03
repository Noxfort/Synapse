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
# File: src/phases/runtime_launcher.py
# Author: Gabriel Moraes
# Date: 2026-02-13

import traceback
from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThread

from src.domain.app_state import AppState
from src.phases.command_registry import CommandRegistry
from src.phases.engine_worker import EngineWorker
from src.factories.engine_component_factory import EngineComponentFactory

if TYPE_CHECKING:
    from src.managers.kse_manager import KSEManager
    from src.services.fenix_service import FenixService


class RuntimeLauncher(QObject):
    """
    Handles the Compute Layer (Phase 2b).

    Single Responsibility: Orchestrate thread lifecycles.
    - Start/stop the AI Engine thread (EngineWorker)
    - Start/stop the KSE Physics thread
    - Proxy signals between threads and the UI layer
    - Route commands via CommandRegistry

    Collaborators (each in their own module):
    - EngineWorker          → engine_worker.py      (neural loop)
    - CommandRegistry       → command_registry.py   (command dispatch)
    - EngineComponentFactory → engine_component_factory.py (DI)
    """

    # --- TELEMETRY SIGNALS ---
    log_message = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    # --- LIFECYCLE SIGNALS ---
    engines_started = pyqtSignal()
    engines_stopped = pyqtSignal()

    # --- DATA OUTPUTS ---
    packet_ready_to_send = pyqtSignal(dict)

    # Visualization / Debug Streams
    engine_data_processed = pyqtSignal(dict)
    engine_global_results = pyqtSignal(dict)
    kinetic_data_ready = pyqtSignal(dict)

    # --- ADVANCED STREAMS ---
    audit_update = pyqtSignal(bool, float, float, list)
    linguist_update = pyqtSignal(str, str, float)
    drift_update = pyqtSignal(str, dict)
    xai_result_received = pyqtSignal(dict)

    def __init__(self, app_state: AppState, fenix_service: 'FenixService'):
        super().__init__()
        self.app_state = app_state
        self.fenix_service = fenix_service

        from src.managers.kse_manager import KSEManager
        self._KSEManager = KSEManager

        # Thread handles
        self.engine_thread: Optional[QThread] = None
        self._engine_worker: Optional[EngineWorker] = None

        self.kse_thread: Optional[QThread] = None
        self.kse_manager: Optional['KSEManager'] = None

        # [OCP] Command Registry
        self._command_registry = CommandRegistry()

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def start_engines(self):
        """Initializes and starts all compute threads."""
        if self._engine_worker:
            self.log_message.emit("[Launcher] Engines already running.")
            return

        self.log_message.emit("[Launcher] 🚀 Initializing Compute Engines...")

        try:
            self._start_kse_thread()
            self._start_engine_thread()
        except Exception as e:
            self.error_occurred.emit(f"Failed to start Engines: {str(e)}")
            traceback.print_exc()

    def stop_engines(self):
        """Safely terminates all compute threads."""
        self.log_message.emit("[Launcher] 🛑 Stopping Compute Engines...")

        self._command_registry.clear()
        self._stop_kse_thread()
        self._stop_engine_thread()

        self.engines_stopped.emit()

    def handle_command(self, command_type: str, payload: object = None):
        """Route commands via CommandRegistry (OCP)."""
        self._command_registry.execute(command_type, payload)

    # =========================================================================
    # THREAD LIFECYCLE (Private)
    # =========================================================================

    def _start_kse_thread(self):
        """Boots the KSE Physics Engine on its dedicated thread."""
        self.kse_thread = QThread()
        self.kse_manager = self._KSEManager(self.app_state)
        self.kse_manager.moveToThread(self.kse_thread)

        self.kse_thread.started.connect(self.kse_manager.start)
        self.kse_manager.data_ready_for_transmission.connect(self.packet_ready_to_send)
        self.kse_manager.log_message.connect(self.log_message.emit)

        self.kse_thread.start()
        self.log_message.emit("[KSE] Physics Engine Started on Dedicated Thread.")

    def _stop_kse_thread(self):
        """Gracefully shuts down the KSE thread."""
        if self.kse_manager:
            self.kse_manager.stop()
        if self.kse_thread:
            self.kse_thread.quit()
            self.kse_thread.wait()
            self.kse_thread = None
            self.kse_manager = None

    def _start_engine_thread(self):
        """Boots the AI Engine (EngineWorker) on Thread 2."""
        factory = EngineComponentFactory(self.app_state)
        self._engine_worker = EngineWorker(factory, self.fenix_service)
        self.engine_thread = QThread()
        self._engine_worker.moveToThread(self.engine_thread)

        self._wire_worker_signals()

        self.engine_thread.started.connect(self._engine_worker.initialize)
        self.engine_thread.finished.connect(self.engine_thread.deleteLater)

        self.engine_thread.start()

    def _stop_engine_thread(self):
        """Gracefully shuts down the AI Engine thread."""
        if self._engine_worker:
            self._engine_worker.stop()
        if self.engine_thread:
            self.engine_thread.quit()
            self.engine_thread.wait()
            self.engine_thread = None
            self._engine_worker = None

    # =========================================================================
    # SIGNAL WIRING
    # =========================================================================

    def _wire_worker_signals(self):
        """Connects EngineWorker signals to RuntimeLauncher proxy signals."""
        w = self._engine_worker

        # Telemetry
        w.log_message.connect(self.log_message)
        w.error_occurred.connect(self.error_occurred)

        # Lifecycle — also triggers command registration
        w.engines_started.connect(self.engines_started)
        w.engines_started.connect(self._register_commands)

        # Data Streams
        w.engine_data_processed.connect(self.engine_data_processed)
        w.engine_global_results.connect(self.engine_global_results)
        w.kinetic_data_ready.connect(self.kinetic_data_ready)

        # Advanced Streams
        w.audit_update.connect(self.audit_update)
        w.linguist_update.connect(self.linguist_update)
        w.drift_update.connect(self.drift_update)
        w.xai_result_received.connect(self.xai_result_received)

        # Critical Link: AI → Physics (cross-thread, safe via QueuedConnection)
        w.engine_global_results.connect(self._relay_engine_to_kse)

    @pyqtSlot()
    def _register_commands(self):
        """Populates the CommandRegistry once the engine is ready (OCP)."""
        if not self._engine_worker or not self._engine_worker.inference_engine:
            return

        worker = self._engine_worker
        engine = worker.inference_engine
        router = worker.data_flow_router
        xai = worker.xai_manager
        graph = worker.graph_manager
        r = self._command_registry

        if router:
            r.register("process_data", router.process_data_point)

        r.register("run_cycle", engine.run_global_cycle)

        if xai:
            r.register("explain_buffer", lambda: xai.process_buffer_strategy(
                [n.id for n in self.app_state.get_all_nodes()]
            ))
            r.register("explain_local", lambda sid: (
                xai.explain_local(sid, graph.get_node(sid))
                if graph and graph.get_node(sid)
                else None
            ))
            r.register("explain_global", lambda: (
                xai.explain_global(
                    getattr(getattr(engine, 'processor', None), 'fuser', None),
                    graph.nodes,
                    seq_len=60
                )
                if graph and graph.nodes
                else None
            ))

        r.register("update_model", lambda p: self.log_message.emit(
            f"[Launcher] Model update requested: {p}"
        ))

    @pyqtSlot(dict)
    def _relay_engine_to_kse(self, results: dict):
        """Syncs the Physics Engine (KSE) with the latest AI Snapshot."""
        if self.kse_manager:
            snapshot = results.get('sensor_snapshot', {})
            self.kse_manager.sync_with_reality(snapshot)
