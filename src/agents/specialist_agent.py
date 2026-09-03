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
# File: src/agents/specialist_agent.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
import numpy as np
from typing import List, Any, Optional

from src.agents.base_agent import BaseAgent
from src.mixins.pbt_mixin import PBTMixin
from src.interfaces.pipelines import ISpecialistPipeline
from src.interfaces.trainers import ISpecialistTrainer
from src.pipeline.specialist_pipeline import SpecialistPipeline
from src.trainer.specialist_trainer import SpecialistTrainer


class SpecialistAgent(BaseAgent, PBTMixin):
    """
    The Specialist Agent ('O Tático').
    
    Pure Orchestrator Architecture (SOLID Compliant):
    - Single Responsibility: Manages temporal feature extraction and PBT population lifecycle.
    - Delegations:
      -> TCN Execution & Embeddings: ISpecialistPipeline (src/pipeline/specialist_pipeline.py)
      -> TCN Training Routines: ISpecialistTrainer (src/trainer/specialist_trainer.py)
    """

    def __init__(
        self,
        pipeline: Optional[ISpecialistPipeline] = None,
        trainer: Optional[ISpecialistTrainer] = None,
        input_dim: int = 1,
        output_dim: int = 32,
        num_channels: Optional[List[int]] = None,
        kernel_size: int = 2,
        dropout: float = 0.2,
        learning_rate: float = 0.001,
        name: str = "SpecialistAgent",
        **kwargs: Any
    ):
        num_channels = num_channels or [16, 32]

        if pipeline is None:
            pipeline = SpecialistPipeline(
                input_dim=input_dim,
                output_dim=output_dim,
                num_channels=num_channels,
                kernel_size=kernel_size,
                dropout=dropout
            )

        model = getattr(pipeline, "model", None)
        super().__init__(model=model, name=name)

        self.pipeline: ISpecialistPipeline = pipeline
        self.trainer: ISpecialistTrainer = trainer or SpecialistTrainer(
            model=self.model,
            input_dim=input_dim,
            output_dim=output_dim,
            learning_rate=learning_rate,
            device=getattr(self.pipeline, "device", None)
        )

        self.input_dim = input_dim
        self.output_dim = output_dim
        self.num_channels = num_channels
        self.kernel_size = kernel_size
        self.dropout = dropout
        self.learning_rate = learning_rate

        # Shortcuts for compatibility
        self.tcn = self.model["tcn"]
        self.decoder = self.model["decoder"] if "decoder" in self.model else None
        self.reconstruction_head = self.model["reconstruction_head"] if "reconstruction_head" in self.model else None

        # Extractor and Modality attached by the Linguist
        self.extractor: Optional[Any] = None
        self.semantic_type: Optional[str] = None
        self.inferred_unit: Optional[str] = None

        # PBT Metrics
        self.running_loss = 0.0
        self.steps = 0

    def set_extractor(
        self,
        extractor: Any,
        semantic_type: Optional[str] = None,
        unit: Optional[str] = None
    ) -> 'SpecialistAgent':
        """
        Attaches the extraction pipeline and modality taught by the Linguist,
        enabling this local TCN to process raw sensor packets autonomously.
        """
        self.extractor = extractor
        self.semantic_type = semantic_type
        self.inferred_unit = unit
        return self

    @property
    def optimizer(self):
        """Delegates optimizer access to the underlying trainer."""
        if hasattr(self.trainer, "optimizer"):
            return self.trainer.optimizer
        return getattr(self, "_optimizer", None)

    def freeze(self) -> 'SpecialistAgent':
        """Freezes specialist weights for drift-safe real-time inference (Freeze phase)."""
        if hasattr(self.pipeline, "freeze"):
            self.pipeline.freeze()
        return self

    def unfreeze(self) -> 'SpecialistAgent':
        """Unfreezes specialist weights for dynamic recalibration."""
        if hasattr(self.pipeline, "unfreeze"):
            self.pipeline.unfreeze()
        return self

    @property
    def is_frozen(self) -> bool:
        if hasattr(self.pipeline, "is_frozen"):
            return self.pipeline.is_frozen
        return False

    def inference(self, input_data: Any) -> Any:
        """
        Standard Interface Wrapper: accepts either raw sensor packets (using its attached extractor)
        or numerical time-series arrays, and outputs 32-dim latent space embeddings.
        """
        return self.predict(input_data)

    def predict(self, input_sequence: Any) -> np.ndarray:
        """
        Processes the input sequence or raw payload and returns TCN latent embeddings.
        """
        # If input is a raw dictionary, list of dicts, or unparsed payload, use attached extractor
        if isinstance(input_sequence, (dict, list)) and self.extractor is not None:
            if isinstance(input_sequence, dict):
                input_data = [input_sequence]
            else:
                input_data = input_sequence
            if len(input_data) > 0 and isinstance(input_data[0], (dict, str)):
                seq_np = self.extractor.extract(input_data)
                return self.pipeline.predict(seq_np)

        return self.pipeline.predict(input_sequence)

    def train_step(self, batch_data: Any) -> float:
        """Delegates training step to SpecialistTrainer."""
        return self.trainer.train_step(batch_data)

    def train(self, inputs: torch.Tensor, targets: torch.Tensor, epochs: int = 1, batch_size: int = 32) -> float:
        """Delegates training loop to SpecialistTrainer and tracks PBT running loss."""
        avg_loss = self.trainer.train(inputs, targets, epochs=epochs, batch_size=batch_size)
        self.running_loss = 0.9 * self.running_loss + 0.1 * avg_loss if self.steps > 0 else avg_loss
        self.steps += 1
        return avg_loss

    # --- Persistence Primitives ---

    def get_state(self) -> dict:
        """Returns the agent's internal neural state dictionary."""
        state = {
            "agent_weights": {
                "tcn": self.tcn.state_dict(),
            }
        }
        if self.decoder is not None and hasattr(self.decoder, "state_dict"):
            state["agent_weights"]["decoder"] = self.decoder.state_dict()
        if self.reconstruction_head is not None and hasattr(self.reconstruction_head, "state_dict"):
            state["agent_weights"]["head"] = self.reconstruction_head.state_dict()
        state.update(self.get_pbt_state())
        return state

    def set_state(self, state: dict):
        """Loads weights safely into components."""
        weights = state.get("agent_weights", {})
        if "tcn" in weights:
            self.tcn.load_state_dict(weights["tcn"])
        if self.decoder is not None and "decoder" in weights and hasattr(self.decoder, "load_state_dict"):
            self.decoder.load_state_dict(weights["decoder"])
        if self.reconstruction_head is not None and "head" in weights and hasattr(self.reconstruction_head, "load_state_dict"):
            self.reconstruction_head.load_state_dict(weights["head"])

        self.set_pbt_state(state)
