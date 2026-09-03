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
# File: tests/unit/test_prompt_formatter.py
# Author: Gabriel Moraes
# Date: 2026-08-29

import pytest
from src.services.prompt_formatter import ChatPromptBuilder, _SafeFormatter
from src.interfaces.prompts import IPromptBuilder


@pytest.fixture
def builder():
    return ChatPromptBuilder()


def test_implements_protocol(builder):
    assert isinstance(builder, IPromptBuilder)


def test_safe_formatter_missing_key():
    formatter = _SafeFormatter({"present": "value"})
    template = "Var: {present}, Missing: {missing}"
    assert template.format_map(formatter) == "Var: value, Missing: {missing}"


def test_build_messages_with_kwargs(builder):
    template = {
        "system": "System for {role} on stream {stream_id}.",
        "user": "Data value: {value}."
    }
    messages = builder.build_messages(
        template,
        role="Auditor",
        stream_id="cam_01",
        value=42.5
    )
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "System for Auditor on stream cam_01."
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "Data value: 42.5."


def test_build_messages_legacy_parameters(builder):
    template = {
        "system": "System {source}",
        "user": "Status: {status}, Values: {values}"
    }
    messages = builder.build_messages(
        template,
        source="sensor_01",
        status="WARNING",
        values=[1, 2, 3]
    )
    assert len(messages) == 2
    assert messages[0]["content"] == "System sensor_01"
    assert "Status: WARNING" in messages[1]["content"]
    assert "Values: [1, 2, 3]" in messages[1]["content"]
