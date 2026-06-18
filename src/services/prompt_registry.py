# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# File: src/services/prompt_registry.py
# Author: Gabriel Moraes
# Date: 2026-04-26

import os
import re
import json
from typing import Dict, List


class PromptRegistry:
    """
    Single Responsibility: Load and resolve multilingual prompt templates
    for the Jurist Agent (XAI / Legal Compliance) directly from JSON resources.
    
    Separates prompt engineering from LLM lifecycle and inference logic.
    """

    _CACHE = {}

    @classmethod
    def _load_template(cls, language: str) -> Dict[str, str]:
        """Loads a Jurist prompt template from JSON, caching it in memory."""
        lang_key = cls._resolve_language(language)
        
        if lang_key in cls._CACHE:
            return cls._CACHE[lang_key]

        # Resolve path to src/templates/jurist_{lang_key}.json
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, "templates", f"jurist_{lang_key}.json")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                template = json.load(f)
                cls._CACHE[lang_key] = template
                return template
        except Exception as e:
            # Fallback to PT-BR if file doesn't exist
            print(f"[PromptRegistry] Warning: Could not load {file_path}: {e}")
            if lang_key != "pt_br":
                return cls._load_template("pt_br")
            
            # Absolute worst-case fallback
            return {
                "system": "Você é o Agente Jurista do sistema SYNAPSE. Sua função é analisar dados técnicos de tráfego e emitir laudos explicativos baseados no Código de Trânsito Brasileiro (CTB). Seja técnico, direto e jurídico. Justifique as decisões da IA com base nos vetores fornecidos.\\nIMPORTANTE: Você DEVE primeiro pensar passo-a-passo usando tags <think> e </think>, e em seguida fornecer sua resposta final.",
                "user": "Relatório de Incidente:\\n- Fonte: {source}\\n- Estado Detectado: {status}\\n- Dados Numéricos: {values}\\n\\nAnalise este cenário. Se houver anomalia, cite o artigo do CTB aplicável e sugira a ação de controle."
            }

    @classmethod
    def build_messages(cls, source: str, status: str, values: list, language: str = "pt_BR") -> List[Dict[str, str]]:
        """
        Builds the chat messages for the Jurist LLM.
        
        Args:
            source: Sensor/source identifier.
            status: Detected state (NORMAL, DRIFT, ATTACK, etc).
            values: Numerical data payload.
            language: Target language code.
            
        Returns:
            List of message dicts [{role, content}, ...] ready for tokenization.
        """
        template = cls._load_template(language)

        return [
            {"role": "system", "content": template.get("system", "")},
            {"role": "user", "content": template.get("user", "").format(
                source=source, status=status, values=values
            )}
        ]

    @staticmethod
    def clean_response(response: str) -> str:
        """
        Removes CoT thinking tags from LLM output.
        
        Handles:
        - Complete <think>...</think> blocks
        - Unclosed <think> tags (truncated output)
        """
        # Remove complete think blocks
        cleaned = re.sub(r'(?s)<think>.*?</think>', '', response).strip()

        # Handle unclosed think tags
        if '<think>' in cleaned:
            parts = cleaned.split('</think>', 1)
            if len(parts) > 1:
                cleaned = parts[1].strip()
            else:
                cleaned = cleaned.replace('<think>', '').strip()

        return cleaned

    @staticmethod
    def _resolve_language(language: str) -> str:
        """Maps language codes to template keys."""
        lang = language.lower()
        if 'en' in lang:
            return 'en'
        elif 'fr' in lang:
            return 'fr'
        elif 'es' in lang:
            return 'es'
        elif 'ru' in lang:
            return 'ru'
        elif 'zh' in lang:
            return 'zh'
        return 'pt_br'
