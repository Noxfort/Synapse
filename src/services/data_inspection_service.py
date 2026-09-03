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
# File: src/services/data_inspection_service.py
# Author: Gabriel Moraes
# Date: 2026-08-30

"""
Data Inspection Service (SOLID: SRP).

Encapsulates metadata extraction, schema validation, and tabular inspection (e.g. Parquet files).
"""

import os
from typing import Dict, Any, Optional

from src.utils.logging_setup import get_logger


class DataInspectionService:
    """Service responsible for reading and inspecting analytical data formats."""

    def __init__(self):
        self.logger = get_logger("DataInspectionService")

    def inspect_parquet(self, file_path: str) -> Dict[str, Any]:
        """
        Inspects schema and size of a Parquet file without loading full payload into memory.
        """
        clean_path = file_path.strip().strip('"\'')
        if clean_path.startswith("file://"):
            clean_path = clean_path[7:]

        clean_path = os.path.expanduser(clean_path)
        if not clean_path.lower().endswith(".parquet"):
            raise ValueError(f"O arquivo deve ter extensão .parquet: {clean_path}")

        if not clean_path or not os.path.exists(clean_path):
            raise FileNotFoundError(f"Arquivo Parquet não encontrado no disco: {clean_path}")

        file_size_mb = round(os.path.getsize(clean_path) / (1024 * 1024), 2)

        # 1. Try fast inspection via pyarrow (Zero memory overhead)
        try:
            import pyarrow.parquet as pq

            pq_file = pq.ParquetFile(clean_path)
            num_rows = int(pq_file.metadata.num_rows)
            columns = [str(col) for col in pq_file.schema.names]

            return {
                "num_rows": num_rows,
                "columns": columns,
                "head": [],
                "size_mb": file_size_mb,
            }
        except Exception as pyarrow_err:
            self.logger.warning(f"pyarrow inspection fallback for '{clean_path}': {pyarrow_err}")

        # 2. Fallback to pandas read_parquet
        try:
            import pandas as pd

            df = pd.read_parquet(clean_path)
            return {
                "num_rows": int(len(df)),
                "columns": [str(c) for c in df.columns],
                "head": [],
                "size_mb": file_size_mb,
            }
        except Exception as ex:
            self.logger.error(f"Error inspecting parquet file '{clean_path}': {ex}", exc_info=True)
            raise ValueError(f"Formato Parquet inválido ou arquivo corrompido: {ex}") from ex
