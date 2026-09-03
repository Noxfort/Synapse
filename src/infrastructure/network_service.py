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
# File: src/infrastructure/network_service.py
# Author: Gabriel Moraes
# Date: 2026-08-30

"""
Network Information and Diagnostics Service (SOLID: SRP).

Encapsulates low-level socket operations and local network metadata resolution.
"""

import socket
from typing import Dict, Any


class NetworkService:
    """Provides local network interface metadata."""

    @staticmethod
    def get_local_ip() -> str:
        """Determines the primary local outbound IP address."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("10.254.254.254", 1))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    @classmethod
    def get_network_info(cls, default_port: int = 8000) -> Dict[str, Any]:
        """Returns standard local network information payload."""
        return {
            "local_ip": cls.get_local_ip(),
            "default_port": default_port,
        }
