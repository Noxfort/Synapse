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
# File: src/strategies/veto_medoid_strategy.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import numpy as np
from typing import List, Dict

class VetoMedoidStrategy:
    """
    Mathematical Strategy (Strategy Pattern)
    Finds the medoid (most representative anomaly) in a list of events.
    Extracted from XAIManager (SRP).
    """

    @staticmethod
    def find_medoid(veto_buffer: List[Dict]) -> Dict:
        """
        Returns the event that represents the centroid of the vector cluster.
        """
        if not veto_buffer:
            raise ValueError("Cannot calculate medoid on empty buffer.")

        vectors = [item['vector'] for item in veto_buffer]
        matrix = np.array(vectors)
        centroid = np.mean(matrix, axis=0)
        distances = np.linalg.norm(matrix - centroid, axis=1)
        medoid_index = np.argmin(distances)
        
        return veto_buffer[medoid_index]
