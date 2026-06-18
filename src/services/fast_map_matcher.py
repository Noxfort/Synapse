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
# File: src/services/fast_map_matcher.py
# Author: Gabriel Moraes
# Date: 2026-03-08

"""
FastMapMatcher — The First Line of Defense (CPU Heuristic Layer).

Architecture:
    1. R-Tree Spatial Index  → Instant candidate filtering (µs)
    2. Fréchet / Hausdorff   → Exact geometric distance (ms)
    3. Shannon Entropy        → Ambiguity thermometer  

If entropy is low  → match is confident, return immediately.
If entropy is high → ambiguity detected, escalate to neural disambiguator.
"""

import math
import numpy as np
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass

from rtree import index as rtree_index

from src.domain.entities import MapEdge
from src.utils.logging_setup import logger
from src.utils.geometry import point_to_polyline_distance, frechet_distance


# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MatchCandidate:
    """A single candidate edge with its matching score."""
    edge_id: str
    edge: MapEdge
    distance: float           # Geometric distance (meters)
    probability: float = 0.0  # Normalized probability [0, 1]


@dataclass
class MatchResult:
    """Complete result from the fast matching pipeline."""
    candidates: List[MatchCandidate]
    entropy: float              # Shannon Entropy H ∈ [0, log2(N)]
    best_edge_id: Optional[str] # Top candidate ID (may be None)
    best_probability: float     # Confidence of the best match [0, 1]
    is_ambiguous: bool          # True if entropy > threshold


# ─────────────────────────────────────────────────────────────────────────────
# FAST MAP MATCHER
# ─────────────────────────────────────────────────────────────────────────────

