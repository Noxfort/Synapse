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
# File: tests/unit/test_memory_structures.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import pytest
import torch
import numpy as np

from src.memory.temporal_memory import TemporalMemory
from src.memory.spatial_memory import SpatialMemory
from src.memory.spatiotemporal_memory import SpatioTemporalMemory
from src.memory.episodic_memory import EpisodicMemory, AnomalyMemory
from src.memory.semantic_memory import SemanticMemory
from src.memory.topology_memory import TopologyMemory


class TestTemporalMemory:
    def test_temporal_memory_basic_and_rollback(self):
        mem = TemporalMemory(feature_dim=2, max_len=5)
        assert not mem.is_ready()
        
        for i in range(5):
            mem.push([float(i), float(i * 2)])
            
        assert mem.is_ready()
        tensor = mem.get_tensor()
        assert tensor.shape == (1, 5, 2)
        
        # Test rollback
        mem.rollback(2)
        assert len(mem) == 3
        assert not mem.is_ready()


class TestSpatialMemory:
    def test_spatial_memory_update_and_missing(self):
        node_ids = ["node_A", "node_B", "node_C"]
        mem = SpatialMemory(node_ids=node_ids, feature_dim=4)
        
        assert len(mem.get_missing_nodes()) == 3
        
        mem.update_node("node_A", [1.0, 2.0, 3.0, 4.0])
        tensor = mem.get_node_features_tensor()
        
        assert tensor.shape == (3, 4)
        assert "node_A" not in mem.get_missing_nodes()
        assert len(mem.get_missing_nodes()) == 2


class TestSpatioTemporalMemory:
    def test_spatiotemporal_memory_multi_node_and_observability(self):
        nodes = ["sensor_1", "sensor_2", "sensor_3"]
        mem = SpatioTemporalMemory(node_ids=nodes, feature_dim=2, max_len=10)
        
        assert not mem.is_warmed_up()
        
        # Update only sensor_1 and sensor_2
        for t in range(10):
            mem.update_node("sensor_1", [10.0 + t, 20.0 + t])
            mem.update_node("sensor_2", [30.0 + t, 40.0 + t])
            
        assert not mem.is_warmed_up(min_fraction=1.0)
        assert mem.is_warmed_up(min_fraction=0.6)
        
        # Check 4D tensor format [Batch=1, Num_Nodes=3, SeqLen=10, Features=2]
        tensor = mem.get_tensor(batch_first=True)
        assert tensor.shape == (1, 3, 10, 2)
        
        # Check spatial snapshot [Num_Nodes=3, Features=2]
        snapshot = mem.get_spatial_snapshot()
        assert snapshot.shape == (3, 2)
        assert snapshot[0, 0].item() == pytest.approx(19.0)
        assert snapshot[2, 0].item() == pytest.approx(0.0) # sensor_3 is inactive
        
        # Observability mask: sensor_1 and sensor_2 active, sensor_3 inactive
        mask = mem.get_observability_mask()
        assert mask.shape == (3,)
        assert mask[0].item() == 1.0
        assert mask[1].item() == 1.0
        assert mask[2].item() == 0.0


class TestEpisodicMemory:
    def test_episodic_memory_record_and_sample(self):
        mem = EpisodicMemory(capacity=10)
        
        for i in range(5):
            sig = np.random.randn(20)
            score = float(i) * 0.2
            residual = float(i) * 1.5
            mem.record_episode(
                sensor_id=f"sensor_{i}",
                signature=sig,
                anomaly_score=score,
                physics_residual=residual,
                metadata={"type": "speed_violation"}
            )
            
        assert len(mem) == 5
        
        batch = mem.sample_batch(batch_size=3)
        assert batch is not None
        signatures, scores = batch
        assert signatures.shape == (3, 20)
        assert scores.shape == (3,)
        
        hardest = mem.get_hardest_violations(top_k=2)
        assert len(hardest) == 2
        assert hardest[0].physics_residual >= hardest[1].physics_residual


class TestSemanticMemory:
    def test_semantic_memory_concept_and_similarity(self):
        mem = SemanticMemory()
        
        vec_congestion = torch.tensor([1.0, 0.0, 0.0])
        vec_accident = torch.tensor([0.0, 1.0, 0.0])
        
        mem.set_concept("Congestion", vec_congestion, example_texts=["heavy traffic", "slow flow"])
        mem.set_concept("Accident", vec_accident, example_texts=["crash", "collision"])
        
        assert len(mem) == 2
        assert len(mem.get_examples("Congestion")) == 2
        
        # Test query similar to Congestion
        query = torch.tensor([0.98, 0.02, 0.0])
        best_name, sim = mem.find_nearest_concept(query, threshold=0.80)
        
        assert best_name == "Congestion"
        assert sim >= 0.95
        
        # Test query not meeting threshold
        query_unrelated = torch.tensor([0.0, 0.0, 1.0])
        best_name_unrelated, sim_unrelated = mem.find_nearest_concept(query_unrelated, threshold=0.80)
        assert best_name_unrelated is None


class TestTopologyMemory:
    def test_topology_memory_coo_and_dynamic_closures(self):
        topo = TopologyMemory()
        
        # Corridor: 0 -> 1 -> 2
        topo.set_graph(num_nodes=3, edge_list=[(0, 1), (1, 2)], edge_weights=[1.0, 2.0])
        
        edge_index = topo.get_edge_index_tensor()
        weights = topo.get_edge_weights_tensor()
        
        assert edge_index.shape == (2, 2)
        assert weights.shape == (2,)
        assert weights[1].item() == 2.0
        
        # Simulate road closure: disable edge 1 -> 2
        assert topo.disable_edge(1, 2) is True
        
        active_edge_index = topo.get_edge_index_tensor()
        active_weights = topo.get_edge_weights_tensor()
        
        assert active_edge_index.shape == (2, 1)
        assert active_edge_index[0, 0].item() == 0
        assert active_edge_index[1, 0].item() == 1
        assert active_weights.shape == (1,)
        
        # Re-open edge
        topo.enable_edge(1, 2, weight=1.5)
        reopened_edge_index = topo.get_edge_index_tensor()
        assert reopened_edge_index.shape == (2, 2)
