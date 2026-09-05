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
# File: src/services/linguist_service.py
# Author: Gabriel Moraes
# Date: 2026-08-20

import math
from typing import Dict, Optional, List, Any
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

# --- Domain & Workers ---
from src.domain.app_state import AppState
from src.domain.entities import SourceStatus, DataSource, MapEdge
from src.workers.ingestion_worker import IngestionWorker

# --- Interfaces (DIP / ISP) ---
from src.interfaces.quarantine import (
    ISeriesExtractorPipeline,
    ISemanticClassifier,
    ISensorPhysicsValidator,
    IKnowledgeTransfer,
)

# --- Concrete Implementations (Defaults) ---
from src.pipeline.series_extractor_pipeline import SeriesExtractorPipeline
from src.services.semantic_classifier import SemanticClassifier
from src.physics.sensor_physical_validator import SensorPhysicalValidator
from src.services.knowledge_transfer_service import KnowledgeTransferService
from src.factories.agent_factory import AgentFactory

# --- Utils ---
from src.utils.logging_setup import get_logger

logger = get_logger("LinguistService")


class LinguistService(QObject):
    """
    The 'Neuro-Symbolic' Gatekeeper Service.
    
    Pure Orchestrator Architecture (SOLID Compliant):
    - [SRP] Exclusively coordinates the quarantine state machine workflow.
    - [OCP] Data parsing, semantic inference, physics validation and knowledge transfer
            are delegated to injected strategy components.
    - [DIP] Relies on abstract interfaces (ISeriesExtractorPipeline, ISemanticClassifier,
            ISensorPhysicsValidator, IKnowledgeTransfer).
    """

    # Signal emitted when a source is successfully analyzed and promoted
    update_signal = pyqtSignal(str, str, float)

    def __init__(
        self,
        app_state: AppState,
        ingestion_worker: IngestionWorker,
        agent_factory: AgentFactory,
        series_extractor: Optional[ISeriesExtractorPipeline] = None,
        semantic_classifier: Optional[ISemanticClassifier] = None,
        physics_validator: Optional[ISensorPhysicsValidator] = None,
        knowledge_transfer: Optional[IKnowledgeTransfer] = None,
    ):
        super().__init__()
        self.app_state = app_state
        self.ingestion = ingestion_worker
        self.agent_factory = agent_factory

        # Injected Strategy Components (DIP / OCP)
        self.series_extractor = series_extractor or SeriesExtractorPipeline()
        self.semantic_classifier = semantic_classifier or SemanticClassifier()
        self.physics_validator = physics_validator or SensorPhysicalValidator(
            semantic_classifier=self.semantic_classifier,
            app_state=self.app_state
        )
        self.knowledge_transfer = knowledge_transfer or KnowledgeTransferService()

        # Memory to track training attempts per source (Key: source_id, Value: attempt_count)
        self.learning_attempts: Dict[str, int] = {}

        # Thresholds (5 to 10 samples validation)
        self.SAMPLE_CHUNK_SIZE = 5
        self.MAX_ATTEMPTS = 2  # Allows up to 10 samples total (attempt 1 at 5, attempt 2 at 10)
        self.GRAMMAR_LOSS_THRESHOLD = 0.5  # PINN combined loss limit to consider "Learned"

    @pyqtSlot()
    def run_check(self):
        """
        Invoked via signal from the Neural thread.
        Scans quarantined sources and progresses their state machine.
        If no quarantined sources exist, returns immediately (standby).
        """
        pipeline = self.ingestion.get_pipeline()
        sources = self.app_state.get_all_data_sources()

        for source in sources:
            if source.status == SourceStatus.QUARANTINE:
                self._process_quarantine_source(source, pipeline)

    def _process_quarantine_source(self, source: DataSource, pipeline: Any):
        """
        Executes the quarantine lifecycle:
        Collect -> Discover Schema & Semantics -> Train PINN -> Validate Physics -> Teach TCN -> Promote.
        """
        # 1. Check Data Availability (5 samples initially, 10 on retry)
        current_attempt = self.learning_attempts.get(source.id, 0)
        required_samples = self.SAMPLE_CHUNK_SIZE * (current_attempt + 1)

        if not pipeline.has_enough_data(source.id, required_samples):
            return  # Wait for ingestion buffer

        data_chunk = pipeline.get_quarantine_data(source.id)
        data_np = self.series_extractor.extract(data_chunk)

        # 2. Discover Semantics and Modality
        sem_type, unit, confidence = self.semantic_classifier.classify(source, data_np, data_chunk)

        logger.info(
            f"🔬 [Linguist] {len(data_chunk)} amostras coletadas para '{source.name}' ({source.id}). "
            f"Modalidade detectada: '{sem_type}' [{unit}]. Iniciando treino PINN e validação física (Tentativa {current_attempt+1})..."
        )

        # 3. Summon the Linguist Agent (The Learner)
        linguist = self.agent_factory.get_or_create_linguist(source.id)

        # Train on current chunk with local convergence loop and modality conditioning
        loss = linguist.train_step(data_np.tolist(), epochs=10, semantic_type=sem_type)

        # 4. Decision Gate: Did we learn the signal grammar and physics?
        if loss < self.GRAMMAR_LOSS_THRESHOLD:
            logger.info(
                f"🧠 [Linguist] Gramática do sinal aprendida com sucesso! "
                f"(Perda PINN: {loss:.4f} < Limite {self.GRAMMAR_LOSS_THRESHOLD}). Validando Leis da Física..."
            )

            # 5. Physics Validation (Symbolic + Modality-Conditioned PINN Check)
            if self.physics_validator.validate(source, data_np, data_chunk, linguist):
                logger.info(
                    f"⚖️ [Linguist: Física] ✅ Consistência física APROVADA para '{source.name}' ({sem_type})."
                )

                # 5b. Directional Reconciliation & Orientation (CompassAgent)
                orientation_data = None
                candidate_edges = self._find_candidate_edges(source)
                if candidate_edges:
                    try:
                        compass = self.agent_factory.get_or_create_compass(source.id)
                        orientation_data = compass.orient_and_reconcile(
                            source=source,
                            candidate_edges=candidate_edges,
                            data_chunk=data_chunk,
                            data_np=data_np,
                            semantic_type=sem_type
                        )
                        primary_edge = orientation_data.get("primary_edge_id")
                        if primary_edge:
                            if hasattr(self.app_state, "sources") and hasattr(self.app_state.sources, "associate"):
                                self.app_state.sources.associate(source.id, primary_edge)
                                sec_edge = orientation_data.get("secondary_edge_id")
                                if sec_edge:
                                    self.app_state.sources.associate(source.id, sec_edge)
                            elif hasattr(self.app_state, "associate"):
                                self.app_state.associate(source.id, primary_edge)

                        if source.metadata is not None:
                            source.metadata["orientation"] = orientation_data.get("orientation")
                            source.metadata["orientation_vector"] = orientation_data.get("vector")

                        logger.info(
                            f"🧭 [Linguist -> Compass] Sensor '{source.name}' orientado para "
                            f"'{primary_edge}' ({orientation_data.get('orientation')})."
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ [Linguist -> Compass] Falha na reconciliação direcional: {e}")
                    finally:
                        if hasattr(self.agent_factory, "release_compass"):
                            self.agent_factory.release_compass(source.id)

                # 6. Teach the Specialist (MLOps Knowledge Transfer, Extractor Attachment, Orientation & TCN Warmup)
                specialist = self.agent_factory.get_or_create_specialist(source.id)
                self.knowledge_transfer.transfer(
                    linguist,
                    specialist,
                    data_series=data_np,
                    extractor=self.series_extractor,
                    semantic_type=sem_type,
                    unit=unit,
                    orientation_data=orientation_data
                )

                # 7. Promote to Active
                self._promote_source(source, pipeline, data_np, data_chunk, sem_type, unit, confidence)
            else:
                # Physics failed despite good grammar -> Probable Spoofing / Hallucination
                self._reject_source(source, reason=f"Violação das restrições físicas para a modalidade '{sem_type}'.")
        else:
            # Grammar not learned yet
            self._handle_learning_failure(source, pipeline, loss)

    def _handle_learning_failure(self, source: DataSource, pipeline: Any, loss: float):
        """Logic for when the agent fails to understand the signal pattern or physics diverges."""
        attempts = self.learning_attempts.get(source.id, 0) + 1
        self.learning_attempts[source.id] = attempts

        if attempts >= self.MAX_ATTEMPTS:
            logger.warning(
                f"❌ [Linguist] Falha na validação física/gramatical após 10 amostras ({attempts} tentativas). Sinal rejeitado."
            )
            self._reject_source(source, reason="Padrão não físico / Não convergência do PINN após 10 amostras.")
        else:
            logger.info(
                f"⏳ [Linguist] Calibrando física do sinal (Perda PINN: {loss:.4f}). "
                f"Coletando mais +{self.SAMPLE_CHUNK_SIZE} amostras (total até 10)..."
            )
            pipeline.extend_quarantine_buffer(source.id, self.SAMPLE_CHUNK_SIZE)

    def _promote_source(
        self,
        source: DataSource,
        pipeline: Any,
        data_np: np.ndarray,
        data_chunk: List[Any],
        sem_type: str,
        unit: str,
        confidence: float
    ):
        """Final promotion to ACTIVE state after validation."""
        source.status = SourceStatus.ACTIVE
        source.semantic_type = sem_type
        source.inferred_unit = unit
        source.confidence_score = confidence

        if len(data_np) > 0:
            source.latest_value = float(data_np[-1])
            self.app_state.update_source_value(source.id, source.latest_value)

        pipeline.promote_to_active(source.id)
        self.update_signal.emit(source.name, sem_type, confidence)

        # Persist updated source state through clean encapsulation
        self._persist_source_state(source)

        # Ephemeral Lifecycle: Deactivate and release the LinguistAgent from memory
        if hasattr(self.agent_factory, "release_linguist"):
            self.agent_factory.release_linguist(source.id)
            logger.info(f"🛑 [Linguist] Agente Linguista de '{source.name}' ({source.id}) auto-desativado e liberado da memória (TCN Local operando autonomamente).")

        logger.info(
            f"🎉 [Linguist] 🟢 Sensor '{source.name}' ({source.id}) VALIDADO COM SUCESSO! "
            f"Promovido para status ATIVO. [Modalidade: {sem_type} ({unit}) | Confiança: {confidence*100:.0f}%]"
        )

        # Cleanup memory
        if source.id in self.learning_attempts:
            del self.learning_attempts[source.id]

    def _reject_source(self, source: DataSource, reason: str):
        """Rejects the source, keeping it out of the active ingestion pipeline."""
        logger.error(f"[System] ⛔ Source '{source.name}' REJECTED. Reason: {reason}")
        source.status = SourceStatus.REJECTED
        self.learning_attempts[source.id] = 0
        self._persist_source_state(source)

        # Ephemeral Lifecycle: Deactivate on rejection as well
        if hasattr(self.agent_factory, "release_linguist"):
            self.agent_factory.release_linguist(source.id)

    def _persist_source_state(self, source: DataSource):
        """Safely updates and persists the source state in the domain repository."""
        if hasattr(self.app_state, "notify_source_updated"):
            self.app_state.notify_source_updated(source)
        elif hasattr(self.app_state, "sources"):
            if hasattr(self.app_state.sources, "notify_source_updated"):
                self.app_state.sources.notify_source_updated(source)
            else:
                if hasattr(self.app_state.sources, "source_added"):
                    self.app_state.sources.source_added.emit(source)
                if hasattr(self.app_state.sources, "save"):
                    self.app_state.sources.save()

    def _find_candidate_edges(self, source: DataSource) -> List[MapEdge]:
        """
        Locates candidate MapEdges for directional reconciliation.
        Checks associated element, metadata (edge_id, element_id, street_id),
        and discovers opposing edges (e.g. -edge_id or reversed endpoints).
        """
        if not self.app_state:
            return []

        candidates: List[MapEdge] = []
        element_id = None

        # 1. Direct association in repository or app_state
        if hasattr(self.app_state, "get_element_for_source"):
            raw = self.app_state.get_element_for_source(source.id)
            if isinstance(raw, str) and raw:
                element_id = raw
        elif hasattr(self.app_state, "sources") and hasattr(self.app_state.sources, "get_element_for_source"):
            raw = self.app_state.sources.get_element_for_source(source.id)
            if isinstance(raw, str) and raw:
                element_id = raw

        # 2. Check metadata
        if not element_id and source.metadata:
            element_id = (
                source.metadata.get("edge_id")
                or source.metadata.get("element_id")
                or source.metadata.get("street_id")
                or source.metadata.get("road_id")
            )

        get_edge_fn = getattr(self.app_state, "get_edge", None)
        all_edges: List[MapEdge] = []
        if hasattr(self.app_state, "get_all_edges"):
            try:
                all_edges = self.app_state.get_all_edges() or []
            except Exception:
                all_edges = []

        if element_id:
            primary_edge = None
            if get_edge_fn:
                try:
                    primary_edge = get_edge_fn(str(element_id))
                except Exception:
                    primary_edge = None
            if not primary_edge:
                for e in all_edges:
                    if getattr(e, "id", None) == str(element_id):
                        primary_edge = e
                        break

            if primary_edge:
                candidates.append(primary_edge)
                # Search for opposite direction edge
                opp_id = f"-{primary_edge.id}" if not primary_edge.id.startswith("-") else primary_edge.id[1:]
                opp_edge = None
                if get_edge_fn:
                    try:
                        opp_edge = get_edge_fn(opp_id)
                    except Exception:
                        opp_edge = None
                if not opp_edge:
                    for e in all_edges:
                        if getattr(e, "id", None) == opp_id:
                            opp_edge = e
                            break
                        if (
                            getattr(e, "from_node", None) == primary_edge.to_node
                            and getattr(e, "to_node", None) == primary_edge.from_node
                            and getattr(e, "id", None) != primary_edge.id
                        ):
                            opp_edge = e
                            break
                if opp_edge and opp_edge.id not in [c.id for c in candidates]:
                    candidates.append(opp_edge)
                return candidates

        # 3. If element_id was a node or not an edge, check edges connected to it
        if element_id:
            for e in all_edges:
                if getattr(e, "from_node", None) == str(element_id) or getattr(e, "to_node", None) == str(element_id):
                    if e not in candidates:
                        candidates.append(e)
            if candidates:
                return candidates

        # 4. Fallback: if coordinates (lat, lon) or (x, y) in metadata, find closest edge
        if source.metadata:
            pos_x = source.metadata.get("x") or source.metadata.get("lon") or source.metadata.get("longitude")
            pos_y = source.metadata.get("y") or source.metadata.get("lat") or source.metadata.get("latitude")
            if pos_x is not None and pos_y is not None and all_edges:
                try:
                    px, py = float(pos_x), float(pos_y)

                    def edge_dist(e: MapEdge) -> float:
                        shape = getattr(e, "shape", None)
                        if shape:
                            mx = sum(p[0] for p in shape) / len(shape)
                            my = sum(p[1] for p in shape) / len(shape)
                            return math.hypot(px - mx, py - my)
                        return float("inf")

                    sorted_edges = sorted(all_edges, key=edge_dist)
                    if sorted_edges:
                        closest = sorted_edges[0]
                        candidates.append(closest)
                        opp_id = f"-{closest.id}" if not closest.id.startswith("-") else closest.id[1:]
                        for e in all_edges:
                            if getattr(e, "id", None) == opp_id or (
                                getattr(e, "from_node", None) == closest.to_node
                                and getattr(e, "to_node", None) == closest.from_node
                                and getattr(e, "id", None) != closest.id
                            ):
                                candidates.append(e)
                                break
                        return candidates
                except Exception as e:
                    logger.debug(f"[Linguist] Erro ao buscar edges por proximidade: {e}")

        return candidates

