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
# File: src/utils/model_paths.py
# Author: Gabriel Moraes
# Date: 2026-08-28

import os
from typing import Optional


def get_project_root() -> str:
    """Returns the absolute root directory of the SYNAPSE project."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_model_vault_dir() -> str:
    """Returns the absolute path to the Model_Vault directory."""
    root = get_project_root()
    return os.path.join(root, "Model_Vault")


def get_distilroberta_path() -> str:
    """Returns the unified local path for DistilRoBERTa in Model_Vault."""
    vault = get_model_vault_dir()
    distil_path = os.path.join(vault, "distilroberta")
    if os.path.exists(distil_path):
        return distil_path
    
    # Fallback to distilroberta_v1 if present
    v1_path = os.path.join(vault, "distilroberta_v1")
    if os.path.exists(v1_path):
        return v1_path
        
    return "sentence-transformers/all-distilroberta-v1"


def get_distilroberta_v1_path() -> str:
    """Backward-compatible alias for DistilRoBERTa path."""
    return get_distilroberta_path()


def get_distilroberta_base_path() -> str:
    """Backward-compatible alias for DistilRoBERTa path."""
    return get_distilroberta_path()


def get_qwen_gguf_path() -> str:
    """Returns the local path to the Qwen GGUF model in Model_Vault."""
    vault = get_model_vault_dir()
    qwen_gguf = os.path.join(vault, "Qwen3.5-2B-UD-Q6_K_XL.gguf")
    return qwen_gguf
