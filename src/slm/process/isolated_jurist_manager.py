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
# File: src/slm/process/isolated_jurist_manager.py
# Author: Gabriel Moraes
# Date: 2026-09-04

"""
Process Supervisor & Gateway for Out-of-Process LLM Inference.

Adheres strictly to SOLID:
- [SRP] Exclusively supervises subprocess lifecycle, IPC pipes, timeouts, and fault containment.
- [DIP] Consumed by JuristPipeline to satisfy IJuristPipeline without leaking process mechanics.
- [Fault Domain Isolation] If the worker process crashes (OOM/Segfault), the main process survives
  and falls back seamlessly.
"""

import os
import time
import uuid
import threading
import multiprocessing
from multiprocessing.connection import Connection
from typing import Dict, Any, Optional

from src.slm.process.llm_worker_process import run_llm_worker
from src.utils.logging_setup import get_logger
from src.utils.model_paths import get_qwen_gguf_path

logger = get_logger("SLM.IsolatedManager")


class IsolatedJuristManager:
    """
    Supervises the execution of the isolated LLM inference worker.
    """

    def __init__(
        self,
        model_id: Optional[str] = None,
        default_device: str = "auto",
        default_gpu_layers: int = 16,
        command_timeout: float = 60.0,
    ):
        self.model_id = model_id or get_qwen_gguf_path()
        self.default_device = default_device
        self.default_gpu_layers = default_gpu_layers
        self.command_timeout = command_timeout
        self.is_gguf = str(self.model_id).endswith(".gguf")

        self._process: Optional[multiprocessing.Process] = None
        self._parent_conn: Optional[Connection] = None
        self._lock = threading.Lock()
        self._is_loaded = False

    @property
    def is_alive(self) -> bool:
        """Returns True if the worker process is currently running."""
        return self._process is not None and self._process.is_alive()

    @property
    def is_loaded(self) -> bool:
        """Returns True if the model is loaded and worker is alive."""
        return self.is_alive and self._is_loaded

    def _ensure_worker_started(self) -> None:
        """Spawns the dedicated worker process if not already active."""
        if self.is_alive:
            return

        self._cleanup_process()

        logger.info(f"Spawning isolated LLM worker process for model: {self.model_id}")
        ctx = multiprocessing.get_context("spawn")
        self._parent_conn, child_conn = ctx.Pipe(duplex=True)

        self._process = ctx.Process(
            target=run_llm_worker,
            args=(
                child_conn,
                self.model_id,
                self.default_device,
                self.default_gpu_layers,
            ),
            daemon=True,
            name="Synapse-LLM-Worker",
        )
        self._process.start()

        # Close child handle in parent process
        try:
            child_conn.close()
        except Exception:
            pass

        logger.info(f"Isolated LLM Worker started with PID={self._process.pid}")

    def send_command(
        self,
        cmd: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """
        Sends a synchronous command envelope to the isolated worker and awaits response.
        Thread-safe and fault-tolerant.
        """
        timeout_val = timeout if timeout is not None else self.command_timeout

        with self._lock:
            self._ensure_worker_started()

            if not self._parent_conn or not self.is_alive:
                raise RuntimeError("Failed to establish IPC connection with isolated LLM worker process.")

            req_id = str(uuid.uuid4())
            envelope = {"id": req_id, "cmd": cmd, "payload": payload or {}}

            try:
                self._parent_conn.send(envelope)
            except Exception as e_send:
                logger.error(f"Failed to send command '{cmd}' over pipe: {e_send}")
                self._cleanup_process()
                raise RuntimeError(f"IPC Send failed: {e_send}") from e_send

            # Wait for response with timeout
            start_time = time.time()
            poll_interval = 0.1

            while time.time() - start_time < timeout_val:
                if not self.is_alive:
                    exit_code = self._process.exitcode if self._process else -1
                    self._cleanup_process()
                    raise RuntimeError(f"Isolated LLM Worker process died unexpectedly (exitcode={exit_code}).")

                try:
                    if self._parent_conn.poll(poll_interval):
                        resp = self._parent_conn.recv()
                        if isinstance(resp, dict) and resp.get("id") == req_id:
                            if resp.get("success"):
                                return resp.get("result")
                            else:
                                raise RuntimeError(resp.get("error", "Unknown worker error"))
                except (EOFError, BrokenPipeError) as e_pipe:
                    self._cleanup_process()
                    raise RuntimeError(f"IPC Pipe broken during command '{cmd}': {e_pipe}") from e_pipe

            # Timed out
            logger.error(f"Command '{cmd}' timed out after {timeout_val:.1f}s. Terminating worker.")
            self._cleanup_process(force=True)
            raise TimeoutError(f"Isolated LLM inference timed out after {timeout_val}s.")

    def load_resources(self, device: str = "auto", gpu_layers: int = 16) -> None:
        """Instructs worker to load model weights."""
        try:
            res = self.send_command(
                "load_resources",
                payload={"device": device, "gpu_layers": gpu_layers},
                timeout=45.0,
            )
            self._is_loaded = True
            logger.info(f"Isolated Jurist resources loaded: {res}")
        except Exception as e:
            logger.error(f"Error loading resources in isolated worker: {e}", exc_info=True)
            self._is_loaded = False
            raise

    def unload_resources(self) -> None:
        """Instructs worker to unload model weights and terminates process to guarantee 0 bytes VRAM."""
        if not self.is_alive:
            self._is_loaded = False
            return

        try:
            self.send_command("unload_resources", timeout=5.0)
        except Exception as e:
            logger.warning(f"Error while sending unload command to worker: {e}")
        finally:
            self._is_loaded = False
            self.shutdown()

    def generate_report(
        self,
        tensor_data: Dict[str, Any],
        timestamp: str = "",
        locale: str = "pt_BR",
        target: str = "XAI_Attribution",
        auto_unload: bool = True,
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> str:
        """
        Executes XAI narrative report synthesis in the isolated process.
        """
        payload = {
            "tensor_data": tensor_data,
            "timestamp": timestamp,
            "locale": locale,
            "target": target,
            "auto_unload": auto_unload,
            **kwargs,
        }
        try:
            result = self.send_command("generate_report", payload=payload, timeout=timeout)
            if auto_unload:
                self.shutdown()
            return str(result)
        except Exception as e:
            logger.error(f"Isolated report generation failed: {e}")
            if auto_unload:
                self.shutdown()
            return f"Erro: Inferência da LLM em processo isolado falhou: {e}"

    def generate(
        self,
        context_data: Dict[str, Any],
        auto_unload: bool = False,
        timeout: float = 60.0,
    ) -> str:
        """
        Executes general verdict generation in the isolated process.
        """
        payload = dict(context_data)
        payload["auto_unload"] = auto_unload

        try:
            result = self.send_command("generate_verdict", payload=payload, timeout=timeout)
            if auto_unload:
                self.shutdown()
            return str(result)
        except Exception as e:
            logger.error(f"Isolated verdict generation failed: {e}")
            if auto_unload:
                self.shutdown()
            return f"Erro: Inferência da LLM em processo isolado falhou: {e}"

    def shutdown(self) -> None:
        """Gracefully stops the worker process and frees all OS resources."""
        self._cleanup_process(force=False)

    def _cleanup_process(self, force: bool = False) -> None:
        """Internal helper to shut down and clean up worker process and pipe."""
        if self._parent_conn:
            if not force and self.is_alive:
                try:
                    self._parent_conn.send({"id": "exit", "cmd": "shutdown", "payload": {}})
                    time.sleep(0.1)
                except Exception:
                    pass
            try:
                self._parent_conn.close()
            except Exception:
                pass
            self._parent_conn = None

        if self._process is not None:
            if self._process.is_alive():
                try:
                    self._process.join(timeout=1.0)
                    if self._process.is_alive():
                        self._process.terminate()
                        self._process.join(timeout=1.0)
                        if self._process.is_alive():
                            self._process.kill()
                except Exception:
                    pass
            self._process = None

        self._is_loaded = False
        logger.info("Isolated LLM worker process cleaned up.")
