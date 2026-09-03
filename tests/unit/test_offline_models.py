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
# File: tests/unit/test_offline_models.py
# Author: Gabriel Moraes
# Date: 2026-08-28

import os
import pytest
import torch

from src.utils.model_paths import (
    get_model_vault_dir,
    get_distilroberta_path,
    get_distilroberta_v1_path,
    get_distilroberta_base_path,
    get_qwen_gguf_path,
)
from src.models.distilroberta import (
    DistilRobertaEmbeddingModel,
    DistilRobertaSemanticExtractor,
)
from src.models.neuro_symbolic import NeuroSymbolicModel
from src.pipeline.linguist_pipeline import LinguistPipeline
from src.agents.linguist_agent import LinguistAgent
from src.agents.jurist_agent import JuristAgent
from src.factories.jurist_factory import JuristFactory
from src.factories.linguist_factory import LinguistFactory


def test_model_vault_paths():
    vault_dir = get_model_vault_dir()
    assert os.path.exists(vault_dir)
    assert os.path.isdir(vault_dir)

    distil_path = get_distilroberta_path()
    assert os.path.exists(distil_path)
    assert os.path.isdir(distil_path)

    v1_path = get_distilroberta_v1_path()
    assert os.path.exists(v1_path)

    base_path = get_distilroberta_base_path()
    assert os.path.exists(base_path)

    gguf_path = get_qwen_gguf_path()
    assert os.path.exists(gguf_path)
    assert gguf_path.endswith(".gguf")


def test_distilroberta_embedding_model_offline():
    emb_model = DistilRobertaEmbeddingModel()
    assert emb_model.model_name == get_distilroberta_v1_path()
    
    # Check parameters are frozen
    for p in emb_model.transformer.parameters():
        assert p.requires_grad is False

    dummy_ids = torch.tensor([[101, 2054, 2003, 1037, 102]])
    dummy_mask = torch.tensor([[1, 1, 1, 1, 1]])
    
    with torch.no_grad():
        out = emb_model(dummy_ids, dummy_mask)
    assert out.shape == (1, 768)
    norm = torch.norm(out, p=2, dim=-1)
    assert pytest.approx(norm.item(), abs=1e-4) == 1.0


def test_distilroberta_semantic_extractor_offline():
    extractor = DistilRobertaSemanticExtractor()
    concept, is_new = extractor.learn_and_map_semantics(["sensor de velocidade"])
    assert isinstance(concept, str)
    assert is_new is True

    # Same text should match existing concept
    concept2, is_new2 = extractor.learn_and_map_semantics(["sensor de velocidade"])
    assert concept2 == concept
    assert is_new2 is False


def test_neuro_symbolic_model_offline():
    model = NeuroSymbolicModel()
    assert model.model_name == get_distilroberta_base_path()
    for p in model.transformer.parameters():
        assert p.requires_grad is False


def test_linguist_pipeline_and_agent_offline():
    agent = LinguistFactory.create()
    assert isinstance(agent, LinguistAgent)

    res = agent.inference({"text": "traffic speed normal", "semantic_type": "Vehicle Speed"})
    assert isinstance(res, dict)
    assert "is_valid" in res
    assert "error_score" in res


def test_jurist_factory_and_agent_gguf_integration():
    jurist = JuristFactory.create()
    assert isinstance(jurist, JuristAgent)
    assert jurist.is_gguf is True
    assert jurist.model_id == get_qwen_gguf_path()

    jurist.load_resources()
    assert jurist.is_loaded is True

    verdict = jurist.generate_verdict({
        "source_id": "sensor_01",
        "status": "NORMAL",
        "values": ["fluxo: 100", "velocidade: 60"],
        "language": "pt_BR"
    })
    assert isinstance(verdict, str)
    assert len(verdict) > 0
    assert "<think>" not in verdict  # PromptRegistry cleans reasoning tags

    report = jurist.generate_report(
        tensor_data={"fluxo": 100.0, "velocidade": 60.0},
        timestamp="2026-08-28T18:00:00",
        locale="pt_BR"
    )
    assert isinstance(report, str)
    assert len(report) > 0

    jurist.unload_resources()
    assert jurist.is_loaded is False
    
    import gc
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
