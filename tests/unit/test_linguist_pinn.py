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
# File: tests/unit/test_linguist_pinn.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import pytest
import torch
import numpy as np
from unittest.mock import MagicMock, patch

from src.models.neuro_symbolic import NeuroSymbolicModel
from src.agents.linguist_agent import LinguistAgent
from src.services.linguist_service import LinguistService
from src.pipeline.series_extractor_pipeline import SeriesExtractorPipeline
from src.services.semantic_classifier import SemanticClassifier
from src.physics.sensor_physical_validator import SensorPhysicalValidator
from src.physics.traffic_loss import TrafficPhysicsLoss
from src.services.knowledge_transfer_service import KnowledgeTransferService
from src.domain.app_state import AppState
from src.domain.entities import DataSource, SourceType, SourceStatus, MapEdge


def test_neuro_symbolic_pinn_residuals():
    """Verifies that NeuroSymbolicModel computes differentiable PINN residuals."""
    with patch("src.models.neuro_symbolic.AutoModel.from_pretrained") as MockAutoModel, \
         patch("src.models.neuro_symbolic.AutoConfig.from_pretrained") as MockAutoConfig:

        mock_config = MagicMock()
        mock_config.hidden_size = 64
        MockAutoConfig.return_value = mock_config

        mock_transformer = MagicMock()
        mock_output = MagicMock()
        mock_output.last_hidden_state = torch.randn(2, 5, 64)
        mock_transformer.return_value = mock_output
        MockAutoModel.return_value = mock_transformer

        model = NeuroSymbolicModel(model_name="mock-model", freeze_transformer=True, latent_dim=32)

        input_ids = torch.randint(0, 1000, (2, 5))
        attention_mask = torch.ones((2, 5))

        recon, orig, residuals = model(input_ids, attention_mask, semantic_type="Vehicle Speed")

        assert recon.shape == (2, 5, 64)
        assert orig.shape == (2, 5, 64)
        assert "loss_bounds" in residuals
        assert "loss_kinematics" in residuals
        assert "loss_conservation" in residuals
        assert "total_physics_loss" in residuals
        assert residuals["total_physics_loss"].item() >= 0.0


def test_linguist_agent_train_and_inference_pinn():
    """Verifies that LinguistAgent trains with local convergence loop and runs inference."""
    with patch("src.agents.linguist_agent.AutoTokenizer.from_pretrained") as MockTokenizer, \
         patch("src.models.neuro_symbolic.AutoModel.from_pretrained") as MockAutoModel, \
         patch("src.models.neuro_symbolic.AutoConfig.from_pretrained") as MockAutoConfig:

        mock_config = MagicMock()
        mock_config.hidden_size = 64
        MockAutoConfig.return_value = mock_config

        mock_transformer = MagicMock()
        mock_output = MagicMock()
        mock_output.last_hidden_state = torch.randn(1, 5, 64)
        mock_transformer.return_value = mock_output
        MockAutoModel.return_value = mock_transformer

        mock_tok_inst = MockTokenizer.return_value
        mock_tok_inst.return_value = {
            "input_ids": torch.randint(0, 1000, (1, 5)),
            "attention_mask": torch.ones((1, 5))
        }

        agent = LinguistAgent(model_name="mock-model")

        # Train step with numerical batch and modality
        batch = [10.0, 12.0, 14.0, 15.0, 16.0]
        loss = agent.train_step(batch, epochs=5, semantic_type="Vehicle Speed")
        assert isinstance(loss, float)
        assert loss >= 0.0

        # Inference with modality conditioning
        result = agent.inference({"text": "Speed is 50 km/h, flow is 1200 veh/h"}, semantic_type="Vehicle Speed")
        assert "is_valid" in result
        assert "physics_residual" in result
        assert "error_score" in result


def test_series_extractor_camera_detections_and_timestamps():
    """Verifies that SeriesExtractorPipeline extracts vehicle detection counts and ignores IDs/timestamps."""
    extractor = SeriesExtractorPipeline()

    camera_payloads = [
        {
            "packet_id": "100825",
            "sensor_id": "cam_01",
            "timestamp": 1787196563800,
            "detections": [
                {"track_id": 1, "class": "car"},
                {"track_id": 2, "class": "bus"},
                {"track_id": 3, "class": "car"}
            ]
        },
        {
            "packet_id": "100827",
            "sensor_id": "cam_01",
            "timestamp": 1787196564800,
            "detections": [
                {"track_id": 1, "class": "car"}
            ]
        }
    ]

    arr = extractor.extract(camera_payloads)
    assert len(arr) == 2
    # Must be the vehicle counts (3 and 1), and NEVER packet_id (100825)!
    assert arr[0] == pytest.approx(3.0)
    assert arr[1] == pytest.approx(1.0)


