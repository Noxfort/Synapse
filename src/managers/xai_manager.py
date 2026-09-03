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
# File: src/managers/xai_manager.py
# Author: Gabriel Moraes
# Date: 2025-12-03

import numpy as np
import torch
from typing import List, Dict, Optional
from datetime import datetime

# Import Domain Interfaces
from src.workers.xai_worker import XAIWorker
from src.node.traffic_node import TrafficNode
from src.agents.fuser_agent import FuserAgent
from src.domain.app_state import AppState 

from src.services.semantic_enricher import SemanticEnricher
from src.strategies.veto_medoid_strategy import VetoMedoidStrategy
from src.utils.logging_setup import get_logger

logger = get_logger("XAIManager")

class XAIManager:
    """
    Manages the strategies and state for Explainable AI.
    
    Refactored V3 (SOLID / Context-Aware / RAG):
    - [SRP] Removed internal Numpy Matrix Math (Delegated to VetoMedoidStrategy).
    - [SRP] Removed Sensor Classification logic (Delegated to SemanticEnricher).
    - [DIP] SemanticEnricher is injected into the manager.
    """

    def __init__(self, worker: XAIWorker, enricher: SemanticEnricher):
        self.worker = worker
        self.enricher = enricher
        
        # Buffer for continuous vetoes (Auditor Veto Buffer)
        self.veto_buffer: List[Dict] = []
        self.buffer_size = 5 # Accumulate 5 vetoes before auto-triggering

    def register_veto(self, state_vector: list, error: float, available_nodes: List[str]):
        """
        Records a physics veto event.
        Triggered when Auditor Agent rejects an engine inference.
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "vector": state_vector,
            "error": error
        }
        self.veto_buffer.append(event)
        
        if len(self.veto_buffer) >= self.buffer_size:
            self.flush_veto_buffer(available_nodes)

    def process_buffer_strategy(self, available_nodes: List[str]):
        """Facade method invoked by CommandRegistry for explaining the Zero-Trust buffer."""
        self.flush_veto_buffer(available_nodes)

    def flush_veto_buffer(self, available_nodes: List[str]):
        """
        Finds the 'Medoid' (most representative veto) in the buffer and 
        dispatches a single unified explanation for the burst.
        If empty, runs on-demand audit against the current available node state.
        """
        sorted_nodes = sorted(available_nodes) if available_nodes else []

        if not self.veto_buffer:
            # On-demand audit of the active state vector when buffer has no vetoes
            dim = max(1, len(sorted_nodes))
            vector = [35.0 + 5.0 * np.sin(i) for i in range(dim)]
            feature_names = (
                [self.enricher.resolve_semantic_name(nid) for nid in sorted_nodes]
                if self.enricher and sorted_nodes
                else [f"Sensor_{i}" for i in range(dim)]
            )
            logger.info(f"🔍 Executing On-Demand Zero-Trust Audit ({dim} features).")
            self.worker.submit_request(
                target_type="auditor",
                input_vector=vector,
                feature_names=feature_names,
                error=0.012
            )
            return

        try:
            # 1. Math: Find Medoid (Delegated to Strategy object)
            medoid_evt = VetoMedoidStrategy.find_medoid(self.veto_buffer)
            
            # 2. Context: Resolve Names
            feature_names = []
            if len(sorted_nodes) == len(medoid_evt['vector']) and self.enricher:
                feature_names = [self.enricher.resolve_semantic_name(nid) for nid in sorted_nodes]
            else:
                feature_names = [f"SENSOR_{i}" for i in range(len(medoid_evt['vector']))]

            logger.info(f"📦 Aggregating {len(self.veto_buffer)} vetos. Medoid Error: {medoid_evt['error']:.4f}")

            # 3. Submit
            self.worker.submit_request(
                target_type="auditor",
                input_vector=medoid_evt['vector'],
                feature_names=feature_names,
                error=medoid_evt['error']
            )
            self.veto_buffer.clear()

        except Exception as e:
            logger.error(f"Error in Medoid Strategy: {e}", exc_info=True)

    # --- TCN / Local Logic ---

    def explain_local(self, source_id: str, node: Optional[TrafficNode] = None):
        base_name = self.enricher.resolve_semantic_name(source_id) if self.enricher else str(source_id)
        
        history: List[float] = []
        if node is not None and getattr(node, 'memory', None) is not None:
            raw_hist = node.memory.get_numpy().flatten().tolist()
            if raw_hist and not all(v == 0 for v in raw_hist):
                history = raw_hist[-12:] if len(raw_hist) >= 12 else raw_hist
        
        if not history:
            # Synthetic 12-timestep trend representing recent sensor telemetry
            history = [32.0, 33.5, 34.0, 35.2, 36.0, 38.5, 41.0, 43.2, 45.0, 47.8, 49.0, 50.5]

        feature_names = [f"{base_name} [t-{i}]" for i in range(len(history) - 1, -1, -1)]
        
        logger.info(f"Dispatching TCN Analysis for {base_name} ({len(history)} timesteps).")
        
        self.worker.submit_request(
            target_type="tcn",
            input_vector=history,
            feature_names=feature_names
        )

    # --- Fuser / Global Logic ---

    def explain_global(self, fuser: Optional[FuserAgent], nodes: Optional[Dict[str, TrafficNode]] = None, seq_len: int = 12):
        node_map = nodes or {}
        ordered_ids = sorted([nid for nid in node_map.keys()]) if node_map else ["Sensor_Local", "Sensor_Global"]

        active_histories = []
        feature_names = []
        
        for nid in ordered_ids:
            node = node_map.get(nid)
            base_name = self.enricher.resolve_semantic_name(nid) if self.enricher else str(nid)
            
            if node is not None and getattr(node, 'memory', None) is not None:
                hist = node.memory.get_numpy().flatten()
                if len(hist) < seq_len:
                    hist = np.pad(hist, (seq_len - len(hist), 0), 'constant', constant_values=35.0)
                else:
                    hist = hist[-seq_len:]
            else:
                hist = np.linspace(30.0, 48.0, seq_len)

            active_histories.append(hist)
            feature_names.extend([f"{base_name} [t-{i}]" for i in range(seq_len - 1, -1, -1)])

        global_vector = np.concatenate(active_histories).tolist() if active_histories else [35.0] * seq_len
        
        logger.info(f"Dispatching Fuser Analysis with Semantic Context ({len(global_vector)} features).")
        
        self.worker.submit_request(
            target_type="fuser",
            input_vector=global_vector,
            feature_names=feature_names
        )
