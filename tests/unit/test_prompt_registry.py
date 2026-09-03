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
# File: tests/unit/test_prompt_registry.py
# Author: Gabriel Moraes
# Date: 2026-08-29

import pytest
from src.services.prompt_registry import PromptRegistry


@pytest.fixture(autouse=True)
def cleanup_registry():
    """Cleans up cache and custom registrations after each test."""
    PromptRegistry.clear_cache()
    yield
    PromptRegistry.clear_cache()


def test_language_resolution_standard():
    assert PromptRegistry._resolve_language("pt_BR") == "pt_br"
    assert PromptRegistry._resolve_language("pt-br") == "pt_br"
    assert PromptRegistry._resolve_language("pt") == "pt_br"
    assert PromptRegistry._resolve_language("en_US") == "en"
    assert PromptRegistry._resolve_language("en") == "en"
    assert PromptRegistry._resolve_language("es_ES") == "es"
    assert PromptRegistry._resolve_language("fr_FR") == "fr"
    assert PromptRegistry._resolve_language("ru_RU") == "ru"
    assert PromptRegistry._resolve_language("zh_CN") == "zh"
    # Unknown fallback
    assert PromptRegistry._resolve_language("unknown_lang") == "pt_br"


def test_language_registration_ocp_extension():
    """Verifies that new languages can be registered at runtime without code modification."""
    PromptRegistry.register_language("de", "de")
    PromptRegistry.register_language("de-de", "de")
    PromptRegistry.register_language("german", "de")

    assert PromptRegistry._resolve_language("de") == "de"
    assert PromptRegistry._resolve_language("de-DE") == "de"
    assert PromptRegistry._resolve_language("german") == "de"


def test_load_existing_jurist_templates():
    for lang in ["pt_BR", "en", "es", "fr", "ru", "zh"]:
        tmpl = PromptRegistry.load_template("jurist", language=lang)
        assert isinstance(tmpl, dict)
        assert "system" in tmpl
        assert "user" in tmpl
        assert len(tmpl["system"]) > 0
        assert len(tmpl["user"]) > 0


def test_prompt_directories_priority():
    dirs = PromptRegistry._get_prompt_dirs()
    assert len(dirs) >= 2
    assert any("prompts" in d for d in dirs)



def test_register_template_ocp_extension():
    """Verifies that new agent/domain templates can be registered dynamically."""
    custom_template = {
        "system": "You are the Auditor Agent. Threshold: {threshold}",
        "user": "Audit stream {stream_id} with drift score {drift_score}."
    }
    PromptRegistry.register_template("auditor", "en", custom_template)

    loaded = PromptRegistry.load_template("auditor", "en")
    assert loaded == custom_template

    messages = PromptRegistry.build_messages(
        template_name="auditor",
        language="en",
        threshold=0.85,
        stream_id="stream_42",
        drift_score=0.92
    )
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "Threshold: 0.85" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "stream_42" in messages[1]["content"]
    assert "0.92" in messages[1]["content"]


def test_register_fallback_ocp_extension():
    """Verifies domain-specific fallback registration."""
    fallback_tmpl = {
        "system": "Fallback system prompt for Corrector.",
        "user": "Correct sensor: {sensor}."
    }
    PromptRegistry.register_fallback("corrector", fallback_tmpl)

    # Request a non-existent language for non-existent file
    tmpl = PromptRegistry.load_template("corrector", language="non_existent_lang")
    assert tmpl == fallback_tmpl


def test_build_messages_backward_compatibility():
    """Verifies legacy positional/keyword parameters used by JuristAgent."""
    messages = PromptRegistry.build_messages(
        source="sensor_alpha",
        status="ATTACK",
        values=["v: 120", "f: 500"],
        language="pt_BR"
    )
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "Agente Jurista" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "sensor_alpha" in messages[1]["content"]
    assert "ATTACK" in messages[1]["content"]
    assert "['v: 120', 'f: 500']" in messages[1]["content"]


def test_safe_formatter_robustness():
    """Verifies missing template variables do not crash and extra variables are safely ignored."""
    custom_template = {
        "system": "System with {existing_var} and {missing_var}",
        "user": "User prompt"
    }
    PromptRegistry.register_template("test_safe", "pt_br", custom_template)

    messages = PromptRegistry.build_messages(
        template_name="test_safe",
        language="pt_BR",
        existing_var="FOUND",
        extra_unused_var="IGNORED"
    )
    assert "FOUND" in messages[0]["content"]
    assert "{missing_var}" in messages[0]["content"]


def test_clean_response_cot_tags():
    # Closed think tag
    raw = "<think>Analysing CTB article 218...</think>Infração média detectada."
    cleaned = PromptRegistry.clean_response(raw)
    assert cleaned == "Infração média detectada."

    # Multiline think tag
    raw_multiline = "<think>\nStep 1\nStep 2\n</think>\n\nLaudo emitido."
    cleaned_multiline = PromptRegistry.clean_response(raw_multiline)
    assert cleaned_multiline == "Laudo emitido."

    # Unclosed think tag (truncated generation)
    raw_unclosed = "<think>Thinking about data... Autuação confirmada."
    cleaned_unclosed = PromptRegistry.clean_response(raw_unclosed)
    assert cleaned_unclosed == "Thinking about data... Autuação confirmada." or "Autuação confirmada" in cleaned_unclosed


def test_clean_response_with_custom_cleaner():
    """Verifies custom post-processing filter callbacks."""
    raw = "<think>...</think> [REDACTED] Relatório final."
    cleaned = PromptRegistry.clean_response(
        raw,
        cleaners=[lambda text: text.replace("[REDACTED]", "CONFIDENTIAL")]
    )
    assert "CONFIDENTIAL Relatório final." in cleaned


def test_prompt_registry_custom_instance_di():
    """Verifies that PromptRegistry supports dependency injection of custom strategy components."""
    class CustomLoader:
        def load_template(self, template_name="jurist", language="pt_BR", custom_dir=None):
            return {"system": "Custom DI System", "user": "Custom DI User {x}"}
        def register_language(self, alias, canonical_code): pass
        def register_template(self, template_name, language, template): pass
        def register_fallback(self, template_name, fallback_template): pass
        def clear_cache(self): pass
        def resolve_language(self, language): return "pt_br"

    class CustomBuilder:
        def build_messages(self, template, **kwargs):
            return [{"role": "system", "content": "DI Formatted"}]

    class CustomSanitizer:
        def clean(self, response, cleaners=None):
            return "DI Sanitized: " + response

    registry = PromptRegistry(
        loader=CustomLoader(),
        builder=CustomBuilder(),
        sanitizer=CustomSanitizer()
    )

    template = registry.loader.load_template("test")
    assert template["system"] == "Custom DI System"

    messages = registry.builder.build_messages(template)
    assert messages[0]["content"] == "DI Formatted"

    cleaned = registry.sanitizer.clean("Raw response")
    assert cleaned == "DI Sanitized: Raw response"

