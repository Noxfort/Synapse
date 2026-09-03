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
# File: src/utils/logging_setup.py
# Author: Gabriel Moraes
# Date: 2026-08-28

"""
Pure Orchestrator / Backward Compatibility Facade for SYNAPSE Logging.
Delegates all formatting, handlers, interceptors, and configuration to src.logging.
"""

import logging
from typing import Optional
from pathlib import Path

from src.logging.config import LogConfig
from src.logging.formatters import DetailedColoredFormatter, DetailedFileFormatter
from src.logging.interceptors import StreamToLogger
from src.logging.facade import (
    setup_logging,
    get_logger,
    set_global_level,
    get_log_dir,
    get_session_log_path,
)


def setup_logger(
    logger_name: str = "Synapse",
    console_level: Optional[int] = None,
    file_level: int = logging.DEBUG,
    redirect_streams: Optional[bool] = None
) -> logging.Logger:
    """
    Backward-compatible orchestration wrapper for setup_logging.
    """
    config = LogConfig.from_env(
        logger_name=logger_name,
        console_level=console_level,
        file_level=file_level,
        redirect_streams=redirect_streams
    )
    return setup_logging(config)


# Exported singleton instance for legacy imports
logger = setup_logger()

__all__ = [
    "setup_logger",
    "setup_logging",
    "get_logger",
    "set_global_level",
    "get_log_dir",
    "get_session_log_path",
    "DetailedColoredFormatter",
    "DetailedFileFormatter",
    "StreamToLogger",
    "logger",
]
