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
# File: src/handlers/system_handler.py
# Author: Gabriel Moraes
# Date: 2026-08-30

"""
System Lifecycle & Diagnostics Command Handler (SOLID: SRP & DIP).

Translates IPC actions related to application lifecycle, online/offline pipeline runs,
and explainability (XAI) commands to the underlying MainController / SystemController.
"""

from typing import Any, Callable, Dict, Optional

from src.ipc.ipc_protocol import IpcMessage
from src.ipc.command_router import Responder
from src.utils.logging_setup import get_logger


class SystemCommandHandler:
    """Handles system lifecycle, flow controls, and diagnostic actions."""

    def __init__(
        self,
        controller: Any,
        on_shutdown: Optional[Callable[[], None]] = None,
        security_manager: Optional[Any] = None,
        audit_logger: Optional[Any] = None,
        report_service: Optional[Any] = None,
    ):
        self.controller = controller
        self.on_shutdown = on_shutdown
        self.security_manager = security_manager
        self.audit_logger = audit_logger
        self.report_service = report_service
        self.logger = get_logger("SystemCommandHandler")
        self._connected = False

    def _get_current_user(self) -> str:
        if self.security_manager and hasattr(self.security_manager, "last_auth_user"):
            return self.security_manager.last_auth_user or "SYSTEM"
        return "SYSTEM"

    def handle_get_system_status(self, msg: IpcMessage) -> Dict[str, Any]:
        recommended_phase = "IDLE_OPTIMIZATION"
        completed_phases = []
        if hasattr(self.controller, "system") and hasattr(self.controller.system, "sync_completed_phases"):
            stage = self.controller.system.sync_completed_phases()
            completed = getattr(self.controller.system, "_completed_phases", set())
            completed_phases = list(completed)
            if stage == "runtime":
                recommended_phase = "IDLE_ONLINE"
            elif stage == "bootstrap":
                recommended_phase = "IDLE_OFFLINE"
            else:
                recommended_phase = "IDLE_OPTIMIZATION"

        return {
            "status": "ok",
            "phase": recommended_phase,
            "completed_phases": completed_phases,
        }

    def handle_ping(self, msg: IpcMessage) -> Dict[str, Any]:
        if not self._connected:
            self._connected = True
            self.logger.info("🟢 [IPC STATUS] CONECTADO: Frontend Desktop (Tauri/React) conectado ao Core Python.")
        status_info = self.handle_get_system_status(msg)
        status_info["app"] = "SYNAPSE Core v2.0"
        return status_info

    def handle_start_optimization(self, msg: IpcMessage) -> Dict[str, Any]:
        if self.security_manager and self.security_manager.is_lockdown():
            raise RuntimeError("Operação bloqueada. O sistema está em estado de LOCKDOWN.")
        res = self.controller.start_optimization_flow()
        if self.audit_logger:
            self.audit_logger.log_action(self._get_current_user(), "START_OPTIMIZATION", "Início do fluxo de Otimização de Topologia")
        return {"started": res}

    def handle_stop_optimization(self, msg: IpcMessage) -> Dict[str, Any]:
        if hasattr(self.controller, "system"):
            self.controller.system.stop_optimization()
        if self.audit_logger:
            self.audit_logger.log_action(self._get_current_user(), "STOP_OPTIMIZATION", "Interrupção da Otimização de Topologia")
        return {"stopped": True}

    def handle_start_offline_bootstrap(self, msg: IpcMessage) -> Dict[str, Any]:
        if self.security_manager and self.security_manager.is_lockdown():
            raise RuntimeError("Operação bloqueada. O sistema está em estado de LOCKDOWN.")
        if hasattr(self.controller, "system"):
            self.controller.system.start_offline_bootstrap()
        if self.audit_logger:
            self.audit_logger.log_action(self._get_current_user(), "START_OFFLINE_BOOTSTRAP", "Início do Bootstrap Offline dos modelos MEH")
        return {"started": True}

    def handle_stop_offline_bootstrap(self, msg: IpcMessage) -> Dict[str, Any]:
        if hasattr(self.controller, "system"):
            self.controller.system.stop_offline_bootstrap()
        if self.audit_logger:
            self.audit_logger.log_action(self._get_current_user(), "STOP_OFFLINE_BOOTSTRAP", "Interrupção do Bootstrap Offline")
        return {"stopped": True}

    def handle_start_online_operation(self, msg: IpcMessage) -> Dict[str, Any]:
        if self.security_manager and self.security_manager.is_lockdown():
            raise RuntimeError("Operação bloqueada. O sistema está em estado de LOCKDOWN.")
        if hasattr(self.controller, "system"):
            self.controller.system.start_online_operation()
        if self.audit_logger:
            self.audit_logger.log_action(self._get_current_user(), "START_ONLINE_OPERATION", "Início da Operação Online em Tempo Real (HFT)")
        return {"started": True}

    def handle_stop_online_operation(self, msg: IpcMessage) -> Dict[str, Any]:
        if hasattr(self.controller, "system"):
            self.controller.system.stop_online_operation()
        if self.audit_logger:
            self.audit_logger.log_action(self._get_current_user(), "STOP_ONLINE_OPERATION", "Interrupção da Operação Online")
        return {"stopped": True}

    def handle_explain_buffer(self, msg: IpcMessage) -> Dict[str, Any]:
        if hasattr(self.controller, "system") and hasattr(self.controller.system, "cmd_explain_buffer"):
            self.controller.system.cmd_explain_buffer.emit()
        return {"requested": "buffer"}

    def handle_explain_local(self, msg: IpcMessage) -> Dict[str, Any]:
        node_id = msg.payload.get("node_id", "")
        if hasattr(self.controller, "system") and hasattr(self.controller.system, "cmd_explain_local"):
            self.controller.system.cmd_explain_local.emit(node_id)
        return {"requested": "local", "node_id": node_id}

    def handle_explain_global(self, msg: IpcMessage) -> Dict[str, Any]:
        if hasattr(self.controller, "system") and hasattr(self.controller.system, "cmd_explain_global"):
            self.controller.system.cmd_explain_global.emit()
        return {"requested": "global"}

    def handle_hot_swap_model(self, msg: IpcMessage) -> Dict[str, Any]:
        payload = msg.payload or {}
        model_path = payload.get("model_path", "")
        self.logger.info(f"🔄 [IPC] Hot-swap requested for model checkpoint: {model_path}")
        if hasattr(self.controller, "fenix_service") and self.controller.fenix_service:
            self.controller.fenix_service.request_model_hot_swap.emit(model_path)
        elif hasattr(self.controller, "system") and hasattr(self.controller.system, "request_model_hot_swap"):
            self.controller.system.request_model_hot_swap.emit(model_path)
        return {"hot_swap_requested": True, "model_path": model_path}

    def handle_get_process_health(self, msg: IpcMessage) -> Dict[str, Any]:
        import os
        return {
            "status": "healthy",
            "pid": os.getpid(),
            "supervised": os.environ.get("SYNAPSE_SUPERVISED") == "1",
        }

    def handle_generate_official_report(self, msg: IpcMessage) -> Dict[str, Any]:
        """Synthesizes the complete, authoritative Official Municipal Traffic Audit Report."""
        from src.services.traffic_report_service import TrafficReportService

        payload = msg.payload or {}
        result_id = payload.get("result_id")
        municipal_config = payload.get("municipal_config")
        xai_result = payload.get("xai_result")

        app_state = getattr(self.controller, "app_state", None)
        service = self.report_service or TrafficReportService(app_state=app_state)
        report_output = service.build_report(
            result_id=result_id,
            municipal_config=municipal_config,
            xai_result=xai_result,
        )

        if self.audit_logger:
            protocol = report_output.get("report", {}).get("protocol", "DESCONHECIDO")
            self.audit_logger.log_action(
                self._get_current_user(),
                "GENERATE_OFFICIAL_REPORT",
                f"Emissão de Laudo Técnico Oficial de Tráfego: {protocol}",
            )

        return {
            "success": True,
            "report": report_output["report"],
            "formatted_markdown": report_output["formatted_markdown"],
        }

    def handle_shutdown(self, msg: IpcMessage, responder: Responder) -> None:
        responder(True, {"shutting_down": True})
        if self.on_shutdown:
            self.on_shutdown()