def test_series_extractor_tomtom_nested():
    """Verifies that SeriesExtractorPipeline extracts currentSpeed from nested flowSegmentData."""
    extractor = SeriesExtractorPipeline()

    tomtom_payload = [{
        "flowSegmentData": {
            "segmentId": "seg_01",
            "currentSpeed": 48.5,
            "freeFlowSpeed": 60.0,
            "currentTravelTime": 120
        }
    }]

    arr = extractor.extract(tomtom_payload)
    assert len(arr) == 1
    assert arr[0] == pytest.approx(48.5)


def test_semantic_classifier_camera_and_tomtom():
    """Verifies that SemanticClassifier identifies Camera as Vehicle Count and TomTom as Vehicle Speed."""
    classifier = SemanticClassifier()

    cam_src = DataSource(id="src_camera_1", name="Camera", source_type=SourceType.API, is_local=True)
    cam_chunk = [{"packet_id": "100", "detections": [{"track_id": 1}]}]
    sem_type, unit, conf = classifier.classify(cam_src, np.array([1.0]), cam_chunk)
    assert sem_type == "Vehicle Count"
    assert unit == "vehicles"
    assert conf >= 0.9

    tomtom_src = DataSource(id="src_tom_tom_1", name="Tom Tom", source_type=SourceType.API, is_local=False)
    tomtom_chunk = [{"flowSegmentData": {"currentSpeed": 50.0}}]
    sem_type, unit, conf = classifier.classify(tomtom_src, np.array([50.0]), tomtom_chunk)
    assert sem_type == "Vehicle Speed"
    assert unit == "km/h"


def test_modality_conditioned_physics_loss():
    """Verifies that TrafficPhysicsLoss conditions residuals based on modality."""
    loss_engine = TrafficPhysicsLoss()
    state = torch.tensor([[[10.0, 12.0, 15.0]]])

    loss_count = loss_engine.compute_losses(state, semantic_type="Vehicle Count")
    assert "total_physics_loss" in loss_count
    assert loss_count["loss_conservation"].item() == 0.0

    loss_speed = loss_engine.compute_losses(state, semantic_type="Vehicle Speed")
    assert "loss_kinematics" in loss_speed


def test_sensor_physical_validator_modality():
    """Verifies that SensorPhysicalValidator validates counts and speeds appropriately."""
    validator = SensorPhysicalValidator()
    src_cam = DataSource(id="c1", name="Camera 1", source_type=SourceType.API, is_local=True)

    # Valid discrete count (0 to 10 cars)
    assert validator.validate(src_cam, np.array([0.0, 3.0, 2.0, 0.0])) is True

    # Negative count is rejected
    assert validator.validate(src_cam, np.array([-1.0, 2.0])) is False

    # Exorbitant count (> 500 cars per frame) is rejected
    assert validator.validate(src_cam, np.array([999.0])) is False


def test_knowledge_transfer_service_with_warmup():
    """Verifies that KnowledgeTransferService transfers encoder weights and warms up TCN."""
    transfer_service = KnowledgeTransferService()

    mock_linguist = MagicMock()
    mock_encoder = MagicMock()
    mock_state = {"weight": torch.tensor([1.0, 2.0])}
    mock_encoder.state_dict.return_value = mock_state
    mock_linguist.model.ae.encoder = mock_encoder

    mock_specialist = MagicMock()
    mock_specialist.tcn = MagicMock()
    mock_specialist.predict.return_value = np.zeros((32,))

    series = np.array([10.0, 12.0, 14.0, 15.0, 16.0], dtype=np.float32)
    success = transfer_service.transfer(mock_linguist, mock_specialist, data_series=series)

    assert success is True
    mock_specialist.tcn.load_state_dict.assert_called_once_with(mock_state, strict=False)
    mock_specialist.predict.assert_called_once()


