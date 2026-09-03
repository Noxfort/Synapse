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
# File: src/slm/model_loader.py
# Author: Gabriel Moraes
# Date: 2026-09-03

import os
from typing import Any, Optional
from src.utils.logging_setup import get_logger

logger = get_logger("SLM.ModelLoader")


class SLMModelLoader:
    """
    Encapsulates loading and initialization of GGUF model files using llama-cpp-python,
    handling GPU acceleration and automatic graceful CPU fallback in a single process.
    Adheres to the CARINA SLM architecture pattern.
    """

    @staticmethod
    def load_model(
        model_path: str,
        device_setting: str = "auto",
        gpu_layers: int = -1,
        n_ctx: int = 4096
    ) -> Any:
        """
        Loads the GGUF model file. Tries GPU acceleration first (if configured),
        falling back automatically to CPU without crashing.
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model Vault file not found at: {model_path}")

        try:
            from llama_cpp import Llama
        except ImportError:
            raise RuntimeError("llama-cpp-python is not installed in the virtual environment.")

        n_gpu_layers = gpu_layers if device_setting != "cpu" else 0
        model: Optional[Any] = None

        if n_gpu_layers != 0:
            try:
                logger.info(
                    f"[SLMModelLoader] Loading GGUF model with GPU acceleration (gpu_layers={n_gpu_layers}, n_ctx={n_ctx}): {model_path}"
                )
                model = Llama(
                    model_path=model_path,
                    n_ctx=n_ctx,
                    n_gpu_layers=n_gpu_layers,
                    verbose=False
                )
                logger.info("✅ [SLMModelLoader] GGUF model loaded successfully on GPU.")
                return model
            except Exception as e:
                logger.warning(
                    f"⚠️ [SLMModelLoader] GPU load failed (gpu_layers={n_gpu_layers}): {e}. Attempting CPU fallback..."
                )
                model = None

        if model is None:
            try:
                logger.info(f"[SLMModelLoader] Loading GGUF model on CPU (gpu_layers=0, n_ctx={n_ctx}): {model_path}")
                model = Llama(
                    model_path=model_path,
                    n_ctx=n_ctx,
                    n_gpu_layers=0,
                    verbose=False
                )
                logger.info("✅ [SLMModelLoader] GGUF model loaded successfully on CPU.")
                return model
            except Exception as e:
                logger.error(f"❌ [SLMModelLoader] CPU model loading failed: {e}")
                raise RuntimeError(f"Failed to load SLM model resources: {e}")
