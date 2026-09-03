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
# File: src/logging/facade.py
# Author: Gabriel Moraes
# Date: 2026-08-29

"""
Public Facade for the SYNAPSE Logging Subsystem.
Orchestrates configuration, formatting, handlers, and interceptors cleanly conforming to SOLID.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from src.logging.config import LogConfig, LEVEL_MAP, resolve_log_directory
from src.logging.formatters import DetailedColoredFormatter, DetailedFileFormatter
from src.logging.handlers import create_console_handler, create_rotating_file_handler
from src.logging.interceptors import StreamToLogger, install_excepthook, redirect_system_streams


_CURRENT_SESSION_FILE: Optional[Path] = None
_CONSOLE_HANDLER: Optional[logging.Handler] = None
_FILE_HANDLER: Optional[logging.Handler] = None
_IS_INITIALIZED: bool = False


def get_log_dir() -> Path:
    """Returns the central directory for SYNAPSE logs."""
    return resolve_log_directory()


def get_session_log_path() -> Optional[Path]:
    """Returns the path to the current session's log file."""
    return _CURRENT_SESSION_FILE


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Returns a standardized logger instance under the Synapse hierarchy.
    
    Usage:
        logger = get_logger(__name__)
        logger = get_logger("Coordinator")
    """
    if not name:
        return logging.getLogger("Synapse")
    
    if name.startswith("Synapse.") or name == "Synapse":
        return logging.getLogger(name)
    elif name.startswith("src."):
        # Standardize src.submodule -> Synapse.submodule
        clean_name = name[4:]
        return logging.getLogger(f"Synapse.{clean_name}")
    else:
        return logging.getLogger(f"Synapse.{name}")


def setup_logging(config: Optional[LogConfig] = None) -> logging.Logger:
    """
    Orchestrates and initializes the logging infrastructure according to LogConfig.
    """
    global _CURRENT_SESSION_FILE, _CONSOLE_HANDLER, _FILE_HANDLER, _IS_INITIALIZED

    cfg = config or LogConfig.from_env()

    # 1. Resolve Log File Location
    log_dir = cfg.log_dir or resolve_log_directory()
    session_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    _CURRENT_SESSION_FILE = log_dir / f"session_{session_id}.log"

    # 2. Base Logger Setup (Root + Synapse)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Root allows everything; handlers filter

    synapse_logger = logging.getLogger(cfg.logger_name)
    synapse_logger.setLevel(logging.DEBUG)
    synapse_logger.propagate = True  # Propagate to root handlers

    # Clean existing handlers on root to avoid duplicate outputs
    if _CONSOLE_HANDLER and _CONSOLE_HANDLER in root_logger.handlers:
        root_logger.removeHandler(_CONSOLE_HANDLER)
    if _FILE_HANDLER and _FILE_HANDLER in root_logger.handlers:
        root_logger.removeHandler(_FILE_HANDLER)

    # 3. Create Handlers
    console_handler = create_console_handler(level=cfg.console_level)
    root_logger.addHandler(console_handler)
    _CONSOLE_HANDLER = console_handler

    file_handler = create_rotating_file_handler(
        file_path=_CURRENT_SESSION_FILE,
        level=cfg.file_level,
        max_bytes=cfg.max_bytes,
        backup_count=cfg.backup_count
    )
    if file_handler:
        root_logger.addHandler(file_handler)
        _FILE_HANDLER = file_handler

    # 4. Quiet Noisy Third-Party Libraries
    for lib in cfg.noisy_libs:
        logging.getLogger(lib).setLevel(logging.WARNING)

    # 5. Global Uncaught Exception Hook
    if cfg.enable_excepthook:
        install_excepthook(synapse_logger)

    # 6. Stream Redirection
    if cfg.redirect_streams:
        redirect_system_streams(synapse_logger)

    if not _IS_INITIALIZED:
        _IS_INITIALIZED = True
        synapse_logger.info(f"=== SYNAPSE LOGGING INITIALIZED (Level: {logging.getLevelName(cfg.console_level)}) ===")
        synapse_logger.info(f"Session Log File: {_CURRENT_SESSION_FILE}")

    return synapse_logger


def set_global_level(level_str: str):
    """
    Dynamically updates the global log level for console output and all active loggers.
    """
    target_level = LEVEL_MAP.get(level_str.upper(), logging.INFO)

    # Update console handler level
    if _CONSOLE_HANDLER:
        _CONSOLE_HANDLER.setLevel(target_level)

    # Update root and base Synapse loggers
    root = logging.getLogger()
    root.setLevel(target_level)
    logging.getLogger("Synapse").setLevel(target_level)
    logging.getLogger("SYNAPSE").setLevel(target_level)

    for name, log_obj in logging.root.manager.loggerDict.items():
        if isinstance(log_obj, logging.Logger):
            if name.startswith("Synapse") or name.startswith("SYNAPSE") or name.startswith("src"):
                log_obj.setLevel(target_level)

    logging.getLogger("Synapse").info(f"Log level updated globally to: {logging.getLevelName(target_level)}")


__all__ = [
    "setup_logging",
    "get_logger",
    "set_global_level",
    "get_log_dir",
    "get_session_log_path",
    "LogConfig",
    "DetailedColoredFormatter",
    "DetailedFileFormatter",
    "StreamToLogger",
    "create_console_handler",
    "create_rotating_file_handler",
    "install_excepthook",
    "redirect_system_streams",
]
