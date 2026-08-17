# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2025 Noxfort Systems
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
# File: src/domain/interfaces.py
# Author: Gabriel Moraes
# Date: 2025-12-24

from typing import Any, List, Dict, Optional, Protocol, runtime_checkable, Union

# --- AGENT INTERFACES (DIP/OCP) ---

@runtime_checkable
class IAgent(Protocol):
    """Base contract for any AI Agent in the system."""
    def to(self, device: Any) -> 'IAgent':
        """Moves the agent's internal model to a computing device (CPU/GPU)."""
        ...

@runtime_checkable
class ISpatialAgent(IAgent, Protocol):
    """Contract for agents that understand space (e.g. GATv2)."""
    def process_region(self, node_features: Any, edge_index: Any) -> Any:
        """Processes a graph snapshot and returns node embeddings."""
        ...

@runtime_checkable
class ITemporalAgent(IAgent, Protocol):
    """Contract for agents that understand time (e.g. Transformers)."""
    def predict_state(self, history: Any) -> Any:
        """Predicts future states based on historical time-series."""
        ...

# --- INFRASTRUCTURE INTERFACES (DIP) ---

@runtime_checkable
class IPipeline(Protocol):
    """Contract for data ingestion pipelines."""
    def process_packet(self, source_id: str, payload: Any) -> bool:
        ...
    
    def is_ready_for_linguist(self, source_id: str) -> bool:
        ...

# --- STATE INTERFACES (ISP) ---

@runtime_checkable
class ITopologyProvider(Protocol):
    """Interface for components that only need to READ map data."""
    def get_all_nodes(self) -> List[Any]: ...
    def get_all_edges(self) -> List[Any]: ...

@runtime_checkable
class ISourceProvider(Protocol):
    """Interface for components that only need to READ sensor data."""
    def get_all_data_sources(self) -> List[Any]: ...
    def get_data_source(self, source_id: str) -> Any: ...

# --- FUSION & CALIBRATION INTERFACES (ISP/DIP) ---

@runtime_checkable
class ISensorCalibrator(Protocol):
    """Contract for dynamic sensor calibration and online bias correction."""
    def update_observability(self, active_mask: Any) -> None: ...
    def apply(self, raw_output: Any, current_history: Any, observability_mask: Any = None) -> Any: ...
    def reset(self) -> None: ...

@runtime_checkable
class IFusionPipeline(Protocol):
    """Contract for multi-model neural fusion pipelines."""
    def execute(
        self,
        current_history: Any,
        spatial_context: Optional[Any] = None,
        observability_mask: Optional[Any] = None,
        global_velocities: Optional[Any] = None,
        edge_index: Optional[Any] = None
    ) -> Any: ...
    def to(self, device: Any) -> 'IFusionPipeline': ...

@runtime_checkable
class IFuserTrainer(Protocol):
    """Contract for Fuser neural optimization and training routines."""
    def train_step(self, batch_data: Any) -> float: ...
    def train(self, inputs: Any, targets: Any, epochs: int = 100, batch_size: int = 16, **kwargs: Any) -> float: ...

# --- AUDITOR INTERFACES ---

@runtime_checkable
class IAuditorPipeline(Protocol):
    """Contract for anomaly detection and physical-spectral auditing pipeline."""
    def audit(self, input_data: Any) -> Dict[str, Any]: ...
    def to(self, device: Any) -> 'IAuditorPipeline': ...

@runtime_checkable
class IAuditorTrainer(Protocol):
    """Contract for Auditor neural optimization and adaptive threshold routines."""
    def train_step(self, batch_data: Any) -> float: ...

# --- IMPUTER INTERFACES ---

@runtime_checkable
class IImputerPipeline(Protocol):
    """Contract for missing sensor data reconstruction and gap imputation."""
    def reconstruct(self, incomplete_seq: Any, chunk_size: int = 4096) -> Any: ...
    def to(self, device: Any) -> 'IImputerPipeline': ...

@runtime_checkable
class IImputerTrainer(Protocol):
    """Contract for Imputer masked training routines."""
    def train_step(self, batch_data: Any) -> float: ...

# --- CORRECTOR INTERFACES ---

@runtime_checkable
class ICorrectorPipeline(Protocol):
    """Contract for physics-informed denoising and golden dataset reconstruction."""
    def correct(self, input_data: Any, batch_size: int = 128) -> Any: ...
    def to(self, device: Any) -> 'ICorrectorPipeline': ...

