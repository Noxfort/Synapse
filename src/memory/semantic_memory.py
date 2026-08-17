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
# File: src/memory/semantic_memory.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple


class SemanticMemory:
    """
    Semantic Memory and Dynamic Ontology Concept Cache.
    
    Provides high-throughput in-RAM/VRAM storage and cosine similarity retrieval
    for learned semantic concept embeddings produced by DistilRoBERTa.
    """

    def __init__(self, device: Optional[torch.device] = None):
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.concepts: Dict[str, torch.Tensor] = {}
        self.examples: Dict[str, List[str]] = {}

    def set_concept(
        self,
        concept_name: str,
        embedding: torch.Tensor,
        example_texts: Optional[List[str]] = None
    ) -> None:
        """
        Stores or updates a concept embedding centroid.
        """
        tensor = embedding.detach().to(self.device)
        if tensor.dim() == 1:
            tensor = tensor.unsqueeze(0)
        norm_tensor = F.normalize(tensor, p=2, dim=-1)
        self.concepts[concept_name] = norm_tensor
        
        if example_texts:
            if concept_name not in self.examples:
                self.examples[concept_name] = []
            for ex in example_texts:
                if ex not in self.examples[concept_name]:
                    self.examples[concept_name].append(ex)

    def get_concept(self, concept_name: str) -> Optional[torch.Tensor]:
        """Returns the embedding for a specific concept."""
        return self.concepts.get(concept_name)

    def get_all_concepts(self) -> Dict[str, torch.Tensor]:
        """Returns all stored concept embeddings."""
        return dict(self.concepts)

    def get_examples(self, concept_name: str) -> List[str]:
        """Returns typical text examples for a concept."""
        return self.examples.get(concept_name, [])

    def find_nearest_concept(
        self,
        query_embedding: torch.Tensor,
        threshold: float = 0.80
    ) -> Tuple[Optional[str], float]:
        """
        Calculates cosine similarity against all stored concept centroids.
        
        Returns:
            (best_concept_name, similarity_score) if similarity >= threshold, else (None, best_similarity).
        """
        if not self.concepts:
            return None, 0.0

        q = query_embedding.to(self.device)
        if q.dim() == 1:
            q = q.unsqueeze(0)
        q_norm = F.normalize(q, p=2, dim=-1)

        best_concept: Optional[str] = None
        best_sim: float = -1.0

        for name, centroid in self.concepts.items():
            sim = torch.mm(q_norm, centroid.t()).item()
            if sim > best_sim:
                best_sim = sim
                if sim >= threshold:
                    best_concept = name

        return best_concept, float(best_sim)

    def export_snapshot(self) -> Dict[str, torch.Tensor]:
        """Exports all concept tensors for SafeTensors persistence."""
        return {name: t.detach().cpu() for name, t in self.concepts.items()}

    def load_snapshot(self, tensors: Dict[str, torch.Tensor]) -> None:
        """Loads concept tensors into memory from a dictionary."""
        for name, t in tensors.items():
            self.set_concept(name, t)

    def clear(self) -> None:
        """Clears all cached concepts and examples."""
        self.concepts.clear()
        self.examples.clear()

    def __len__(self) -> int:
        return len(self.concepts)
