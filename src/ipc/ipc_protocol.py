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
# File: src/ipc/ipc_protocol.py
# Author: Gabriel Moraes
# Date: 2026-08-29

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional
import json


@dataclass
class IpcMessage:
    """Represents an incoming command from the UI/Tauri process via STDIN."""
    action: str
    id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, raw: str) -> Optional['IpcMessage']:
        try:
            data = json.loads(raw.strip())
            return cls(
                action=data.get("action", ""),
                id=data.get("id"),
                payload=data.get("payload", {})
            )
        except Exception:
            return None


@dataclass
class IpcEvent:
    """Represents an asynchronous domain event emitted to STDOUT."""
    event: str
    data: Any = None
    type: str = "event"

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, default=str)


@dataclass
class IpcResponse:
    """Represents a response to a correlated command."""
    id: Optional[str]
    success: bool
    result: Any = None
    error: Optional[str] = None
    type: str = "response"

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, default=str)
