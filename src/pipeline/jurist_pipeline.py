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
# File: src/pipeline/jurist_pipeline.py
# Author: Gabriel Moraes
# Date: 2026-09-03

import os
import gc
import torch
import threading
from typing import Dict, Any, Optional, List

from src.interfaces.pipelines import IJuristPipeline
from src.services.prompt_registry import PromptRegistry
from src.slm.device_manager import SLMDeviceManager
from src.slm.model_loader import SLMModelLoader
from src.slm.output_sanitizer import SLMOutputSanitizer
from src.slm.prompt_builder import SLMPromptBuilder
from src.slm.process.isolated_jurist_manager import IsolatedJuristManager
from src.utils.logging_setup import get_logger
from src.utils.model_paths import get_qwen_gguf_path

logger = get_logger("Pipeline.Jurist")


class JuristPipeline(IJuristPipeline):
    """
    On-Demand SLM Execution & Technical-Legal Reasoning Pipeline.
    
    SOLID Architecture:
    - [SRP] Encapsulates all neural model lifecycle, C++ llama_cpp bindings, tokenization,
            and memory cleanups away from the high-level Agent.
    - [DIP] Implements IJuristPipeline interface.
    - [Fault Domain Isolation] Delegates execution to IsolatedJuristManager (out-of-process) by default.
    """

    def __init__(self, model_id: Optional[str] = None, isolated: bool = True):
        self.model_id = model_id or get_qwen_gguf_path()
        self.isolated = isolated
        self.is_gguf = str(self.model_id).endswith(".gguf")
        self._lock = threading.Lock()
        self._device = "cpu"

        # In-process state (used if isolated=False or fallback)
        self.tokenizer: Optional[Any] = None
        self._model: Optional[Any] = None
        self._is_loaded = False

        # Out-of-process manager (Fault-Domain & Zero-VRAM Isolation)
        self._isolated_manager = (
            IsolatedJuristManager(model_id=self.model_id) if self.isolated else None
        )

    @property
    def is_loaded(self) -> bool:
        if self.isolated and self._isolated_manager:
            return self._isolated_manager.is_loaded
        return self._is_loaded and self._model is not None

    @property
    def model(self) -> Optional[Any]:
        return self._model

    def to(self, device: torch.device) -> 'JuristPipeline':
        """Moves resources to target device (IDeviceMovable)."""
        self._device = str(device)
        return self

    def load_resources(self, device: str = "auto", gpu_layers: int = 16) -> None:
        """Loads the SLM model into memory on demand using CARINA-style SLM loader."""
        if self.is_loaded:
            return

        if self.isolated and self._isolated_manager:
            self._isolated_manager.load_resources(device=device, gpu_layers=gpu_layers)
            return

        logger.info(f"[JuristPipeline] Loading SLM on-demand from: {self.model_id}")
        try:
            if self.is_gguf:
                device_setting, resolved_layers = SLMDeviceManager.resolve_device_settings(device, gpu_layers)
                self._model = SLMModelLoader.load_model(
                    model_path=self.model_id,
                    device_setting=device_setting,
                    gpu_layers=resolved_layers,
                    n_ctx=2048
                )
                self.tokenizer = None
                self._is_loaded = True
                self._device = device_setting
                logger.info(f"[JuristPipeline] GGUF SLM loaded (device={device_setting}, layers={resolved_layers}).")
            else:
                from transformers import AutoTokenizer, AutoModelForCausalLM
                is_local = os.path.isdir(self.model_id)
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.model_id,
                    local_files_only=is_local
                )
                self._model = AutoModelForCausalLM.from_pretrained(
                    self.model_id,
                    device_map="auto",
                    torch_dtype=torch.float16,
                    trust_remote_code=True,
                    local_files_only=is_local
                )
                self._is_loaded = True
                logger.info("[JuristPipeline] HF LLM Loaded successfully (FP16).")
        except Exception as e:
            logger.error(f"[JuristPipeline] Failed to load SLM ({self.model_id}): {e}", exc_info=True)
            self._is_loaded = False
            self._model = None

    def unload_resources(self) -> None:
        """Frees VRAM/RAM by destroying the model instance and clearing GPU cache."""
        if self.isolated and self._isolated_manager:
            self._isolated_manager.unload_resources()
            return

        if not self._is_loaded and self._model is None:
            return

        logger.info("[JuristPipeline] Unloading SLM to free system resources...")
        if self._model is not None:
            if hasattr(self._model, 'close'):
                try:
                    self._model.close()
                except Exception:
                    pass
            elif hasattr(self._model, 'cpu'):
                try:
                    self._model.cpu()
                except Exception:
                    pass
            del self._model

        self._model = None
        self.tokenizer = None
        self._is_loaded = False

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            try:
                free_vram, total_vram = torch.cuda.mem_get_info()
                logger.info(
                    f"[JuristPipeline] SLM resources released. Free VRAM: {free_vram / (1024**3):.2f} GB / Total: {total_vram / (1024**3):.2f} GB"
                )
            except Exception:
                pass

    def generate_report(
        self,
        tensor_data: Dict[str, Any],
        timestamp: str = "",
        locale: str = "pt_BR",
        target: str = "XAI_Attribution",
        auto_unload: bool = True,
        **kwargs: Any
    ) -> str:
        """
        Executes on-demand XAI narrative synthesis.
        Delegates to isolated process worker when isolated=True.
        """
        if self.isolated and self._isolated_manager:
            return self._isolated_manager.generate_report(
                tensor_data=tensor_data,
                timestamp=timestamp,
                locale=locale,
                target=target,
                auto_unload=auto_unload,
                **kwargs
            )

        with self._lock:
            try:
                if not self.is_loaded:
                    self.load_resources()

                if not self.is_loaded or self._model is None:
                    return "Erro: Modelo Jurista não pôde ser carregado do Model_Vault."

                if self.is_gguf:
                    messages = SLMPromptBuilder.build_xai_chat_messages(
                        target=target,
                        attribution_map=tensor_data,
                        timestamp=timestamp,
                        locale=locale
                    )
                    response_dict = self._model.create_chat_completion(
                        messages=messages,
                        max_tokens=256,
                        temperature=0.0
                    )
                    raw_response = response_dict["choices"][0]["message"]["content"] or ""
                else:
                    values_summary = [f"{k}: {v}" for k, v in tensor_data.items()]
                    context_data = {
                        "source_id": target,
                        "status": "INVESTIGATION_FLAGGED",
                        "values": values_summary,
                        "language": locale,
                        "timestamp": timestamp
                    }
                    raw_response = self.generate(context_data, auto_unload=False)

                return SLMOutputSanitizer.sanitize(raw_response)

            finally:
                if auto_unload:
                    self.unload_resources()

    def generate(self, context_data: Dict[str, Any], auto_unload: bool = False) -> str:
        """
        Executes general verdict generation with prompt formatting and post-cleaning.
        """
        if self.isolated and self._isolated_manager:
            return self._isolated_manager.generate(
                context_data=context_data,
                auto_unload=auto_unload
            )

        with self._lock:
            try:
                if not self.is_loaded:
                    self.load_resources()

                if not self.is_loaded or self._model is None:
                    return "Erro: Modelo Jurista não pôde ser carregado do Model_Vault."

                messages = PromptRegistry.build_messages(
                    source=context_data.get('source_id', 'Unknown'),
                    status=context_data.get('status', 'NORMAL'),
                    values=context_data.get('values', []),
                    language=context_data.get('language', 'pt_BR')
                )

                if self.is_gguf:
                    try:
                        response_dict = self._model.create_chat_completion(
                            messages=messages,
                            max_tokens=256,
                            temperature=0.0
                        )
                        raw_response = response_dict["choices"][0]["message"]["content"] or ""
                    except Exception as e:
                        logger.error(f"[JuristPipeline] GGUF generation failed: {e}")
                        return f"Erro na inferência do Jurista: {e}"
                else:
                    device = torch.device(self._device)
                    text = self.tokenizer.apply_chat_template(
                        messages, tokenize=False, add_generation_prompt=True
                    )
                    model_inputs = self.tokenizer([text], return_tensors="pt").to(device)

                    with torch.no_grad():
                        generated_ids = self._model.generate(
                            **model_inputs,
                            max_new_tokens=256,
                            temperature=0.0,
                            do_sample=False
                        )

                    generated_ids = [
                        output_ids[len(input_ids):] 
                        for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
                    ]
                    raw_response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

                cleaned = PromptRegistry.clean_response(raw_response)
                return SLMOutputSanitizer.sanitize(cleaned)

            finally:
                if auto_unload:
                    self.unload_resources()
