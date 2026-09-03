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
# File: src/workers/xai_worker.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import torch
from datetime import datetime
from typing import Any, Dict, List, Optional
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from src.interfaces.xai import (
    IXAIExplainer,
    IXAIReporter,
    IXAIStrategy,
    IXAIStrategyRegistry,
)
from src.strategies.xai_strategies import XAIStrategyRegistry
from src.services.xai_explainer_service import CaptumExplainerService
from src.services.xai_reporter_service import XAIReporterService
from src.utils.logging_setup import get_logger

logger = get_logger("XAI.Worker")


class _XAITask(QThread):
    """
    Ephemeral thread executing a single XAI attribution job.
    Delegates model preparation, gradient computation, and reporting to injected services.
    
    Lifecycle: Created → run() → result_ready emitted → finished → deleteLater.
    """

    result_ready = pyqtSignal(dict)

    def __init__(
        self,
        payload: Dict[str, Any],
        device: torch.device,
        registry: IXAIStrategyRegistry,
        explainer: IXAIExplainer,
        reporter: IXAIReporter,
        model_config: Dict[str, Any]
    ):
        super().__init__()
        self.payload = payload
        self.device = device
        self.registry = registry
        self.explainer = explainer
        self.reporter = reporter
        self.model_config = model_config

        # Auto-cleanup on thread termination
        self.finished.connect(self.deleteLater)

    def run(self):
        """Executes attribution analysis pipeline via decoupled services."""
        target = self.payload["target"]
        logger.info(f"🧠 Analyzing '{target}' (ephemeral thread)...")

        try:
            # 1. Retrieve Strategy & Prepare Model Wrapper
            strategy = self.registry.get(target)
            if not strategy:
                raise ValueError(f"Unknown target model or unregistered XAI strategy: '{target}'")

            model_wrapper = strategy.prepare_wrapper(
                input_vector=self.payload["input_vector"],
                model_config=self.model_config,
                device=self.device
            )

            # 2. Mathematical Attribution via Explainer Service
            attr_list, delta = self.explainer.compute_attributions(
                model_wrapper=model_wrapper,
                input_vector=self.payload["input_vector"],
                device=self.device
            )

            # 3. Semantic Report Generation
            report_text = self.reporter.generate_report(
                target=target,
                attr_list=attr_list,
                feature_names=self.payload.get("feature_names", []),
                timestamp=self.payload["timestamp"],
                delta=delta,
                strategy=strategy
            )

            # 4. Emit Result
            result = {
                "type": "XAI_RESULT",
                "target": target,
                "request_id": self.payload["request_id"],
                "timestamp": self.payload["timestamp"],
                "input_vector": self.payload["input_vector"],
                "feature_names": self.payload.get("feature_names", []),
                "attributions": attr_list,
                "convergence_delta": delta,
                "semantic_text": report_text
            }
            self.result_ready.emit(result)

        except Exception as e:
            logger.error(f"Process Error in XAI Task: {e}", exc_info=True)
            self.result_ready.emit({
                "type": "XAI_RESULT",
                "target": target,
                "request_id": self.payload["request_id"],
                "timestamp": self.payload["timestamp"],
                "input_vector": [],
                "feature_names": [],
                "attributions": [],
                "convergence_delta": 0.0,
                "semantic_text": f"Analysis Process Failed: {str(e)}"
            })


class XAIWorker(QObject):
    """
    On-Demand XAI Manager / Pure Orchestrator Facade (SOLID V5).
    
    Responsibilities:
    - Coordinates asynchronous execution via ephemeral worker threads.
    - Exposes PyQt signals for UI and controller layers.
    - Delegates domain logic to injected strategy registry, explainer, and reporter services.
    """

    result_ready = pyqtSignal(dict)

    def __init__(
        self,
        model_config: Optional[Dict[str, Any]] = None,
        registry: Optional[IXAIStrategyRegistry] = None,
        explainer: Optional[IXAIExplainer] = None,
        reporter: Optional[IXAIReporter] = None,
        device: Optional[torch.device] = None
    ):
        super().__init__()
        self.model_config = model_config or {}
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.registry = registry or XAIStrategyRegistry()
        self.explainer = explainer or CaptumExplainerService()
        self.reporter = reporter or XAIReporterService()

        # Track active tasks to prevent early Python garbage collection
        self._active_tasks: List[_XAITask] = []

    @property
    def jurist(self):
        """Backward-compatible accessor for the underlying Jurist agent if available."""
        return getattr(self.reporter, "jurist", None)

    def submit_request(
        self,
        target_type: str,
        input_vector: List[float],
        feature_names: List[str],
        model_state: Optional[Dict[str, Any]] = None,
        error: float = 0.0
    ) -> None:
        """Spawns an ephemeral thread for one XAI analysis job."""
        payload = {
            "timestamp": datetime.now().isoformat(),
            "target": target_type,
            "input_vector": input_vector,
            "feature_names": feature_names,
            "model_state": model_state,
            "error": error,
            "request_id": f"req_{target_type}_{int(datetime.now().timestamp())}"
        }

        task = _XAITask(
            payload=payload,
            device=self.device,
            registry=self.registry,
            explainer=self.explainer,
            reporter=self.reporter,
            model_config=self.model_config
        )
        task.result_ready.connect(self.result_ready)
        task.finished.connect(lambda: self._cleanup_task(task))

        self._active_tasks.append(task)
        task.start()

        logger.debug(f"Spawned ephemeral thread for '{target_type}' analysis.")

    def _cleanup_task(self, task: _XAITask) -> None:
        """Removes finished task from tracking list."""
        if task in self._active_tasks:
            self._active_tasks.remove(task)

    def unload_resources(self) -> None:
        """Delegates resource/VRAM cleanup to the reporter service."""
        if self.reporter is not None:
            self.reporter.unload_resources()
