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
# File: tests/unit/test_compass_pipeline.py
# Author: Gabriel Moraes
# Date: 2026-09-05

import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from src.domain.entities import DataSource, SourceType, SourceStatus, MapEdge
from src.pipeline.compass_pipeline import CompassPipeline
from src.agents.compass_agent import CompassAgent
from src.factories.compass_factory import CompassFactory
from src.factories.agent_factory import AgentFactory


@pytest.fixture
def sample_edges():
    """Provides two opposing edges representing a two-way street."""
    # Edge A: West to East (shape: (0, 0) -> (100, 0)) -> Centro
    edge_a = MapEdge(
        id="edge_centro",
        from_node="node_west",
        to_node="node_centro",
        shape=[(0.0, 0.0), (100.0, 0.0)],
        real_name="Avenida Brasil Sentido Centro",
        weight=1.0,
        length=100.0,
        lanes=2
    )
    # Edge B: East to West (shape: (100, 0) -> (0, 0)) -> Bairro
    edge_b = MapEdge(
        id="-edge_centro",
        from_node="node_centro",
        to_node="node_bairro",
        shape=[(100.0, 0.0), (0.0, 0.0)],
        real_name="Avenida Brasil Sentido Bairro",
        weight=1.0,
        length=100.0,
        lanes=2
    )
    return [edge_a, edge_b]


def test_compass_pipeline_no_candidates():
    """Verifies that empty candidates list returns INDETERMINADO."""
    pipeline = CompassPipeline(confidence_threshold=0.6)
    source = DataSource(id="s1", name="Sensor 1", source_type=SourceType.API)

    result = pipeline.orient_and_reconcile(source, candidate_edges=[])
    assert result["orientation"] == "INDETERMINADO"
    assert result["primary_edge_id"] is None
    assert result["confidence"] == 0.0
    assert result["method"] == "no_candidates"


def test_compass_pipeline_fast_path_one_way(sample_edges):
    """Verifies O(1) fast-path when street is one-way (single candidate edge)."""
    pipeline = CompassPipeline(confidence_threshold=0.6)
    source = DataSource(id="s1", name="Camera Rua Direita", source_type=SourceType.API)

    result = pipeline.orient_and_reconcile(source, candidate_edges=[sample_edges[0]])
    assert result["orientation"] == "IDA"
    assert result["primary_edge_id"] == "edge_centro"
    assert result["confidence"] == 1.0
    assert result["method"] == "single_edge_fast"
    # Vector should be pointing East: (1.0, 0.0)
    assert pytest.approx(result["vector"][0], rel=1e-3) == 1.0
    assert pytest.approx(result["vector"][1], abs=1e-3) == 0.0


def test_compass_pipeline_multichannel_metadata(sample_edges):
    """Verifies that multichannel sensor with metadata channels is split across opposing edges."""
    pipeline = CompassPipeline(confidence_threshold=0.6)
    source = DataSource(
        id="s_radar",
        name="Radar Portal Bidirecional",
        source_type=SourceType.API,
        metadata={"channels": {"pista_ida": "cam1", "pista_volta": "cam2"}}
    )

    result = pipeline.orient_and_reconcile(source, candidate_edges=sample_edges)
    assert result["orientation"] == "DUPLO"
    assert result["primary_edge_id"] == "edge_centro"
    assert result["secondary_edge_id"] == "-edge_centro"
    assert "pista_ida" in result["channels"]
    assert "pista_volta" in result["channels"]
    assert result["method"] == "multichannel_metadata_split"


