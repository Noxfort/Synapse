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
# File: src/services/xai_reporter_service.py
# Author: Gabriel Moraes
# Date: 2026-08-31

from typing import Any, Dict, List, Optional

from src.interfaces.xai import IXAIReporter, IXAIStrategy
from src.agents.jurist_agent import JuristAgent
from src.utils.logging_setup import get_logger

logger = get_logger("XAI.ReporterService")


class XAIReporterService(IXAIReporter):
    """
    Semantic Reporting Service for XAI.
    Manages Jurist on-demand SLM lifecycle and provides seamless fallback to model strategy reports.
    Single-process and zero-VRAM-leakage architecture.
    """

    def __init__(self, jurist: Optional[JuristAgent] = None, auto_load_jurist: bool = True):
        self._jurist = jurist
        self._auto_load_jurist = auto_load_jurist

    @property
    def jurist(self) -> Optional[JuristAgent]:
        return self._jurist

    def _ensure_jurist_ready(self) -> None:
        """Ensures Jurist Agent instance is ready for on-demand dispatch."""
        if self._jurist is None and self._auto_load_jurist:
            try:
                self._jurist = JuristAgent()
            except Exception as e:
                logger.error(f"Failed to instantiate JuristAgent: {e}", exc_info=True)
                self._jurist = None

    def generate_report(
        self,
        target: str,
        attr_list: List[float],
        feature_names: List[str],
        timestamp: str,
        delta: float,
        strategy: Optional[IXAIStrategy] = None
    ) -> str:
        """
        Generates human-readable semantic interpretation text.
        Delegates to Jurist on-demand SLM if available, with immediate fallback to strategy reports.
        """
        self._ensure_jurist_ready()

        resolved_names = feature_names if feature_names else [f"F{i}" for i in range(len(attr_list))]
        attribution_map = dict(zip(resolved_names, attr_list))
        sig_map = {k: v for k, v in attribution_map.items() if abs(v) > 0.001}
        if not sig_map:
            sig_map = attribution_map

        if self._jurist is not None:
            try:
                report_text = self._jurist.generate_report(
                    tensor_data=sig_map,
                    timestamp=timestamp,
                    locale="pt_BR",
                    target=target,
                    auto_unload=True
                )
                if report_text and not report_text.startswith("Erro:"):
                    return report_text
                else:
                    logger.warning(f"Jurist returned error or empty text: '{report_text}'. Triggering strategy fallback.")
            except Exception as e_gen:
                logger.error(f"Jurist Generation Error: {e_gen}", exc_info=True)

        # Resilient fallback to mathematical/domain strategy template
        if strategy:
            return strategy.generate_fallback_text(
                delta=delta,
                sig_map=sig_map,
                attr_list=attr_list
            )

        return (
            f"Análise XAI ({target}): Concluída com delta {delta:.4f} em {len(attr_list)} features."
        )

    def unload_resources(self) -> None:
        """Releases Jurist SLM VRAM."""
        if self._jurist is not None:
            logger.info("Unloading Jurist SLM resources from ReporterService.")
            try:
                self._jurist.unload_resources()
            except Exception as e:
                logger.warning(f"Error unloading Jurist resources: {e}")
            finally:
                self._jurist = None
