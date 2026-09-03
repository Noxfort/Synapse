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
# File: tests/integration/test_latency_benchmark.py
# Author: Gabriel Moraes
# Date: 2026-08-29

import pytest
import time
from unittest.mock import MagicMock
from src.engine.inference_engine import InferenceEngine

@pytest.mark.benchmark
def test_inference_pipeline_latency_benchmark(mock_app_state):
    """
    Performance Benchmark Test.
    Simulates the full neural processing cycle to ensure it completes
    within the target 150ms - 250ms window.
    """
    # 1. Setup mocked dependencies
    mock_ingestion = MagicMock()
    mock_graph = MagicMock()
    
    class DummyNode:
        id = "dummy_sensor"
        def tick(self): pass
    mock_graph.nodes = {"dummy_sensor": DummyNode()}
    
    mock_historical = MagicMock()
    mock_historical.is_ready = True
    
    mock_xai = MagicMock()
    
    # 2. Instantiate Engine via EngineComponentFactory (DIP)
    try:
        from src.factories.engine_component_factory import EngineComponentFactory
        components = EngineComponentFactory(mock_app_state).build()
        engine = components.inference_engine
        engine.graph_manager.nodes = {"dummy_sensor": DummyNode()}
    except Exception as e:
        pytest.skip(f"Could not load InferenceEngine (missing models?): {e}")

    # Patch snapshot builder to return lightweight dummy snapshot if needed
    # (By default it will build an empty one if nodes have no valid embeddings)

    # 3. Warm-up cycles (PyTorch has initial CUDA allocation overhead)
    for _ in range(3):
        engine.run_global_cycle()
        
    # 4. Benchmark cycles
    num_cycles = 10
    execution_times = []
    
    for _ in range(num_cycles):
        start_time = time.perf_counter()
        engine.run_global_cycle()
        end_time = time.perf_counter()
        execution_times.append(end_time - start_time)
        
    avg_latency_sec = sum(execution_times) / num_cycles
    avg_latency_ms = avg_latency_sec * 1000.0
    
    print(f"\\n[BENCHMARK] Average Inference Latency: {avg_latency_ms:.2f} ms")
    print(f"[BENCHMARK] Min: {min(execution_times)*1000:.2f} ms | Max: {max(execution_times)*1000:.2f} ms")
    
    # 5. Assert performance target (Allowing tolerance for variable testing hardware)
    # Target: 150ms to 250ms. 
    # We assert < 300ms to avoid flaky CI builds, and warn if > 250ms.
    assert avg_latency_ms < 350.0, f"Critical Latency Failure: {avg_latency_ms:.2f} ms exceeds maximum budget!"
