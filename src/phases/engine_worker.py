# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2025 Noxfort Systems
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
# File: src/phases/engine_worker.py
# Author: Gabriel Moraes
# Date: 2026-04-27
#
# SOLID Refactoring — Extracted from runtime_launcher.py
# [SRP] This module has ONE responsibility: manage the Neural Inference
#       thread lifecycle (heartbeat, signal wiring, start/stop).

import traceback
from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThread, QTimer

from src.factories.engine_component_factory import EngineComponentFactory

if TYPE_CHECKING:
    from src.engine.inference_engine import InferenceEngine
    from src.services.linguist_service import LinguistService
    from src.workers.xai_worker import XAIWorker


class EngineWorker(QObject):
    """
    Thread 2 — Neural Inference Worker.

    Lives INSIDE the engine QThread. Single Responsibility:
    - Receive pre-built components from EngineComponentFactory (DIP)
    - Wire inter-component signals
    - Drive the heartbeat timer (1s neural inference cycles)
    - Manage child thread lifecycles (Linguist T4, XAI T3)

    This class was extracted from runtime_launcher.py to satisfy SRP —
    RuntimeLauncher only orchestrates threads, this class only runs
    the neural inference loop.
    """

    # --- Proxy signals (bubbled up to RuntimeLauncher) ---
    log_message = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    engines_started = pyqtSignal()

    # Data streams
    engine_data_processed = pyqtSignal(dict)
    engine_global_results = pyqtSignal(dict)
    kinetic_data_ready = pyqtSignal(dict)

    # Advanced streams
    audit_update = pyqtSignal(bool, float, float, list)
    linguist_update = pyqtSignal(str, str, float)
    drift_update = pyqtSignal(str, dict)
    xai_result_received = pyqtSignal(dict)

    def __init__(self, factory: EngineComponentFactory, fenix_service):
        """
        Args:
            factory: Pre-configured EngineComponentFactory (DIP — injected).
            fenix_service: FenixService for health monitoring.
        """
        super().__init__()
        self._factory = factory
        self.fenix_service = fenix_service
        self.inference_engine: Optional['InferenceEngine'] = None
        self._heartbeat: Optional[QTimer] = None

        # Thread 4 — Linguist (Standby)
        self._linguist_thread: Optional[QThread] = None
        self._linguist_service: Optional['LinguistService'] = None

        # Thread 3 — XAI (On-Demand)
        self._xai_worker: Optional['XAIWorker'] = None

    @pyqtSlot()
    def initialize(self):
        """
        Called when the QThread starts. Runs ENTIRELY on the worker thread.

        Construction is delegated to the factory. This method only
        wires signals and starts the heartbeat timer.
        """
        try:
            self.log_message.emit("[Launcher] ⏳ Building AI Engine on worker thread...")

            # ── 1. Delegate construction to factory (SRP + DIP) ────────
            components = self._factory.build()

            self.inference_engine = components.inference_engine
            self._xai_worker = components.xai_worker
            self._linguist_service = components.linguist_service

            # ── 2. Wire XAI signals (Thread 3 — On-Demand) ────────────
            self._xai_worker.result_ready.connect(self.xai_result_received)
            self.log_message.emit("[XAI] On-demand worker ready (ephemeral threads).")

            # ── 3. Wire neural output signals (Thread 2) ──────────────
            self._wire_engine_signals()

            # FENIX Health Check
            self.inference_engine.drift_update.connect(
                lambda t, p: self.fenix_service.check_health_metrics(p.get('loss', 0.0))
            )

            # ── 4. Start Linguist on dedicated thread (Thread 4) ──────
            self._start_linguist()

            # ── 5. Boot subsystems ────────────────────────────────────
            self.inference_engine.initialize_system()

            # Heartbeat ON THIS THREAD (drives neural inference)
            self._heartbeat = QTimer()
            self._heartbeat.timeout.connect(self._on_tick)
            self._heartbeat.start(1000)

            self.log_message.emit("[Launcher] Inference Engine Online.")
            self.engines_started.emit()

        except Exception as e:
            self.error_occurred.emit(f"Failed to build AI Engine: {e}")
            traceback.print_exc()

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    def _wire_engine_signals(self):
        """Connects InferenceEngine output signals to this worker's proxies."""
        self.inference_engine.data_processed.connect(self.engine_data_processed)
        self.inference_engine.global_cycle_results.connect(self.engine_global_results)
        self.inference_engine.kinetic_data_ready.connect(self.kinetic_data_ready)
        self.inference_engine.audit_update.connect(self.audit_update)
        self.inference_engine.drift_update.connect(self.drift_update)

    def _start_linguist(self):
        """Boots the Linguist service on its own standby thread (Thread 4)."""
        self._linguist_thread = QThread()
        self._linguist_service.moveToThread(self._linguist_thread)
        self._linguist_thread.start()

        # Wire: InferenceEngine → Linguist (cross-thread, queued)
        self.inference_engine.linguist_check_requested.connect(
            self._linguist_service.run_check
        )
        # Wire: Linguist results → launcher proxy
        self._linguist_service.update_signal.connect(self.linguist_update)

        self.log_message.emit("[Linguist] Standby thread started (Thread 4).")

    # =========================================================================
    # LIFECYCLE
    # =========================================================================

    @pyqtSlot()
    def _on_tick(self):
        """Heartbeat: runs run_global_cycle on the worker thread."""
        if self.inference_engine:
            self.inference_engine.run_global_cycle()

    @pyqtSlot()
    def stop(self):
        """Graceful shutdown of this thread and child threads."""
        # Stop heartbeat
        if self._heartbeat:
            self._heartbeat.stop()

        # Stop neural engine
        if self.inference_engine:
            self.inference_engine.stop()

        # Stop Linguist thread (Thread 4)
        if self._linguist_thread:
            self._linguist_thread.quit()
            self._linguist_thread.wait()
            self._linguist_thread = None
            self._linguist_service = None

        # Cleanup XAI resources (Thread 3, ephemeral)
        if self._xai_worker:
            self._xai_worker.unload_resources()
            self._xai_worker = None
