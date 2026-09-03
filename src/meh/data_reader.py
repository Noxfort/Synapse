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
# File: src/meh/data_reader.py
# Author: Gabriel Moraes
# Date: 2026-02-28

import os
from typing import Optional, Dict, Tuple
import pandas as pd
import torch
from safetensors.torch import load_file

from src.managers.storage_manager import StorageManager
from src.utils.logging_setup import logger


class DataLakeReader:
    """
    Single Responsibility: Disk I/O operations for Historical DataLake & Ontology files.
    Decoupled from data processing, cataloging, and analytical queries.
    """

    def __init__(self, storage_manager: Optional[StorageManager] = None):
        self.storage = storage_manager or StorageManager()
        self.gold_path = os.path.join(self.storage.get_datalake_golden_path(), "golden_v1.parquet")
        
        base_dir = os.path.dirname(os.path.dirname(self.storage.get_datalake_golden_path()))
        self.config_path = os.path.join(base_dir, "data", "config", "ontology.safetensors")

    def read_ontology(self, path: Optional[str] = None) -> Dict[str, torch.Tensor]:
        """Reads Safetensors ontology file from disk if present."""
        target_path = path or self.config_path
        if os.path.exists(target_path):
            try:
                ontology = load_file(target_path)
                logger.info(f"[DataLakeReader] 📚 Loaded ontology with {len(ontology)} semantic concepts.")
                return ontology
            except Exception as e:
                logger.error(f"[DataLakeReader] ❌ Failed to read ontology at {target_path}: {e}")
                return {}
        else:
            logger.warning(f"[DataLakeReader] ⚠️ Ontology safetensors not found at {target_path}. Semantic translation bypassed.")
            return {}

    def read_golden_parquet(self, path: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Reads Golden Parquet dataset from disk."""
        target_path = path or self.gold_path
        if not os.path.exists(target_path):
            logger.warning(f"[DataLakeReader] ⚠️ Golden Dataset not found at: {target_path}")
            logger.info(f"[DataLakeReader] 💡 Tip: Run Phase 1 (Offline Bootstrap) first.")
            return None

        try:
            return pd.read_parquet(target_path)
        except Exception as e:
            logger.error(f"[DataLakeReader] ❌ Failed to read golden parquet at {target_path}: {e}")
            return None

    def read_all(
        self,
        gold_path: Optional[str] = None,
        config_path: Optional[str] = None
    ) -> Tuple[Optional[pd.DataFrame], Dict[str, torch.Tensor]]:
        """Reads both golden dataset and ontology."""
        ontology = self.read_ontology(config_path)
        raw_data = self.read_golden_parquet(gold_path)
        return raw_data, ontology
