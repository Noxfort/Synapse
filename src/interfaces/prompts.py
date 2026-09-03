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
# File: src/interfaces/prompts.py
# Author: Gabriel Moraes
# Date: 2026-08-29

from typing import Dict, List, Optional, Any, Callable, Protocol, runtime_checkable


@runtime_checkable
class ITemplateLoader(Protocol):
    """Contract for discovering, resolving, loading, caching, and registering prompt templates."""

    def register_language(self, alias: str, canonical_code: str) -> None:
        """Extends supported languages at runtime."""
        ...

    def register_template(self, template_name: str, language: str, template: Dict[str, str]) -> None:
        """Registers an in-memory template."""
        ...

    def register_fallback(self, template_name: str, fallback_template: Dict[str, str]) -> None:
        """Registers a domain-specific fallback template."""
        ...

    def clear_cache(self) -> None:
        """Clears all in-memory cached templates."""
        ...

    def resolve_language(self, language: str) -> str:
        """Maps language aliases to canonical template keys."""
        ...

    def load_template(
        self,
        template_name: str = "jurist",
        language: str = "pt_BR",
        custom_dir: Optional[str] = None
    ) -> Dict[str, str]:
        """Loads and returns template dictionary containing system and user prompts."""
        ...


@runtime_checkable
class IPromptBuilder(Protocol):
    """Contract for formatting dynamic prompt context into LLM chat messages."""

    def build_messages(
        self,
        template: Dict[str, str],
        source: Optional[str] = None,
        status: Optional[str] = None,
        values: Optional[Any] = None,
        **kwargs: Any
    ) -> List[Dict[str, str]]:
        """Interpolates variables into template strings and constructs chat message list."""
        ...


@runtime_checkable
class IResponseSanitizer(Protocol):
    """Contract for cleaning and sanitizing LLM text responses."""

    def clean(self, response: str, cleaners: Optional[List[Callable[[str], str]]] = None) -> str:
        """Removes Chain-of-Thought tags and applies custom cleaner filters."""
        ...


__all__ = [
    "ITemplateLoader",
    "IPromptBuilder",
    "IResponseSanitizer",
]
