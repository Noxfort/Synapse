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
# File: src/optimization/optimization_task.py
# Author: Gabriel Moraes
# Date: 2026-04-27

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class OptimizationTask:
    """
    Declarative description of a single Optuna optimization phase.
    
    The OptimizerService iterates over a list of these tasks without
    knowing anything about the concrete agents or strategies — adhering
    to the Dependency Inversion Principle (DIP).
    
    Attributes:
        name: Internal key used for checkpoint dict (e.g., 'coordinator').
        label: Human-readable label with emoji for logs/UI.
        objective_fn: Callable(trial) -> float. The Optuna objective.
        slope_threshold: Convergence slope for early stopping.
        window: Number of past trials for convergence regression.
        enabled: Toggle to skip a phase without modifying the orchestrator (OCP).
        post_hook: Optional callable to run after optimization (e.g., save diploma).
    """
    name: str
    label: str
    objective_fn: Callable
    slope_threshold: float = 1e-5
    window: int = 25
    enabled: bool = True
    post_hook: Optional[Callable] = field(default=None, repr=False)
