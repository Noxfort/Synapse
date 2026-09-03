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
# File: src/infrastructure/dialog_service.py
# Author: Gabriel Moraes
# Date: 2026-08-30

"""
Native Operating System Dialog Service (SOLID: SRP & DIP).

Isolates OS-specific GUI dialogs (Zenity subprocess and Tkinter fallback)
away from the IPC transport and core domain logic.
"""

import os
import sys
import subprocess
from urllib.parse import unquote, urlparse
from typing import Optional

from src.logging.facade import get_logger


class NativeDialogService:
    """Provides platform-native file and folder selection dialogs."""

    def __init__(self):
        self.logger = get_logger("NativeDialogService")

    def pick_file(
        self, title: str = "Selecionar Arquivo", file_filter: str = "*"
    ) -> Optional[str]:
        """
        Opens a native OS file dialog using zenity (on Linux) or Tkinter fallback.
        """
        self.logger.info(f"📂 [NativeDialogService] Abrindo seletor de arquivos. Título: '{title}' | Filtro: '{file_filter}'")

        if sys.platform.startswith("linux"):
            try:
                cmd = ["zenity", "--file-selection", f"--title={title}"]
                if file_filter and file_filter != "*":
                    cmd.append(f"--file-filter={file_filter}")

                self.logger.debug(f"[NativeDialogService] Executando Zenity: {' '.join(cmd)}")
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if res.returncode == 0:
                    path = res.stdout.strip()
                    if path:
                        if path.startswith("file://"):
                            path = unquote(urlparse(path).path)
                        path = unquote(path)
                        if os.path.exists(path):
                            self.logger.info(f"✅ [NativeDialogService] Arquivo selecionado via Zenity: '{path}'")
                            return path
                        else:
                            self.logger.warning(f"⚠️ [NativeDialogService] Arquivo retornado não existe: '{path}'")
                elif res.returncode == 1:
                    # User cancelled
                    self.logger.info("ℹ️ [NativeDialogService] Seleção cancelada pelo usuário no Zenity.")
                    return None
                else:
                    self.logger.warning(f"⚠️ [NativeDialogService] Zenity retornou código {res.returncode}: {res.stderr}")
            except Exception as ex:
                self.logger.warning(f"⚠️ [NativeDialogService] Erro no Zenity: {ex}. Tentando fallback Tkinter...")

        # Fallback to Tkinter file picker dialog
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)

            # Build Tkinter filetypes list if filter provided
            filetypes = []
            if file_filter and "|" in file_filter:
                parts = file_filter.split("|")
                desc = parts[0].strip()
                patterns = parts[1].strip()
                filetypes.append((desc, patterns))
            elif file_filter and file_filter != "*":
                filetypes.append(("Arquivos Filtrados", file_filter))
            else:
                filetypes.append(("Todos os Arquivos", "*.*"))

            self.logger.debug(f"[NativeDialogService] Abrindo Tkinter filedialog com filetypes: {filetypes}")
            selected = filedialog.askopenfilename(title=title, filetypes=filetypes)
            root.destroy()
            if selected:
                if selected.startswith("file://"):
                    selected = unquote(urlparse(selected).path)
                selected = unquote(selected)
                if os.path.exists(selected):
                    self.logger.info(f"✅ [NativeDialogService] Arquivo selecionado via Tkinter: '{selected}'")
                    return selected
                else:
                    self.logger.warning(f"⚠️ [NativeDialogService] Arquivo retornado não existe: '{selected}'")
            else:
                self.logger.info("ℹ️ [NativeDialogService] Seleção cancelada no Tkinter.")
        except Exception as ex:
            self.logger.error(f"❌ [NativeDialogService] Erro no seletor Tkinter: {ex}", exc_info=True)

        return None
