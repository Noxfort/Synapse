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
# File: tests/unit/test_compass_knowledge_transfer.py
# Author: Gabriel Moraes
# Date: 2026-09-05

import pytest
import numpy as np
import torch
from unittest.mock import MagicMock

from src.agents.specialist_agent import SpecialistAgent
from src.services.knowledge_transfer_service import KnowledgeTransferService


def test_specialist_agent_set_orientation():
    """Verifies that SpecialistAgent records orientation vector, target edge ID, and channel key."""
    # Mock pipeline and trainer to avoid loading real models
    mock_pipeline = MagicMock()
    mock_pipeline.model = {"tcn": MagicMock()}
    mock_trainer = MagicMock()

    agent = SpecialistAgent(pipeline=mock_pipeline, trainer=mock_trainer)
    assert agent.orientation_vector is None
    assert agent.target_edge_id is None
    assert agent.channel_key is None

    agent.set_orientation(vector=(0.707, 0.707), edge_id="edge_42", channel_key="lane_inbound")
    assert agent.orientation_vector == (0.707, 0.707)
    assert agent.target_edge_id == "edge_42"
    assert agent.channel_key == "lane_inbound"


def test_knowledge_transfer_with_orientation_data():
    """Verifies that KnowledgeTransferService passes orientation_data to SpecialistAgent."""
    transfer_service = KnowledgeTransferService()

    mock_linguist = MagicMock()
    mock_encoder = MagicMock()
    mock_encoder.state_dict.return_value = {"weight": torch.tensor([1.0, 2.0])}
    mock_linguist.model.ae.encoder = mock_encoder

    mock_specialist = MagicMock(spec=SpecialistAgent)
    mock_specialist.tcn = MagicMock()
    mock_specialist.predict.return_value = np.zeros((32,))

    orientation_data = {
        "orientation": "IDA",
        "primary_edge_id": "edge_paulista_centro",
        "secondary_edge_id": None,
        "channels": {"cam_feed": "edge_paulista_centro"},
        "vector": (1.0, 0.0),
        "confidence": 0.98,
        "method": "semantic_neural_reconciliation"
    }

    success = transfer_service.transfer(
        source_agent=mock_linguist,
        target_agent=mock_specialist,
        data_series=np.array([10.0, 20.0, 30.0], dtype=np.float32),
        semantic_type="Vehicle Count",
        unit="vehicles",
        orientation_data=orientation_data
    )

    assert success is True
    mock_specialist.set_orientation.assert_called_once_with(
        vector=(1.0, 0.0),
        edge_id="edge_paulista_centro",
        channel_key="cam_feed"
    )
