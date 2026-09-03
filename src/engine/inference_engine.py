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
# File: src/engine/inference_engine.py
# Author: Gabriel Moraes
# Date: 2026-08-30

import time
import logging
import numpy as np
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from src.domain.app_state import AppState
from src.managers.graph_manager import GraphManager
from src.workers.ingestion_worker import IngestionWorker
from src.interfaces.engine import (
    IInferenceEngine,
    IGatingPolicy,
    IForecastImputer,
    ISnapshotBuilder,
    ICycleProcessor,
)
from src.kse.packet_builder import PacketBuilder
from src.utils.debug_logger import perf_logger


class InferenceEngine(QObject):
    """
    The Real-Time Neural Inference Orchestrator (Implements IInferenceEngine).

    Coordinates the synchronous inference loop (~1Hz):
    1. Async input polling (Global APIs)
    2. Source readiness & quarantine evaluation (GatingPolicy)
    3. Graph physics progression (GraphManager)
    4. State snapshot aggregation (SnapshotBuilder)
    5. Spatio-temporal neural inference (CycleProcessor)
    6. Forecast imputation for unobserved nodes (ForecastImputer)
    7. Event & telemetry dissemination (PyQt Signals)
    """

    # --- SIGNALS ---
    # Slow Path: Full Inference Cycle Results
    global_cycle_results = pyqtSignal(dict)
    kinetic_data_ready = pyqtSignal(dict)

    # Security & Drift Signals
    audit_update = pyqtSignal(bool, float, float, list)
    drift_update = pyqtSignal(str, dict)

    # Cross-Thread Coordination
    linguist_check_requested = pyqtSignal()

    def __init__(
        self,
        app_state: AppState,
        graph_manager: GraphManager,
        snapshot_builder: ISnapshotBuilder,
        processor: ICycleProcessor,
        gating_policy: IGatingPolicy,
        forecast_imputer: IForecastImputer,
        ingestion: Optional[IngestionWorker] = None,
    ):
        super().__init__()
        self.app_state = app_state
        self.graph_manager = graph_manager
        self.snapshot_builder = snapshot_builder
        self.processor = processor
        self.gating_policy = gating_policy
        self.forecast_imputer = forecast_imputer
        self.ingestion = ingestion
        self.cycle_count = 0
        self.logger = logging.getLogger(__name__)

    @pyqtSlot()
    def run_global_cycle(self) -> None:
        """Executes one iteration of the neural inference pipeline."""
        self.cycle_count += 1
        _cycle_start = time.time()
        _ts_start = datetime.now().strftime('%H:%M:%S.%f')[:-3]

        # 1. Async Inputs: Adaptive polling for Global APIs
        if self.ingestion:
            self.ingestion.check_global_fetch(_cycle_start)

        # 2. Gating & Quarantine Policy Evaluation
        gating = self.gating_policy.evaluate(self.app_state, self.cycle_count)
        if gating.should_trigger_linguist:
            self.linguist_check_requested.emit()

        if gating.is_frozen:
            self.gating_policy.log_frozen_status(gating, self.cycle_count)
            return

        # 3. Advance Graph Physics (Dead Reckoning)
        for node in self.graph_manager.nodes.values():
            node.tick()

        # 4. Gather Reality Snapshot
        snapshot = self.snapshot_builder.gather_snapshot()

        # 5. Execute Spatio-Temporal Neural Inference
        results, _ = self.processor.run_logic(snapshot)
        if not results:
            return

        # 6. Neural Forecast Imputation for Unobserved Nodes
        self.forecast_imputer.impute(results.get("forecast"), snapshot, self.graph_manager)

        # 7. Route Security & Drift Events
        if results.get("alert_event"):
            event = results["alert_event"]
            payload = event.get("payload", {})
            self.drift_update.emit(event.get("title", ""), payload)

            if payload.get("status") in ["DRIFT", "ATTACK"]:
                loss = payload.get("loss", 0.0)
                self.audit_update.emit(True, loss, 0.15, [])

        # 8. Calculate per-node and global telemetry (losses, drift PSI, qualities)
        losses = {}
        drift_scores = {}
        qualities = {}

        for node_id, node in self.graph_manager.nodes.items():
            node_loss = getattr(getattr(node, "state", None), "last_loss", 0.008)
            node_psi = getattr(getattr(node, "state", None), "last_psi", 0.012)
            losses[node_id] = float(max(0.0001, min(0.5, node_loss)))
            drift_scores[node_id] = float(max(0.0001, min(0.5, node_psi)))
            qualities[node_id] = int(max(10, min(100, round(100 - losses[node_id] * 1200))))

        # Map to data sources from AppState
        for src in self.app_state.get_all_data_sources():
            elem_id = getattr(src, "associated_element", src.id) or src.id
            if elem_id in losses:
                losses[src.id] = losses[elem_id]
                drift_scores[src.id] = drift_scores[elem_id]
                qualities[src.id] = qualities[elem_id]
            else:
                base_loss = float(results.get("security_score", 0.008))
                losses[src.id] = base_loss if base_loss > 0 else 0.008
                drift_scores[src.id] = 0.012
                qualities[src.id] = int(max(10, min(100, round(100 - losses[src.id] * 1200))))

        avg_loss = float(sum(losses.values()) / len(losses)) if losses else float(results.get("security_score", 0.008))
        avg_drift = float(sum(drift_scores.values()) / len(drift_scores)) if drift_scores else 0.012

        # 8b. Build Fluid Dynamics Telemetry across the entire road network (LWR / Greenshields model)
        edge_data = {}
        mean_speed = 0.0
        mean_occupancy = 0.0
        try:
            packet = PacketBuilder.build(snapshot, "realtime", self.app_state)
            if packet and "traffic" in packet:
                speeds = []
                occs = []
                for item in packet["traffic"]:
                    raw_s = float(item["speed"])
                    speed_kmh = raw_s * 3.6 if raw_s <= 35.0 else raw_s
                    edge_id = str(item["edge_id"])
                    density_val = float(item["density"])
                    occ_val = float(item["occupancy"])
                    queue_val = int(item["queue"])

                    edge_data[edge_id] = {
                        "speed": round(speed_kmh, 1),
                        "density": round(density_val, 1),
                        "occupancy": round(occ_val, 3),
                        "queue": queue_val,
                    }
                    speeds.append(speed_kmh)
                    occs.append(occ_val)

                if speeds:
                    mean_speed = round(sum(speeds) / len(speeds), 1)
                if occs:
                    mean_occupancy = round(sum(occs) / len(occs), 3)
        except Exception as e:
            self.logger.warning(f"Failed to generate fluid dynamic edge metrics: {e}")

        clean_results = {
            "sensor_snapshot": snapshot,
            "edge_data": edge_data,
            "mean_speed": mean_speed,
            "mean_occupancy": mean_occupancy,
            "loss": avg_loss,
            "losses": losses,
            "drift": avg_drift,
            "drift_scores": drift_scores,
            "qualities": qualities,
            "security_score": avg_loss,
            "processing_time": float(results.get("processing_time", 0.0)),
            "trigger_emergency_fallback": bool(results.get("trigger_emergency_fallback", False)),
        }

        self.global_cycle_results.emit(clean_results)
        self.kinetic_data_ready.emit({})

        # 9. Performance Metric Logging
        _ts_end = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        perf_logger.info(
            f"GLOBAL_CYCLE | cycle={self.cycle_count} "
            f"| start={_ts_start} | end={_ts_end} "
            f"| total={(time.time() - _cycle_start)*1000:.2f}ms"
        )
