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
# File: src/utils/debug_logger.py
# Author: Gabriel Moraes
# Date: 2026-08-19

import json
import logging
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from src.utils.logging_setup import get_log_dir


def _create_debug_logger(name: str, subfolder: str, prefix: str) -> logging.Logger:
    """
    Creates an independent rotating file logger under ~/Documentos/Synapse/logs/<subfolder>/.
    
    Each logger:
    - Writes to a session-based file: <prefix>_YYYY-MM-DD_HH-MM-SS.log
    - Uses RotatingFileHandler (max 20MB, 5 backups)
    - Has its own isolated hierarchy (no propagation to root)
    - Includes high-resolution timestamps, thread info, and file:line correlation
    """
    base_dir = get_log_dir() / subfolder
    
    try:
        base_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[DEBUG_LOGGER] Warning: Could not create {base_dir}: {e}")
        base_dir = Path.cwd() / "logs" / subfolder
        base_dir.mkdir(parents=True, exist_ok=True)
    
    session_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = base_dir / f"{prefix}_{session_id}.log"
    
    dbg_logger = logging.getLogger(f"Synapse.debug.{name}")
    dbg_logger.setLevel(logging.DEBUG)
    dbg_logger.propagate = False  # Isolate from root/SYNAPSE logger
    
    # Avoid duplicate handlers on reimport
    if dbg_logger.hasHandlers():
        dbg_logger.handlers.clear()
    
    # High-resolution formatter with milliseconds for cross-log correlation
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d | %(levelname)-7s | [%(process)d:%(threadName)s] | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    handler = RotatingFileHandler(
        log_file,
        maxBytes=20 * 1024 * 1024,  # 20 MB
        backupCount=5,
        encoding='utf-8'
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    dbg_logger.addHandler(handler)
    
    dbg_logger.info(f"--- SESSION STARTED: {log_file} ---")
    
    return dbg_logger


class JsonLinesLogger:
    """
    Thread-safe, append-only JSON Lines (JSONL) rotating logger for high-frequency telemetry.
    Writes one valid JSON object per line.
    """
    def __init__(self, subfolder: str, prefix: str):
        self.subfolder = subfolder
        self.prefix = prefix
        self._lock = threading.Lock()
        self._file_handle = None
        self._current_file: Optional[Path] = None
        self._session_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self._init_file()

    def _init_file(self):
        base_dir = get_log_dir() / self.subfolder
        try:
            base_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            base_dir = Path.cwd() / "logs" / self.subfolder
            base_dir.mkdir(parents=True, exist_ok=True)
            
        self._current_file = base_dir / f"{self.prefix}_{self._session_id}.jsonl"
        self._file_handle = open(self._current_file, "a", encoding="utf-8", buffering=1)

    def log(self, data: Dict[str, Any]) -> None:
        """Appends a single JSON line thread-safely."""
        try:
            line = json.dumps(data, ensure_ascii=False)
            with self._lock:
                if self._file_handle is None or self._file_handle.closed:
                    self._init_file()
                self._file_handle.write(line + "\n")
        except Exception:
            # Failsafe: Logging errors must never impact the real-time pipeline
            pass

    @property
    def file_path(self) -> Optional[Path]:
        return self._current_file

    def close(self):
        with self._lock:
            if self._file_handle and not self._file_handle.closed:
                try:
                    self._file_handle.close()
                except Exception:
                    pass
                self._file_handle = None


# ============================================================================
# EXPORTED SINGLETON LOGGERS
# ============================================================================

# Log 1: Carina Data Flow (KSE packet build + gRPC serialization + transmission)
# Records: KSE_BUILD, GRPC_FRAME, GRPC_SCENARIO, GRPC_COMMAND
carina_logger = _create_debug_logger("carina", "carina", "carina")

# Log 2: Neural Network Performance Metrics
# Records: CYCLE (per-stage timing), GLOBAL_CYCLE (total engine cycle)
perf_logger = _create_debug_logger("performance", "performance", "perf")

# Structured JSONL Dumps: Input data arriving at KSE vs Output traffic packets sent to CARINA
carina_input_logger = JsonLinesLogger("carina", "carina_input")
carina_output_logger = JsonLinesLogger("carina", "carina_output")