@runtime_checkable
class ICorrectorTrainer(Protocol):
    """Contract for Corrector PI-VAE training and convergence routines."""
    def train_step(self, batch_data: Any) -> float: ...
    def train(self, data: Any, epochs: int = 100, batch_size: int = 64, **kwargs: Any) -> Dict[str, list]: ...

# --- SPECIALIST INTERFACES ---

@runtime_checkable
class ISpecialistPipeline(Protocol):
    """Contract for temporal convolutional feature extraction and decoding."""
    def predict(self, input_sequence: Any) -> Any: ...
    def to(self, device: Any) -> 'ISpecialistPipeline': ...

@runtime_checkable
class ISpecialistTrainer(Protocol):
    """Contract for Specialist training routines."""
    def train_step(self, batch_data: Any) -> float: ...
    def train(self, inputs: Any, targets: Any, epochs: int = 1, batch_size: int = 32) -> float: ...

# --- LINGUIST INTERFACES ---

@runtime_checkable
class ILinguistPipeline(Protocol):
    """Contract for semantic-physical validation and contradiction detection."""
    def validate(self, input_data: Any) -> Dict[str, Any]: ...
    def calibrate_threshold(self, validation_texts: List[str]) -> None: ...
    def to(self, device: Any) -> 'ILinguistPipeline': ...

@runtime_checkable
class ILinguistTrainer(Protocol):
    """Contract for NeuroSymbolic reasoning training routines."""
    def train_step(self, batch_data: Any) -> float: ...

# --- COORDINATOR INTERFACES ---

@runtime_checkable
class ICoordinatorPipeline(Protocol):
    """Contract for spatial graph reasoning and global network embeddings."""
    def forward_pass(self, x: Any, edge_index: Optional[Any] = None) -> Any: ...
    def to(self, device: Any) -> 'ICoordinatorPipeline': ...

@runtime_checkable
class ICoordinatorTrainer(Protocol):
    """Contract for graph neural network optimization."""
    def train_step(self, batch_data: Any) -> float: ...

# --- SEMANTIC & PERSISTENCE INTERFACES ---

@runtime_checkable
class ISemanticEmbedder(Protocol):
    """Contract for NLP semantic text embedding models."""
    def encode(self, texts: List[str]) -> Any: ...

@runtime_checkable
class ISemanticClusterer(Protocol):
    """Contract for dynamic semantic concept clustering and discovery."""
    def match_or_create_concept(self, current_embedding: Any, clean_texts: List[str], **kwargs: Any) -> Tuple[str, bool]: ...
    def get_ontology_report(self) -> Dict[str, List[str]]: ...

@runtime_checkable
class IOntologyRepository(Protocol):
    """Contract for persisting ontology tensors and model checkpoints."""
    def save_tensors(self, tensors: Dict[str, Any], filepath: str) -> bool: ...
    def load_tensors(self, filepath: str, device: str = "cpu") -> Dict[str, Any]: ...

# --- PHYSICS INTERFACES (FORWARD EXPORT) ---
from src.physics.physics_interfaces import IFundamentalDiagram, IPhysicsConstraint, IPhysicsLossEngine

# --- MEMORY INTERFACES ---

@runtime_checkable
class ISpatioTemporalMemory(Protocol):
    """Contract for continuous spatio-temporal tensor buffering."""
    def update_node(self, node_id: str, features: Any) -> bool: ...
    def get_tensor(self, batch_first: bool = True, device: Optional[Any] = None) -> Any: ...
    def get_observability_mask(self, device: Optional[Any] = None) -> Any: ...

@runtime_checkable
class IEpisodicMemory(Protocol):
    """Contract for episodic replay buffers and anomaly recording."""
    def record_episode(self, sensor_id: str, signature: Any, anomaly_score: float, **kwargs: Any) -> None: ...
    def sample_batch(self, batch_size: int, device: Optional[Any] = None) -> Optional[Tuple[Any, Any]]: ...

@runtime_checkable
class ISemanticMemory(Protocol):
    """Contract for fast dynamic ontology and concept memory."""
    def set_concept(self, concept_name: str, embedding: Any, **kwargs: Any) -> None: ...
    def find_nearest_concept(self, query_embedding: Any, threshold: float = 0.80) -> Tuple[Optional[str], float]: ...

@runtime_checkable
class ITopologyMemory(Protocol):
    """Contract for dynamic graph connectivity tracking."""
    def set_graph(self, num_nodes: int, edge_list: List[Tuple[int, int]], **kwargs: Any) -> None: ...
    def get_edge_index_tensor(self, device: Optional[Any] = None) -> Any: ...