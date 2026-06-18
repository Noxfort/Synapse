# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2025 Noxfort Systems
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
# File: src/phases/command_registry.py
# Author: Gabriel Moraes
# Date: 2026-04-27
#
# SOLID Refactoring:
# - [OCP] Replaces the hardcoded if/elif dispatch chain in
#   RuntimeLauncher.handle_command(). New commands can be added via
#   register() without modifying the dispatcher itself.

import logging
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


class CommandRegistry:
    """
    Dynamic command dispatcher (Open/Closed Principle).

    Instead of a growing if/elif chain, commands are registered as
    (name → handler) pairs. The execute() method performs a single
    dict lookup — O(1) dispatch with zero conditional branches.

    Usage:
        registry = CommandRegistry()
        registry.register("run_cycle", engine.run_global_cycle)
        registry.execute("run_cycle")
    """

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}

    def register(self, command_type: str, handler: Callable) -> None:
        """
        Registers a handler for the given command type.

        Args:
            command_type: Unique string key (e.g. "run_cycle").
            handler: Callable that accepts an optional payload argument.
                     For payload-less commands, the payload will be None.
        """
        self._handlers[command_type] = handler
        logger.debug(f"[CommandRegistry] Registered: '{command_type}'")

    def unregister(self, command_type: str) -> None:
        """Removes a previously registered command handler."""
        self._handlers.pop(command_type, None)

    def execute(self, command_type: str, payload: object = None) -> None:
        """
        Dispatches a command to its registered handler.

        Args:
            command_type: The command key to look up.
            payload: Optional data to pass to the handler.
        """
        handler = self._handlers.get(command_type)
        if handler is None:
            logger.warning(
                f"[CommandRegistry] Unknown command: '{command_type}' "
                f"(registered: {list(self._handlers.keys())})"
            )
            return

        # Invoke: handlers that accept payload receive it;
        # handlers that don't (zero-arg) are called without it.
        try:
            if payload is not None:
                handler(payload)
            else:
                handler()
        except TypeError:
            # Fallback: handler signature doesn't match — try without payload
            handler()

    def clear(self) -> None:
        """Removes all registered handlers."""
        self._handlers.clear()

    @property
    def registered_commands(self) -> list:
        """Returns a list of currently registered command names."""
        return list(self._handlers.keys())
