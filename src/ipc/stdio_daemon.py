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
# File: src/ipc/stdio_daemon.py
# Author: Gabriel Moraes
# Date: 2026-08-30

"""
Pure Headless IPC Facade & Orchestrator (SOLID Architecture).

Adheres strictly to SOLID:
- [SRP] Pure facade coordinating IPC transport, command routing, and event bridging.
- [DIP] Injected with abstract protocols/services (Transport, Router, EventBridge, Controller).
- [OCP] Extensible command routing without modifying daemon core logic.
- [ISP] Communicates via well-defined, segregated service interfaces.
"""

import sys
import signal
from typing import Any, Callable, Optional

from PyQt6.QtCore import QCoreApplication, QTimer

from src.factories.controller_factory import ControllerFactory
from src.ipc.ipc_protocol import IpcMessage, IpcEvent, IpcResponse
from src.ipc.stdio_transport import StdioTransport
from src.ipc.command_router import IpcCommandRouter
from src.ipc.event_bridge import IpcEventBridge
from src.handlers.handler_registry import register_default_command_handlers
from src.utils.logging_setup import get_logger
from src.utils.hardware import configure_hardware_acceleration


class StdioDaemon:
    """
    Headless IPC Server communicating via STDIN/STDOUT JSON streams.
    Runs inside the Tauri application as a native sidecar with Zero Network Ports.
    """

    def __init__(
        self,
        controller: Optional[Any] = None,
        transport: Optional[StdioTransport] = None,
        router: Optional[IpcCommandRouter] = None,
        event_bridge: Optional[IpcEventBridge] = None,
        on_shutdown: Optional[Callable[[], None]] = None,
    ):
        self.logger = get_logger("StdioDaemon")

        # 1. Resolve Dependencies (DIP)
        self.controller = (
            controller
            if controller is not None
            else ControllerFactory.create_main_controller()
        )
        self.app_state = getattr(self.controller, "app_state", None)

        self.transport = transport if transport is not None else StdioTransport()
        self.router = router if router is not None else IpcCommandRouter()
        self.on_shutdown_cb = on_shutdown or self._default_shutdown

        # 2. Event Bridge (Qt Signals -> IPC Events)
        self.event_bridge = (
            event_bridge
            if event_bridge is not None
            else IpcEventBridge(self.emit_event)
        )
        if self.app_state:
            self.event_bridge.bind_signals(self.controller, self.app_state)

        # 3. Register Default Handlers if router is empty
        if not self.router._handlers:
            register_default_command_handlers(
                router=self.router,
                controller=self.controller,
                app_state=self.app_state,
                event_emitter=self.emit_event,
                on_shutdown=self.shutdown,
            )

    def _default_shutdown(self) -> None:
        """Default shutdown callback closing Qt event loop."""
        self.stop()
        QCoreApplication.quit()

    def emit_event(self, event_name: str, data: Any = None) -> bool:
        """Emits an asynchronous event to Tauri STDOUT."""
        event = IpcEvent(event=event_name, data=data)
        return self.transport.write_line(event.to_json())

    def emit_response(
        self,
        msg_id: Optional[str],
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
    ) -> bool:
        """Emits a response envelope matching a command."""
        resp = IpcResponse(id=msg_id, success=success, result=result, error=error)
        return self.transport.write_line(resp.to_json())

    def emit_response_object(self, resp: IpcResponse) -> bool:
        """Emits an IpcResponse instance to STDOUT."""
        return self.transport.write_line(resp.to_json())

    def dispatch_command(self, msg: IpcMessage) -> None:
        """Processes incoming actions by delegating to the command router."""
        self.router.dispatch(msg, self.emit_response_object)

    def _on_line_received(self, line: str) -> None:
        """Callback invoked when a clean line is received from STDIN."""
        msg = IpcMessage.from_json(line)
        if msg:
            self.dispatch_command(msg)
        else:
            self.logger.warning(f"Malformed or unparsable IPC message line: {line}")

    def _on_disconnect(self) -> None:
        """Callback invoked when the STDIN pipe closes (Parent window closed)."""
        self.logger.warning("🔴 [IPC STATUS] DESCONECTADO: Canal STDIN fechado. Finalizando processo Python.")
        self.shutdown()

    def start(self) -> None:
        """Starts the transport background listener."""
        self.logger.info("⚡ [IPC STATUS] Core Python ONLINE. Aguardando conexão do frontend Desktop...")
        self.transport.start_reader_loop(
            on_line_received=self._on_line_received,
            on_disconnect=self._on_disconnect,
        )

    def stop(self) -> None:
        """Stops the transport loop."""
        self.transport.stop()

    def shutdown(self) -> None:
        """Coordinates graceful shutdown across all subsystems."""
        if hasattr(self.controller, "shutdown"):
            self.controller.shutdown()
        if self.on_shutdown_cb:
            self.on_shutdown_cb()


def main():
    from src.utils.process_utils import hard_kill
    from src.logging.facade import setup_logging
    from src.logging.config import LogConfig

    # Initialize logging subsystem targeting stderr for live terminal output without mutating stdout IPC
    config = LogConfig.from_env(redirect_streams=False)
    setup_logging(config)

    configure_hardware_acceleration()
    signal.signal(signal.SIGINT, hard_kill)
    signal.signal(signal.SIGTERM, hard_kill)

    app = QCoreApplication(sys.argv)
    daemon = StdioDaemon()

    # Launch background STDIN listener thread
    daemon.start()

    # Emit initial ready signal to Tauri
    daemon.emit_event("ready", {"status": "online", "platform": sys.platform})

    # Allow OS signals (Ctrl+C) by yielding to Python interpreter
    sig_timer = QTimer()
    sig_timer.start(250)
    sig_timer.timeout.connect(lambda: None)

    try:
        exit_code = app.exec()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        daemon.logger.info("KeyboardInterrupt received. Exiting.")
        sys.exit(0)


if __name__ == "__main__":
    main()
