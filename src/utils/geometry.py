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
# File: src/utils/geometry.py
# Author: Gabriel Moraes
# Date: 2026-04-27
#
# Pure computational geometry functions.
# Extracted from FastMapMatcher to allow reuse across the codebase
# (e.g., CartographerAgent, spatial validators, etc.).

import math
import numpy as np
from typing import List, Tuple


def point_to_polyline_distance(px: float, py: float, polyline: List[Tuple[float, float]]) -> float:
    """
    Minimum perpendicular distance from point (px, py) to a polyline.
    Uses segment-by-segment projection with clamped parametric t.

    Args:
        px: X coordinate of the query point.
        py: Y coordinate of the query point.
        polyline: Ordered list of (x, y) vertices defining the polyline.

    Returns:
        Minimum distance in the same unit as the coordinates.
    """
    if not polyline:
        return float('inf')

    min_dist = float('inf')

    for i in range(len(polyline) - 1):
        ax, ay = polyline[i]
        bx, by = polyline[i + 1]

        # Vector AB
        abx = bx - ax
        aby = by - ay

        # Vector AP
        apx = px - ax
        apy = py - ay

        # Project AP onto AB, clamped to [0, 1]
        ab_sq = abx * abx + aby * aby
        if ab_sq < 1e-12:
            # Degenerate segment (zero length)
            dist = math.sqrt(apx * apx + apy * apy)
        else:
            t = max(0.0, min(1.0, (apx * abx + apy * aby) / ab_sq))
            # Closest point on segment
            cx = ax + t * abx
            cy = ay + t * aby
            dx = px - cx
            dy = py - cy
            dist = math.sqrt(dx * dx + dy * dy)

        min_dist = min(min_dist, dist)

    return min_dist


def frechet_distance(polyline_a: List[Tuple[float, float]], polyline_b: List[Tuple[float, float]]) -> float:
    """
    Discrete Fréchet distance between two polylines.
    Measures similarity between curves accounting for vertex ordering.

    Uses recursive DP for small inputs (n*m ≤ 10000) and switches to
    iterative DP for larger polylines to avoid stack overflow.

    Complexity: O(n·m) time and space.

    Args:
        polyline_a: First polyline as list of (x, y) tuples.
        polyline_b: Second polyline as list of (x, y) tuples.

    Returns:
        Fréchet distance in the same unit as the coordinates.
    """
    n = len(polyline_a)
    m = len(polyline_b)

    if n == 0 or m == 0:
        return float('inf')

    # Use iterative approach for large polylines to avoid stack overflow
    if n * m > 10000:
        return _frechet_iterative(polyline_a, polyline_b)

    # Dynamic programming table
    ca = np.full((n, m), -1.0)

    def _dist(i: int, j: int) -> float:
        dx = polyline_a[i][0] - polyline_b[j][0]
        dy = polyline_a[i][1] - polyline_b[j][1]
        return math.sqrt(dx * dx + dy * dy)

    def _frechet_rec(i: int, j: int) -> float:
        if ca[i, j] >= 0.0:
            return ca[i, j]

        d = _dist(i, j)

        if i == 0 and j == 0:
            ca[i, j] = d
        elif i == 0:
            ca[i, j] = max(_frechet_rec(0, j - 1), d)
        elif j == 0:
            ca[i, j] = max(_frechet_rec(i - 1, 0), d)
        else:
            ca[i, j] = max(
                min(
                    _frechet_rec(i - 1, j),
                    _frechet_rec(i - 1, j - 1),
                    _frechet_rec(i, j - 1)
                ),
                d
            )
        return ca[i, j]

    return _frechet_rec(n - 1, m - 1)


def _frechet_iterative(polyline_a: List[Tuple[float, float]], polyline_b: List[Tuple[float, float]]) -> float:
    """Iterative Fréchet distance for large polylines (avoids recursion limit)."""
    n = len(polyline_a)
    m = len(polyline_b)
    ca = np.zeros((n, m))

    def _dist(i, j):
        dx = polyline_a[i][0] - polyline_b[j][0]
        dy = polyline_a[i][1] - polyline_b[j][1]
        return math.sqrt(dx * dx + dy * dy)

    ca[0, 0] = _dist(0, 0)
    for i in range(1, n):
        ca[i, 0] = max(ca[i - 1, 0], _dist(i, 0))
    for j in range(1, m):
        ca[0, j] = max(ca[0, j - 1], _dist(0, j))

    for i in range(1, n):
        for j in range(1, m):
            ca[i, j] = max(
                min(ca[i - 1, j], ca[i - 1, j - 1], ca[i, j - 1]),
                _dist(i, j)
            )

    return ca[n - 1, m - 1]
