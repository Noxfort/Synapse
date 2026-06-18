# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2025 Noxfort Labs
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
# Date: 2026-02-14

import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import Dict, Any, Optional
import gc

from src.agents.base_agent import BaseAgent
from src.services.prompt_registry import PromptRegistry


class JuristAgent(BaseAgent):
    """
    The Jurist Agent ('O Juiz').
    
    Responsibilities:
    1. XAI Generation: Explains technical decisions in natural/legal language.
    2. Regulatory Compliance: Maps anomalies to Traffic Code infractions.
    
    Refactored V6 (SOLID):
    - Prompts delegated to PromptRegistry (SRP).
    - Response parsing delegated to PromptRegistry.clean_response().
    - Agent is now a thin orchestrator: load model, build prompt, generate, clean.
    """

    def __init__(self, model_id: Optional[str] = None):
        """
        Initializes the agent but DOES NOT load the model immediately.
        """
        super().__init__(model=None, name="JuristAgent")
        
        if model_id is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.model_id = os.path.join(base_dir, "Model Vault", "qwen3_1.7B")
        else:
            self.model_id = model_id

        self.tokenizer = None
        self.is_loaded = False

    def _get_current_device(self) -> torch.device:
        if not self.is_loaded or self.model is None:
            return torch.device("cpu")
        try:
            return next(self.model.parameters()).device
        except StopIteration:
            return torch.device("cpu")

    # =========================================================================
    # LIFECYCLE
    # =========================================================================

    def load_resources(self):
        """Explicitly loads the Heavy LLM into VRAM in Native FP16 mode."""
        if self.is_loaded:
            return

        print(f"[{self.name}] Loading LLM ({self.model_id}) in FP16 Mode...")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                device_map="auto",
                torch_dtype=torch.float16,
                trust_remote_code=True
            )
            self.is_loaded = True
            print(f"[{self.name}] LLM Loaded successfully (FP16).")
        except Exception as e:
            print(f"[{self.name}] Failed to load LLM: {e}")
            self.is_loaded = False

    def unload_resources(self):
        """Frees VRAM by moving the model to CPU and deleting references."""
        if not self.is_loaded:
            return

        print(f"[{self.name}] Unloading LLM to free VRAM...")
        
        if self.model:
            self.model.cpu()
        
        del self.model
        del self.tokenizer
        
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    # =========================================================================
    # INFERENCE (Orchestration Only)
    # =========================================================================

    def inference(self, input_data: Dict[str, Any]) -> str:
        """Standard Interface: Generates a verdict."""
        return self.generate_verdict(input_data)

    def generate_verdict(self, context_data: Dict[str, Any]) -> str:
        """
        Orchestrates the verdict generation pipeline:
        1. Build prompt via PromptRegistry
        2. Tokenize & generate via LLM
        3. Clean response via PromptRegistry
        """
        if not self.is_loaded:
            self.load_resources()

        device = self._get_current_device()

        # 1. Build Messages (Delegated to PromptRegistry)
        messages = PromptRegistry.build_messages(
            source=context_data.get('source_id', 'Unknown'),
            status=context_data.get('status', 'NORMAL'),
            values=context_data.get('values', []),
            language=context_data.get('language', 'pt_BR')
        )

        # 2. Tokenization & Generation
        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        model_inputs = self.tokenizer([text], return_tensors="pt").to(device)

        with torch.no_grad():
            generated_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=512,
                temperature=0.0,
                do_sample=False
            )

        # 3. Decode
        generated_ids = [
            output_ids[len(input_ids):] 
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

        # 4. Clean (Delegated to PromptRegistry)
        return PromptRegistry.clean_response(response)

    def train_step(self, batch_data: Any) -> float:
        """Jurist Agent does not train in the real-time loop."""
        return 0.0