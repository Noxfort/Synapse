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
# File: src/logging/formatters.py
# Author: Gabriel Moraes
# Date: 2026-08-28

"""
Specialized formatters for console and persistent file logs.
Pure formatting logic conforming to SRP and LSP.
"""

import sys
import os
import logging
from datetime import datetime
from typing import Dict, Tuple


class DetailedColoredFormatter(logging.Formatter):
    """
    Console Formatter with ANSI colors and high-precision metadata for VS Code / Terminal.
    Formats logs as:
    [HH:MM:SS.mmm] LEVEL   [LoggerName] filename.py:line (function) - Message
    """

    # ANSI Codes
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"

    # Foreground Colors
    GREY = "\033[90m"
    CYAN = "\033[36m"
    BRIGHT_CYAN = "\033[96m"
    GREEN = "\033[32m"
    BRIGHT_GREEN = "\033[92m"
    YELLOW = "\033[33m"
    BRIGHT_YELLOW = "\033[93m"
    RED = "\033[31m"
    BRIGHT_RED = "\033[91m"
    MAGENTA = "\033[35m"
    WHITE = "\033[97m"

    # Background Colors
    BG_RED = "\033[41m"

    LEVEL_CONFIG: Dict[int, Tuple[str, str]] = {
        logging.DEBUG: (BRIGHT_CYAN, "DEBUG   "),
        logging.INFO: (BRIGHT_GREEN, "INFO    "),
        logging.WARNING: (BRIGHT_YELLOW, "WARNING "),
        logging.ERROR: (BRIGHT_RED, "ERROR   "),
        logging.CRITICAL: (f"{BG_RED}{WHITE}{BOLD}", "CRITICAL"),
    }

    def __init__(self, use_colors: bool = True):
        super().__init__(datefmt="%H:%M:%S")
        # Check if terminal supports colors
        self.use_colors = use_colors and (
            hasattr(sys.__stdout__, "isatty") and sys.__stdout__.isatty()
            or os.environ.get("COLORTERM") is not None
            or os.environ.get("TERM") in ("xterm", "xterm-256color", "screen", "vt100")
            or "VSCODE_PID" in os.environ
        )

    def format(self, record: logging.LogRecord) -> str:
        # High precision timestamp
        created = datetime.fromtimestamp(record.created)
        timestamp_str = created.strftime("%H:%M:%S") + f".{record.msecs:03.0f}"

        level_color, level_label = self.LEVEL_CONFIG.get(
            record.levelno, (self.WHITE, f"{record.levelname:<8}")
        )

        # Truncate / format logger name for clean alignment
        logger_name = record.name
        if logger_name.startswith("Synapse."):
            logger_name = logger_name[8:]
        elif logger_name.startswith("src."):
            logger_name = logger_name[4:]

        # Location info (clickable in VS Code terminal: file.py:line)
        loc = f"{record.filename}:{record.lineno}"
        func = f"({record.funcName})" if record.funcName != "<module>" else ""

        # Format message
        message = record.getMessage()

        if self.use_colors:
            header = (
                f"{self.GREY}[{timestamp_str}]{self.RESET} "
                f"{level_color}{level_label}{self.RESET} "
                f"{self.MAGENTA}[{logger_name}]{self.RESET} "
                f"{self.CYAN}{loc}{self.RESET} "
                f"{self.DIM}{func}{self.RESET}"
            )
            formatted = f"{header} - {message}"
        else:
            header = f"[{timestamp_str}] {level_label} [{logger_name}] {loc} {func}"
            formatted = f"{header} - {message}"

        # Handle exception / stack trace if present
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
            if record.exc_text:
                if self.use_colors:
                    formatted += f"\n{self.BRIGHT_RED}{record.exc_text}{self.RESET}"
                else:
                    formatted += f"\n{record.exc_text}"

        if record.stack_info:
            formatted += f"\n{self.formatStack(record.stack_info)}"

        return formatted


class DetailedFileFormatter(logging.Formatter):
    """
    Structured, complete log formatter for persistent session log files.
    """
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s.%(msecs)03d | %(levelname)-7s | [%(process)d:%(threadName)s] | %(name)s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
