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
# File: src/logging/interceptors.py
# Author: Gabriel Moraes
# Date: 2026-08-28

"""
Runtime interceptors for system stdout/stderr streams and uncaught exceptions.
Isolates low-level runtime monkey patching from logging business logic.
"""

import sys
import os
import inspect
import logging
from typing import Optional


class StreamToLogger:
    """
    Custom stream object that redirects standard system outputs (stdout/stderr)
    to the logger safely, avoiding recursion crashes with a thread-safe guard.
    """
    def __init__(self, logger_instance: logging.Logger, log_level: int, stream_name: str = "stdout"):
        self.logger = logger_instance
        self.log_level = log_level
        self.stream_name = stream_name
        self._is_logging = False

    def flush(self):
        """Pass-through flush for TextIO compatibility."""
        pass

    def reconfigure(self, *args, **kwargs):
        """Pass-through reconfigure for TextIOWrapper compatibility."""
        pass

    def write(self, buf: str):
        """Intercepts raw text and routes it to the logger safely."""
        if self._is_logging:
            return
            
        self._is_logging = True
        try:
            for line in buf.rstrip().splitlines():
                clean_line = line.strip()
                if clean_line:
                    # Find actual caller frame outside logging infrastructure
                    frame = inspect.currentframe()
                    caller_file = "stdout"
                    caller_line = 0
                    caller_func = "print"
                    try:
                        while frame:
                            f_code = frame.f_code
                            filename = f_code.co_filename
                            if ("logging" not in filename and 
                                "interceptors.py" not in filename and 
                                "logging_setup.py" not in filename):
                                caller_file = os.path.basename(filename)
                                caller_line = frame.f_lineno
                                caller_func = f_code.co_name
                                break
                            frame = frame.f_back
                    finally:
                        del frame

                    # Construct custom LogRecord to preserve real caller location
                    record = self.logger.makeRecord(
                        name=f"Synapse.{self.stream_name.upper()}",
                        level=self.log_level,
                        fn=caller_file,
                        lno=caller_line,
                        msg=clean_line,
                        args=(),
                        exc_info=None,
                        func=caller_func
                    )
                    self.logger.handle(record)
        finally:
            self._is_logging = False

    def flush(self):
        """Pass-through for compatibility."""
        pass

    def isatty(self) -> bool:
        """Indicates whether stream is interactive."""
        return False


def install_excepthook(target_logger: logging.Logger):
    """Installs global exception hooks for both main and worker threads to capture unhandled errors with full traceback."""
    def _uncaught_exception_handler(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Allow graceful termination without noisy tracebacks
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        target_logger.critical(
            "💥 UNCAUGHT EXCEPTION OCCURRED IN MAIN THREAD:",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
    sys.excepthook = _uncaught_exception_handler

    # Also capture unhandled exceptions in background threads
    import threading
    if hasattr(threading, "excepthook"):
        def _threading_excepthook(args):
            if issubclass(args.exc_type, KeyboardInterrupt):
                return
            target_logger.critical(
                f"💥 UNCAUGHT EXCEPTION IN THREAD '{args.thread.name}':",
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback)
            )
        threading.excepthook = _threading_excepthook


def redirect_system_streams(target_logger: logging.Logger):
    """Safely redirects standard stdout and stderr to the target logger."""
    sys.stdout = StreamToLogger(target_logger, logging.INFO, stream_name="stdout")
    sys.stderr = StreamToLogger(target_logger, logging.ERROR, stream_name="stderr")
