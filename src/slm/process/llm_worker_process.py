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
# File: src/slm/process/llm_worker_process.py
# Author: Gabriel Moraes
# Date: 2026-09-04

"""
Dedicated Out-of-Process LLM Worker (Fault-Domain & VRAM Isolation).

Responsibilities:
1. Runs inside an isolated operating system process spawned via multiprocessing ('spawn' context).
2. Completely shields the main SYNAPSE daemon and real-time HFT loop from:
   - PyTorch CUDA Out-Of-Memory (OOM) crashes.
   - C++ segmentation faults in llama-cpp / ggml bindings.
   - Global Interpreter Lock (GIL) contention during token generation.
3. Upon process termination, the OS kernel guarantees 100% reclamation of all RAM and VRAM.
"""

import os
import gc
import sys
import signal
import logging
from multiprocessing.connection import Connection
from typing import Dict, Any, Optional

# Configure minimal fallback logging inside isolated process
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(process)d] [%(levelname)s] [LLM.WorkerProcess] %(message)s",
)
logger = logging.getLogger("LLM.WorkerProcess")


class LLMWorkerInstance:
    """
    Stateful inference worker instance running inside the dedicated subprocess.
    """

    def __init__(self, model_id: str, device: str = "auto", gpu_layers: int = 16):
        self.model_id = model_id
        self.default_device = device
        self.default_gpu_layers = gpu_layers
        self.is_gguf = str(model_id).endswith(".gguf")
        self._model: Optional[Any] = None
        self._tokenizer: Optional[Any] = None
        self._is_loaded = False
        self._active_device = "cpu"

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded and self._model is not None

    def load_resources(self, device: Optional[str] = None, gpu_layers: Optional[int] = None) -> Dict[str, Any]:
        """Loads model into isolated process memory."""
        if self.is_loaded:
            return {"loaded": True, "device": self._active_device, "cached": True}

        target_device = device or self.default_device
        target_layers = gpu_layers if gpu_layers is not None else self.default_gpu_layers

        logger.info(f"Loading SLM in isolated worker (PID={os.getpid()}) from: {self.model_id}")

        if self.is_gguf:
            from src.slm.device_manager import SLMDeviceManager
            from src.slm.model_loader import SLMModelLoader

            device_setting, resolved_layers = SLMDeviceManager.resolve_device_settings(target_device, target_layers)
            self._model = SLMModelLoader.load_model(
                model_path=self.model_id,
                device_setting=device_setting,
                gpu_layers=resolved_layers,
                n_ctx=2048,
            )
            self._tokenizer = None
            self._is_loaded = True
            self._active_device = device_setting
            logger.info(f"GGUF SLM loaded in isolated worker (device={device_setting}, layers={resolved_layers}).")
        else:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM

            is_local = os.path.isdir(self.model_id)
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_id, local_files_only=is_local)
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                device_map="auto",
                torch_dtype=torch.float16,
                trust_remote_code=True,
                local_files_only=is_local,
            )
            self._is_loaded = True
            self._active_device = "auto"
            logger.info("HuggingFace LLM loaded in isolated worker (FP16).")

        return {"loaded": True, "device": self._active_device, "cached": False}

    def unload_resources(self) -> Dict[str, Any]:
        """Releases all model references and clears GPU cache."""
        if not self._is_loaded and self._model is None:
            return {"unloaded": True, "was_empty": True}

        logger.info("Unloading SLM in isolated worker to release resources...")
        if self._model is not None:
            if hasattr(self._model, "close"):
                try:
                    self._model.close()
                except Exception:
                    pass
            elif hasattr(self._model, "cpu"):
                try:
                    self._model.cpu()
                except Exception:
                    pass
            del self._model

        self._model = None
        self._tokenizer = None
        self._is_loaded = False

        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

        return {"unloaded": True}

    def generate_report(self, payload: Dict[str, Any]) -> str:
        """Synthesizes an XAI narrative report."""
        from src.slm.output_sanitizer import SLMOutputSanitizer
        from src.slm.prompt_builder import SLMPromptBuilder

        auto_unload = payload.get("auto_unload", False)
        tensor_data = payload.get("tensor_data", {})
        timestamp = payload.get("timestamp", "")
        locale = payload.get("locale", "pt_BR")
        target = payload.get("target", "XAI_Attribution")
        max_tokens = payload.get("max_tokens", 384)
        temperature = payload.get("temperature", 0.0)

        try:
            if not self.is_loaded:
                self.load_resources()

            if not self.is_loaded or self._model is None:
                return "Erro: Modelo Jurista não pôde ser carregado no processo isolado."

            if self.is_gguf:
                messages = SLMPromptBuilder.build_xai_chat_messages(
                    target=target,
                    attribution_map=tensor_data,
                    timestamp=timestamp,
                    locale=locale,
                )
                response_dict = self._model.create_chat_completion(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                raw_response = response_dict["choices"][0]["message"]["content"] or ""
            else:
                values_summary = [f"{k}: {v}" for k, v in tensor_data.items()]
                context_data = {
                    "source_id": target,
                    "status": "INVESTIGATION_FLAGGED",
                    "values": values_summary,
                    "language": locale,
                    "timestamp": timestamp,
                }
                raw_response = self.generate_verdict(context_data)

            return SLMOutputSanitizer.sanitize(raw_response)

        finally:
            if auto_unload:
                self.unload_resources()

    def generate_verdict(self, payload: Dict[str, Any]) -> str:
        """Generates general technical-legal verdict on traffic data."""
        from src.slm.output_sanitizer import SLMOutputSanitizer
        from src.services.prompt_registry import PromptRegistry

        auto_unload = payload.get("auto_unload", False)
        max_tokens = payload.get("max_tokens", 256)
        temperature = payload.get("temperature", 0.0)

        try:
            if not self.is_loaded:
                self.load_resources()

            if not self.is_loaded or self._model is None:
                return "Erro: Modelo Jurista não pôde ser carregado no processo isolado."

            messages = PromptRegistry.build_messages(
                source=payload.get("source_id", "Unknown"),
                status=payload.get("status", "NORMAL"),
                values=payload.get("values", []),
                language=payload.get("language", "pt_BR"),
            )

            if self.is_gguf:
                response_dict = self._model.create_chat_completion(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                raw_response = response_dict["choices"][0]["message"]["content"] or ""
            else:
                import torch
                device = torch.device(self._active_device if self._active_device != "auto" else "cpu")
                text = self._tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
                model_inputs = self._tokenizer([text], return_tensors="pt").to(device)

                with torch.no_grad():
                    generated_ids = self._model.generate(
                        **model_inputs,
                        max_new_tokens=max_tokens,
                        temperature=temperature,
                        do_sample=False,
                    )
                generated_ids = [
                    output_ids[len(input_ids):]
                    for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
                ]
                raw_response = self._tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

            cleaned = PromptRegistry.clean_response(raw_response)
            return SLMOutputSanitizer.sanitize(cleaned)

        finally:
            if auto_unload:
                self.unload_resources()


def run_llm_worker(
    pipe_conn: Connection,
    model_id: str,
    device: str = "auto",
    gpu_layers: int = 16,
) -> None:
    """
    Subprocess main event loop receiving commands over multiprocessing.Pipe.
    """
    # Ignore SIGINT in child worker; main process coordinates graceful shutdown
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    logger.info(f"🚀 Isolated LLM Worker Process online (PID={os.getpid()}, model={model_id})")

    worker = LLMWorkerInstance(model_id=model_id, device=device, gpu_layers=gpu_layers)

    try:
        while True:
            try:
                msg = pipe_conn.recv()
            except (EOFError, KeyboardInterrupt):
                logger.info("Pipe closed or interrupted. Exiting LLM worker process.")
                break

            if not isinstance(msg, dict):
                continue

            msg_id = msg.get("id", "")
            cmd = msg.get("cmd", "")
            payload = msg.get("payload", {})

            try:
                if cmd == "ping":
                    pipe_conn.send({"id": msg_id, "success": True, "result": "pong", "pid": os.getpid()})

                elif cmd == "load_resources":
                    res = worker.load_resources(
                        device=payload.get("device"),
                        gpu_layers=payload.get("gpu_layers"),
                    )
                    pipe_conn.send({"id": msg_id, "success": True, "result": res})

                elif cmd == "unload_resources":
                    res = worker.unload_resources()
                    pipe_conn.send({"id": msg_id, "success": True, "result": res})

                elif cmd == "generate_report":
                    text = worker.generate_report(payload)
                    pipe_conn.send({"id": msg_id, "success": True, "result": text})

                elif cmd == "generate_verdict":
                    text = worker.generate_verdict(payload)
                    pipe_conn.send({"id": msg_id, "success": True, "result": text})

                elif cmd == "shutdown":
                    logger.info("Shutdown command received. Cleaning up worker process.")
                    worker.unload_resources()
                    pipe_conn.send({"id": msg_id, "success": True, "result": "shutdown_ok"})
                    break

                else:
                    pipe_conn.send({"id": msg_id, "success": False, "error": f"Unknown command: {cmd}"})

            except Exception as cmd_err:
                logger.error(f"Error handling command '{cmd}': {cmd_err}", exc_info=True)
                pipe_conn.send({"id": msg_id, "success": False, "error": str(cmd_err)})

    finally:
        worker.unload_resources()
        try:
            pipe_conn.close()
        except Exception:
            pass
        logger.info(f"Isolated LLM Worker Process (PID={os.getpid()}) terminated cleanly.")
        sys.exit(0)
