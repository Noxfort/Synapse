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
# File: src/services/knowledge_transfer_service.py
# Author: Gabriel Moraes
# Date: 2026-08-20

from typing import Any, Optional, Dict
import numpy as np
import logging
from src.interfaces.quarantine import IKnowledgeTransfer

logger = logging.getLogger("Synapse.Services.KnowledgeTransferService")


class KnowledgeTransferService(IKnowledgeTransfer):
    """
    Encapsulates MLOps neural representation, weight transfer, and TCN teaching/warmup
    between the LinguistAgent (Learner) and the SpecialistAgent (Tactical Real-Time Converter).
    """

    def transfer(
        self,
        source_agent: Any,
        target_agent: Any,
        data_series: Optional[np.ndarray] = None,
        extractor: Optional[Any] = None,
        semantic_type: Optional[str] = None,
        unit: Optional[str] = None,
        orientation_data: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> bool:
        """
        Transfers learned representations from source_agent and teaches/calibrates target_agent (TCN).
        
        Args:
            source_agent: Trained LinguistAgent containing the learned feature encoder.
            target_agent: SpecialistAgent whose TCN will convert real-time data for the graph.
            data_series: Optional extracted 1D time-series used to warmup and calibrate the TCN filters.
            extractor: Optional SeriesExtractorPipeline attached to the Specialist for autonomous parsing.
            semantic_type: Modality string ("Vehicle Count", "Vehicle Speed", etc.).
            unit: Engineering unit ("vehicles", "km/h", etc.).
            orientation_data: Optional directional decision dictionary produced by CompassAgent.
            
        Returns:
            bool: True if transfer and TCN initialization succeeded, False otherwise.
        """
        try:
            # 1. Weight Transfer (Encoder -> TCN)
            encoder_state = self._extract_encoder_state(source_agent)
            if encoder_state is not None:
                self._load_encoder_state(target_agent, encoder_state)
                logger.info("✅ [KnowledgeTransfer] Transferência de pesos neurais do Encoder para TCN realizada.")
            else:
                logger.info("ℹ️ [KnowledgeTransfer] Especialista inicializado com pesos nativos.")

            # 2. Attach Extractor & Modality to enable autonomous real-time conversion
            if hasattr(target_agent, "set_extractor") and extractor is not None:
                target_agent.set_extractor(extractor, semantic_type=semantic_type, unit=unit)
                logger.info(f"🔗 [KnowledgeTransfer] Extrator autônomo e modalidade '{semantic_type}' [{unit}] vinculados à TCN Local.")

            # 2b. Attach Directional Orientation taught by the CompassAgent
            if hasattr(target_agent, "set_orientation") and orientation_data is not None:
                vec = orientation_data.get("vector")
                edge_id = orientation_data.get("primary_edge_id")
                channels = orientation_data.get("channels", {})
                ch_key = next(iter(channels.keys())) if channels else None
                target_agent.set_orientation(vector=vec, edge_id=edge_id, channel_key=ch_key)
                logger.info(f"🧭 [KnowledgeTransfer] Orientação vetorial {vec} e aresta '{edge_id}' vinculadas ao Especialista.")

            # 3. TCN Warmup & Calibration (The "Teaching" Phase)
            if data_series is not None and len(data_series) > 0:
                self._warmup_specialist_tcn(target_agent, data_series)

            return True
        except Exception as e:
            logger.error(f"⚠️ [KnowledgeTransfer] Falha na transferência/calibração: {e}. O especialista continuará do zero.")
            return False

    def _warmup_specialist_tcn(self, target_agent: Any, data_series: np.ndarray):
        """Runs a forward prediction pass to calibrate TCN batch norms and embedding dimensions."""
        try:
            if hasattr(target_agent, "predict"):
                embedding = target_agent.predict(data_series)
                logger.info(f"🎓 [KnowledgeTransfer] TCN calibrada com sucesso. Dimensão do embedding: {getattr(embedding, 'shape', len(embedding))}")
        except Exception as e:
            logger.debug(f"[KnowledgeTransfer] TCN warmup pass notice: {e}")

    def _extract_encoder_state(self, source_agent: Any) -> Optional[dict]:
        """Safely retrieves state_dict from source agent encoder."""
        model = getattr(source_agent, "model", None)
        if model is not None:
            ae = getattr(model, "ae", None)
            if ae is not None:
                encoder = getattr(ae, "encoder", None)
                if encoder is not None and hasattr(encoder, "state_dict"):
                    return encoder.state_dict()
                if hasattr(ae, "state_dict"):
                    return ae.state_dict()
            if hasattr(model, "state_dict"):
                return model.state_dict()

        if hasattr(source_agent, "get_encoder_state_dict"):
            return source_agent.get_encoder_state_dict()

        return None

    def _load_encoder_state(self, target_agent: Any, state_dict: dict):
        """Safely loads state_dict into target agent."""
        tcn = getattr(target_agent, "tcn", None)
        if tcn is not None and hasattr(tcn, "load_state_dict"):
            tcn.load_state_dict(state_dict, strict=False)
            return

        if hasattr(target_agent, "load_encoder_state"):
            target_agent.load_encoder_state(state_dict)
            return

        model = getattr(target_agent, "model", None)
        if model is not None and hasattr(model, "load_state_dict"):
            model.load_state_dict(state_dict, strict=False)
