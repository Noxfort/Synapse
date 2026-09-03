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
# File: src/handlers/dialog_handler.py
# Author: Gabriel Moraes
# Date: 2026-08-30

"""
OS Dialog & Network Info Command Handler (SOLID: SRP & DIP).

Translates IPC actions related to native file picker dialogs and network interface queries.
"""

from typing import Any, Dict, Optional

from src.ipc.ipc_protocol import IpcMessage
from src.infrastructure.dialog_service import NativeDialogService
from src.infrastructure.network_service import NetworkService


class SystemDialogHandler:
    """Handles OS dialogs and network diagnostics."""

    def __init__(
        self,
        dialog_service: Optional[NativeDialogService] = None,
        network_service: Optional[NetworkService] = None,
    ):
        self.dialog_service = dialog_service or NativeDialogService()
        self.network_service = network_service or NetworkService()

    def handle_pick_file(self, msg: IpcMessage) -> Dict[str, Any]:
        title = msg.payload.get("title", "Selecionar Arquivo")
        filter_str = msg.payload.get("filter", "*")
        selected_path = self.dialog_service.pick_file(title, filter_str)
        return {"path": selected_path, "cancelled": selected_path is None}

    def handle_get_network_info(self, msg: IpcMessage) -> Dict[str, Any]:
        return self.network_service.get_network_info()
