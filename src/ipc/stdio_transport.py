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
# File: src/ipc/stdio_transport.py
# Author: Gabriel Moraes
# Date: 2026-08-30

"""
Low-Level Standard I/O Transport Layer (SOLID: SRP).

Handles thread-safe writing to STDOUT and continuous asynchronous reading from STDIN.
Completely decoupled from domain controllers, business rules, and message formats.
"""

import sys
import threading
from typing import Callable, Optional, TextIO

from src.utils.logging_setup import get_logger


class StdioTransport:
    """
    Manages raw OS STDIN/STDOUT stream I/O with line-buffering and thread-safety.
    """

    def __init__(
        self,
        stdin_stream: Optional[TextIO] = None,
        stdout_stream: Optional[TextIO] = None,
    ):
        self._raw_stdin = (
            stdin_stream
            if stdin_stream is not None
            else (sys.__stdin__ if sys.__stdin__ is not None else sys.stdin)
        )
        self._raw_stdout = (
            stdout_stream
            if stdout_stream is not None
            else (sys.__stdout__ if sys.__stdout__ is not None else sys.stdout)
        )

        self._reconfigure_streams()

        self.logger = get_logger("StdioTransport")
        self._running = False
        self._write_lock = threading.Lock()
        self._reader_thread: Optional[threading.Thread] = None

    def _reconfigure_streams(self) -> None:
        """Configures line buffering and UTF-8 encoding on OS streams if supported."""
        if hasattr(self._raw_stdout, "reconfigure"):
            try:
                self._raw_stdout.reconfigure(line_buffering=True, encoding="utf-8")
            except Exception:
                pass
        if hasattr(self._raw_stdin, "reconfigure"):
            try:
                self._raw_stdin.reconfigure(encoding="utf-8")
            except Exception:
                pass

    @property
    def is_running(self) -> bool:
        return self._running

    def write_line(self, text: str) -> bool:
        """
        Thread-safe write of a single line to STDOUT followed by an immediate flush.
        Returns True if successful, False if the pipe disconnected.
        """
        with self._write_lock:
            try:
                stream = self._raw_stdout or sys.stdout
                stream.write(text + "\n")
                stream.flush()
                return True
            except (BrokenPipeError, OSError, ValueError) as ex:
                self.logger.debug(f"IPC stdout pipe closed: {ex}")
                self._running = False
                return False

    def start_reader_loop(
        self,
        on_line_received: Callable[[str], None],
        on_disconnect: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Launches the background listener thread for incoming lines on STDIN.
        """
        if self._running:
            return

        self._running = True

        def _loop():
            while self._running:
                try:
                    line = self._raw_stdin.readline()
                    if not line:
                        # EOF / Pipe closed
                        self.logger.info("STDIN closed (EOF). Terminating transport listener.")
                        self._running = False
                        if on_disconnect:
                            on_disconnect()
                        break

                    cleaned_line = line.strip()
                    if not cleaned_line:
                        continue

                    on_line_received(cleaned_line)

                except Exception as ex:
                    if self._running:
                        self.logger.error(f"STDIN read error: {ex}", exc_info=True)

        self._reader_thread = threading.Thread(target=_loop, daemon=True)
        self._reader_thread.start()

    def stop(self) -> None:
        """Stops the transport loop."""
        self._running = False
