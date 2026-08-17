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
# File: src/models/distilroberta.py
# Author: Gabriel Moraes
# Date: 2026-08-17

from typing import List, Optional, Tuple, Dict, Any
import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel

# Enable Tensor Cores globally for matrix multiplications and cuDNN operations
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True


class DistilRobertaEmbeddingModel(nn.Module):
    """
    Pure Neural Transformer Embedding Model (DistilRoBERTa Backbone).
    
    A clean PyTorch Module responsible exclusively for:
    1. Processing input IDs and attention masks through transformer layers.
    2. Applying masked mean pooling over token embeddings.
    3. Returning L2-normalized continuous semantic embeddings.
    
    Adheres to SOLID: zero file I/O, zero clustering state, zero external side-effects.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-distilroberta-v1",
        transformer: Optional[nn.Module] = None
    ):
        super(DistilRobertaEmbeddingModel, self).__init__()
        self.model_name = model_name
        self.transformer = transformer or AutoModel.from_pretrained(model_name)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        """
        Forward pass for semantic representation extraction.
        
        Args:
            input_ids: Token indices tensor [Batch, SeqLen]
            attention_mask: Attention mask tensor [Batch, SeqLen]
            
        Returns:
            normalized_embeddings: Normalized sentence embeddings [Batch, HiddenDim]
        """
        model_output = self.transformer(input_ids=input_ids, attention_mask=attention_mask)
        token_embeddings = model_output[0]
        
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, dim=1)
        sum_mask = torch.clamp(input_mask_expanded.sum(dim=1), min=1e-9)
        mean_pooled = sum_embeddings / sum_mask
        
        return F.normalize(mean_pooled, p=2, dim=-1)


# Clean Facade Orchestrator maintained for legacy agent/pipeline integration
class DistilRobertaSemanticExtractor:
    """
    Semantic Orchestrator Facade.
    
    Coordinates the pure DistilRobertaEmbeddingModel with tokenization,
    semantic clustering (ISemanticClusterer), and persistence (IOntologyRepository).
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-distilroberta-v1",
        similarity_threshold: float = 0.80,
        tokenizer: Optional[AutoTokenizer] = None,
        model: Optional[DistilRobertaEmbeddingModel] = None,
        clusterer: Optional[Any] = None,
        repository: Optional[Any] = None
    ):
        from src.strategies.semantic_clustering import CosineSemanticClusterer
        from src.infrastructure.safetensors_repository import SafetensorsRepository
        import logging

        self.logger = logging.getLogger(self.__class__.__name__)
        self.similarity_threshold = similarity_threshold
        
        self.clusterer = clusterer or CosineSemanticClusterer(similarity_threshold=similarity_threshold, logger=self.logger)
        self.repository = repository or SafetensorsRepository(logger=self.logger)
        
        self.tokenizer = tokenizer or AutoTokenizer.from_pretrained(model_name)
        self.model = model or DistilRobertaEmbeddingModel(model_name=model_name)
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()

    @property
    def learned_concepts(self) -> Dict[str, torch.Tensor]:
        return self.clusterer.get_concept_tensors()

    @property
    def concept_examples(self) -> Dict[str, List[str]]:
        return self.clusterer.get_ontology_report()

    def _get_embedding(self, texts: List[str]) -> torch.Tensor:
        encoded_input = self.tokenizer(texts, padding=True, truncation=True, return_tensors='pt').to(self.device)
        device_type = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        with torch.no_grad():
            with torch.autocast(device_type=device_type, dtype=torch.float16 if device_type == 'cuda' else torch.bfloat16):
                pooled = self.model(encoded_input['input_ids'], encoded_input['attention_mask'])
                
        cluster_embedding = torch.mean(pooled, dim=0, keepdim=True)
        return F.normalize(cluster_embedding, p=2, dim=1)

    def learn_and_map_semantics(self, unique_values: List[str]) -> Tuple[str, bool]:
        if not self.model or not unique_values:
            return "unknown_concept", False

        try:
            clean_texts = [str(val).strip().lower() for val in unique_values if str(val).strip()]
            if not clean_texts:
                return "empty_data", False

            current_embedding = self._get_embedding(clean_texts)
            return self.clusterer.match_or_create_concept(
                current_embedding=current_embedding,
                clean_texts=clean_texts,
                device=self.device
            )
        except Exception as e:
            self.logger.error(f"Error during semantic embedding extraction: {e}")
            return "error_in_extraction", False

    def get_ontology_report(self) -> Dict[str, List[str]]:
        return self.clusterer.get_ontology_report()

    def save_ontology(self, filepath: str) -> None:
        tensors = self.clusterer.get_concept_tensors()
        self.repository.save_tensors(tensors, filepath)