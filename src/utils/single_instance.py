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
# File: src/utils/single_instance.py
# Author: Gabriel Moraes
# Date: 2026-08-29

import getpass
import logging
import os
import sys
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

logger = logging.getLogger(__name__)


class SingleInstanceGuard(QObject):
    """
    Ensures that only a single instance of the application runs per user session.
    Uses Qt's QLocalServer and QLocalSocket for inter-process communication (IPC).
    
    When a secondary instance attempts to start:
    1. It connects to the primary instance's QLocalServer.
    2. Sends an activation message (e.g., "ACTIVATE" or command-line arguments).
    3. Exits cleanly, allowing the primary instance to bring its window to the foreground.
    """

    activation_requested = pyqtSignal(str)

    def __init__(self, app_key: str = "synapse_core", parent: Optional[QObject] = None):
        super().__init__(parent)
        self.app_key = app_key
        self.server_name = self._generate_server_name(app_key)
        self.server: Optional[QLocalServer] = None
        self.is_primary = False

    @staticmethod
    def _generate_server_name(app_key: str) -> str:
        """
        Generates a unique, user-scoped socket identifier to prevent
        cross-user permission conflicts on multi-user systems.
        """
        try:
            user = getpass.getuser()
        except Exception:
            user = str(os.getuid()) if hasattr(os, "getuid") else "default_user"
        
        sanitized_user = "".join(c for c in user if c.isalnum() or c in ("-", "_"))
        return f"{app_key}_{sanitized_user}_ipc"

    def try_acquire(self, timeout_ms: int = 500, message: str = "ACTIVATE") -> bool:
        """
        Attempts to acquire the single-instance lock.
        
        Returns:
            True if this process is the primary instance and acquired the server.
            False if another instance is already running (message sent to existing instance).
        """
        # Step 1: Probe existing server via QLocalSocket
        probe_socket = QLocalSocket()
        probe_socket.connectToServer(self.server_name)
        
        if probe_socket.waitForConnected(timeout_ms):
            logger.info(f"[SingleInstance] Found existing instance on '{self.server_name}'. Sending focus message...")
            payload = (message.strip() + "\n").encode("utf-8")
            probe_socket.write(payload)
            probe_socket.waitForBytesWritten(timeout_ms)
            probe_socket.disconnectFromServer()
            probe_socket.close()
            self.is_primary = False
            return False

        probe_socket.close()

        # Step 2: If connection failed, remove stale socket file if left over from a previous crash
        QLocalServer.removeServer(self.server_name)

        # Step 3: Start QLocalServer for this primary instance
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._on_new_connection)
        
        if not self.server.listen(self.server_name):
            logger.error(
                f"[SingleInstance] Failed to start local server '{self.server_name}': {self.server.errorString()}"
            )
            # Try one more aggressive cleanup and re-listen
            QLocalServer.removeServer(self.server_name)
            if not self.server.listen(self.server_name):
                logger.critical(
                    f"[SingleInstance] Unrecoverable failure listening on '{self.server_name}': {self.server.errorString()}"
                )
                self.is_primary = False
                return False

        logger.info(f"[SingleInstance] Primary instance acquired server '{self.server_name}'.")
        self.is_primary = True
        return True

    def _on_new_connection(self) -> None:
        """Handles incoming IPC connections from secondary instances."""
        if not self.server:
            return

        client_socket = self.server.nextPendingConnection()
        if not client_socket:
            return

        has_emitted = False

        def _on_ready_read():
            nonlocal has_emitted
            try:
                if client_socket.isOpen():
                    data = bytes(client_socket.readAll()).decode("utf-8", errors="ignore").strip()
                    if not has_emitted:
                        has_emitted = True
                        logger.info(f"[SingleInstance] Received IPC message from secondary instance: '{data}'")
                        self.activation_requested.emit(data or "ACTIVATE")
            except Exception as e:
                logger.warning(f"[SingleInstance] Error reading IPC message: {e}")
                if not has_emitted:
                    has_emitted = True
                    self.activation_requested.emit("ACTIVATE")

        def _on_disconnected():
            nonlocal has_emitted
            if not has_emitted:
                has_emitted = True
                self.activation_requested.emit("ACTIVATE")
            client_socket.deleteLater()

        client_socket.readyRead.connect(_on_ready_read)
        client_socket.disconnected.connect(_on_disconnected)

        if client_socket.bytesAvailable() > 0:
            _on_ready_read()


    def cleanup(self) -> None:
        """Closes the server and removes the socket file on shutdown."""
        if self.server:
            try:
                self.server.close()
                self.server.deleteLater()
            except Exception:
                pass
            self.server = None
        QLocalServer.removeServer(self.server_name)
        self.is_primary = False
        logger.info(f"[SingleInstance] Cleaned up IPC server '{self.server_name}'.")