def test_compass_pipeline_multichannel_payload(sample_edges):
    """Verifies that sensor payload with dual keys (inbound/outbound) triggers DUPLO orientation."""
    pipeline = CompassPipeline(confidence_threshold=0.6)
    source = DataSource(id="s_gantry", name="Pórtico Rodoviário", source_type=SourceType.API)
    data_chunk = [
        {"inbound": 45, "outbound": 38, "timestamp": 1700000000},
        {"inbound": 42, "outbound": 40, "timestamp": 1700000001}
    ]

    result = pipeline.orient_and_reconcile(source, candidate_edges=sample_edges, data_chunk=data_chunk)
    assert result["orientation"] == "DUPLO"
    assert result["primary_edge_id"] == "edge_centro"
    assert result["secondary_edge_id"] == "-edge_centro"
    assert result["channels"]["inbound"] == "edge_centro"
    assert result["channels"]["outbound"] == "-edge_centro"
    assert result["method"] == "multichannel_payload_split"


def test_compass_pipeline_two_way_disambiguation_keywords(sample_edges):
    """Verifies disambiguation between opposing directions using semantic keywords."""
    pipeline = CompassPipeline(confidence_threshold=0.6)

    # Sensor referencing "centro"
    src_centro = DataSource(
        id="s_c",
        name="Radar Av Brasil - Acesso Centro",
        source_type=SourceType.API
    )
    res_c = pipeline.orient_and_reconcile(src_centro, candidate_edges=sample_edges)
    assert res_c["orientation"] == "IDA"
    assert res_c["primary_edge_id"] == "edge_centro"

    # Sensor referencing "bairro"
    src_bairro = DataSource(
        id="s_b",
        name="Radar Av Brasil - Retorno Bairro",
        source_type=SourceType.API
    )
    res_b = pipeline.orient_and_reconcile(src_bairro, candidate_edges=sample_edges)
    assert res_b["orientation"] == "VOLTA"
    assert res_b["primary_edge_id"] == "-edge_centro"


def test_compass_pipeline_two_way_bearing(sample_edges):
    """Verifies that geometric bearing aligns sensor with the correct edge vector."""
    pipeline = CompassPipeline(confidence_threshold=0.6)

    # Angle 0 degrees = East (1.0, 0.0) -> edge_centro
    src_east = DataSource(
        id="s_east",
        name="Sensor Direcional",
        source_type=SourceType.API,
        metadata={"bearing": 0.0}
    )
    res_east = pipeline.orient_and_reconcile(src_east, candidate_edges=sample_edges)
    assert res_east["primary_edge_id"] == "edge_centro"

    # Angle 180 degrees = West (-1.0, 0.0) -> -edge_centro
    src_west = DataSource(
        id="s_west",
        name="Sensor Direcional",
        source_type=SourceType.API,
        metadata={"bearing": 180.0}
    )
    res_west = pipeline.orient_and_reconcile(src_west, candidate_edges=sample_edges)
    assert res_west["primary_edge_id"] == "-edge_centro"


def test_compass_agent_inference_delegation(sample_edges):
    """Verifies that CompassAgent conforms to BaseAgent and delegates to pipeline."""
    mock_pipeline = MagicMock()
    mock_pipeline.orient_and_reconcile.return_value = {
        "orientation": "IDA",
        "primary_edge_id": "edge_centro",
        "confidence": 0.99,
        "method": "mock"
    }

    agent = CompassAgent(pipeline=mock_pipeline)
    source = DataSource(id="s1", name="Cam", source_type=SourceType.API)

    # Via unified BaseAgent inference
    out = agent.inference({"source": source, "candidate_edges": sample_edges})
    assert out["orientation"] == "IDA"
    assert out["primary_edge_id"] == "edge_centro"
    mock_pipeline.orient_and_reconcile.assert_called_once()


def test_compass_factory_and_agent_factory_lifecycle(sample_edges):
    """Verifies CompassFactory creation and AgentFactory get/release lifecycle."""
    agent = CompassFactory.create()
    assert isinstance(agent, CompassAgent)

    factory = AgentFactory(config={})
    compass = factory.get_or_create_compass("sensor_abc")
    assert isinstance(compass, CompassAgent)

    # Verify singleton retrieval for same source
    compass_same = factory.get_or_create_compass("sensor_abc")
    assert compass is compass_same

    # Release from memory
    factory.release_compass("sensor_abc")
    assert factory.registry.get("sensor_abc", "compass") is None
