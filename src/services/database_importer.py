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

class DatabaseImporter(QObject):
    """
    ETL Engine responsible for ingesting Historical Parquet Data.
    
    Refactored V4 (Parquet Only):
    - Parquet is the sole supported format (.parquet).
    - Removes legacy SQLite (.db) conversion and manual timebase resampling.
    - Saves output directly to 'datalake/base/base_v1.parquet'.
    - Validates dataset integrity and minimum historical span (>= 7 days).
    """
    
    # Signals
    log_message = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    import_finished = pyqtSignal(bool, str) # Success, Message

    def __init__(self, storage_manager: Optional[StorageManager] = None):
        super().__init__()
        if storage_manager:
            self.storage = storage_manager
        else:
            self.storage = StorageManager()

    def execute_import(self, source_path_str: str):
        """
        Main entry point for importing historical parquet datasets.
        """
        abs_path = Path(os.path.abspath(source_path_str))
        self.log_message.emit(f"[ETL] Starting Historical Data Import from: {abs_path}")
        self.progress_update.emit(10)

        if not abs_path.exists():
            self.import_finished.emit(False, f"File not found: {abs_path}")
            return

        if abs_path.suffix.lower() != '.parquet':
            self.import_finished.emit(False, "Unsupported file format. Historical data must be in .parquet format.")
            return

        try:
            target_path = Path(self.storage.get_datalake_base_path()) / "base_v1.parquet"
            target_path.parent.mkdir(parents=True, exist_ok=True)

            self.log_message.emit("[ETL] Parquet detected. Verifying dataset readability...")
            self.progress_update.emit(30)
            
            # 1. Verify readability (Sanity Check)
            pd.read_parquet(abs_path)
            
            # 2. Validate historical span (Minimum 7 days)
            self.log_message.emit("[ETL] Validating historical span (minimum 7 days requirement)...")
            self.progress_update.emit(50)
            try:
                is_valid = ParquetValidator.validate_minimum_timespan(str(abs_path))
                if not is_valid:
                    self.import_finished.emit(False, "Dataset rejected: Must contain at least 7 days of historical data.")
                    return
            except Exception as ve:
                self.import_finished.emit(False, f"Validation failed due to dataset structure: {ve}")
                return

            # 3. Direct Binary Copy (shutil)
            self.log_message.emit("[ETL] Copying verified historical data to Base Data Lake...")
            self.progress_update.emit(80)
            shutil.copy2(abs_path, target_path)

            self.log_message.emit(f"[ETL] Success. File saved to: {target_path}")
            self.progress_update.emit(100)
            self.import_finished.emit(True, "Import Successful (Parquet Base Registered).")

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.import_finished.emit(False, f"Critical ETL Error: {str(e)}")