def test_linguist_service_promotes_camera_with_detections():
    """Verifies that LinguistService successfully promotes camera payload with detections and teaches TCN."""
    app_state = MagicMock(spec=AppState)
    ingestion = MagicMock()
    pipeline = MagicMock()
    ingestion.get_pipeline.return_value = pipeline
    agent_factory = MagicMock()

    src = DataSource(id="src_cam_1", name="Camera Av Paulista", source_type=SourceType.API, is_local=True, status=SourceStatus.QUARANTINE)
    app_state.get_all_data_sources.return_value = [src]

    # Buffer contains 5 camera packets with packet_id and detections
    pipeline.has_enough_data.return_value = True
    pipeline.get_quarantine_data.return_value = [
        {"packet_id": "101", "sensor_id": "cam_01", "detections": [{"id": 1}, {"id": 2}]},
        {"packet_id": "102", "sensor_id": "cam_01", "detections": [{"id": 1}, {"id": 2}, {"id": 3}]},
        {"packet_id": "103", "sensor_id": "cam_01", "detections": [{"id": 1}]},
        {"packet_id": "104", "sensor_id": "cam_01", "detections": [{"id": 1}, {"id": 2}]},
        {"packet_id": "105", "sensor_id": "cam_01", "detections": [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]}
    ]

    mock_linguist = MagicMock()
    mock_linguist.train_step.return_value = 0.02
    mock_linguist.inference.return_value = {"is_valid": True, "is_anomaly": False, "physics_residual": 0.01}
    agent_factory.get_or_create_linguist.return_value = mock_linguist

    mock_specialist = MagicMock()
    agent_factory.get_or_create_specialist.return_value = mock_specialist

    service = LinguistService(app_state, ingestion, agent_factory)
    service.run_check()

    assert src.status == SourceStatus.ACTIVE
    assert src.semantic_type == "Vehicle Count"
    assert src.inferred_unit == "vehicles"
    pipeline.promote_to_active.assert_called_once_with("src_cam_1")
    agent_factory.release_linguist.assert_called_once_with("src_cam_1")


def test_linguist_service_promotes_tomtom_feed():
    """Verifies that LinguistService promotes nested TomTom speed feed and releases linguist."""
    app_state = MagicMock(spec=AppState)
    ingestion = MagicMock()
    pipeline = MagicMock()
    ingestion.get_pipeline.return_value = pipeline
    agent_factory = MagicMock()

    src = DataSource(id="src_tomtom_1", name="Tom Tom", source_type=SourceType.API, is_local=False, status=SourceStatus.QUARANTINE)
    app_state.get_all_data_sources.return_value = [src]

    pipeline.has_enough_data.return_value = True
    pipeline.get_quarantine_data.return_value = [
        {"flowSegmentData": {"segmentId": "seg_1", "currentSpeed": 45.0}},
        {"flowSegmentData": {"segmentId": "seg_1", "currentSpeed": 46.0}},
        {"flowSegmentData": {"segmentId": "seg_1", "currentSpeed": 44.0}},
        {"flowSegmentData": {"segmentId": "seg_1", "currentSpeed": 48.0}},
        {"flowSegmentData": {"segmentId": "seg_1", "currentSpeed": 45.0}}
    ]

    mock_linguist = MagicMock()
    mock_linguist.train_step.return_value = 0.02
    mock_linguist.inference.return_value = {"is_valid": True, "is_anomaly": False, "physics_residual": 0.01}
    agent_factory.get_or_create_linguist.return_value = mock_linguist
    agent_factory.get_or_create_specialist.return_value = MagicMock()

    service = LinguistService(app_state, ingestion, agent_factory)
    service.run_check()

    assert src.status == SourceStatus.ACTIVE
    assert src.semantic_type == "Vehicle Speed"
    assert src.inferred_unit == "km/h"
    pipeline.promote_to_active.assert_called_once_with("src_tomtom_1")
    agent_factory.release_linguist.assert_called_once_with("src_tomtom_1")


def test_specialist_agent_autonomous_raw_packet_inference():
    """Verifies that SpecialistAgent with attached extractor processes raw sensor packets autonomously."""
    from src.agents.specialist_agent import SpecialistAgent
    specialist = SpecialistAgent()
    extractor = SeriesExtractorPipeline()

    specialist.set_extractor(extractor, semantic_type="Vehicle Count", unit="vehicles")

    raw_packets = [
        {"packet_id": "100", "detections": [{"id": 1}, {"id": 2}]},
        {"packet_id": "101", "detections": [{"id": 1}, {"id": 2}, {"id": 3}]},
        {"packet_id": "102", "detections": [{"id": 1}]},
        {"packet_id": "103", "detections": [{"id": 1}, {"id": 2}]},
        {"packet_id": "104", "detections": [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]}
    ]

    # Specialist processes raw packets directly without external parsing
    embedding = specialist.inference(raw_packets)

    assert isinstance(embedding, np.ndarray)
    assert len(embedding) == 32
    assert specialist.semantic_type == "Vehicle Count"
    assert specialist.inferred_unit == "vehicles"


