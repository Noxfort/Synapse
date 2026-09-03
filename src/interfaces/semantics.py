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
# File: src/interfaces/semantics.py
# Author: Gabriel Moraes
# Date: 2026-08-19

from typing import Any, Dict, List, Protocol, Tuple, runtime_checkable


@runtime_checkable
class ISemanticEmbedder(Protocol):
    """Contract for NLP semantic text embedding models."""
    def encode(self, texts: List[str]) -> Any: ...


@runtime_checkable
class ISemanticClusterer(Protocol):
    """Contract for dynamic semantic concept clustering and discovery."""
    def match_or_create_concept(
        self,
        current_embedding: Any,
        clean_texts: List[str],
        **kwargs: Any
    ) -> Tuple[str, bool]: ...

    def get_ontology_report(self) -> Dict[str, List[str]]: ...


@runtime_checkable
class IOntologyRepository(Protocol):
    """Contract for persisting ontology tensors and model checkpoints."""
    def save_tensors(self, tensors: Dict[str, Any], filepath: str) -> bool: ...
    def load_tensors(self, filepath: str, device: str = "cpu") -> Dict[str, Any]: ...
