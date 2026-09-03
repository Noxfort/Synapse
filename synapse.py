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
# File: synapse.py
# Author: Gabriel Moraes
# Date: 2026-08-29

import sys
import os

# 1. Initialize environment variables and PATH
root_dir = os.path.dirname(os.path.abspath(__file__))
os.environ["SYNAPSE_ROOT"] = root_dir
if root_dir not in os.environ.get("PYTHONPATH", ""):
    os.environ["PYTHONPATH"] = f"{root_dir}:{os.environ.get('PYTHONPATH', '')}"

cargo_bin = os.path.expanduser("~/.cargo/bin")
current_path = os.environ.get("PATH", "")
if os.path.isdir(cargo_bin) and cargo_bin not in current_path:
    os.environ["PATH"] = f"{cargo_bin}:{current_path}"

# 2. Auto-reexec with the project virtual environment (.venv) if invoked via global Python
if sys.prefix == sys.base_prefix:
    venv_python = os.path.join(root_dir, ".venv", "bin", "python")
    if os.name == "nt":
        venv_python = os.path.join(root_dir, ".venv", "Scripts", "python.exe")
    if os.path.isfile(venv_python):
        os.execv(venv_python, [venv_python] + sys.argv)

import subprocess
import shutil
import signal
import platform

from src.utils.logging_setup import get_logger
from src.utils.hardware import configure_hardware_acceleration
from src.utils.process_utils import hard_kill
from src.ipc.stdio_daemon import main as start_daemon

# Register immediate exit handlers on Ctrl+C and SIGTERM
signal.signal(signal.SIGINT, hard_kill)
signal.signal(signal.SIGTERM, hard_kill)

# Hardware acceleration setup (TF32 / PyTorch)
configure_hardware_acceleration()

logger = get_logger("Launcher")


def launch_desktop_ui():
    """
    Launches the modern desktop frontend (Tauri v2 + React).
    The Tauri runtime automatically spawns the Python StdioDaemon as its backend sidecar.
    """
    ui_dir = os.path.join(root_dir, "ui")
    release_bin = os.path.join(ui_dir, "src-tauri", "target", "release", "synapse-desktop")

    # 1. If release binary exists, execute it directly
    if os.path.isfile(release_bin) and os.access(release_bin, os.X_OK):
        logger.info(f"🚀 Launching compiled SYNAPSE Desktop binary: {release_bin}")
        subprocess.run([release_bin])
        return

    # 2. Check if Cargo/Rust and npm are installed
    cargo_path = shutil.which("cargo")
    npm_path = shutil.which("npm")

    if not cargo_path:
        logger.warning(
            "⚠️  Rust/Cargo não foi detectado no sistema!\n"
            "   Para abrir a janela Desktop nativa, instale o Rust:\n"
            "     curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y\n"
            "     source \"$HOME/.cargo/env\"\n"
            "\n"
            "   Ou execute no terminal:\n"
            "     npm run tauri dev (dentro da pasta ui/)\n"
        )
        logger.info("Iniciando SYNAPSE Core em modo Daemon Headless...")
        try:
            start_daemon()
        except KeyboardInterrupt:
            logger.info("Termination signal received. Exiting.")
            sys.exit(0)
        return

    # 3. Prepare clean environment (sanitize LD_LIBRARY_PATH and Snap overrides)
    clean_env = os.environ.copy()
    clean_env["SYNAPSE_ROOT"] = root_dir
    clean_env["PYTHONPATH"] = root_dir
    clean_env["PYTHONUNBUFFERED"] = "1"
    clean_env["LD_LIBRARY_PATH"] = "/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu"
    clean_env.pop("LD_PRELOAD", None)
    for key in list(clean_env.keys()):
        if key.startswith("SNAP") or "SNAP" in key:
            del clean_env[key]

    if os.path.isdir(cargo_bin) and cargo_bin not in clean_env.get("PATH", ""):
        clean_env["PATH"] = f"{cargo_bin}:{clean_env.get('PATH', '')}"

    # 4. Launch via npm run tauri dev
    if npm_path and os.path.isdir(ui_dir):
        logger.info(f"⚡ Booting SYNAPSE Desktop in Development Mode (Tauri v2 + React) from {ui_dir}...")
        try:
            subprocess.run(["npm", "run", "tauri", "dev"], cwd=ui_dir, env=clean_env, check=True)
            return
        except KeyboardInterrupt:
            logger.info("Termination signal received. Exiting gracefully.")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Erro ao iniciar Tauri via npm: {e}")
            sys.exit(1)

    # 5. Fallback to direct daemon execution if frontend runner is unavailable
    logger.info("Starting SYNAPSE Core Headless Daemon...")
    start_daemon()


def start_supervisor():
    """
    Process 2 Entry Point: Runs F.E.N.I.X. as an external Process Supervisor / Watchdog.
    Monitors, protects, and auto-resurrects the Neural Core Process.
    """
    import time
    from src.fenix.process_supervisor import FenixProcessSupervisor, SupervisorConfig

    logger.info("🛡️  Booting F.E.N.I.X. Out-of-Process Supervisor...")
    config = SupervisorConfig(core_args=["--daemon"])
    supervisor = FenixProcessSupervisor(config=config)
    
    if not supervisor.start():
        logger.critical("Failed to start F.E.N.I.X. Supervisor.")
        sys.exit(1)

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        logger.info("Termination signal received. Stopping supervisor...")
        supervisor.stop()
        sys.exit(0)


def main():
    """
    Main entry point for SYNAPSE Core.
    Checks CLI arguments to decide between Desktop GUI mode, Supervisor mode, and Headless Daemon mode.
    """
    logger.info(f"⚡ SYNAPSE Core v2.0 on {platform.system()} {platform.release()} (Python {platform.python_version()}) [PID: {os.getpid()}]")

    args = sys.argv[1:]
    if "--supervisor" in args:
        start_supervisor()
    elif "--daemon" in args or "--engine-core" in args or "--headless" in args or os.environ.get("SYNAPSE_HEADLESS") == "1":
        logger.info("Executing in Headless IPC Daemon mode (Neural Core)...")
        start_daemon()
    else:
        launch_desktop_ui()


if __name__ == "__main__":
    main()

