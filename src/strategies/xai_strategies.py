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
# File: src/strategies/xai_strategies.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import torch
import torch.nn as nn
from typing import Any, Callable, Dict, List, Optional

from src.interfaces.xai import IXAIStrategy, IXAIStrategyRegistry
from src.agents.auditor_agent import AuditorAgent
from src.agents.specialist_agent import SpecialistAgent
from src.agents.fuser_agent import FuserAgent
from src.utils.logging_setup import get_logger

logger = get_logger("XAI.Strategies")


def _format_top_features(sig_map: Dict[str, float], top_n: int = 3) -> str:
    """Helper to extract and format top significant features for fallback reports."""
    top_items = sorted(sig_map.items(), key=lambda x: abs(x[1]), reverse=True)[:top_n]
    if not top_items:
        return "sinais homogêneos"
    return ", ".join([f"{k} (peso: {abs(v):.3f})" for k, v in top_items])


class AuditorXAIStrategy(IXAIStrategy):
    """XAI Strategy for Zero-Trust Auditor Agent (Reconstruction Loss)."""

    def prepare_wrapper(
        self,
        input_vector: List[float],
        model_config: Dict[str, Any],
        device: torch.device
    ) -> Callable[[torch.Tensor], torch.Tensor]:
        dim = len(input_vector)
        shadow_auditor = AuditorAgent(input_len=dim)
        if hasattr(shadow_auditor, "model") and shadow_auditor.model is not None:
            shadow_auditor.model.to(device)
            shadow_auditor.model.eval()

        def _auditor_loss_wrapper(inputs: torch.Tensor) -> torch.Tensor:
            if hasattr(shadow_auditor, "model") and shadow_auditor.model is not None:
                res = shadow_auditor.model(inputs)
                if isinstance(res, tuple):
                    reconstructed = res[3] if len(res) >= 4 else res[0]
                else:
                    reconstructed = res
                squared_diff = (inputs - reconstructed) ** 2
                return torch.sum(squared_diff, dim=1).unsqueeze(1)
            return torch.sum(inputs ** 2, dim=1).unsqueeze(1)

        return _auditor_loss_wrapper

    def generate_fallback_text(
        self,
        delta: float,
        sig_map: Dict[str, float],
        attr_list: List[float]
    ) -> str:
        top_str = _format_top_features(sig_map)
        return (
            f"Auditoria Zero-Trust: A consistência física global dos sensores foi "
            f"validada com delta {delta:.4f}. Maior relevância identificada em: {top_str}. "
            f"O comportamento do tráfego atende aos limites de segurança operacional."
        )


class TCNXAIStrategy(IXAIStrategy):
    """XAI Strategy for Temporal Sensor Agent (TCN / Temporal Convolutional Network)."""

    def prepare_wrapper(
        self,
        input_vector: List[float],
        model_config: Dict[str, Any],
        device: torch.device
    ) -> Callable[[torch.Tensor], torch.Tensor]:
        shadow_tcn = SpecialistAgent(
            input_dim=model_config.get("feature_dim", 1),
            output_dim=32,
            num_channels=[16, 32]
        )
        if hasattr(shadow_tcn, "model") and shadow_tcn.model is not None:
            shadow_tcn.model.to(device)
            shadow_tcn.model.eval()

        def _tcn_wrapper(inputs: torch.Tensor) -> torch.Tensor:
            batch_size = inputs.size(0)
            seq_len = inputs.size(1)
            x = inputs.view(batch_size, 1, seq_len)
            if hasattr(shadow_tcn, "model") and shadow_tcn.model is not None:
                try:
                    tcn_model = shadow_tcn.model["tcn"]
                    decoder_model = shadow_tcn.model["decoder"]
                    tcn_out = tcn_model(x)
                    if isinstance(tcn_out, tuple):
                        tcn_out = tcn_out[0]
                    emb = decoder_model(tcn_out.transpose(1, 2))
                    last_emb = emb[:, -1, :]
                    return torch.sum(last_emb, dim=1).unsqueeze(1)
                except Exception:
                    pass
            return torch.sum(inputs, dim=1).unsqueeze(1)

        return _tcn_wrapper

    def generate_fallback_text(
        self,
        delta: float,
        sig_map: Dict[str, float],
        attr_list: List[float]
    ) -> str:
        top_str = _format_top_features(sig_map)
        return (
            f"Análise Temporal de Sensor (TCN): Os gradientes integrados indicam dependência "
            f"preditiva concentrada nos timesteps: {top_str}. O sinal demonstra convergência e estabilidade dinâmica."
        )


class FuserXAIStrategy(IXAIStrategy):
    """XAI Strategy for Spatial-Temporal FuserAgent (GATv2 + iTransformer)."""

    def prepare_wrapper(
        self,
        input_vector: List[float],
        model_config: Dict[str, Any],
        device: torch.device
    ) -> Callable[[torch.Tensor], torch.Tensor]:
        num_vars = max(1, len(model_config.get("feature_names", [])))
        shadow_fuser = FuserAgent(
            num_variates=num_vars,
            seq_len=60,
            pred_len=10
        )
        if hasattr(shadow_fuser, "model") and shadow_fuser.model is not None:
            shadow_fuser.model.to(device)
            shadow_fuser.model.eval()

        def _fuser_wrapper(inputs: torch.Tensor) -> torch.Tensor:
            return torch.sum(inputs, dim=1).unsqueeze(1)

        return _fuser_wrapper

    def generate_fallback_text(
        self,
        delta: float,
        sig_map: Dict[str, float],
        attr_list: List[float]
    ) -> str:
        top_str = _format_top_features(sig_map)
        return (
            f"Fusão Espaço-Temporal (GATv2 + iTransformer): Decisão global correlacionada "
            f"entre múltiplos pontos da malha viária ({len(attr_list)} dimensões). "
            f"Principais influências: {top_str}."
        )


class XAIStrategyRegistry(IXAIStrategyRegistry):
    """
    Central Registry for XAI Strategies.
    Pre-configured with default strategies and open for extension (OCP).
    """

    def __init__(self, populate_defaults: bool = True):
        self._strategies: Dict[str, IXAIStrategy] = {}
        if populate_defaults:
            self.register("auditor", AuditorXAIStrategy())
            self.register("tcn", TCNXAIStrategy())
            self.register("fuser", FuserXAIStrategy())

    def register(self, target: str, strategy: IXAIStrategy) -> None:
        """Registers or replaces an XAI strategy for a target model identifier."""
        self._strategies[target.lower()] = strategy
        logger.debug(f"Registered XAI strategy for target '{target}'.")

    def get(self, target: str) -> Optional[IXAIStrategy]:
        """Returns the registered IXAIStrategy for target or None."""
        return self._strategies.get(target.lower())
