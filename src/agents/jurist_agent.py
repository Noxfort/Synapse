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
# File: src/agents/jurist_agent.py
# Author: Gabriel Moraes
# Date: 2026-08-29

from typing import Dict, Any, Optional

from src.agents.base_agent import BaseAgent
from src.interfaces.pipelines import IJuristPipeline
from src.pipeline.jurist_pipeline import JuristPipeline
from src.utils.logging_setup import get_logger

logger = get_logger("JuristAgent")


class JuristAgent(BaseAgent):
    """
    The Jurist Agent ('O Juiz').
    
    Pure Orchestrator Architecture (SOLID Compliant):
    - Single Responsibility: High-level technical-legal traffic reasoning and report generation.
    - Delegation:
      -> Neural Pipeline & On-Demand SLM Lifecycle: IJuristPipeline (src/pipeline/jurist_pipeline.py)
    """

    def __init__(
        self,
        pipeline: Optional[IJuristPipeline] = None,
        model_id: Optional[str] = None,
        name: str = "JuristAgent",
        **kwargs: Any
    ):
        if pipeline is None:
            pipeline = JuristPipeline(model_id=model_id)

        model = getattr(pipeline, "model", None)
        super().__init__(model=model, name=name)

        self.pipeline: IJuristPipeline = pipeline

    @property
    def is_loaded(self) -> bool:
        return self.pipeline.is_loaded

    @property
    def is_gguf(self) -> bool:
        return getattr(self.pipeline, "is_gguf", False)

    @property
    def model_id(self) -> Optional[str]:
        return getattr(self.pipeline, "model_id", None)

    def load_resources(self, device: str = "auto", gpu_layers: int = 16) -> None:
        """Delegates resource loading to JuristPipeline."""
        self.pipeline.load_resources(device=device, gpu_layers=gpu_layers)

    def unload_resources(self) -> None:
        """Delegates resource cleanup and VRAM clearance to JuristPipeline."""
        self.pipeline.unload_resources()

    def inference(self, input_data: Dict[str, Any]) -> str:
        """Unified inference entry point."""
        return self.pipeline.generate(input_data)

    def generate_verdict(self, context_data: Dict[str, Any], auto_unload: bool = False) -> str:
        """Delegates verdict generation to JuristPipeline."""
        return self.pipeline.generate(context_data, auto_unload=auto_unload)

    def generate_report(
        self,
        tensor_data: Dict[str, Any],
        timestamp: str = "",
        locale: str = "pt_BR",
        target: str = "XAI_Attribution",
        auto_unload: bool = True,
        **kwargs: Any
    ) -> str:
        """Delegates on-demand XAI narrative synthesis to JuristPipeline."""
        return self.pipeline.generate_report(
            tensor_data=tensor_data,
            timestamp=timestamp,
            locale=locale,
            target=target,
            auto_unload=auto_unload,
            **kwargs
        )

    def train_step(self, batch_data: Any) -> float:
        """Jurist Agent does not train in the real-time loop."""
        return 0.0
