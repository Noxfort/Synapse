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
# File: tests/unit/test_linguist_compass_integration.py
# Author: Gabriel Moraes
# Date: 2026-09-05

import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from src.domain.app_state import AppState
from src.domain.entities import DataSource, SourceType, SourceStatus, MapEdge
from src.services.linguist_service import LinguistService
from src.agents.compass_agent import CompassAgent


@pytest.fixture
def mock_app_state_and_edges():
    app_state = MagicMock(spec=AppState)
    edge_ida = MapEdge(
        id="edge_100",
        from_node="node_A",
        to_node="node_B",
        shape=[(0.0, 0.0), (50.0, 0.0)],
        real_name="Rua Central Sentido Leste"
    )
    edge_volta = MapEdge(
        id="-edge_100",
        from_node="node_B",
        to_node="node_A",
        shape=[(50.0, 0.0), (0.0, 0.0)],
        real_name="Rua Central Sentido Oeste"
    )
    app_state.get_edge.side_effect = lambda eid: edge_ida if eid == "edge_100" else (edge_volta if eid == "-edge_100" else None)
    app_state.get_all_edges.return_value = [edge_ida, edge_volta]
    app_state.sources = MagicMock()
    app_state.sources.associate = MagicMock()
    app_state.sources.get_element_for_source.return_value = "edge_100"
    return app_state, edge_ida, edge_volta


def test_find_candidate_edges_discovers_opposing_edge(mock_app_state_and_edges):
    """Verifies that _find_candidate_edges finds both primary and opposing edge."""
    app_state, edge_ida, edge_volta = mock_app_state_and_edges
    ingestion = MagicMock()
    agent_factory = MagicMock()

    service = LinguistService(app_state, ingestion, agent_factory)
    source = DataSource(id="src_1", name="Radar Teste", metadata={"edge_id": "edge_100"})

    candidates = service._find_candidate_edges(source)
    assert len(candidates) == 2
    assert candidates[0].id == "edge_100"
    assert candidates[1].id == "-edge_100"


def test_linguist_service_runs_compass_and_releases(mock_app_state_and_edges):
    """Verifies full quarantine cycle: Linguist validates physics, invokes Compass, associates, and releases Compass."""
    app_state, edge_ida, edge_volta = mock_app_state_and_edges
    ingestion = MagicMock()
    pipeline = MagicMock()
    ingestion.get_pipeline.return_value = pipeline
    agent_factory = MagicMock()

    source = DataSource(
        id="src_radar_paulista",
        name="Radar Paulista Sentido Leste",
        source_type=SourceType.API,
        is_local=True,
        status=SourceStatus.QUARANTINE,
        metadata={"edge_id": "edge_100"}
    )
    app_state.get_all_data_sources.return_value = [source]

    pipeline.has_enough_data.return_value = True
    pipeline.get_quarantine_data.return_value = [
        {"speed": 50.0, "timestamp": 1000},
        {"speed": 52.0, "timestamp": 1001},
        {"speed": 48.0, "timestamp": 1002},
        {"speed": 55.0, "timestamp": 1003},
        {"speed": 51.0, "timestamp": 1004}
    ]

    # Mock LinguistAgent
    mock_linguist = MagicMock()
    mock_linguist.train_step.return_value = 0.01  # Passes grammar
    mock_linguist.inference.return_value = {"is_valid": True, "is_anomaly": False, "physics_residual": 0.01}
    agent_factory.get_or_create_linguist.return_value = mock_linguist

    # Mock CompassAgent
    mock_compass = MagicMock(spec=CompassAgent)
    mock_compass.orient_and_reconcile.return_value = {
        "orientation": "IDA",
        "primary_edge_id": "edge_100",
        "secondary_edge_id": None,
        "channels": {},
        "confidence": 0.96,
        "vector": (1.0, 0.0),
        "method": "semantic_neural_reconciliation"
    }
    agent_factory.get_or_create_compass.return_value = mock_compass

    # Mock SpecialistAgent
    mock_specialist = MagicMock()
    agent_factory.get_or_create_specialist.return_value = mock_specialist

    service = LinguistService(app_state, ingestion, agent_factory)

    with patch.object(service.physics_validator, "validate", return_value=True), \
         patch.object(service.semantic_classifier, "classify", return_value=("Vehicle Speed", "km/h", 0.95)), \
         patch.object(service.series_extractor, "extract", return_value=np.array([50.0, 52.0, 48.0, 55.0, 51.0])):

        service.run_check()

    # 1. Compass orient_and_reconcile was invoked
    mock_compass.orient_and_reconcile.assert_called_once()

    # 2. Association recorded
    app_state.sources.associate.assert_called_with("src_radar_paulista", "edge_100")

    # 3. Source metadata enriched
    assert source.metadata["orientation"] == "IDA"
    assert source.metadata["orientation_vector"] == (1.0, 0.0)

    # 4. Ephemeral lifecycle: release_compass called in finally
    agent_factory.release_compass.assert_called_once_with("src_radar_paulista")

    # 5. Promoted to ACTIVE
    assert source.status == SourceStatus.ACTIVE
    pipeline.promote_to_active.assert_called_once_with("src_radar_paulista")
