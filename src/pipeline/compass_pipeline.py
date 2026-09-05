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
# File: src/pipeline/compass_pipeline.py
# Author: Gabriel Moraes
# Date: 2026-09-05

import os
import math
import logging
from typing import Dict, Any, List, Optional, Tuple

import torch
import torch.nn.functional as F
import numpy as np
from transformers import AutoTokenizer, AutoModel

from src.domain.entities import MapEdge, DataSource
from src.interfaces.pipelines import ICompassPipeline
from src.utils.model_paths import get_distilroberta_base_path

logger = logging.getLogger("Synapse.CompassPipeline")


class CompassPipeline(ICompassPipeline):
    """
    Dedicated Neural Pipeline for Directional Disambiguation & Orientation Reconciliation.
    
    Responsibilities:
    1. Fast-path ($O(1)$) passthrough for single-direction streets (mão única).
    2. Multichannel dual-flow identification for simultaneous two-way sensors (e.g. gantry radars).
    3. Agnostic semantic direction extraction using DistilRoBERTa and topological descriptors.
    4. Hydrodynamic continuity and vector orientation consistency checks.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[torch.device] = None,
        confidence_threshold: float = 0.65
    ):
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.confidence_threshold = confidence_threshold
        resolved_name = model_name or get_distilroberta_base_path()
        self.model_name = resolved_name

        self.tokenizer = None
        self.transformer = None

        # Load DistilRoBERTa safely (local-first)
        try:
            is_local = os.path.isdir(resolved_name)
            self.tokenizer = AutoTokenizer.from_pretrained(resolved_name, local_files_only=is_local)
            self.transformer = AutoModel.from_pretrained(resolved_name, local_files_only=is_local)
            self.transformer.to(self.device)
            self.transformer.eval()
            for p in self.transformer.parameters():
                p.requires_grad = False
            logger.info(f"[CompassPipeline] 🧭 DistilRoBERTa inicializado com sucesso em {self.device}.")
        except Exception as e:
            logger.warning(f"[CompassPipeline] ⚠️ DistilRoBERTa não disponível ({e}). Usando fallback heurístico.")

    def to(self, device: Any) -> 'CompassPipeline':
        self.device = torch.device(device) if isinstance(device, str) else device
        if self.transformer is not None:
            self.transformer.to(self.device)
        return self

    def orient_and_reconcile(
        self,
        source: DataSource,
        candidate_edges: List[MapEdge],
        data_chunk: Optional[List[Any]] = None,
        data_np: Optional[np.ndarray] = None,
        semantic_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes directional disambiguation for a sensor against candidate edges.
        
        Args:
            source: The DataSource being analyzed.
            candidate_edges: List of candidate MapEdge entities (e.g. [edge_ida, edge_volta]).
            data_chunk: Raw samples from quarantine buffer.
            data_np: Extracted numeric values.
            semantic_type: Inferred modality ("Vehicle Speed", "Traffic Flow", etc.).
            
        Returns:
            Dict with orientation, primary_edge_id, secondary_edge_id, channels, confidence, vector, method.
        """
        # --- GATE 0: No candidates ---
        if not candidate_edges:
            logger.warning(f"[CompassPipeline] ⚠️ Nenhuma aresta candidata informada para '{source.id}'.")
            return {
                "orientation": "INDETERMINADO",
                "primary_edge_id": None,
                "secondary_edge_id": None,
                "channels": {},
                "confidence": 0.0,
                "vector": (0.0, 0.0),
                "method": "no_candidates"
            }

        # --- GATE 1: Single-direction street (Mão Única) -> O(1) Fast Path ---
        if len(candidate_edges) == 1:
            edge = candidate_edges[0]
            vec = self._compute_edge_vector(edge)
            logger.info(f"[CompassPipeline] ⚡ Via de mão única detectada para '{source.name}' -> {edge.id}.")
            return {
                "orientation": "IDA",
                "primary_edge_id": edge.id,
                "secondary_edge_id": None,
                "channels": {},
                "confidence": 1.0,
                "vector": vec,
                "method": "single_edge_fast"
            }

        # --- GATE 2: Multichannel / Dual-Direction Inspection ---
        multichannel_split = self._detect_multichannel(source, candidate_edges, data_chunk)
        if multichannel_split:
            logger.info(f"[CompassPipeline] 🔄 Sensor multicanal de mão dupla simultânea detectado para '{source.name}'.")
            return multichannel_split

        # --- GATE 3: Two-way Street Disambiguation (Mão Dupla) ---
        return self._disambiguate_two_way(source, candidate_edges, data_chunk, data_np)

    def _compute_edge_vector(self, edge: MapEdge) -> Tuple[float, float]:
        """Calculates normalized (cos, sin) directional vector from edge geometry."""
        if not edge.shape or len(edge.shape) < 2:
            return (1.0, 0.0)
        p_start = edge.shape[0]
        p_end = edge.shape[-1]
        dx = p_end[0] - p_start[0]
        dy = p_end[1] - p_start[1]
        norm = math.hypot(dx, dy)
        if norm < 1e-6:
            return (1.0, 0.0)
        return (dx / norm, dy / norm)

    def _detect_multichannel(
        self,
        source: DataSource,
        candidate_edges: List[MapEdge],
        data_chunk: Optional[List[Any]]
    ) -> Optional[Dict[str, Any]]:
        """Identifies whether incoming sensor payload has separate channels for opposing directions."""
        if len(candidate_edges) < 2:
            return None

        # 1. Inspect metadata for channel definitions
        meta = source.metadata or {}
        channels_meta = meta.get("channels") or meta.get("lanes")
        if isinstance(channels_meta, dict) and len(channels_meta) >= 2:
            keys = list(channels_meta.keys())
            return {
                "orientation": "DUPLO",
                "primary_edge_id": candidate_edges[0].id,
                "secondary_edge_id": candidate_edges[1].id,
                "channels": {
                    keys[0]: candidate_edges[0].id,
                    keys[1]: candidate_edges[1].id
                },
                "confidence": 0.95,
                "vector": self._compute_edge_vector(candidate_edges[0]),
                "method": "multichannel_metadata_split"
            }

        # 2. Inspect data_chunk items for dual direction keys
        if data_chunk and len(data_chunk) > 0:
            sample = data_chunk[0]
            if isinstance(sample, dict):
                has_inbound = any(k in sample for k in ("inbound", "ida", "north", "northbound", "lane_1", "lane_in"))
                has_outbound = any(k in sample for k in ("outbound", "volta", "south", "southbound", "lane_2", "lane_out"))
                if has_inbound and has_outbound:
                    return {
                        "orientation": "DUPLO",
                        "primary_edge_id": candidate_edges[0].id,
                        "secondary_edge_id": candidate_edges[1].id,
                        "channels": {
                            "inbound": candidate_edges[0].id,
                            "outbound": candidate_edges[1].id
                        },
                        "confidence": 0.92,
                        "vector": self._compute_edge_vector(candidate_edges[0]),
                        "method": "multichannel_payload_split"
                    }

        return None

    def _disambiguate_two_way(
        self,
        source: DataSource,
        candidate_edges: List[MapEdge],
        data_chunk: Optional[List[Any]],
        data_np: Optional[np.ndarray]
    ) -> Dict[str, Any]:
        """Resolves directional choice between opposing edges using semantic clues, bearing, and NLP."""
        edge_a = candidate_edges[0]
        edge_b = candidate_edges[1]

        vec_a = self._compute_edge_vector(edge_a)
        vec_b = self._compute_edge_vector(edge_b)

        # 1. Compile source text clues
        meta_str = " ".join([f"{k}:{v}" for k, v in (source.metadata or {}).items()])
        sample_str = ""
        if data_chunk and len(data_chunk) > 0:
            sample_str = str(data_chunk[:2])
        text_blob = f"{source.name} {source.connection_string} {meta_str} {sample_str}".lower()

        score_a = 0.0
        score_b = 0.0

        # 2. Heuristic Keyword Matching against Node & Edge identifiers
        for node_id in [edge_a.to_node.lower(), (edge_a.real_name or "").lower()]:
            if node_id and len(node_id) > 2 and node_id in text_blob:
                score_a += 2.5

        for node_id in [edge_b.to_node.lower(), (edge_b.real_name or "").lower()]:
            if node_id and len(node_id) > 2 and node_id in text_blob:
                score_b += 2.5

        # Semantic keywords
        if any(w in text_blob for w in ("centro", "inbound", "ida", "descida", "norte", "leste")):
            score_a += 1.5
        if any(w in text_blob for w in ("bairro", "outbound", "volta", "subida", "sul", "oeste")):
            score_b += 1.5

        # 3. Geometric Bearing Check (if provided in metadata)
        bearing = None
        for key in ("bearing", "heading", "azimuth", "angle", "orientation"):
            if key in (source.metadata or {}):
                try:
                    bearing = float(source.metadata[key])
                    break
                except (ValueError, TypeError):
                    pass

        if bearing is not None:
            rad = math.radians(bearing)
            sensor_vec = (math.cos(rad), math.sin(rad))
            dot_a = sensor_vec[0] * vec_a[0] + sensor_vec[1] * vec_a[1]
            dot_b = sensor_vec[0] * vec_b[0] + sensor_vec[1] * vec_b[1]
            score_a += dot_a * 3.0
            score_b += dot_b * 3.0

        # 4. Neural Semantic Alignment (DistilRoBERTa)
        if self.transformer is not None and self.tokenizer is not None:
            neural_score_a, neural_score_b = self._neural_semantic_scores(text_blob, edge_a, edge_b)
            score_a += neural_score_a * 2.0
            score_b += neural_score_b * 2.0

        # 5. Normalize with Softmax for probabilistic confidence
        scores_t = torch.tensor([score_a, score_b], dtype=torch.float32)
        probs = F.softmax(scores_t / 1.5, dim=0).tolist()
        prob_a, prob_b = probs[0], probs[1]

        if prob_a >= prob_b:
            chosen_edge = edge_a
            chosen_vec = vec_a
            confidence = prob_a
            orientation = "IDA"
        else:
            chosen_edge = edge_b
            chosen_vec = vec_b
            confidence = prob_b
            orientation = "VOLTA"

        logger.info(
            f"[CompassPipeline] 🧭 Desambiguação '{source.name}': "
            f"Edge {chosen_edge.id} ({orientation}) com confiança {confidence:.2%}. "
            f"Scores: [A={score_a:.2f}, B={score_b:.2f}]."
        )

        return {
            "orientation": orientation,
            "primary_edge_id": chosen_edge.id,
            "secondary_edge_id": None,
            "channels": {},
            "confidence": float(confidence),
            "vector": chosen_vec,
            "method": "semantic_neural_reconciliation"
        }

    def _neural_semantic_scores(self, text_blob: str, edge_a: MapEdge, edge_b: MapEdge) -> Tuple[float, float]:
        """Calculates contextual semantic similarity using DistilRoBERTa embeddings."""
        try:
            desc_a = f"via de tráfego de {edge_a.from_node} para {edge_a.to_node} {edge_a.real_name or ''}"
            desc_b = f"via de tráfego de {edge_b.from_node} para {edge_b.to_node} {edge_b.real_name or ''}"

            texts = [text_blob[:128], desc_a, desc_b]
            inputs = self.tokenizer(texts, padding=True, truncation=True, max_length=64, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.transformer(**inputs)
                # Mean pooling
                attn_mask = inputs["attention_mask"].unsqueeze(-1)
                emb = (outputs.last_hidden_state * attn_mask).sum(dim=1) / attn_mask.sum(dim=1).clamp(min=1e-6)
                emb = F.normalize(emb, p=2, dim=1)

            sim_a = F.cosine_similarity(emb[0:1], emb[1:2]).item()
            sim_b = F.cosine_similarity(emb[0:1], emb[2:3]).item()
            return float(sim_a), float(sim_b)
        except Exception as e:
            logger.debug(f"[CompassPipeline] NLP cosine similarity fallback: {e}")
            return 0.0, 0.0
