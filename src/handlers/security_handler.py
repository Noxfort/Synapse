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
# File: src/handlers/security_handler.py
# Author: Gabriel Moraes
# Date: 2026-09-03

"""
Security Command Handler (SOLID: SRP & DIP).
Handles security authentication, user account operations, lockdown verification, and audit logs.
"""

from typing import Any, Callable, Optional

from src.ipc.ipc_protocol import IpcMessage
from src.ipc.command_router import Responder
from src.security.security_manager import SecurityManager
from src.security.audit_logger import AuditLogger
from src.utils.logging_setup import get_logger


class SecurityCommandHandler:
    """
    Handles all incoming IPC requests related to authentication, account management, and lockdown failsafe.
    """

    def __init__(
        self,
        security_manager: Optional[SecurityManager] = None,
        audit_logger: Optional[AuditLogger] = None,
        event_emitter: Optional[Callable[[str, Any], bool]] = None,
        telemetry_service: Optional[Any] = None,
    ):
        self.logger = get_logger("SecurityCommandHandler")
        self.security_manager = security_manager or SecurityManager()
        self.audit_logger = audit_logger or AuditLogger()
        self.event_emitter = event_emitter or (lambda event, data=None: True)
        self.telemetry_service = telemetry_service
        self.last_auth_user = "SYSTEM"

    def handle_authenticate(self, msg: IpcMessage, responder: Responder) -> None:
        """Authenticates user credentials and checks for lockdown conditions."""
        username = msg.payload.get("username", "").strip()
        password = msg.payload.get("password", "")

        if not username or not password:
            responder(False, None, "Preencha o nome de usuário e a senha.")
            return

        was_locked = self.security_manager.is_lockdown()
        success, role_or_msg = self.security_manager.authenticate(username, password)
        if success:
            self.last_auth_user = username
            self.audit_logger.log_action(
                username, "LOGIN_SUCCESS", f"Sessão autenticada como {role_or_msg}"
            )
            self.logger.info(f"User '{username}' successfully authenticated with role '{role_or_msg}'.")
            
            # If unlocking from lockdown, notify frontend and monitor
            if was_locked and not self.security_manager.is_lockdown():
                self.event_emitter("lockdown_event", {"active": False})
                if self.telemetry_service:
                    self.telemetry_service.report_incident(
                        "SOFTWARE",
                        "INFO",
                        f"LOCKDOWN de segurança desativado pelo usuário: {username}"
                    )

            responder(True, {"success": True, "role": role_or_msg, "username": username})
        else:
            self.audit_logger.log_action(
                username or "UNKNOWN", "LOGIN_FAILED", f"Falha de autenticação ({role_or_msg})"
            )
            self.logger.warning(f"Failed authentication attempt for '{username}': {role_or_msg}")

            if self.telemetry_service:
                self.telemetry_service.report_incident(
                    "SOFTWARE",
                    "WARNING",
                    f"Falha de autenticação detectada para o usuário: {username}"
                )

            if self.security_manager.is_lockdown():
                self.audit_logger.log_action(
                    "SYSTEM", "LOCKDOWN_TRIGGERED", "Sistema bloqueado devido a múltiplas tentativas falhas."
                )
                self.event_emitter("lockdown_event", {"active": True})
                if self.telemetry_service:
                    self.telemetry_service.report_incident(
                        "SOFTWARE",
                        "CRITICAL",
                        "LOCKDOWN de segurança ativado devido a múltiplas falhas de login."
                    )

            responder(False, None, role_or_msg)

    def handle_check_lockdown(self, msg: IpcMessage, responder: Responder) -> None:
        """Returns the current lockdown state of the system."""
        is_locked = self.security_manager.is_lockdown()
        if is_locked:
            self.event_emitter("lockdown_event", {"active": True})
        responder(True, {"active": is_locked})

    def handle_list_users(self, msg: IpcMessage, responder: Responder) -> None:
        """Returns the list of registered users."""
        users = self.security_manager.list_users()
        responder(True, {"users": users})

    def handle_add_user(self, msg: IpcMessage, responder: Responder) -> None:
        """Adds a new user account."""
        username = msg.payload.get("username", "").strip()
        password = msg.payload.get("password", "")
        role = msg.payload.get("role", "OPERATOR").upper()

        success = self.security_manager.add_user(username, password, role)
        if success:
            self.audit_logger.log_action(
                self.last_auth_user, "ADD_USER", f"Usuário '{username}' adicionado ({role})."
            )
            users = self.security_manager.list_users()
            responder(True, {"success": True, "users": users})
        else:
            responder(
                False,
                None,
                "Falha ao criar usuário. Verifique se o nome já existe ou se os campos são válidos.",
            )

    def handle_remove_user(self, msg: IpcMessage, responder: Responder) -> None:
        """Removes a user account."""
        username = msg.payload.get("username", "").strip()
        success = self.security_manager.remove_user(username)
        if success:
            self.audit_logger.log_action(
                self.last_auth_user, "REMOVE_USER", f"Usuário '{username}' removido."
            )
            if self.telemetry_service:
                self.telemetry_service.report_incident(
                    "SOFTWARE",
                    "WARNING",
                    f"Usuário removido da base de segurança: {username}"
                )
            users = self.security_manager.list_users()
            responder(True, {"success": True, "users": users})
        else:
            responder(False, None, f"Não foi possível remover o usuário '{username}'.")

    def handle_get_audit_logs(self, msg: IpcMessage, responder: Responder) -> None:
        """Returns the most recent security audit logs."""
        limit = msg.payload.get("limit", 100)
        logs = self.audit_logger.get_logs(limit=limit)
        responder(True, {"logs": logs})
