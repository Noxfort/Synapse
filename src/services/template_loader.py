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
# File: src/services/template_loader.py
# Author: Gabriel Moraes
# Date: 2026-08-29

import os
import json
import logging
from typing import Dict, List, Optional
from src.interfaces.prompts import ITemplateLoader

logger = logging.getLogger("TemplateLoader")


class JSONTemplateLoader(ITemplateLoader):
    """
    Template loader and caching service for JSON prompt templates.
    
    Responsibilities (SRP):
    - Discover prompt directories and read JSON templates from disk.
    - Resolve language codes and locale aliases into canonical suffixes.
    - Cache loaded templates in memory for low latency.
    - Manage fallback templates when specific locales or files are missing.
    """

    DEFAULT_LANGUAGE_ALIASES: Dict[str, str] = {
        "pt": "pt_br",
        "pt_br": "pt_br",
        "pt-br": "pt_br",
        "portuguese": "pt_br",
        "en": "en",
        "en_us": "en",
        "en-us": "en",
        "english": "en",
        "es": "es",
        "es_es": "es",
        "es-es": "es",
        "spanish": "es",
        "fr": "fr",
        "fr_fr": "fr",
        "fr-fr": "fr",
        "french": "fr",
        "ru": "ru",
        "ru_ru": "ru",
        "russian": "ru",
        "zh": "zh",
        "zh_cn": "zh",
        "zh-cn": "zh",
        "chinese": "zh",
    }

    def __init__(self, custom_dirs: Optional[List[str]] = None):
        self._cache: Dict[str, Dict[str, str]] = {}
        self._language_aliases: Dict[str, str] = dict(self.DEFAULT_LANGUAGE_ALIASES)
        self._fallbacks: Dict[str, Dict[str, str]] = {}
        self._custom_dirs = custom_dirs or []

    def get_prompt_dirs(self, custom_dir: Optional[str] = None) -> List[str]:
        """Returns candidate directories containing prompt JSON templates in priority order."""
        if custom_dir:
            return [custom_dir]
        if self._custom_dirs:
            return self._custom_dirs
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return [
            os.path.join(base_dir, "prompts"),
            os.path.join(base_dir, "prompt"),
            os.path.join(base_dir, "templates"),
        ]

    def register_language(self, alias: str, canonical_code: str) -> None:
        """Extends supported languages without modifying the codebase (OCP)."""
        self._language_aliases[alias.lower().strip()] = canonical_code.lower().strip()

    def register_template(self, template_name: str, language: str, template: Dict[str, str]) -> None:
        """Registers an in-memory template for an agent or domain."""
        lang_key = self.resolve_language(language)
        cache_key = f"{template_name.lower().strip()}:{lang_key}"
        self._cache[cache_key] = template

    def register_fallback(self, template_name: str, fallback_template: Dict[str, str]) -> None:
        """Registers a domain fallback template when JSON files cannot be found."""
        self._fallbacks[template_name.lower().strip()] = fallback_template

    def clear_cache(self) -> None:
        """Clears all cached in-memory templates."""
        self._cache.clear()

    def resolve_language(self, language: str) -> str:
        """Maps arbitrary language codes or locale strings to canonical template keys."""
        if not language or not isinstance(language, str):
            return "pt_br"

        lang = language.lower().strip()

        # Direct match in alias map
        if lang in self._language_aliases:
            return self._language_aliases[lang]

        # Primary subtag match (e.g. 'en_US' -> 'en')
        prefix = lang.replace("-", "_").split("_")[0]
        if prefix in self._language_aliases:
            return self._language_aliases[prefix]

        # Substring search
        for key, target in self._language_aliases.items():
            if key in lang:
                return target

        return "pt_br"

    def _resolve_language(self, language: str) -> str:
        """Alias for backward compatibility."""
        return self.resolve_language(language)

    def load_template(
        self,
        template_name: str = "jurist",
        language: str = "pt_BR",
        custom_dir: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Loads a prompt template from memory cache or JSON resource files.
        """
        domain = template_name.lower().strip()
        lang_key = self.resolve_language(language)
        cache_key = f"{domain}:{lang_key}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        candidate_dirs = self.get_prompt_dirs(custom_dir)
        filename = f"{domain}_{lang_key}.json"

        for directory in candidate_dirs:
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        template = json.load(f)
                        self._cache[cache_key] = template
                        return template
                except Exception as e:
                    logger.warning(f"Could not read prompt template {file_path}: {e}")

        # 1. Fallback to default PT-BR file for this domain if not already requested
        if lang_key != "pt_br":
            try:
                return self.load_template(domain, "pt_br", custom_dir=custom_dir)
            except Exception:
                pass

        # 2. Fallback to registered in-memory domain fallback
        if domain in self._fallbacks:
            return self._fallbacks[domain]

        # 3. Generic fallback
        return {
            "system": f"You are an intelligent agent for SYNAPSE. Domain: {domain}.",
            "user": "{input}"
        }
