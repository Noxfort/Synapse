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
# File: src/managers/storage_manager.py
# Author: Gabriel Moraes
# Date: 2026-02-16

import os
import logging
from pathlib import Path
from typing import Optional, Any, Dict
from PyQt6.QtCore import pyqtSignal

class StorageManager:
    """
    Manages external configuration files (JSON).
    Handles OS-level folder scaffolding (SRP).
    """
    # Refactored V4 (Strict Folder Structure):
    # - REMOVED 'data' folder creation.
    # - REMOVED SQLite database logic (synapse_metadata.sqlite).
    # - ONLY creates:
    #     1. ~/Documentos/Synapse/Checkpoint
    #     2. ~/Documentos/Synapse/datalake/base
    #     3. ~/Documentos/Synapse/datalake/golden
    """
    Central Persistence Manager for SYNAPSE.
    
    Refactored V4 (Strict Folder Structure):
    - REMOVED 'data' folder creation.
    - REMOVED SQLite database logic (synapse_metadata.sqlite).
    - ONLY creates:
        1. ~/Documentos/Synapse/Checkpoint
        2. ~/Documentos/Synapse/datalake/base
        3. ~/Documentos/Synapse/datalake/golden
    """

    def __init__(self):
        """
        Initializes the storage manager with strict directory rules.
        """
        # 1. Resolve User Home Directory
        self.home = Path.home()
        
        # 2. Locate 'Documents' folder (Handles PT-BR 'Documentos' vs EN 'Documents')
        self.documents_dir = self.home / "Documentos"
        if not self.documents_dir.exists():
            self.documents_dir = self.home / "Documents"
            
        # 3. Define Project Root
        self.project_root = self.documents_dir / "Synapse"
        
        # 4. Define ONLY The Allowed Folders
        self.checkpoint_dir = self.project_root / "Checkpoint"
        self.datalake_dir = self.project_root / "datalake"
        self.base_dir = self.datalake_dir / "base"
        self.golden_dir = self.datalake_dir / "golden"
        
        # Internal State
        self.is_connected = True # Mocked as true since we removed DB
        
        # Ensure directories exist immediately upon instantiation
        self._ensure_structure()
        
        logging.info(f"[StorageManager] Storage initialized at: {self.project_root}")

    def _ensure_structure(self):
        """Creates ONLY the necessary folder structure."""
        paths = [
            self.project_root,
            self.checkpoint_dir,    # Pasta 1
            self.datalake_dir,      # Pasta 2 (Pai)
            self.base_dir,          # Pasta 2.1 (Base)
            self.golden_dir         # Pasta 2.2 (Golden)
        ]
        
        for path in paths:
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    logging.critical(f"[StorageManager] Failed to create directory {path}: {e}")

    # =========================================================================
    #  PATH ACCESSORS (Getters)
    # =========================================================================

    def get_datalake_base_path(self) -> str:
        """Returns path to where raw .parquet files should be saved."""
        return str(self.base_dir)

    def get_datalake_golden_path(self) -> str:
        """Returns path to where processed files are saved."""
        return str(self.golden_dir)
    
    def get_checkpoint_path(self) -> str:
        """Returns path for best_hparams.pth."""
        return str(self.checkpoint_dir)

    def get_checkpoints_path(self) -> str:
        """Backwards-compatible alias for get_checkpoint_path."""
        return self.get_checkpoint_path()

    def save_node_checkpoint(self, source_id: str, state: Dict[str, Any]) -> bool:
        """Persists a single node's state checkpoint (PyTorch dictionary) to disk."""
        try:
            import torch
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
            file_path = self.checkpoint_dir / f"state_{source_id}.pth"
            torch.save(state, str(file_path))
            return True
        except Exception as e:
            logging.error(f"[StorageManager] Failed to save node checkpoint for '{source_id}': {e}")
            return False

    def load_node_checkpoint(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Loads and returns a node state checkpoint if it exists and is valid."""
        try:
            import torch
            file_path = self.checkpoint_dir / f"state_{source_id}.pth"
            if file_path.exists():
                return torch.load(str(file_path), map_location="cpu", weights_only=False)
            return None
        except Exception as e:
            logging.error(f"[StorageManager] Failed to load checkpoint for '{source_id}': {e}")
            return None

    def get_config_path(self) -> str:
        """Returns path for configuration artifacts (ontology, schedule, auditor)."""
        config_path = self.project_root / "data" / "config"
        return str(config_path)

    def has_phase0_artifacts(self) -> bool:
        """Verifies if Phase 0 (AutoML) hyperparameter checkpoint exists and is valid (> 0 bytes)."""
        try:
            checkpoint_file = Path(self.get_checkpoint_path()) / "best_hparams.pth"
            return checkpoint_file.exists() and checkpoint_file.stat().st_size > 0
        except Exception as e:
            logging.warning(f"[StorageManager] Error checking Phase 0 artifacts: {e}")
            return False

    def has_phase1_artifacts(self) -> bool:
        """Verifies if Phase 1 (Offline Bootstrap) DataLake, Ontology, Schedule, and Auditor exist."""
        try:
            base_dir = Path(self.get_datalake_base_path())
            golden_dir = Path(self.get_datalake_golden_path())
            config_dir = Path(self.get_config_path())

            if not base_dir.exists() or not golden_dir.exists() or not config_dir.exists():
                return False

            base_parquets = list(base_dir.glob("*.parquet"))
            golden_parquets = list(golden_dir.glob("*.parquet"))

            safetensors = config_dir / "ontology.safetensors"
            peak_schedule = config_dir / "peak_schedule.json"
            auditor_checkpoint = config_dir / "auditor_calibrated.pth"

            return (
                len(base_parquets) > 0
                and len(golden_parquets) > 0
                and safetensors.exists() and safetensors.stat().st_size > 0
                and peak_schedule.exists() and peak_schedule.stat().st_size > 0
                and auditor_checkpoint.exists() and auditor_checkpoint.stat().st_size > 0
            )
        except Exception as e:
            logging.warning(f"[StorageManager] Error checking Phase 1 artifacts: {e}")
            return False
    # =========================================================================
    #  CONNECTION LIFECYCLE (Simplified)
    # =========================================================================

    def _ensure_directories(self):
        """
        Creates the mandatory folder structure requested.
        Crucial for preventing errors when files are deleted.
        Moved from SystemController to adhere to SRP.
        """
        try:
            home = Path.home()
            docs = home / "Documentos"
            if not docs.exists():
                docs = home / "Documents"
            
            synapse_root = docs / "Synapse"
            
            paths_to_check = [
                synapse_root / "Checkpoint",          # For best_hparams.pth
                synapse_root / "datalake" / "base",   # For raw .parquet copy
                synapse_root / "datalake" / "golden", # For processed .parquet
                synapse_root / "data" / "db",         # For metadata
                synapse_root / "data" / "config"      # For JSON configs
            ]
            
            for p in paths_to_check:
                os.makedirs(p, exist_ok=True)
                
        except Exception as e:
            print(f"[StorageManager] ⚠️ Directory creation failed: {e}")

    def connect(self):
        """
        Ensures physical path integrity on boot.
        """
        self._ensure_directories()

    def save_state(self, app_state: Any, file_path: str) -> bool:
        """Persists the full AppState (sources, associations, map path) to a JSON file."""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            from src.infrastructure.json_source_storage import JsonSourceStorage
            storage_helper = JsonSourceStorage(file_path)
            data_sources = {s.id: s for s in app_state.get_all_data_sources()}
            associations = app_state.sources._associations if hasattr(app_state, "sources") else {}
            map_path = app_state.get_map_source_path()
            return storage_helper.save(data_sources, associations, map_path)
        except Exception as e:
            logging.error(f"[StorageManager] Failed to save state to {file_path}: {e}")
            return False

    def load_state(self, app_state: Any, file_path: str) -> bool:
        """Restores AppState (sources, associations, map path) from a JSON file."""
        try:
            if not os.path.exists(file_path):
                return False
            from src.infrastructure.json_source_storage import JsonSourceStorage
            storage_helper = JsonSourceStorage(file_path)
            sources, associations, map_path = storage_helper.load()
            
            if hasattr(app_state, "sources"):
                app_state.sources._data_sources.clear()
                app_state.sources._data_sources.update(sources)
                app_state.sources._associations.clear()
                app_state.sources._associations.update(associations)
            if map_path:
                app_state.set_map_source_path(map_path)
            return True
        except Exception as e:
            logging.error(f"[StorageManager] Failed to load state from {file_path}: {e}")
            return False

    def close(self):
        """No-op."""
        pass
