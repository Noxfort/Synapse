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
# File: src/interfaces/trainers.py
# Author: Gabriel Moraes
# Date: 2026-08-19

from typing import Any, Dict, Protocol, runtime_checkable
from src.interfaces.base import IStepTrainable, IDeviceMovable, ITrainable


@runtime_checkable
class IFuserTrainer(IStepTrainable, IDeviceMovable, Protocol):
    """Contract for Fuser neural optimization and training routines."""
    def train(self, inputs: Any, targets: Any, epochs: int = 100, batch_size: int = 16, **kwargs: Any) -> float: ...


@runtime_checkable
class IAuditorTrainer(IStepTrainable, IDeviceMovable, Protocol):
    """Contract for Auditor neural optimization and adaptive threshold routines."""
    ...


@runtime_checkable
class IImputerTrainer(IStepTrainable, IDeviceMovable, Protocol):
    """Contract for Imputer masked training routines."""
    ...


@runtime_checkable
class ICorrectorTrainer(IStepTrainable, IDeviceMovable, Protocol):
    """Contract for Corrector PI-DVAE training and convergence routines."""
    def train(self, data: Any, epochs: int = 100, batch_size: int = 64, **kwargs: Any) -> Dict[str, list]: ...


@runtime_checkable
class ISpecialistTrainer(IStepTrainable, IDeviceMovable, Protocol):
    """Contract for Specialist training routines."""
    def train(self, inputs: Any, targets: Any, epochs: int = 1, batch_size: int = 32) -> float: ...


@runtime_checkable
class ILinguistTrainer(IStepTrainable, IDeviceMovable, Protocol):
    """Contract for NeuroSymbolic reasoning training routines."""
    def train_step(self, batch_data: Any, epochs: int = 10, semantic_type: Any = None) -> float: ...


@runtime_checkable
class ICoordinatorTrainer(IStepTrainable, IDeviceMovable, Protocol):
    """Contract for graph neural network optimization."""
    ...


@runtime_checkable
class ICartographerTrainer(IStepTrainable, IDeviceMovable, Protocol):
    """Contract for Sinkhorn Cross-Attention graph matching training routines."""
    def train_step(self, source_data: Any, mutant_data: Any = None, ground_truth: Any = None) -> float: ...


