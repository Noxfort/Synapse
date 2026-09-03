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
# File: src/services/prompt_registry.py
# Author: Gabriel Moraes
# Date: 2026-04-26

import logging
from typing import Dict, List, Optional, Any, Callable

# --- Interfaces (DIP / ISP) ---
from src.interfaces.prompts import (
    ITemplateLoader,
    IPromptBuilder,
    IResponseSanitizer,
)

# --- Concrete Sub-services (SRP) ---
from src.services.template_loader import JSONTemplateLoader
from src.services.prompt_formatter import ChatPromptBuilder, _SafeFormatter
from src.services.response_sanitizer import ResponseSanitizer

logger = logging.getLogger("PromptRegistry")


class PromptRegistry:
    """
    Pure Orchestrator & Unified Facade for SYNAPSE Prompt Engineering Subsystem.
    
    SOLID Architecture:
    - [SRP] Orchestrates the prompt lifecycle by delegating specialized operations:
            - ITemplateLoader: I/O, directory discovery, language resolution, caching.
            - IPromptBuilder: Template variable interpolation and chat message construction.
            - IResponseSanitizer: LLM response post-processing and reasoning tag stripping.
    - [OCP] Open for new template sources (DB/Redis) or custom sanitizers without modifying this class.
    - [LSP] Any sub-service implementing ITemplateLoader, IPromptBuilder, or IResponseSanitizer can be substituted.
    - [ISP] Independent interfaces allow clients to consume only the sub-services they need.
    - [DIP] Relies on abstract Protocols and supports Dependency Injection.
    """

    # Shared default strategy components
    _default_loader: ITemplateLoader = JSONTemplateLoader()
    _default_builder: IPromptBuilder = ChatPromptBuilder()
    _default_sanitizer: IResponseSanitizer = ResponseSanitizer()

    def __init__(
        self,
        loader: Optional[ITemplateLoader] = None,
        builder: Optional[IPromptBuilder] = None,
        sanitizer: Optional[IResponseSanitizer] = None,
    ):
        """
        Initializes an instance-based PromptRegistry with optional dependency injection.
        """
        self.loader: ITemplateLoader = loader or JSONTemplateLoader()
        self.builder: IPromptBuilder = builder or ChatPromptBuilder()
        self.sanitizer: IResponseSanitizer = sanitizer or ResponseSanitizer()

    # =========================================================================
    # EXTENSION & LOADER APIS (Delegated to ITemplateLoader)
    # =========================================================================

    @classmethod
    def register_language(cls, alias: str, canonical_code: str) -> None:
        """Extends supported languages without modifying the codebase (OCP)."""
        cls._default_loader.register_language(alias, canonical_code)

    @classmethod
    def register_template(cls, template_name: str, language: str, template: Dict[str, str]) -> None:
        """Registers an in-memory template for an agent or domain."""
        cls._default_loader.register_template(template_name, language, template)

    @classmethod
    def register_fallback(cls, template_name: str, fallback_template: Dict[str, str]) -> None:
        """Registers a domain fallback template when JSON files cannot be found."""
        cls._default_loader.register_fallback(template_name, fallback_template)

    @classmethod
    def clear_cache(cls) -> None:
        """Clears all cached in-memory templates."""
        cls._default_loader.clear_cache()

    @classmethod
    def _resolve_language(cls, language: str) -> str:
        """Maps arbitrary language codes or locale strings to canonical template keys."""
        return cls._default_loader.resolve_language(language)

    @classmethod
    def _get_prompt_dirs(cls, custom_dir: Optional[str] = None) -> List[str]:
        """Returns candidate directories containing prompt JSON templates."""
        if hasattr(cls._default_loader, "get_prompt_dirs"):
            return cls._default_loader.get_prompt_dirs(custom_dir)
        return []

    @classmethod
    def load_template(
        cls,
        template_name: str = "jurist",
        language: str = "pt_BR",
        custom_dir: Optional[str] = None
    ) -> Dict[str, str]:
        """Loads a prompt template from memory cache or JSON resource files."""
        return cls._default_loader.load_template(
            template_name=template_name,
            language=language,
            custom_dir=custom_dir
        )

    @classmethod
    def _load_template(cls, language: str = "pt_BR", template_name: str = "jurist") -> Dict[str, str]:
        """Backward-compatible method for legacy internal calls."""
        return cls.load_template(template_name=template_name, language=language)

    # =========================================================================
    # MESSAGE BUILDING & FORMATTING (Delegated to IPromptBuilder)
    # =========================================================================

    @classmethod
    def build_messages(
        cls,
        source: Optional[str] = None,
        status: Optional[str] = None,
        values: Optional[Any] = None,
        language: str = "pt_BR",
        template_name: str = "jurist",
        **kwargs: Any
    ) -> List[Dict[str, str]]:
        """
        Builds and formats chat messages for an LLM agent.
        
        Loads the template via the configured ITemplateLoader and formats
        the chat payload via IPromptBuilder.
        """
        template = cls.load_template(template_name=template_name, language=language)
        return cls._default_builder.build_messages(
            template=template,
            source=source,
            status=status,
            values=values,
            **kwargs
        )

    # =========================================================================
    # RESPONSE CLEANING & POST-PROCESSING (Delegated to IResponseSanitizer)
    # =========================================================================

    @classmethod
    def clean_response(cls, response: str, cleaners: Optional[List[Callable[[str], str]]] = None) -> str:
        """
        Cleans and sanitizes LLM output (removes <think> tags, applies custom filters).
        """
        return cls._default_sanitizer.clean(response, cleaners)


__all__ = [
    "_SafeFormatter",
    "PromptRegistry",
]
