import pytest
import torch
import numpy as np
from unittest.mock import MagicMock

# Import the core components
from src.engine.cycle_processor import CycleProcessor
from src.agents.specialist_agent import SpecialistAgent
from src.agents.coordinator_agent import CoordinatorAgent
from src.agents.fuser_agent import FuserAgent
from src.agents.auditor_agent import AuditorAgent
from src.managers.graph_manager import GraphManager

@pytest.fixture
def mock_managers():
    """Mocks the external domain dependencies."""
    app_state = MagicMock()
    app_state.get_all_nodes.return_value = [
        MagicMock(id="N1"), MagicMock(id="N2"), MagicMock(id="N3")
    ]
    
    graph_manager = MagicMock(spec=GraphManager)
    graph_manager.get_ordered_node_ids.return_value = ["N1", "N2", "N3"]
    
    # Mock node history returns [Seq]
    mock_node = MagicMock()
    mock_node.memory.get_numpy.return_value = np.random.randn(60, 1)
    graph_manager.get_node.return_value = mock_node
    
    # Mock Edge Index (Connectivity)
    graph_manager.edge_index = torch.tensor([[0, 1, 1], [1, 0, 2]], dtype=torch.long)
    
    xai = MagicMock()
    
    return app_state, graph_manager, xai

def test_global_cycle_processor_e2e(mock_managers):
    """
    Tests the Full E2E Loop of the CycleProcessor using live Neural Agents.
    This guarantees that Tensor Dimensions match perfectly downstream.
    """
    app_state, graph_manager, xai = mock_managers
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # 1. Instantiate Live Agents (with exactly the configured shapes)
    coordinator = CoordinatorAgent(in_channels=32, hidden_channels=32, out_channels=32)
    
    # TensorBuilder inside CycleProcessor looks at coordinator.model.conv1.in_channels
    # So expected_dim will evaluate to 32.
    
    fuser = FuserAgent(num_variates=3, seq_len=60, pred_len=1, d_model=64)
    auditor = AuditorAgent(input_len=60, J=2, latent_dim=16)
    
    # 2. Instantiate Processor
    processor = CycleProcessor(
        app_state=app_state,
        device=device,
        coordinator=coordinator,
        fuser=fuser,
        auditor=auditor,
        xai_manager=xai,
        graph_manager=graph_manager
    )
    
    # 3. Simulate a generic snapshot coming from SnapshotBuilder
    # Snapshot provides embeddings of dim=32 (what TCN usually outputs)
    snapshot = {
        "N1": {"embedding": np.random.randn(32), "value": 10.0},
        "N2": {"embedding": np.random.randn(32), "value": 12.0},
        "N3": {"embedding": np.random.randn(32), "value": 11.0}
    }
    
    # 4. Run the Core Logic
    # If shapes collide (e.g. padding to 4 vs 32, cross-attention mismatch), this will crash.
    results, alert = processor.run_logic(snapshot)
    
    # 5. Assert Completeness
    assert results is not None, "Cycle should return results"
    assert "spatial_embedding" in results, "Missing GATv2 output"
    assert "forecast" in results, "Missing iTransformer output"
    
    # Forecast should be predicting 3 variates (Next step for nodes)
    assert len(results["forecast"]) == 3, "Forecast should map 1-to-1 with nodes"
    
    # Security Alert evaluation
    assert "security_score" in results
