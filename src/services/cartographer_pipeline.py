# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# File: src/services/cartographer_pipeline.py
# Author: Gabriel Moraes
# Date: 2026-04-26

import torch
import logging
from typing import Dict, Any, List, Tuple, Optional
from torch.amp import autocast

from src.services.line_graph_builder import LineGraphBuilder
from src.models.sinkhorn_cross_attention import SinkhornCrossAttention
from src.domain.entities import MapEdge, MapNode

logger = logging.getLogger("Synapse.CartographerPipeline")


class CartographerPipeline:
    """
    Single Responsibility: Neural map matching disambiguation.
    
    Executes the GPU-accelerated neural path when the heuristic
    FastMapMatcher returns ambiguous results (high entropy).
    
    Extracted from CartographerAgent._neural_match() to follow SRP.
    """

    def __init__(self, model: SinkhornCrossAttention, edges: List[MapEdge], nodes: List[MapNode]):
        self._model = model
        self._edges = edges
        self._nodes = nodes

    def update_map(self, edges: List[MapEdge], nodes: List[MapNode]):
        """Updates the map reference when topology changes."""
        self._edges = edges
        self._nodes = nodes

    def disambiguate(
        self,
        x: float,
        y: float,
        fast_result,
        polyline: Optional[List[Tuple[float, float]]],
        device: torch.device
    ) -> Dict[str, Any]:
        """
        Neural disambiguation using SinkhornCrossAttention.
        
        Args:
            x, y: GPS coordinates.
            fast_result: Result from FastMapMatcher with candidates.
            polyline: Optional GPS polyline points.
            device: Target compute device.
            
        Returns:
            Dict with edge_id, confidence, method, entropy.
        """
        self._model.eval()

        # 1. Build SUMO sub-graph from candidates
        candidate_ids = {c.edge_id for c in fast_result.candidates}
        candidate_edges = [c.edge for c in fast_result.candidates]
        context_edges = LineGraphBuilder.get_context_edges(candidate_ids, self._edges)
        all_edges = list({e.id: e for e in candidate_edges + context_edges}.values())

        sumo_graph = LineGraphBuilder.build_from_edges(all_edges, self._nodes)
        if sumo_graph is None:
            return self._fallback(fast_result)

        # 2. Build Sensor graph
        if polyline and len(polyline) >= 2:
            sensor_graph = LineGraphBuilder.build_from_polyline(polyline)
        else:
            sensor_graph = LineGraphBuilder.build_from_polyline([
                (x - 10, y - 10), (x, y), (x + 10, y + 10)
            ])

        if sensor_graph is None:
            return self._fallback(fast_result)

        # 3. Forward (AMP)
        sumo_graph = sumo_graph.to(device)
        sensor_graph = sensor_graph.to(device)

        device_type = device.type if device.type != 'mps' else 'cpu'

        with torch.no_grad():
            with autocast(device_type=device_type, enabled=(device.type == 'cuda')):
                alignment = self._model(sumo_graph, sensor_graph)

        # 4. Extract best match from candidates
        matches = SinkhornCrossAttention.get_best_matches(alignment)
        edge_ids = getattr(sumo_graph, 'edge_ids', [])

        best_id = fast_result.best_edge_id
        best_conf = 0.0

        for src_idx, tgt_idx, conf in matches:
            if src_idx < len(edge_ids):
                eid = edge_ids[src_idx]
                if eid in candidate_ids and conf > best_conf:
                    best_id = eid
                    best_conf = conf

        logger.info(
            f"[CartographerPipeline] 🧠 Neural: H={fast_result.entropy:.2f} → "
            f"{best_id} (conf={best_conf:.3f})"
        )

        return {
            'edge_id': best_id,
            'confidence': float(best_conf),
            'method': 'neural',
            'entropy': fast_result.entropy,
        }

    @staticmethod
    def _fallback(fast_result) -> Dict[str, Any]:
        """Fallback to heuristic when neural path fails."""
        return {
            'edge_id': fast_result.best_edge_id,
            'confidence': fast_result.best_probability,
            'method': 'heuristic_fallback',
            'entropy': fast_result.entropy,
        }
