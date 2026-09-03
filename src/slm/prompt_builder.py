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
# File: src/slm/prompt_builder.py
# Author: Gabriel Moraes
# Date: 2026-09-03

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from src.utils.logging_setup import get_logger

logger = get_logger("SLM.PromptBuilder")


class SLMPromptBuilder:
    """
    Constructs chat-template formatted prompts for Qwen / GGUF models from input payload
    and loads system instruction databases from JSON (src/prompts/slm_prompts.json).
    Tailored specifically to SYNAPSE's Zero-Trust Perception & Traffic Architecture:
    - AUDITOR_XAI: Zero-Trust sensor verification and physics-informed loss (PINN).
    - LOCAL_TCN_XAI: Temporal convolution and timestep predictive attribution (TCN).
    - GLOBAL_FUSION_XAI: Spatial corridor graph attention and flow propagation (GATv2).
    - JURIST_OFFICIAL_REPORT: Brazilian Traffic Code (CTB) & metrological reliability audit.
    """

    @staticmethod
    def load_prompts_db() -> Dict[str, Any]:
        """Loads system prompt database from src/prompts/slm_prompts.json."""
        prompts_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "slm_prompts.json")
        try:
            with open(prompts_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[SLMPromptBuilder] Could not load slm_prompts.json from {prompts_file}: {e}")
            return {}

    @staticmethod
    def _resolve_mode(input_data: Dict[str, Any]) -> str:
        """Resolves the canonical prompt key from target or mode."""
        mode = input_data.get("mode", "")
        if mode in ("AUDITOR_XAI", "LOCAL_TCN_XAI", "GLOBAL_FUSION_XAI", "JURIST_OFFICIAL_REPORT", "XAI_EXPLANATION"):
            return mode

        target = str(input_data.get("target", "")).lower()
        if any(k in target for k in ("auditor", "zero_trust", "pinn", "spectral")):
            return "AUDITOR_XAI"
        if any(k in target for k in ("tcn", "local", "temporal", "specialist")):
            return "LOCAL_TCN_XAI"
        if any(k in target for k in ("fuser", "global", "spatial", "coordinator", "gat")):
            return "GLOBAL_FUSION_XAI"
        if any(k in target for k in ("jurist", "official", "report", "laudo")):
            return "JURIST_OFFICIAL_REPORT"

        return mode or "XAI_EXPLANATION"

    @staticmethod
    def build_chat_messages(input_data: Dict[str, Any], prompts_db: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        """
        Constructs system and user chat messages for LLM inference using the JSON prompt database.
        """
        if prompts_db is None:
            prompts_db = SLMPromptBuilder.load_prompts_db()

        timestamp = input_data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        mode = SLMPromptBuilder._resolve_mode(input_data)
        raw_language = str(input_data.get("language", "pt_br")).lower()

        lang_key = raw_language.split("_")[0].split("-")[0]
        if lang_key == "pt":
            lang_key = "pt_br"

        attributions = input_data.get("attributions", {})
        speed_unit = input_data.get("speed_unit")
        if not speed_unit and isinstance(attributions, dict):
            speed_unit = attributions.get("speed_unit")

        mode_prompts = prompts_db.get(mode, {})
        instruction = mode_prompts.get(
            lang_key,
            mode_prompts.get(
                raw_language,
                mode_prompts.get(
                    "pt_br",
                    mode_prompts.get("en", "Você atua como um Perito Auditor e Engenheiro de Tráfego do sistema SYNAPSE.")
                )
            )
        )

        sub_mode = input_data.get("sub_mode", "")
        if sub_mode and sub_mode in prompts_db:
            sub_prompts = prompts_db.get(sub_mode, {})
            if lang_key in sub_prompts:
                instruction = sub_prompts[lang_key]

        # Build user prompt string with structured data
        input_str = f"TIMESTAMP: [{timestamp}]\nMODE: [{mode}]\nLANGUAGE: [{raw_language}]\n"
        input_str += f"IMPORTANT DIRECTIVE: Write the report text entirely and exclusively in the requested language [{raw_language}]. Strictly forbid answering in English unless LANGUAGE is en.\n"

        target = input_data.get("target")
        if target:
            input_str += f"TARGET_SUBSYSTEM: [{target}]\n"

        if speed_unit:
            input_str += f"SPEED_UNIT: [{speed_unit}]\n"

        if isinstance(attributions, dict):
            input_str += f"DATA_PAYLOAD: {json.dumps(attributions, ensure_ascii=False)}"
        else:
            input_str += f"DATA_PAYLOAD: {str(attributions)}"

        last_report = input_data.get("last_report_text")
        if last_report:
            if len(last_report) > 4000:
                last_report = "... " + last_report[-4000:]
            input_str += f"\nLAST_REPORT_TEXT: {last_report}"

        messages = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": input_str}
        ]

        return messages

    @staticmethod
    def build_xai_chat_messages(
        target: str,
        attribution_map: Dict[str, Any],
        timestamp: str = "",
        locale: str = "pt_BR"
    ) -> List[Dict[str, str]]:
        """
        Convenience wrapper building chat messages for XAI attribution explanation using JSON prompts.
        Automatically maps the target subsystem ('auditor', 'local'/'tcn', 'global'/'fuser', 'jurist')
        to the respective specialized SYNAPSE prompt.
        """
        input_data = {
            "target": target,
            "language": locale,
            "timestamp": timestamp,
            "attributions": attribution_map
        }
        return SLMPromptBuilder.build_chat_messages(input_data)
