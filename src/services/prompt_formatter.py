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
# File: src/services/prompt_formatter.py
# Author: Gabriel Moraes
# Date: 2026-08-29

from typing import Dict, List, Optional, Any
from src.interfaces.prompts import IPromptBuilder


class _SafeFormatter(dict):
    """Dictionary formatter that preserves missing format keys instead of raising KeyError."""
    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


class ChatPromptBuilder(IPromptBuilder):
    """
    Service for formatting prompt templates into chat messages for LLM inference.
    
    Responsibilities (SRP):
    - Interpolate dynamic variables into prompt templates safely.
    - Preserve missing variables to prevent formatting crashes.
    - Format system/user roles into standard chat message payloads.
    """

    def build_messages(
        self,
        template: Dict[str, str],
        source: Optional[str] = None,
        status: Optional[str] = None,
        values: Optional[Any] = None,
        **kwargs: Any
    ) -> List[Dict[str, str]]:
        """
        Builds and formats chat messages for an LLM agent from a raw template dictionary.
        
        Args:
            template: Dict containing template keys (e.g. 'system', 'user').
            source: Legacy source identifier.
            status: Legacy state / anomaly status.
            values: Legacy data payload.
            **kwargs: Dynamic contextual variables.
            
        Returns:
            List of message dicts [{'role': 'system', 'content': ...}, {'role': 'user', 'content': ...}].
        """
        context: Dict[str, Any] = dict(kwargs)
        if source is not None:
            context["source"] = source
        if status is not None:
            context["status"] = status
        if values is not None:
            context["values"] = values

        formatter = _SafeFormatter(context)
        system_raw = template.get("system", "")
        user_raw = template.get("user", "")

        system_content = system_raw.format_map(formatter) if system_raw else ""
        user_content = user_raw.format_map(formatter) if user_raw else ""

        messages: List[Dict[str, str]] = []
        if system_content:
            messages.append({"role": "system", "content": system_content})
        if user_content:
            messages.append({"role": "user", "content": user_content})

        return messages
