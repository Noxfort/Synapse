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
# File: src/optimization/task_registry.py
# Author: Gabriel Moraes
# Date: 2026-04-27

import os
import logging
import numpy as np
import torch
from typing import List, Optional, Any

from src.optimization.optimization_task import OptimizationTask

# Strategy Imports
from src.optimization.strategies_flow import FlowStrategies
from src.optimization.strategies_quality import QualityStrategies
from src.optimization.strategies_semantic import SemanticStrategies

# Geometric data handling for GATv2
try:
    from torch_geometric.data import Data
except ImportError:
    Data = None

# Cartographer Strategy (Safe Import)
try:
    from src.optimization.strategies_spatial import SpatialStrategies
    from src.services.map_service import MapService
    CARTOGRAPHER_AVAILABLE = True
except ImportError:
    CARTOGRAPHER_AVAILABLE = False

logger = logging.getLogger("Synapse.TaskRegistry")


class TaskRegistry:
    """
    Factory that builds the ordered list of OptimizationTasks.
    
    Responsibilities (SRP):
    - Encapsulates ALL data preparation logic per agent.
    - Resolves conditional availability (map, cartographer, PyG).
    - Produces self-contained OptimizationTask objects with closures.
    
    The OptimizerService never touches strategies or data prep directly.
    """

    @staticmethod
    def build_tasks(
        univ_data: np.ndarray,
        map_graph: Optional[Any],
        map_file_path: Optional[str],
        device: torch.device,
        base_dir: str = ""
    ) -> List[OptimizationTask]:
        """
        Constructs the full optimization pipeline as a list of tasks.
        
        Args:
            univ_data: Numeric matrix [TimeSteps, Features] from golden parquet.
            map_graph: PyG Data object or dict from SUMO map (can be None).
            map_file_path: Path to .net.xml.gz file (can be None).
            device: Target torch device.
            base_dir: Synapse root for saving diplomas.
            
        Returns:
            Ordered list of OptimizationTask ready for sequential execution.
        """
        tasks: List[OptimizationTask] = []

        # ═══════════════════════════════════════════════════════════════
        # Phase 1: Spatial — Coordinator (GATv2)
        # ═══════════════════════════════════════════════════════════════
        if map_graph is not None:
            clean_graph = TaskRegistry._prepare_graph(map_graph)
            if clean_graph is not None:
                tasks.append(OptimizationTask(
                    name="coordinator",
                    label="🌐 Tuning Coordinator (GATv2)",
                    objective_fn=lambda t, g=clean_graph: FlowStrategies.coordinator_strategy(t, g, device),
                    slope_threshold=1e-3
                ))

        # ═══════════════════════════════════════════════════════════════
        # Phase 1b: Spatial Alignment — Cartographer (Sinkhorn+GATv2)
        # ═══════════════════════════════════════════════════════════════
        if map_file_path and CARTOGRAPHER_AVAILABLE:
            cart_data = TaskRegistry._prepare_cartographer(map_file_path)
            if cart_data is not None:
                def _cart_post_hook(best_params, bd=base_dir):
                    TaskRegistry._save_cartographer_diploma(best_params, bd)

                tasks.append(OptimizationTask(
                    name="cartographer",
                    label="🗺️ Tuning Cartographer (Sinkhorn+GATv2)",
                    objective_fn=lambda t, cd=cart_data: SpatialStrategies.cartographer_strategy(t, cd, device),
                    slope_threshold=1e-3,
                    post_hook=_cart_post_hook
                ))

        # ═══════════════════════════════════════════════════════════════
        # Phase 2: Temporal — Fuser (iTransformer)
        # ═══════════════════════════════════════════════════════════════
        tasks.append(OptimizationTask(
            name="fuser",
            label="🔮 Tuning Fuser (iTransformer)",
            objective_fn=lambda t: FlowStrategies.fuser_strategy(t, univ_data, device)
        ))

        # ═══════════════════════════════════════════════════════════════
        # Phase 3: Local Patterns — Specialist (TCN)
        # ═══════════════════════════════════════════════════════════════
        tasks.append(OptimizationTask(
            name="specialist",
            label="🎯 Tuning Specialist (TCN)",
            objective_fn=lambda t: FlowStrategies.specialist_strategy(t, univ_data, device)
        ))

        # ═══════════════════════════════════════════════════════════════
        # Phase 4: Security — Auditor (Wavelet AE + OCC)
        # ═══════════════════════════════════════════════════════════════
        tasks.append(OptimizationTask(
            name="auditor",
            label="🛡️ Tuning Auditor (Wavelet AE + OCC)",
            objective_fn=lambda t: QualityStrategies.auditor_strategy(t, univ_data, device)
        ))

        # ═══════════════════════════════════════════════════════════════
        # Phase 5: Resilience — Imputer (PatchTST)
        # ═══════════════════════════════════════════════════════════════
        tasks.append(OptimizationTask(
            name="imputer",
            label="🧬 Tuning Imputer (PatchTST)",
            objective_fn=lambda t: QualityStrategies.imputer_strategy(t, univ_data, device),
            slope_threshold=1e-6,
            window=30
        ))

        # ═══════════════════════════════════════════════════════════════
        # Phase 6: Quality — Corrector (VAE-TCN)
        # ═══════════════════════════════════════════════════════════════
        tasks.append(OptimizationTask(
            name="corrector",
            label="🧹 Tuning Corrector (VAE-TCN)",
            objective_fn=lambda t: QualityStrategies.corrector_strategy(t, univ_data, device)
        ))

        # ═══════════════════════════════════════════════════════════════
        # Phase 7: Semantics — Linguist (DistilRoBERTa + TCN-AE)
        # ═══════════════════════════════════════════════════════════════
        tasks.append(OptimizationTask(
            name="linguist",
            label="🗣️ Tuning Linguist (DistilRoBERTa + TCN-AE)",
            objective_fn=lambda t: SemanticStrategies.linguist_strategy(t, univ_data, device)
        ))

        # ═══════════════════════════════════════════════════════════════
        # Phase 8: Classification — Peak Classifier (TimesNet)
        # ═══════════════════════════════════════════════════════════════
        inputs, targets = TaskRegistry._prepare_classifier_data(univ_data)
        if inputs is not None:
            tasks.append(OptimizationTask(
                name="classifier",
                label="📊 Tuning Peak Classifier (TimesNet)",
                objective_fn=lambda t, inp=inputs, tgt=targets: SemanticStrategies.classifier_strategy(t, inp, tgt, device)
            ))

        return tasks

    # ═══════════════════════════════════════════════════════════════════
    # PRIVATE: Data Preparation Helpers
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _prepare_graph(map_graph: Any) -> Optional[Any]:
        """Converts map dict to PyG Data if needed."""
        if isinstance(map_graph, dict):
            if Data is not None:
                try:
                    logger.info("[TaskRegistry] 🛠️ Converting Map Dict → PyTorch Geometric Data...")
                    return Data(**map_graph)
                except Exception as e:
                    logger.warning(f"[TaskRegistry] ⚠️ Failed to convert map_graph: {e}")
                    return None
            else:
                logger.warning("[TaskRegistry] ⚠️ PyTorch Geometric not found. Skipping Coordinator.")
                return None
        return map_graph

    @staticmethod
    def _prepare_cartographer(map_file_path: str) -> Optional[dict]:
        """Loads MapService and extracts edge/node data for Cartographer."""
        try:
            ms = MapService()
            if ms.load_network(map_file_path):
                return {'edges': ms.edges, 'nodes': ms.nodes}
            else:
                logger.warning("[TaskRegistry] ⚠️ MapService failed to load network for Cartographer.")
                return None
        except Exception as e:
            logger.warning(f"[TaskRegistry] ⚠️ Cartographer data prep skipped: {e}")
            return None

    @staticmethod
    def _prepare_classifier_data(univ_data: np.ndarray):
        """
        Prepares sliding windows and binary labels for the Peak Classifier.
        
        Previously this logic lived inside optimizer_service.run() — violating SRP.
        """
        seq_len = 96
        sample_limit = 64

        if isinstance(univ_data, np.ndarray):
            series_1d = np.mean(univ_data, axis=1) if univ_data.ndim > 1 else univ_data
        else:
            series_1d = np.array(univ_data).flatten()

        threshold = np.mean(series_1d) + np.std(series_1d)

        needed_length = seq_len + sample_limit
        if len(series_1d) > needed_length:
            series_1d = series_1d[-needed_length:]

        x_windows = []
        y_labels = []

        for i in range(len(series_1d) - seq_len):
            window = series_1d[i: i + seq_len]
            target_val = series_1d[i + seq_len]
            x_windows.append(window)
            y_labels.append(1.0 if target_val > threshold else 0.0)

        if not x_windows:
            x_windows = [np.random.randn(seq_len)]
            y_labels = [1.0]

        inputs = np.array(x_windows, dtype=np.float32)
        targets = np.array(y_labels, dtype=np.float32)

        # Ensure at least one positive class to prevent BCE loss collapse
        if targets.sum() == 0:
            targets[0] = 1.0

        return inputs, targets

    @staticmethod
    def _save_cartographer_diploma(best_params: dict, base_dir: str):
        """
        Saves the Cartographer's best model weights after optimization.
        
        Previously this logic lived inside optimizer_service.run() — violating SRP/DIP
        by forcing the orchestrator to import SinkhornCrossAttention directly.
        """
        if not best_params:
            return

        try:
            from src.models.sinkhorn_cross_attention import SinkhornCrossAttention

            diploma_dir = os.path.join(base_dir, "weights")
            os.makedirs(diploma_dir, exist_ok=True)
            diploma_path = os.path.join(diploma_dir, "cartographer.safetensors")

            best_model = SinkhornCrossAttention(
                d_model=best_params.get('cart_d_model', 64),
                n_heads=best_params.get('cart_n_heads', 4),
                n_gat_layers=best_params.get('cart_n_gat_layers', 2),
                sinkhorn_iters=best_params.get('cart_sinkhorn_iters', 10),
                dropout=best_params.get('cart_dropout', 0.1),
                temperature=best_params.get('cart_temperature', 0.1),
            )
            best_model.save_diploma(diploma_path)
            logger.info(f"[TaskRegistry] 🎓 Cartographer diploma saved: {diploma_path}")

        except Exception as e:
            logger.warning(f"[TaskRegistry] ⚠️ Diploma save failed: {e}")