def test_sensor_physical_validator_dynamic_topology():
    """Verifies that SensorPhysicalValidator adapts flow thresholds according to road lanes."""
    app_state = MagicMock(spec=AppState)
    validator = SensorPhysicalValidator(app_state=app_state)

    # Edge 1: Residential 1-lane street (Max capacity: 1 * 2400 * 1.25 = 3000 veh/h)
    edge_1lane = MapEdge(id="edge_res", from_node="n1", to_node="n2", shape=[], lanes=1, max_speed=13.89)
    # Edge 2: 5-lane Highway / Marginal (Max capacity: 5 * 2400 * 1.25 = 15000 veh/h)
    edge_5lanes = MapEdge(id="edge_hwy", from_node="n3", to_node="n4", shape=[], lanes=5, max_speed=25.0)

    src_res = DataSource(id="src_flow_res", name="Radar Rua Residencial", source_type=SourceType.API)
    src_hwy = DataSource(id="src_flow_hwy", name="Radar Marginal Tietê", source_type=SourceType.API)

    app_state.get_element_for_source.side_effect = lambda sid: "edge_res" if sid == "src_flow_res" else "edge_hwy"
    app_state.get_edge.side_effect = lambda eid: edge_1lane if eid == "edge_res" else edge_5lanes

    # 4500 veh/h is physically impossible for a 1-lane residential street -> Rejected
    assert validator.validate(src_res, np.array([4500.0]), [{"flow": 4500.0}]) is False

    # 4500 veh/h is completely normal on a 5-lane highway -> Accepted
    assert validator.validate(src_hwy, np.array([4500.0]), [{"flow": 4500.0}]) is True


def test_sensor_physical_validator_dynamic_speed_limit():
    """Verifies that SensorPhysicalValidator respects posted edge max speed with reasonable overrun."""
    app_state = MagicMock(spec=AppState)
    validator = SensorPhysicalValidator(app_state=app_state)

    # Edge with 50 km/h (13.89 m/s) -> 35% overrun allows up to ~67.5 km/h
    edge_50 = MapEdge(id="edge_50", from_node="n1", to_node="n2", shape=[], lanes=2, max_speed=13.89)
    src_speed = DataSource(id="src_spd", name="Radar Av Paulista", source_type=SourceType.API)

    app_state.get_element_for_source.return_value = "edge_50"
    app_state.get_edge.return_value = edge_50

    # 60 km/h on a 50 km/h street (within 35% overrun) -> Accepted
    assert validator.validate(src_speed, np.array([60.0]), [{"speed": 60.0}]) is True

    # 130 km/h on a 50 km/h urban street -> Rejected
    assert validator.validate(src_speed, np.array([130.0]), [{"speed": 130.0}]) is False


def test_sensor_physical_validator_dynamic_delta_time_counts():
    """Verifies that vehicle count threshold dynamically scales with sampling dt."""
    validator = SensorPhysicalValidator()
    src = DataSource(id="cam_sp", name="Camera SP", source_type=SourceType.API)

    # In 1 second window (dt=1.0s), 200 vehicles in a single frame is physically impossible -> Rejected
    chunk_1s = [{"time": 100.0, "count": 200}, {"time": 101.0, "count": 200}]
    assert validator.validate(src, np.array([200.0]), chunk_1s) is False

    # In 5 minutes window (dt=300.0s), 200 vehicles aggregate is realistic -> Accepted
    chunk_5m = [{"time": 100.0, "count": 200}, {"time": 400.0, "count": 200}]
    assert validator.validate(src, np.array([200.0]), chunk_5m) is True


def test_sensor_physical_validator_offpeak_empty_street():
    """Verifies that quiet streets at night with 0 vehicles are NOT falsely flagged as dead sensors."""
    validator = SensorPhysicalValidator()
    src_cam = DataSource(id="cam_empty", name="Camera Madrugada", source_type=SourceType.API)

    # 20 samples of 0 cars (empty street at 3 AM) -> Must be True
    empty_series = np.zeros(20, dtype=np.float32)
    assert validator.validate(src_cam, empty_series) is True


def test_sensor_physical_validator_kinematic_acceleration_rejection():
    """Verifies that impossible vehicle acceleration jumps are caught and rejected."""
    validator = SensorPhysicalValidator()
    src_speed = DataSource(id="radar_accel", name="Radar Speed", source_type=SourceType.API)

    # Speed jumping from 10 km/h to 100 km/h in 0.5s -> ~50 m/s^2 accel (F1/Rocket impossible) -> Rejected
    chunk = [{"time": 10.0, "speed": 10.0}, {"time": 10.5, "speed": 100.0}]
    telemetry = np.array([10.0, 100.0])
    assert validator.validate(src_speed, telemetry, chunk) is False

