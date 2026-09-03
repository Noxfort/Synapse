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
# File: tests/unit/test_parquet_service.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import os
import tempfile
import pandas as pd
import pytest

from src.services.data_inspection_service import DataInspectionService
from src.handlers.database_handler import DatabaseCommandHandler
from src.ipc.ipc_protocol import IpcMessage


@pytest.fixture
def sample_parquet_file():
    df = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=10, freq="1min"),
        "sensor_id": [f"S_{i}" for i in range(10)],
        "speed": [45.2 + i for i in range(10)],
    })
    tmp = tempfile.NamedTemporaryFile(suffix=".parquet", delete=False)
    tmp.close()
    df.to_parquet(tmp.name)
    yield tmp.name
    if os.path.exists(tmp.name):
        os.unlink(tmp.name)


def test_inspect_parquet_success(sample_parquet_file):
    service = DataInspectionService()
    info = service.inspect_parquet(sample_parquet_file)
    assert info["num_rows"] == 10
    assert "timestamp" in info["columns"]
    assert "sensor_id" in info["columns"]
    assert "speed" in info["columns"]
    assert info["size_mb"] >= 0


def test_inspect_parquet_file_uri_normalization(sample_parquet_file):
    service = DataInspectionService()
    uri_path = f"file://{sample_parquet_file}"
    info = service.inspect_parquet(uri_path)
    assert info["num_rows"] == 10


def test_inspect_parquet_non_existent():
    service = DataInspectionService()
    with pytest.raises(FileNotFoundError):
        service.inspect_parquet("/tmp/definitely_not_a_real_dataset_123.parquet")


def test_inspect_parquet_invalid_extension(sample_parquet_file):
    service = DataInspectionService()
    fake_txt = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
    fake_txt.close()
    try:
        with pytest.raises(ValueError, match=r"\.parquet"):
            service.inspect_parquet(fake_txt.name)
    finally:
        if os.path.exists(fake_txt.name):
            os.unlink(fake_txt.name)


def test_database_command_handler_inspect(sample_parquet_file):
    service = DataInspectionService()
    handler = DatabaseCommandHandler(
        controller=None,
        event_emitter=lambda *args: None,
        data_inspection_service=service,
    )

    responses = []
    msg = IpcMessage(action="inspect_parquet", payload={"path": sample_parquet_file}, id="req-1")
    handler.handle_inspect_parquet(msg, lambda ok, res=None, error=None: responses.append((ok, res, error)))

    assert len(responses) == 1
    assert responses[0][0] is True
    assert responses[0][1]["num_rows"] == 10
