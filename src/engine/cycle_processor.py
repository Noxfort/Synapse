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
# File: src/engine/cycle_processor.py
# Author: Gabriel Moraes
# Date: 2026-02-14

import time
import torch
import numpy as np
import torch.nn.functional as F
from typing import Dict, Any, Tuple, Optional, TYPE_CHECKING

from src.utils.logging_setup import logger
from src.utils.debug_logger import perf_logger

# --- Domain ---
from src.domain.app_state import AppState

# --- Managers & Engine Helpers ---
from src.managers.xai_manager import XAIManager
from src.managers.graph_manager import GraphManager
from src.engine.tensor_builder import TensorBuilder
from src.engine.security_monitor import SecurityMonitor

# --- Lazy Imports (Prevent Circular Dependency) ---
if TYPE_CHECKING:
    from src.agents.coordinator_agent import CoordinatorAgent
    from src.agents.fuser_agent import FuserAgent
    from src.agents.auditor_agent import AuditorAgent

class CycleProcessor:
    """
    Handles the mathematical heavy-lifting of the Global Inference Cycle.
    
    Refactored V9 (SOLID Principles):
    - Uses TensorBuilder for data preprocessing (SRP).
    - Unifies Agent Pipeline abstraction via standard .inference() (LSP/ISP).
    - Uses SecurityMonitor for alerting evaluation (SRP).
    """

    def __init__(self, 
                 app_state: AppState, 
                 device: torch.device,
                 coordinator: 'CoordinatorAgent',
                 fuser: 'FuserAgent',
                 auditor: 'AuditorAgent',
                 xai_manager: XAIManager,
                 graph_manager: GraphManager):
        
        self.app_state = app_state
        self.device = device
        
        # Agents (Injected)
        self.coordinator = coordinator
        self.fuser = fuser
        self.auditor = auditor
        
        # Managers
        self.xai_manager = xai_manager
        self.graph_manager = graph_manager
        
        # --- Engine Domain Extractors (SOLID) ---
        self.tensor_builder = TensorBuilder(device, coordinator.model, graph_manager)
        
        # Extract calibrated threshold from auditor if available (default 0.75)
        auditor_thresh = 0.75
        if auditor:
            if hasattr(auditor, 'pipeline') and hasattr(auditor.pipeline, 'calibrator') and auditor.pipeline.calibrator:
                auditor_thresh = float(auditor.pipeline.calibrator.threshold)
            elif hasattr(auditor, 'model') and hasattr(auditor.model, 'threshold'):
                raw = auditor.model.threshold
                auditor_thresh = float(raw.item() if isinstance(raw, torch.Tensor) else raw)
        self.security_monitor = SecurityMonitor(threshold=auditor_thresh)

    def run_logic(self, snapshot: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """
        Executes the main AI pipeline orchestrating standardized agents.
        """
        start_time = time.time()
        
        # 1. Prepare Tensors (Delegated to TensorBuilder - SRP)
        try:
            tensor_pack = self.tensor_builder.prepare_tensors(snapshot)
            if len(tensor_pack) == 5:
                x_spatial, edge_index, x_temporal, obs_mask, g_vel = tensor_pack
            else:
                x_spatial, edge_index, x_temporal = tensor_pack[:3]
                obs_mask, g_vel = None, None
        except ValueError as ve:
            return {}, None
        except Exception as e:
            logger.error(f"[Processor] Critical Tensor Failure: {e}")
            return {}, None
        t_tensor = time.time()

        # 2. Coordinator (Spatial Pipeline)
        try:
            spatial_embedding = self.coordinator.inference({
                 "x_spatial": x_spatial, 
                 "edge_index": edge_index
            })
        except Exception as e:
            logger.critical(f"[Processor] Spatial Inference Crash: {e}")
            raise e
        t_coordinator = time.time()
        
        # 3. Fuser (Spatio-Temporal Diffusion + PINN + iTransformer Fusion)
        forecast = self.fuser.inference({
            "x_temporal": x_temporal,
            "spatial_context": spatial_embedding,  # Cross-Attention context from GATv2
            "observability_mask": obs_mask,       # Active Ground Truth sensors
            "global_velocities": g_vel,           # Macroscopic API speeds
            "edge_index": edge_index              # Graph topology for diffusion
        })
        t_fuser = time.time()
        
        # 4. Auditor (Security Pipeline)
        security_score = 0.0
        auditor_report: Dict[str, Any] = {}
        if self.auditor:
            try:
                # Compress State: Mean across Embedding Dim -> [1, Nodes]
                signature = spatial_embedding.mean(dim=1).unsqueeze(0) 
                
                # Dynamic Auditor Check is handled natively by the Agent now
                auditor_report = self.auditor.inference({"signature": signature})
                security_score = auditor_report.get("score", 0.0)
            except Exception as e:
                logger.error(f"[Processor] Security sweep failed: {e}")
        t_auditor = time.time()

        # 5. Result Packaging
        total_time = t_auditor - start_time
        results = {
            "spatial_embedding": spatial_embedding,
            "forecast": forecast,
            "security_score": security_score,
            "auditor_report": auditor_report,
            "trigger_emergency_fallback": auditor_report.get("trigger_emergency_fallback", False),
            "processing_time": total_time
        }
        
        # --- Debug Log: CYCLE (per-stage neural performance) ---
        perf_logger.info(
            f"CYCLE | tensor={(t_tensor - start_time)*1000:.2f}ms "
            f"| coordinator={(t_coordinator - t_tensor)*1000:.2f}ms "
            f"| fuser={(t_fuser - t_coordinator)*1000:.2f}ms "
            f"| auditor={(t_auditor - t_fuser)*1000:.2f}ms "
            f"| total={total_time*1000:.2f}ms"
        )
        
        # 6. Alerting (Delegated to SecurityMonitor - SRP)
        active_thresh = auditor_report.get("threshold", self.security_monitor.threshold)
        alert = self.security_monitor.evaluate(security_score, threshold=active_thresh)
        
        return results, alert
