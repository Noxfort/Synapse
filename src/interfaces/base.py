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
# File: src/interfaces/base.py
# Author: Gabriel Moraes
# Date: 2026-08-19

from typing import Any, Protocol, runtime_checkable, Self


@runtime_checkable
class IDeviceMovable(Protocol):
    """Contract for models and pipelines that can be transferred across computing devices (CPU/GPU)."""
    def to(self, device: Any) -> Self:
        """Moves internal model/tensors to the specified computing device."""
        ...


@runtime_checkable
class IStepTrainable(Protocol):
    """Atomic contract for neural optimization step given a batch of data."""
    def train_step(self, batch_data: Any, **kwargs: Any) -> float:
        """Executes a single optimization step given a batch of data."""
        ...


# Backward compatibility alias for IStepTrainable
ITrainable = IStepTrainable

