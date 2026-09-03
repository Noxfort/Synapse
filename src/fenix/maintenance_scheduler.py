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
# File: src/fenix/maintenance_scheduler.py
# Author: Gabriel Moraes
# Date: 2026-08-19

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Optional
from src.utils.logging_setup import logger


class MaintenanceScheduler:
    """
    Manages autonomous opportunity window scanning based on a weekly schedule.
    Slot states: 0 = VALLEY (maintenance window), 1 = NORMAL, 2 = PEAK.
    """

    def __init__(self, schedule_path: Optional[Path] = None):
        self.schedule_path = schedule_path or Path("Synapse/data/maintenance_schedule.json")
        self.schedule_map: Dict[str, int] = {}

    def load_schedule(self) -> Dict[str, int]:
        """Loads schedule JSON mapping from disk."""
        if self.schedule_path.exists():
            try:
                with open(self.schedule_path, 'r', encoding='utf-8') as f:
                    self.schedule_map = json.load(f)
                logger.info(f"[MaintenanceScheduler] 📅 Maintenance Schedule Loaded ({len(self.schedule_map)} slots).")
            except Exception as e:
                logger.error(f"[MaintenanceScheduler] Failed to load schedule JSON: {e}")
                self.schedule_map = {}
        else:
            self.schedule_map = {}
        return self.schedule_map

    def is_opportunity_slot(self, dt: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        Checks if given or current datetime falls into a Valley slot (0).
        
        Returns:
            Tuple[bool, str]: (is_valley, slot_key formatted as 'weekday_hour')
        """
        now = dt or datetime.now()
        key = f"{now.weekday()}_{now.hour}"
        state = self.schedule_map.get(key, 1)  # Default to 1 (NORMAL)
        return (state == 0, key)

    def clear(self):
        """Clears loaded schedule."""
        self.schedule_map = {}
