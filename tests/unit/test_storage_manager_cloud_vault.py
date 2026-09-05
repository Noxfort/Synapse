# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# File: tests/unit/test_storage_manager_cloud_vault.py
# Author: Gabriel Moraes
# Date: 2026-09-04

import os
import shutil
import tempfile
import pytest
import torch
import pandas as pd
from unittest.mock import MagicMock

from src.database.db_engine import DatabaseEngine
from src.repositories.cloud_vault_repo import CloudVaultRepository
from src.managers.storage_manager import StorageManager
from src.infrastructure.json_source_storage import JsonSourceStorage
from src.domain.entities import DataSource, SourceType, SourceStatus


@pytest.fixture
def temp_env():
    work_dir = tempfile.mkdtemp(prefix="synapse_vault_test_")
    project_root = os.path.join(work_dir, "Synapse")

    db_engine = DatabaseEngine(
        custom_config={"db_type": "postgres", "schema": "schema_synapse_test"},
        auto_init=True
    )

    # Clean cloud_file_vault in test schema
    conn = db_engine.get_connection()
    assert conn is not None
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE schema_synapse_test.cloud_file_vault RESTART IDENTITY;")
    conn.commit()
    conn.close()

    yield {"work_dir": work_dir, "db_engine": db_engine, "project_root": project_root}

    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)


def test_storage_manager_save_and_disaster_recovery(temp_env):
    """
    Tests that files saved via StorageManager (.pth checkpoints, .parquet datalake, sources.json)
    are persisted in both physical disk and the database cloud vault, and when the physical
    folder is deleted, a new StorageManager automatically restores all files.
    """
    db_engine = temp_env["db_engine"]
    project_root = temp_env["project_root"]

    # 1. Initialize StorageManager with DB
    sm1 = StorageManager(engine=db_engine, project_root=project_root)

    # 2. Save a node checkpoint .pth
    state = {"model_state": [0.1, 0.2, 0.3], "step": 42}
    saved_node = sm1.save_node_checkpoint("cam_test_01", state)
    assert saved_node is True

    # 3. Save sources.json via JsonSourceStorage
    sources_path = os.path.join(project_root, "config", "sources.json")
    jss = JsonSourceStorage(file_path=sources_path, engine=db_engine)
    src = DataSource(
        id="cam_test_01",
        name="Camera Central 01",
        source_type=SourceType.MQTT,
        connection_string="rtsp://192.168.1.100:554/live",
        is_local=False,
        status=SourceStatus.ACTIVE,
        lat=-23.5505,
        lon=-46.6333
    )
    saved_sources = jss.save(
        data_sources={"cam_test_01": src},
        associations={"cam_test_01": ["radar_01"]},
        map_path="/maps/city_topology.osm"
    )
    assert saved_sources is True

    # 4. Create and sync a test .parquet file
    parquet_path = os.path.join(sm1.get_datalake_base_path(), "base_v1.parquet")
    df = pd.DataFrame({"sensor_id": [1, 2], "flow_rate": [120.0, 150.0], "speed": [55.0, 60.0]})
    df.to_parquet(parquet_path)
    assert sm1.sync_file_to_vault(parquet_path) is True

    # 5. Verify all files are in cloud_file_vault
    vault_repo = CloudVaultRepository(db_engine)
    assert vault_repo.has_file("Checkpoint/state_cam_test_01.pth") is True
    assert vault_repo.has_file("config/sources.json") is True
    assert vault_repo.has_file("datalake/base/base_v1.parquet") is True

    # 6. SIMULATE TOTAL DISASTER: DELETE THE ENTIRE SYNAPSE DIRECTORY!
    shutil.rmtree(project_root)
    assert not os.path.exists(project_root)

    # 7. Instantiate NEW StorageManager on the deleted path
    sm2 = StorageManager(engine=db_engine, auto_restore=True, project_root=project_root)

    # 8. Verify all files were resurrected back to physical disk!
    # A) Node checkpoint .pth
    loaded_state = sm2.load_node_checkpoint("cam_test_01")
    assert loaded_state is not None
    assert loaded_state["step"] == 42
    assert loaded_state["model_state"] == [0.1, 0.2, 0.3]

    # B) Sources .json
    jss2 = JsonSourceStorage(file_path=sources_path, engine=db_engine)
    loaded_sources, associations, map_path = jss2.load()
    assert "cam_test_01" in loaded_sources
    assert loaded_sources["cam_test_01"].name == "Camera Central 01"
    assert loaded_sources["cam_test_01"].lat == -23.5505
    assert associations == {"cam_test_01": ["radar_01"]}
    assert map_path == "/maps/city_topology.osm"

    # C) Parquet datalake file
    assert os.path.exists(parquet_path)
    df_restored = pd.read_parquet(parquet_path)
    assert len(df_restored) == 2
    assert "flow_rate" in df_restored.columns


def test_json_source_storage_vault_recovery_standalone(temp_env):
    """Verifies that JsonSourceStorage restores from vault if sources.json is missing on disk."""
    db_engine = temp_env["db_engine"]
    work_dir = temp_env["work_dir"]
    sources_path = os.path.join(work_dir, "config", "sources.json")

    storage1 = JsonSourceStorage(file_path=sources_path, engine=db_engine)
    src = DataSource(
        id="radar_01",
        name="Radar Express",
        source_type=SourceType.API,
        connection_string="tcp://10.0.0.1:8080",
        is_local=True,
        status=SourceStatus.ACTIVE,
        lat=-23.1,
        lon=-46.2
    )
    assert storage1.save({"radar_01": src}, {}, None) is True
    assert os.path.exists(sources_path)

    # Delete sources.json
    os.remove(sources_path)
    assert not os.path.exists(sources_path)

    # Load with a new storage instance -> restores from vault!
    storage2 = JsonSourceStorage(file_path=sources_path, engine=db_engine)
    sources, _, _ = storage2.load()
    assert "radar_01" in sources
    assert sources["radar_01"].name == "Radar Express"
    assert os.path.exists(sources_path)  # File was restored to disk!


def test_storage_manager_offline_resilience(temp_env):
    """Verifies that if the database is offline, StorageManager works locally without exceptions."""
    work_dir = temp_env["work_dir"]
    project_root = os.path.join(work_dir, "Synapse_offline")

    mock_engine = MagicMock()
    mock_engine.get_connection.return_value = None  # DB offline

    sm = StorageManager(engine=mock_engine, auto_restore=True, project_root=project_root)

    # Local operations should succeed
    state = {"weights": [1, 2, 3]}
    assert sm.save_node_checkpoint("node_off", state) is True
    loaded = sm.load_node_checkpoint("node_off")
    assert loaded == state
