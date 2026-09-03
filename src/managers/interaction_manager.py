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
# File: src/managers/interaction_manager.py
# Author: Gabriel Moraes
# Date: 2026-08-29

from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal

from src.interfaces.interaction import IInteractionManager


class InteractionManager(QObject):
    """
    Presentation/UI State Manager for user modes and element selection.
    
    SOLID Architecture:
    - [SRP] Exclusively tracks transient GUI interaction state (e.g. association mode).
    - [DIP] Satisfies IInteractionManager protocol structurally.
    """
    mode_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self._is_association_mode_active: bool = False
        self._selected_source_id: Optional[str] = None

    def enter_association_mode(self, source_id: str) -> None:
        """Activate association mode and select source ID."""
        self._is_association_mode_active = True
        self._selected_source_id = source_id
        self.mode_changed.emit(True)

    def exit_association_mode(self) -> None:
        """Deactivate association mode and clear selection."""
        self._is_association_mode_active = False
        self._selected_source_id = None
        self.mode_changed.emit(False)
    
    @property
    def is_active(self) -> bool:
        return self._is_association_mode_active
    
    @property
    def selected_id(self) -> Optional[str]:
        return self._selected_source_id


__all__ = ["InteractionManager"]
