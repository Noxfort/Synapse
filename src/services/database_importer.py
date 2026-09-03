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
# File: src/services/database_importer.py
# Author: Gabriel Moraes
# Date: 2026-02-27

import os
import shutil
import pandas as pd
from pathlib import Path
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal

# Utils
from src.utils.parquet_validator import ParquetValidator

# Managers
from src.managers.storage_manager import StorageManager

from src.utils.logging_setup import get_logger

class DatabaseImporter(QObject):
    """
    ETL Engine responsible for ingesting Historical Parquet Data.
    
    Refactored V4 (Parquet Only):
    - Parquet is the sole supported format (.parquet).
    - Removes legacy SQLite (.db) conversion and manual timebase resampling.
    - Saves output directly to 'datalake/base/base_v1.parquet'.
    - Validates dataset integrity and minimum historical span (>= 7 days).
    """
    
    # Qt Signals (for PyQt GUI compatibility)
    log_message = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    import_finished = pyqtSignal(bool, str) # Success, Message

    def __init__(self, storage_manager: Optional[StorageManager] = None):
        super().__init__()
        self.storage = storage_manager if storage_manager else StorageManager()
        self.logger = get_logger("DatabaseImporter")
        
        # Direct Python Callbacks (for Headless IPC / non-Qt event loop execution)
        self.on_log: Optional[Callable[[str], None]] = None
        self.on_progress: Optional[Callable[[int], None]] = None
        self.on_finished: Optional[Callable[[bool, str], None]] = None

    def _emit_log(self, msg: str) -> None:
        self.logger.info(msg)
        try:
            self.log_message.emit(msg)
        except Exception:
            pass
        if self.on_log:
            try:
                self.on_log(msg)
            except Exception as e:
                self.logger.warning(f"Error in on_log callback: {e}")

    def _emit_progress(self, percent: int) -> None:
        self.logger.debug(f"[ETL Progress] {percent}%")
        try:
            self.progress_update.emit(percent)
        except Exception:
            pass
        if self.on_progress:
            try:
                self.on_progress(percent)
            except Exception as e:
                self.logger.warning(f"Error in on_progress callback: {e}")

    def _emit_finished(self, success: bool, msg: str) -> None:
        if success:
            self.logger.info(f"✅ [ETL Finished] {msg}")
        else:
            self.logger.error(f"❌ [ETL Failed] {msg}")
        try:
            self.import_finished.emit(success, msg)
        except Exception:
            pass
        if self.on_finished:
            try:
                self.on_finished(success, msg)
            except Exception as e:
                self.logger.warning(f"Error in on_finished callback: {e}")

    def execute_import(self, source_path_str: str):
        """
        Main entry point for importing historical parquet datasets.
        """
        abs_path = Path(os.path.abspath(source_path_str))
        self._emit_log(f"📦 [ETL] Iniciando importação da base histórica: {abs_path}")
        self._emit_progress(10)

        if not abs_path.exists():
            self._emit_finished(False, f"File not found: {abs_path}")
            return

        if abs_path.suffix.lower() != '.parquet':
            self._emit_finished(False, "Unsupported file format. Historical data must be in .parquet format.")
            return

        try:
            target_path = Path(self.storage.get_datalake_base_path()) / "base_v1.parquet"
            target_path.parent.mkdir(parents=True, exist_ok=True)

            self._emit_log("🔍 [ETL] Verificando legibilidade e integridade do dataset Parquet...")
            self._emit_progress(30)
            
            # 1. Verify readability (Sanity Check)
            pd.read_parquet(abs_path)
            
            # 2. Validate historical span (Minimum 7 days)
            self._emit_log("⏱️ [ETL] Validando amplitude temporal histórica (mínimo de 7 dias)...")
            self._emit_progress(50)
            try:
                is_valid = ParquetValidator.validate_minimum_timespan(str(abs_path))
                if not is_valid:
                    self._emit_finished(False, "Dataset rejected: Must contain at least 7 days of historical data.")
                    return
            except Exception as ve:
                self._emit_finished(False, f"Validation failed due to dataset structure: {ve}")
                return

            # 3. Direct Binary Copy (shutil)
            self._emit_log("💾 [ETL] Copiando dados históricos validados para o Base Data Lake...")
            self._emit_progress(80)
            shutil.copy2(abs_path, target_path)

            self._emit_log(f"🎉 [ETL] Sucesso! Base salva em: {target_path}")
            self._emit_progress(100)
            self._emit_finished(True, "Import Successful (Parquet Base Registered).")

        except Exception as e:
            self.logger.error(f"Erro crítico durante ETL: {e}", exc_info=True)
            self._emit_finished(False, f"Critical ETL Error: {str(e)}")
