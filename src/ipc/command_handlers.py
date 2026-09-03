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
# File: src/ipc/command_handlers.py
# Author: Gabriel Moraes
# Date: 2026-08-31

"""
Backward-compatibility bridge re-exporting handlers from `src.handlers`.
"""

from src.handlers.system_handler import SystemCommandHandler
from src.handlers.map_handler import MapCommandHandler
from src.handlers.source_handler import SourceCommandHandler
from src.handlers.database_handler import DatabaseCommandHandler
from src.handlers.dialog_handler import SystemDialogHandler
from src.handlers.handler_registry import register_default_command_handlers

__all__ = [
    "SystemCommandHandler",
    "MapCommandHandler",
    "SourceCommandHandler",
    "DatabaseCommandHandler",
    "SystemDialogHandler",
    "register_default_command_handlers",
]
