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
# File: src/services/response_sanitizer.py
# Author: Gabriel Moraes
# Date: 2026-08-29

import re
from typing import List, Optional, Callable
from src.interfaces.prompts import IResponseSanitizer


class ResponseSanitizer(IResponseSanitizer):
    """
    Sanitizer and post-processing service for LLM responses.
    
    Responsibilities (SRP):
    - Strip Chain-of-Thought reasoning tags (<think>...</think>).
    - Safely handle unclosed or truncated reasoning tags.
    - Apply custom post-processing filter pipelines.
    """

    def clean(self, response: str, cleaners: Optional[List[Callable[[str], str]]] = None) -> str:
        """
        Cleans and sanitizes LLM output text.
        
        Args:
            response: Raw LLM output string.
            cleaners: Optional list of post-processing filter functions: f(text) -> text.
            
        Returns:
            Cleaned response string.
        """
        if not response:
            return ""

        # Remove complete think blocks
        cleaned = re.sub(r'(?s)<think>.*?</think>', '', response).strip()

        # Handle unclosed think tags (e.g. truncated LLM generation)
        if '<think>' in cleaned:
            parts = cleaned.split('</think>', 1)
            if len(parts) > 1:
                cleaned = parts[1].strip()
            else:
                cleaned = cleaned.replace('<think>', '').strip()

        if cleaners:
            for cleaner in cleaners:
                cleaned = cleaner(cleaned)

        return cleaned
