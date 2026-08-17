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
# File: ui/wizards/import_wizard.py
# Author: Gabriel Moraes
# Date: 2026-02-27

import os
import pandas as pd
import pyarrow.parquet as pq
from PyQt6.QtCore import Qt, pyqtSlot, QThread
from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFileDialog, QFormLayout, QListWidget,
    QProgressBar, QTextEdit, QMessageBox
)
from ui.styles.theme_manager import ThemeManager

from src.services.database_importer import DatabaseImporter
from src.utils.parquet_validator import ParquetValidator

class ImportWizard(QWizard):
    """
    Wizard dialog to guide the user through the Historical Parquet Data ingestion.
    Strictly accepts .parquet files without requiring manual target interval settings.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Import Historical Data"))
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.resize(620, 480)
        
        # Shared State
        self.source_path = ""
        
        # Pages
        self.page_intro = IntroPage(self)
        self.page_config = ConfigPage(self)
        self.page_process = ProcessingPage(self)
        
        self.addPage(self.page_intro)
        self.addPage(self.page_config)
        self.addPage(self.page_process)

class IntroPage(QWizardPage):
    def __init__(self, wizard):
        super().__init__(wizard)
        self.setTitle(self.tr("Select Source Data"))
        self.setSubTitle(self.tr("Choose the historical data file (.parquet) containing traffic records."))
        
        layout = QVBoxLayout(self)
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText(self.tr("Path to .parquet file..."))
        self.path_edit.setReadOnly(True)
        
        btn_browse = QPushButton(self.tr("Browse..."))
        btn_browse.clicked.connect(self._browse)
        
        form = QFormLayout()
        form.addRow(self.tr("Source File:"), self.path_edit)
        form.addRow("", btn_browse)
        
        layout.addLayout(form)
        
        # Validation
        self.registerField("source_path*", self.path_edit) # * means mandatory

    def _browse(self):
        f, _ = QFileDialog.getOpenFileName(
            self, 
            self.tr("Open Historical Data (.parquet)"), 
            "", 
            "Parquet Files (*.parquet)"
        )
        if f:
            self.path_edit.setText(f)
            self.wizard().source_path = f

class ConfigPage(QWizardPage):
    def __init__(self, wizard):
        super().__init__(wizard)
        self.setTitle(self.tr("Dataset Inspection"))
        self.setSubTitle(self.tr("Review dataset structure and historical data summary."))
        
        layout = QVBoxLayout(self)
        
        # Inspection List
        layout.addWidget(QLabel(self.tr("Dataset Information:")))
        self.list_tables = QListWidget()
        layout.addWidget(self.list_tables)

    def initializePage(self):
        """Called when user enters this page. Scans and inspects the parquet file."""
        path = self.wizard().source_path
        self.list_tables.clear()
        
        if not path or not os.path.exists(path):
            self.list_tables.addItem(self.tr("❌ File not found."))
            return

        if not path.lower().endswith('.parquet'):
            self.list_tables.addItem(self.tr("⚠️ Unsupported file format. Please select a .parquet file."))
            return

        self._inspect_parquet(path)

    def _inspect_parquet(self, path: str):
        """Reads Parquet schema and metadata to present complete dataset info."""
        try:
            file_size_mb = os.path.getsize(path) / (1024 * 1024)
            self.list_tables.addItem(f"📁 [File] {os.path.basename(path)} ({file_size_mb:.2f} MB)")
            
            # Read schema and metadata without loading full data in memory
            parquet_file = pq.ParquetFile(path)
            schema = parquet_file.schema
            num_rows = parquet_file.metadata.num_rows
            col_names = schema.names
            
            self.list_tables.addItem(f"📊 [Total Rows] {num_rows:,}")
            self.list_tables.addItem(f"📋 [Columns ({len(col_names)})] {', '.join(col_names)}")
            
            # Detect time column & timespan
            time_col = None
            try:
                time_col = ParquetValidator._detect_time_column(path)
            except Exception:
                pass
                
            if time_col:
                df_time = pd.read_parquet(path, columns=[time_col])
                df_time[time_col] = pd.to_datetime(df_time[time_col], errors='coerce', utc=True)
                df_time = df_time.dropna(subset=[time_col])
                
                if not df_time.empty:
                    min_time = df_time[time_col].min()
                    max_time = df_time[time_col].max()
                    unique_days = df_time[time_col].dt.date.nunique()
                    
                    self.list_tables.addItem(f"⏱️ [Time Column] '{time_col}'")
                    self.list_tables.addItem(f"📅 [Timespan] {min_time.strftime('%Y-%m-%d %H:%M')} to {max_time.strftime('%Y-%m-%d %H:%M')}")
                    self.list_tables.addItem(f"🗓️ [Unique Calendar Days] {unique_days} day(s)")
                    
                    if unique_days >= ParquetValidator.REQUIRED_DAYS:
                        self.list_tables.addItem(f"✅ Historical span requirement met (≥ {ParquetValidator.REQUIRED_DAYS} days).")
                    else:
                        self.list_tables.addItem(f"⚠️ Warning: Dataset has {unique_days} days. Minimum required is {ParquetValidator.REQUIRED_DAYS} days.")
            
            # Detect sensor / source grouping columns
            sensor_cols = [c for c in ['sensor_id', 'source_table', 'edge_id', 'detector_id'] if c in col_names]
            if sensor_cols:
                target_sensor_col = sensor_cols[0]
                df_sensors = pd.read_parquet(path, columns=[target_sensor_col])
                unique_sensors = df_sensors[target_sensor_col].dropna().unique()
                self.list_tables.addItem(f"📡 [Identified Sources/Sensors] {len(unique_sensors)} found ({target_sensor_col})")
                
                sample_sensors = list(unique_sensors[:5])
                sensors_str = ', '.join(str(s) for s in sample_sensors)
                if len(unique_sensors) > 5:
                    sensors_str += f", ... (+{len(unique_sensors) - 5} more)"
                self.list_tables.addItem(f"   ↳ {sensors_str}")

        except Exception as e:
            self.list_tables.addItem(f"❌ Failed to inspect Parquet: {e}")

class ProcessingPage(QWizardPage):
    def __init__(self, wizard):
        super().__init__(wizard)
        self.setTitle(self.tr("Processing Import"))
        self.setSubTitle(self.tr("Importing historical data into Base Database (Parquet)..."))
        
        layout = QVBoxLayout(self)
        
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet(ThemeManager.get_style("console_log"))
        layout.addWidget(self.log_box)
        
        # Worker
        self.importer = DatabaseImporter()
        self.thread = QThread()
        self.importer.moveToThread(self.thread)
        
        # Wiring
        self.importer.log_message.connect(self._log)
        self.importer.progress_update.connect(self.progress.setValue)
        self.importer.import_finished.connect(self._on_finished)
        
        # Signal to start
        self.thread.started.connect(self._start_task)

    def initializePage(self):
        # Disable Back button to prevent state corruption during process
        self.wizard().button(QWizard.WizardButton.BackButton).setEnabled(False)
        self.thread.start()

    def _start_task(self):
        path = self.wizard().source_path
        self.importer.execute_import(path)

    @pyqtSlot(str)
    def _log(self, msg):
        self.log_box.append(msg)

    @pyqtSlot(bool, str)
    def _on_finished(self, success, msg):
        self.thread.quit()
        self.thread.wait()
        
        if success:
            self._log(f"\n✅ {msg}")
            self.wizard().button(QWizard.WizardButton.FinishButton).setEnabled(True)
            self.completeChanged.emit() # Notify wizard we are done
        else:
            self._log(f"\n❌ {msg}")
            QMessageBox.critical(self, self.tr("Import Failed"), msg)

    def isComplete(self):
        return not self.thread.isRunning()