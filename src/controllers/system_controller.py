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
# File: src/controllers/system_controller.py
# Author: Gabriel Moraes
# Date: 2026-02-16

import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

# --- Domain ---
from src.domain.app_state import AppState

# --- Managers ---
from src.managers.storage_manager import StorageManager

# --- Services (Abstracted interface) ---
from typing import Dict, Any

class SystemController(QObject):
    """
    The Master Operations Controller.
    
    Refactored V39 (SOLID Architecture):
    - [SRP] Removed OS folder scaffolding (Moved to StorageManager).
    - [DIP] Receives initialized `FenixService` and `phases` dictionary via Injection.
    - [OCP] Uses a flexible State Machine ruleset instead of hardcoded if/else rules.
    """

    # --- TELEMETRY SIGNALS (Aggregated) ---
    log_message = pyqtSignal(str)
    status_message = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    # --- LIFECYCLE SIGNALS ---
    optimization_finished = pyqtSignal()
    bootstrap_finished = pyqtSignal()
    online_system_started = pyqtSignal()
    online_system_stopped = pyqtSignal()
    
    # --- DATA STREAMS (Proxied from Runtime) ---
    engine_data_processed = pyqtSignal(dict)
    engine_global_results = pyqtSignal(dict)
    kinetic_data_ready = pyqtSignal(dict)
    
    # --- ADVANCED STREAMS ---
    audit_update = pyqtSignal(bool, float, float, list)
    linguist_update = pyqtSignal(str, str, float)
    drift_update = pyqtSignal(str, dict)
    xai_result_received = pyqtSignal(dict)

    # --- COMMANDS ---
    cmd_process_data = pyqtSignal(str, object)
    cmd_run_cycle = pyqtSignal()
    cmd_update_model = pyqtSignal(str)
    
    cmd_explain_buffer = pyqtSignal()
    cmd_explain_local = pyqtSignal(str)
    cmd_explain_global = pyqtSignal()

    def __init__(self, app_state: AppState, storage_manager: StorageManager, phases: Dict[str, Any], fenix_service: Any):
        super().__init__()
        self.app_state = app_state
        self.storage = storage_manager
        
        # [DIP] Injected Dependencies
        self.fenix_service = fenix_service
        self.phases = phases
        
        # [OCP] Dynamic State Tracking
        self._completed_phases = set()

        # Connect Storage
        if self.storage:
            try:
                self.storage.connect()
            except Exception as e:
                print(f"[SystemController] Storage Connection Warning: {e}")

        self._connect_fenix_signals()
        
        # --- Wire Up Injected Phases ---
        if "optimization" in self.phases:
            self._connect_optimization_phase(self.phases["optimization"])
        if "bootstrap" in self.phases:
            self._connect_bootstrap_phase(self.phases["bootstrap"])
        if "runtime" in self.phases:
            self._connect_runtime_phase(self.phases["runtime"])
            self._connect_commands(self.phases["runtime"])
        
        self.log_message.emit("[SystemController] 🟢 Initialized (V39 SOLID Final).")

    def _connect_fenix_signals(self):
        """Bridges FENIX service signals to UI log/status."""
        self.fenix_service.cycle_started.connect(lambda msg: self.log_message.emit(f"[FENIX] 🔥 {msg}"))
        self.fenix_service.cycle_finished.connect(self._on_fenix_finished)
        self.fenix_service.progress_update.connect(lambda msg, pct: self.status_message.emit(f"FENIX: {msg} ({pct}%)"))

    def _on_fenix_finished(self, success, msg):
        status_icon = '✅' if success else '❌'
        self.log_message.emit(f"[FENIX] {status_icon} {msg}")

    # =========================================================================
    # PHASE WIRING
    # =========================================================================

    def _connect_optimization_phase(self, phase_obj):
        phase_obj.log_message.connect(self.log_message)
        phase_obj.error_occurred.connect(self.error_occurred)
        phase_obj.optimization_finished.connect(self._on_optimization_finished)

    def _connect_bootstrap_phase(self, phase_obj):
        phase_obj.log_message.connect(self.log_message)
        phase_obj.bootstrap_finished.connect(self._on_bootstrap_finished)

    def _connect_runtime_phase(self, phase_obj):
        # Telemetry
        phase_obj.log_message.connect(self.log_message)
        phase_obj.status_message.connect(self.status_message)
        phase_obj.error_occurred.connect(self.error_occurred)
        
        # Lifecycle
        phase_obj.system_started.connect(self.online_system_started)
        phase_obj.system_stopped.connect(self.online_system_stopped)
        
        # Data Streams
        phase_obj.engine_data_processed.connect(self.engine_data_processed)
        phase_obj.engine_global_results.connect(self.engine_global_results)
        phase_obj.kinetic_data_ready.connect(self.kinetic_data_ready)
        phase_obj.audit_update.connect(self.audit_update)
        phase_obj.linguist_update.connect(self.linguist_update)
        phase_obj.drift_update.connect(self.drift_update)
        phase_obj.xai_result_received.connect(self.xai_result_received)

    def _connect_commands(self, runtime_obj):
        """Routes external commands (e.g. from UI) to the Runtime Phase with On-Demand fallback."""
        self.cmd_process_data.connect(lambda t, p: runtime_obj.handle_command("process_data", p))
        self.cmd_run_cycle.connect(lambda: runtime_obj.handle_command("run_cycle"))
        self.cmd_update_model.connect(lambda p: runtime_obj.handle_command("update_model", p))
        self.cmd_explain_buffer.connect(lambda: self._handle_explain_buffer_cmd(runtime_obj))
        self.cmd_explain_local.connect(lambda pid: self._handle_explain_local_cmd(runtime_obj, pid))
        self.cmd_explain_global.connect(lambda: self._handle_explain_global_cmd(runtime_obj))

    def _get_on_demand_xai(self):
        if not hasattr(self, "_on_demand_xai_manager") or self._on_demand_xai_manager is None:
            from src.workers.xai_worker import XAIWorker
            from src.managers.xai_manager import XAIManager
            from src.services.semantic_enricher import SemanticEnricher
            worker = XAIWorker(model_config={"feature_dim": 1})
            worker.result_ready.connect(self.xai_result_received.emit)
            enricher = SemanticEnricher(self.app_state)
            self._on_demand_xai_manager = XAIManager(worker, enricher)
            self._on_demand_xai_worker = worker
        return self._on_demand_xai_manager

    def _handle_explain_buffer_cmd(self, runtime_obj):
        if runtime_obj and getattr(runtime_obj, "launcher", None) and getattr(runtime_obj.launcher, "_engine_worker", None):
            runtime_obj.handle_command("explain_buffer")
        else:
            xai = self._get_on_demand_xai()
            nodes = [n.id for n in self.app_state.get_all_nodes()] if hasattr(self.app_state, "get_all_nodes") else []
            xai.process_buffer_strategy(nodes)

    def _handle_explain_local_cmd(self, runtime_obj, sid: str):
        resolved_sid = sid
        if not resolved_sid and hasattr(self.app_state, "get_all_nodes"):
            all_nodes = self.app_state.get_all_nodes()
            if all_nodes:
                resolved_sid = all_nodes[0].id
        if not resolved_sid and hasattr(self.app_state, "get_all_data_sources"):
            sources = self.app_state.get_all_data_sources()
            if sources:
                resolved_sid = sources[0].id
        if not resolved_sid:
            resolved_sid = "Sensor_Principal"

        if runtime_obj and getattr(runtime_obj, "launcher", None) and getattr(runtime_obj.launcher, "_engine_worker", None):
            runtime_obj.handle_command("explain_local", resolved_sid)
        else:
            xai = self._get_on_demand_xai()
            node = self.app_state.get_node(resolved_sid) if hasattr(self.app_state, "get_node") else None
            xai.explain_local(resolved_sid, node)

    def _handle_explain_global_cmd(self, runtime_obj):
        if runtime_obj and getattr(runtime_obj, "launcher", None) and getattr(runtime_obj.launcher, "_engine_worker", None):
            runtime_obj.handle_command("explain_global")
        else:
            xai = self._get_on_demand_xai()
            nodes_dict = {}
            if hasattr(self.app_state, "get_all_nodes"):
                for n in self.app_state.get_all_nodes():
                    nodes_dict[n.id] = n
            xai.explain_global(None, nodes_dict, seq_len=12)

    # =========================================================================
    # INTERNAL HANDLERS (Dynamic State Completion & Auto-Progression)
    # =========================================================================

    def detect_completed_phases(self) -> set:
        """Inspects disk artifacts via StorageManager to detect previously completed phases."""
        completed = set()
        if self.storage:
            if hasattr(self.storage, "has_phase0_artifacts") and self.storage.has_phase0_artifacts():
                completed.add("optimization")
            if hasattr(self.storage, "has_phase1_artifacts") and self.storage.has_phase1_artifacts():
                if "optimization" in completed:
                    completed.add("bootstrap")
        return completed

    def sync_completed_phases(self) -> str:
        """
        Synchronizes internal state with persisted artifacts and returns the recommended active phase.
        Returns: 'runtime', 'bootstrap', or 'optimization'.
        """
        detected = self.detect_completed_phases()
        self._completed_phases.update(detected)

        if "optimization" in self._completed_phases and "bootstrap" in self._completed_phases:
            return "runtime"
        elif "optimization" in self._completed_phases:
            return "bootstrap"
        return "optimization"

    def _on_optimization_finished(self):
        self._completed_phases.add("optimization")
        self.log_message.emit("🔒 Security: Phase 0 (Optimization) Verified.")

        # Check if Phase 1 is also already completed on disk
        if self.storage and hasattr(self.storage, "has_phase1_artifacts") and self.storage.has_phase1_artifacts():
            self._completed_phases.add("bootstrap")
            self.log_message.emit("⚡ Auto-Progression: Phase 1 (Bootstrap) artifacts already present. Skipping directly to Phase 2 (Live Operation).")
            self.status_message.emit("Phase 0 & 1 Complete. Ready for Phase 2 (Live Operation).")
            self.bootstrap_finished.emit()
        else:
            self.status_message.emit("Phase 0 Complete. Ready for Phase 1.")
            self.optimization_finished.emit()

    def _on_bootstrap_finished(self):
        self._completed_phases.add("bootstrap")
        self.log_message.emit("🔒 Security: Phase 1 (Bootstrap) Verified.")
        self.status_message.emit("Phase 1 Complete. Ready for Phase 2.")
        self.bootstrap_finished.emit()

    # =========================================================================
    # PUBLIC API (State Machine)
    # =========================================================================

    def _execute_phase(self, phase_name: str, prerequisites: list) -> bool:
        """
        Generic State Machine executor. Evaluates rules before starting a mapped phase.
        Automatically syncs with disk artifacts before verifying prerequisites.
        """
        self.sync_completed_phases()

        for req in prerequisites:
            if req not in self._completed_phases:
                msg = f"⛔ Phase '{req}' must be completed before starting '{phase_name}'."
                self.log_message.emit(msg)
                self.error_occurred.emit(msg)
                return False
                
        if phase_name in self.phases:
            result = self.phases[phase_name].start()
            # If start() returns a bool, respect it; otherwise assume success
            return result if isinstance(result, bool) else True
        else:
            self.error_occurred.emit(f"⛔ Required system phase '{phase_name}' is not registered.")
            return False

    def _halt_phase(self, phase_name: str):
        if phase_name in self.phases:
            self.phases[phase_name].stop()

    # --- External Invocation API ---
    def start_optimization(self):
        # We don't blindly wipe completed_phases if artifacts exist, but if starting explicitly, allow rerun
        return self._execute_phase("optimization", prerequisites=[])

    def stop_optimization(self):
        self._halt_phase("optimization")

    def start_offline_bootstrap(self):
        return self._execute_phase("bootstrap", prerequisites=["optimization"])

    def stop_offline_bootstrap(self):
        self._halt_phase("bootstrap")

    def start_online_operation(self):
        return self._execute_phase("runtime", prerequisites=["optimization", "bootstrap"])

    def stop_online_operation(self):
        self._halt_phase("runtime")
