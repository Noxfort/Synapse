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
# File: src/interfaces/interaction.py
# Author: Gabriel Moraes
# Date: 2026-08-28

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class IInteractionManager(Protocol):
    """
    Contract for UI interaction state (association mode, element selections).
    (SRP: Pure UI interaction state tracking).
    """

    def enter_association_mode(self, source_id: str) -> None:
        """Activate source-to-element association mode for a given source ID."""
        ...

    def exit_association_mode(self) -> None:
        """Deactivate association mode and clear current selection."""
        ...

    @property
    def is_active(self) -> bool:
        """Whether association mode is currently active."""
        ...

    @property
    def selected_id(self) -> Optional[str]:
        """Currently selected source ID awaiting element association."""
        ...
