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
# File: src/agents/cartographer_agent.py
# Author: Gabriel Moraes
# Date: 2026-03-08

"""
CartographerAgent — The Hybrid Map Matcher.

Refactored V2 (SOLID):
- Neural disambiguation pipeline extracted to CartographerPipeline (SRP).
- Agent is now a thin orchestrator: init model, dispatch to heuristic or pipeline.
"""

import torch
import torch.optim as optim
import logging
from typing import Any, Dict, List, Tuple, Optional
from torch.amp import autocast, GradScaler

from src.agents.base_agent import BaseAgent
from src.models.sinkhorn_cross_attention import SinkhornCrossAttention
from src.services.fast_map_matcher import FastMapMatcher
from src.services.cartographer_pipeline import CartographerPipeline
from src.domain.entities import MapEdge, MapNode

logger = logging.getLogger("Synapse.CartographerAgent")


class CartographerAgent(BaseAgent):
    """
    The Cartographer Agent ('O Cartógrafo').
    
    Cascading Pipeline:
    - Low entropy  → Fast heuristic match (CPU, microseconds)
    - High entropy → Neural disambiguation via CartographerPipeline (GPU, milliseconds)
    
    SOLID V2:
    - Neural match logic delegated to CartographerPipeline service.
    - Agent owns: model init, inference dispatch, train_step, map injection.
    """

    def __init__(
        self,
        raw_dim: int = 11,
        d_model: int = 64,
        n_heads: int = 4,
        n_gat_layers: int = 2,
        sinkhorn_iters: int = 10,
        dropout: float = 0.1,
        temperature: float = 0.1,
        learning_rate: float = 1e-3,
        entropy_threshold: float = 0.7,
        crop_radius: float = 200.0,
    ):
        # 1. Create Model
        model = SinkhornCrossAttention(
            raw_dim=raw_dim,
            d_model=d_model,
            n_heads=n_heads,
            n_gat_layers=n_gat_layers,
            sinkhorn_iters=sinkhorn_iters,
            dropout=dropout,
            temperature=temperature,
        )

        # 2. Initialize Base
        super().__init__(model=model, name="CartographerAgent")

        # 3. Optimizer & Scaler
        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        self.scaler = GradScaler('cuda' if torch.cuda.is_available() else 'cpu')

        # 4. Cascade thresholds
        self.entropy_threshold = entropy_threshold
        self.crop_radius = crop_radius

        # 5. Services (injected via set_map_data)
        self.fast_matcher: Optional[FastMapMatcher] = None
        self._pipeline: Optional[CartographerPipeline] = None

    def _get_current_device(self) -> torch.device:
        try:
            return next(self.model.parameters()).device
        except StopIteration:
            return torch.device("cpu")

    # ─── Domain-Specific: Map Injection ───────────────────────────────────

    def set_map_data(self, edges: List[MapEdge], nodes: List[MapNode]):
        """
        Inject map topology. Builds FastMapMatcher and CartographerPipeline.
        """
        self.fast_matcher = FastMapMatcher(edges, entropy_threshold=self.entropy_threshold)
        self._pipeline = CartographerPipeline(
            model=self.model,
            edges=edges,
            nodes=nodes
        )

        logger.info(
            f"[{self.name}] 🗺️ Map data set: {len(edges)} edges, "
            f"{len(nodes)} nodes. R-Tree index built."
        )

    # ─── BaseAgent Interface ──────────────────────────────────────────────

    def inference(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Primary map matching inference (cascading pipeline).
        Dispatches to heuristic or neural pipeline based on entropy.
        """
        if self.fast_matcher is None:
            return {'edge_id': None, 'confidence': 0.0, 'method': 'no_map', 'entropy': 0.0}

        x = input_data.get('x', 0.0)
        y = input_data.get('y', 0.0)
        polyline = input_data.get('polyline')

        # ── STEP 1: Fast Heuristic (CPU) ──
        if polyline and len(polyline) >= 2:
            fast_result = self.fast_matcher.match_polyline(polyline, self.crop_radius)
        else:
            fast_result = self.fast_matcher.match(x, y, self.crop_radius)

        if not fast_result.candidates:
            return {'edge_id': None, 'confidence': 0.0, 'method': 'none', 'entropy': 0.0}

        # ── STEP 2: Check Entropy ──
        if not fast_result.is_ambiguous:
            return {
                'edge_id': fast_result.best_edge_id,
                'confidence': fast_result.best_probability,
                'method': 'heuristic',
                'entropy': fast_result.entropy,
            }

        # ── STEP 3: Neural Disambiguation (Delegated to Pipeline) ──
        return self._pipeline.disambiguate(
            x, y, fast_result, polyline, self._get_current_device()
        )

    def train_step(self, batch_data: Any) -> float:
        """Standard Training Step (AMP)."""
        self.model.train()
        device = self._get_current_device()

        source_graph, target_graph, gt_alignment = batch_data
        source_graph = source_graph.to(device)
        target_graph = target_graph.to(device)
        gt_alignment = gt_alignment.to(device)

        self.optimizer.zero_grad()
        device_type = device.type if device.type != 'mps' else 'cpu'

        with autocast(device_type=device_type, enabled=(device.type == 'cuda')):
            predicted = self.model(source_graph, target_graph)
            loss = SinkhornCrossAttention.alignment_loss(predicted, gt_alignment)

        self.scaler.scale(loss).backward()
        self.scaler.step(self.optimizer)
        self.scaler.update()

        return loss.item()

    # ─── Convenience Wrappers ─────────────────────────────────────────────

    def match_point(self, x: float, y: float) -> Dict[str, Any]:
        """Match a single GPS point."""
        return self.inference({'x': x, 'y': y})

    def match_polyline(self, polyline: List[Tuple[float, float]]) -> Dict[str, Any]:
        """Match a polyline from external sensor."""
        return self.inference({'polyline': polyline})