class FastMapMatcher:
    """
    CPU-only heuristic map matcher using R-Tree + geometric distance + entropy.
    
    Pipeline:
        match(lat, lon) → R-Tree filter → Fréchet distance → Probabilities → Entropy
    
    Usage:
        matcher = FastMapMatcher(edges)
        result = matcher.match(lat, lon, radius_m=200)
        if result.is_ambiguous:
            # Escalate to neural disambiguator
            ...
    """

    def __init__(self, edges: List[MapEdge], entropy_threshold: float = 0.7):
        """
        Args:
            edges: List of MapEdge entities with populated shape geometry.
            entropy_threshold: H above this → ambiguity (triggers neural).
        """
        self.edges = edges
        self.entropy_threshold = entropy_threshold
        self._edge_lookup: Dict[str, MapEdge] = {e.id: e for e in edges}
        
        # Build R-Tree spatial index
        self._rtree_idx = None
        self._rtree_id_map: Dict[int, str] = {}  # int_id → edge_id
        self._build_rtree()
        
        logger.info(
            f"[FastMapMatcher] ✅ R-Tree built: {len(edges)} edges indexed. "
            f"Entropy threshold: {entropy_threshold:.2f}"
        )

    # ─────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────────────

    def match(self, x: float, y: float, radius_m: float = 200.0) -> MatchResult:
        """
        Match a GPS coordinate to the nearest edge(s) using cascading heuristics.
        
        Args:
            x: X coordinate (SUMO local coords, not lat/lon).
            y: Y coordinate (SUMO local coords, not lat/lon).
            radius_m: Search radius in meters.
            
        Returns:
            MatchResult with candidates, entropy, and ambiguity flag.
        """
        candidate_ids = self._query_rtree(x, y, radius_m)
        
        if not candidate_ids:
            return MatchResult(
                candidates=[], entropy=0.0,
                best_edge_id=None, best_probability=0.0,
                is_ambiguous=False
            )
        
        # Geometric Distance: Exact point-to-polyline distance
        candidates: List[MatchCandidate] = []
        for edge_id in candidate_ids:
            edge = self._edge_lookup[edge_id]
            dist = point_to_polyline_distance(x, y, edge.shape)
            candidates.append(MatchCandidate(
                edge_id=edge_id, edge=edge, distance=dist
            ))
        
        return self._score_candidates(candidates)

    def match_polyline(self, polyline: List[Tuple[float, float]], radius_m: float = 200.0) -> MatchResult:
        """
        Match an entire polyline (e.g., from Waze/TomTom) against the map.
        Uses the centroid of the polyline for R-Tree query, then Fréchet for scoring.
        """
        if not polyline:
            return MatchResult([], 0.0, None, 0.0, False)
        
        # Centroid for R-Tree query
        cx = sum(p[0] for p in polyline) / len(polyline)
        cy = sum(p[1] for p in polyline) / len(polyline)
        
        candidate_ids = self._query_rtree(cx, cy, radius_m)
        if not candidate_ids:
            return MatchResult([], 0.0, None, 0.0, False)
        
        # Fréchet distance: curve-to-curve similarity
        candidates: List[MatchCandidate] = []
        for edge_id in candidate_ids:
            edge = self._edge_lookup[edge_id]
            dist = frechet_distance(polyline, edge.shape)
            candidates.append(MatchCandidate(
                edge_id=edge_id, edge=edge, distance=dist
            ))
        
        return self._score_candidates(candidates)

    # ─────────────────────────────────────────────────────────────────────
    # R-TREE INDEX
    # ─────────────────────────────────────────────────────────────────────

    def _build_rtree(self):
        """Build R-Tree spatial index from edge shapes."""
        p = rtree_index.Property()
        p.dimension = 2
        self._rtree_idx = rtree_index.Index(properties=p)
        
        for i, edge in enumerate(self.edges):
            if not edge.shape:
                continue
            
            xs = [pt[0] for pt in edge.shape]
            ys = [pt[1] for pt in edge.shape]
            bbox = (min(xs), min(ys), max(xs), max(ys))
            
            self._rtree_idx.insert(i, bbox)
            self._rtree_id_map[i] = edge.id

    def _query_rtree(self, x: float, y: float, radius_m: float) -> List[str]:
        """Query R-Tree for edges within radius of point."""
        if self._rtree_idx is None:
            return []
        
        bbox = (x - radius_m, y - radius_m, x + radius_m, y + radius_m)
        hits = list(self._rtree_idx.intersection(bbox))
        return [self._rtree_id_map[h] for h in hits if h in self._rtree_id_map]

    # ─────────────────────────────────────────────────────────────────────
    # SCORING PIPELINE
    # ─────────────────────────────────────────────────────────────────────

    def _score_candidates(self, candidates: List[MatchCandidate]) -> MatchResult:
        """Sort, compute probabilities, entropy, and build the final result."""
        candidates.sort(key=lambda c: c.distance)
        self._compute_probabilities(candidates)
        entropy = self._shannon_entropy(candidates)
        is_ambiguous = entropy > self.entropy_threshold and len(candidates) > 1
        best = candidates[0] if candidates else None

        return MatchResult(
            candidates=candidates,
            entropy=entropy,
            best_edge_id=best.edge_id if best else None,
            best_probability=best.probability if best else 0.0,
            is_ambiguous=is_ambiguous
        )

    @staticmethod
    def _compute_probabilities(candidates: List[MatchCandidate]):
        """Convert distances to probabilities using inverse softmax."""
        if not candidates:
            return
        
        eps = 1e-6
        inv_dists = np.array([1.0 / (c.distance + eps) for c in candidates])
        
        temperature = 0.5
        scaled = inv_dists / temperature
        scaled -= scaled.max()  # Numerical stability
        exp_vals = np.exp(scaled)
        probs = exp_vals / exp_vals.sum()
        
        for i, c in enumerate(candidates):
            c.probability = float(probs[i])

    @staticmethod
    def _shannon_entropy(candidates: List[MatchCandidate]) -> float:
        """Shannon Entropy: H = -Σ p·log₂(p). Low = certainty, High = ambiguity."""
        if not candidates:
            return 0.0
        
        H = 0.0
        for c in candidates:
            if c.probability > 1e-10:
                H -= c.probability * math.log2(c.probability)
        
        return H
