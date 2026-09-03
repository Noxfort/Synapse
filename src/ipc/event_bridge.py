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
# File: src/ipc/event_bridge.py
# Author: Gabriel Moraes
# Date: 2026-08-30

"""
IPC Event Bridge (SOLID: SRP & DIP).

Translates internal Qt signals from domain controllers and AppState into asynchronous
JSON event broadcasts emitted to the frontend.
"""

from typing import Callable, Any, Optional
from src.ipc.serializers import TopologySerializer
from src.utils.logging_setup import get_logger


EventEmitter = Callable[[str, Any], None]


class IpcEventBridge:
    """
    Subscribes to Core Qt signals and adapts them to IPC event payloads.
    """

    def __init__(self, event_emitter: EventEmitter):
        self.emit_event = event_emitter
        self.logger = get_logger("IpcEventBridge")

    def bind_signals(self, controller: Any, app_state: Any) -> None:
        """
        Connects domain, controller, and telemetry signals to IPC event broadcasts.
        """
        system = getattr(controller, "system", None)
        project = getattr(controller, "project", None)
        state = app_state

        # 1. Telemetry & Status
        if system:
            self._safe_connect(system, "log_message", lambda msg: self.emit_event("log_message", {"message": msg, "level": "INFO"}))
            self._safe_connect(system, "status_message", lambda msg: self.emit_event("status_message", {"message": msg}))
            self._safe_connect(system, "error_occurred", lambda msg: self.emit_event("error_occurred", {"error": msg}))

            # 2. Lifecycle Transitions
            self._safe_connect(system, "optimization_finished", lambda: self.emit_event("phase_transition", {"phase": "IDLE_OFFLINE"}))
            self._safe_connect(system, "bootstrap_finished", lambda: self.emit_event("phase_transition", {"phase": "IDLE_ONLINE"}))
            self._safe_connect(system, "online_system_started", lambda: self.emit_event("phase_transition", {"phase": "RUNNING_ONLINE"}))
            self._safe_connect(system, "online_system_stopped", lambda: self.emit_event("phase_transition", {"phase": "IDLE_ONLINE"}))

            # 3. Real-time Streams
            self._safe_connect(system, "engine_data_processed", lambda d: self.emit_event("engine_data", d))
            self._safe_connect(system, "engine_global_results", lambda d: self.emit_event("global_results", d))
            self._safe_connect(system, "linguist_update", lambda src, typ, conf: self.emit_event("linguist_update", {"source": src, "type": typ, "confidence": conf}))
            self._safe_connect(system, "audit_update", lambda safe, err, thr, vec: self.emit_event("audit_update", {"safe": safe, "error": err, "threshold": thr, "vector": vec}))
            self._safe_connect(system, "drift_update", lambda src, metrics: self.emit_event("drift_update", {"source": src, "metrics": metrics}))
            self._safe_connect(system, "xai_result_received", lambda res: self.emit_event("xai_result", res))

        if project:
            self._safe_connect(project, "error_occurred", lambda msg: self.emit_event("error_occurred", {"error": msg}))

        # 4. AppState Model Mutations
        if state:
            self._safe_connect(
                state,
                "data_source_added",
                lambda src: self.emit_event("source_added", {
                    "id": getattr(src, "id", ""),
                    "name": getattr(src, "name", ""),
                    "is_local": getattr(src, "is_local", True),
                }),
            )
            self._safe_connect(state, "data_source_removed", lambda sid: self.emit_event("source_removed", {"id": sid}))
            self._safe_connect(
                state,
                "data_association_changed",
                lambda sid, eid: self.emit_event("source_associated", {"source_id": sid, "element_id": eid}),
            )
            self._safe_connect(
                state,
                "map_data_loaded",
                lambda: self.emit_event("map_loaded", TopologySerializer.serialize_topology(state)),
            )

    def _safe_connect(self, source: Any, signal_name: str, slot: Callable) -> None:
        """Helper to safely connect Qt signals if they exist on the source."""
        sig = getattr(source, signal_name, None)
        if sig is not None and hasattr(sig, "connect"):
            try:
                sig.connect(slot)
            except Exception as ex:
                self.logger.warning(f"Could not connect signal '{signal_name}': {ex}")
