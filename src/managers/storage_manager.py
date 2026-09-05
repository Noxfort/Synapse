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

    def __init__(
        self,
        engine: Optional[Any] = None,
        auto_restore: bool = True,
        project_root: Optional[str] = None
    ):
        """
        Initializes the storage manager with dual-layer persistence (local disk + PostgreSQL vault).
        """
        # 1. Resolve User Home Directory
        self.home = Path.home()
        
        # 2. Locate 'Documents' folder (Handles PT-BR 'Documentos' vs EN 'Documents')
        self.documents_dir = self.home / "Documentos"
        if not self.documents_dir.exists():
            self.documents_dir = self.home / "Documents"
            
        # 3. Define Project Root
        self.project_root = Path(project_root) if project_root else self.documents_dir / "Synapse"
        
        # 4. Define Folders
        self.checkpoint_dir = self.project_root / "Checkpoint"
        self.datalake_dir = self.project_root / "datalake"
        self.base_dir = self.datalake_dir / "base"
        self.golden_dir = self.datalake_dir / "golden"
        self.config_dir = self.project_root / "config"
        self.data_config_dir = self.project_root / "data" / "config"
        
        # Internal State
        self.is_connected = True

        # Database Engine & Cloud File Vault integration
        if engine is not None:
            self.engine = engine
        elif project_root is None:
            try:
                from src.database.db_engine import DatabaseEngine
                self.engine = DatabaseEngine()
            except Exception as e:
                logging.debug(f"[StorageManager] Could not auto-initialize DatabaseEngine: {e}")
                self.engine = None
        else:
            self.engine = None

        if self.engine:
            try:
                from src.repositories.cloud_vault_repo import CloudVaultRepository
                self.cloud_vault = CloudVaultRepository(self.engine)
            except Exception as e:
                logging.debug(f"[StorageManager] Could not initialize CloudVaultRepository: {e}")
                self.cloud_vault = None
        else:
            self.cloud_vault = None

        # Ensure directories exist immediately upon instantiation
        self._ensure_structure(auto_restore=auto_restore)
        
        logging.info(f"[StorageManager] Storage initialized at: {self.project_root}")

    def _ensure_structure(self, auto_restore: bool = True):
        """Creates the necessary folder structure and restores from vault if needed."""
        paths = [
            self.project_root,
            self.checkpoint_dir,
            self.datalake_dir,
            self.base_dir,
            self.golden_dir,
            self.config_dir,
            self.data_config_dir
        ]
        
        for path in paths:
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    logging.critical(f"[StorageManager] Failed to create directory {path}: {e}")

        # If vault is available and the project root has no operational files, attempt disaster recovery
        if auto_restore and self.cloud_vault:
            try:
                existing_files = [
                    f for f in self.project_root.glob("**/*")
                    if f.is_file() and not f.name.endswith(".db") and not f.name.endswith(".log")
                ]
                if len(existing_files) == 0:
                    restored = self.restore_all_from_vault()
                    if restored > 0:
                        logging.info(f"[StorageManager] 🌟 Disaster recovery: {restored} files restored from PostgreSQL cloud vault.")
            except Exception as re:
                logging.debug(f"[StorageManager] Vault auto-restore notice: {re}")

    # =========================================================================
    #  CLOUD VAULT DUAL-LAYER METHODS (Database + Disk)
    # =========================================================================

    def sync_file_to_vault(self, filepath: str) -> bool:
        """Uploads a local file to the cloud file vault in PostgreSQL."""
        if not self.cloud_vault or not os.path.exists(filepath):
            return False
        try:
            return self.cloud_vault.sync_file_to_vault(filepath, str(self.project_root))
        except Exception as e:
            logging.debug(f"[StorageManager] Failed to sync {filepath} to vault: {e}")
            return False

    def restore_file_from_vault(self, relative_path: str, target_filepath: str) -> bool:
        """Restores a single file from the cloud file vault to disk."""
        if not self.cloud_vault:
            return False
        try:
            return self.cloud_vault.restore_file_from_vault(relative_path, target_filepath)
        except Exception as e:
            logging.debug(f"[StorageManager] Failed to restore {relative_path} from vault: {e}")
            return False

    def sync_all_to_vault(self) -> None:
        """Syncs all files in project root to cloud vault."""
        if not self.cloud_vault:
            return
        try:
            self.cloud_vault.sync_all_files_to_vault(str(self.project_root))
        except Exception as e:
            logging.debug(f"[StorageManager] Failed to sync all files to vault: {e}")

    def restore_all_from_vault(self) -> int:
        """Restores all files from cloud vault into project root."""
        if not self.cloud_vault:
            return 0
        try:
            return self.cloud_vault.restore_all_files_from_vault(str(self.project_root))
        except Exception as e:
            logging.debug(f"[StorageManager] Failed to restore all files from vault: {e}")
            return 0

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
        """Persists a single node's state checkpoint to disk and cloud vault."""
        try:
            import torch
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
            file_path = self.checkpoint_dir / f"state_{source_id}.pth"
            torch.save(state, str(file_path))
            self.sync_file_to_vault(str(file_path))
            return True
        except Exception as e:
            logging.error(f"[StorageManager] Failed to save node checkpoint for '{source_id}': {e}")
            return False

    def load_node_checkpoint(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Loads and returns a node state checkpoint if it exists (restores from vault if missing)."""
        try:
            import torch
            file_path = self.checkpoint_dir / f"state_{source_id}.pth"
            if not file_path.exists():
                self.restore_file_from_vault(f"Checkpoint/state_{source_id}.pth", str(file_path))
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
        """Verifies if Phase 0 (AutoML) hyperparameter checkpoint exists (restoring from vault if needed)."""
        try:
            checkpoint_file = Path(self.get_checkpoint_path()) / "best_hparams.pth"
            if not checkpoint_file.exists():
                self.restore_file_from_vault("Checkpoint/best_hparams.pth", str(checkpoint_file))
            return checkpoint_file.exists() and checkpoint_file.stat().st_size > 0
        except Exception as e:
            logging.warning(f"[StorageManager] Error checking Phase 0 artifacts: {e}")
            return False

    def has_phase1_artifacts(self) -> bool:
        """Verifies if Phase 1 DataLake, Ontology, Schedule, and Auditor exist (restoring from vault if needed)."""
        try:
            base_dir = Path(self.get_datalake_base_path())
            golden_dir = Path(self.get_datalake_golden_path())
            config_dir = Path(self.get_config_path())

            # Attempt to restore missing artifacts from vault if needed
            safetensors = config_dir / "ontology.safetensors"
            peak_schedule = config_dir / "peak_schedule.json"
            auditor_checkpoint = config_dir / "auditor_calibrated.pth"

            if not safetensors.exists():
                self.restore_file_from_vault("data/config/ontology.safetensors", str(safetensors))
            if not peak_schedule.exists():
                self.restore_file_from_vault("data/config/peak_schedule.json", str(peak_schedule))
            if not auditor_checkpoint.exists():
                self.restore_file_from_vault("data/config/auditor_calibrated.pth", str(auditor_checkpoint))

            base_parquets = list(base_dir.glob("*.parquet")) if base_dir.exists() else []
            if len(base_parquets) == 0 and base_dir.exists():
                base_target = base_dir / "base_v1.parquet"
                if self.restore_file_from_vault("datalake/base/base_v1.parquet", str(base_target)):
                    base_parquets = [base_target]

            golden_parquets = list(golden_dir.glob("*.parquet")) if golden_dir.exists() else []
            if len(golden_parquets) == 0 and golden_dir.exists():
                golden_target = golden_dir / "golden_v1.parquet"
                if self.restore_file_from_vault("datalake/golden/golden_v1.parquet", str(golden_target)):
                    golden_parquets = [golden_target]

            if not base_dir.exists() or not golden_dir.exists() or not config_dir.exists():
                return False

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
        """Persists the full AppState (sources, associations, map path) to a JSON file and syncs to cloud vault."""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            from src.infrastructure.json_source_storage import JsonSourceStorage
            storage_helper = JsonSourceStorage(file_path, engine=self.engine)
            data_sources = {s.id: s for s in app_state.get_all_data_sources()}
            associations = app_state.sources._associations if hasattr(app_state, "sources") else {}
            map_path = app_state.get_map_source_path()
            saved = storage_helper.save(data_sources, associations, map_path)
            self.sync_file_to_vault(file_path)
            return saved
        except Exception as e:
            logging.error(f"[StorageManager] Failed to save state to {file_path}: {e}")
            return False

    def load_state(self, app_state: Any, file_path: str) -> bool:
        """Restores AppState (sources, associations, map path) from a JSON file (restoring from vault if missing)."""
        try:
            if not os.path.exists(file_path):
                rel_path = os.path.relpath(file_path, str(self.project_root))
                self.restore_file_from_vault(rel_path, file_path)

            if not os.path.exists(file_path):
                return False

            from src.infrastructure.json_source_storage import JsonSourceStorage
            storage_helper = JsonSourceStorage(file_path, engine=self.engine)
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
