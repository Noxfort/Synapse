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
# File: tests/unit/test_response_sanitizer.py
# Author: Gabriel Moraes
# Date: 2026-08-29

import pytest
from src.services.response_sanitizer import ResponseSanitizer
from src.interfaces.prompts import IResponseSanitizer


@pytest.fixture
def sanitizer():
    return ResponseSanitizer()


def test_implements_protocol(sanitizer):
    assert isinstance(sanitizer, IResponseSanitizer)


def test_empty_response(sanitizer):
    assert sanitizer.clean("") == ""
    assert sanitizer.clean(None) == ""


def test_clean_think_tags(sanitizer):
    raw = "<think>Step-by-step reasoning</think>Final answer."
    assert sanitizer.clean(raw) == "Final answer."


def test_clean_multiline_think_tags(sanitizer):
    raw = "<think>\nLine 1\nLine 2\n</think>\n\nVerdict rendered."
    assert sanitizer.clean(raw) == "Verdict rendered."


def test_clean_unclosed_think_tag(sanitizer):
    raw = "<think>Thinking until cutoff... Partial verdict"
    cleaned = sanitizer.clean(raw)
    assert "Partial verdict" in cleaned
    assert "<think>" not in cleaned


def test_clean_with_custom_callbacks(sanitizer):
    raw = "<think>reasoning</think> [FLAG_RED] Critical error."
    cleaned = sanitizer.clean(
        raw,
        cleaners=[lambda text: text.replace("[FLAG_RED]", "ALERT:")]
    )
    assert cleaned == "ALERT: Critical error."
