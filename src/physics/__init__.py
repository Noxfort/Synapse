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
# File: src/physics/__init__.py
# Author: Gabriel Moraes
# Date: 2026-08-17

from src.physics.physics_interfaces import (
    IFundamentalDiagram,
    IPhysicsConstraint,
    IPhysicsLossEngine,
)
from src.physics.fundamental_diagrams import (
    GreenshieldsDiagram,
    UnderwoodDiagram,
    NewellDaganzoDiagram,
)
from src.physics.kinematics import (
    NonNegativityBoundsConstraint,
    KinematicAccelerationConstraint,
    TemporalSmoothnessConstraint,
)
from src.physics.continuum import (
    ContinuumConservation,
    SpatialGraphConservation,
)
from src.physics.traffic_loss import TrafficPhysicsLoss

__all__ = [
    "IFundamentalDiagram",
    "IPhysicsConstraint",
    "IPhysicsLossEngine",
    "GreenshieldsDiagram",
    "UnderwoodDiagram",
    "NewellDaganzoDiagram",
    "NonNegativityBoundsConstraint",
    "KinematicAccelerationConstraint",
    "TemporalSmoothnessConstraint",
    "ContinuumConservation",
    "SpatialGraphConservation",
    "TrafficPhysicsLoss",
]
