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
# File: tests/unit/test_map_service.py
# Author: Gabriel Moraes
# Date: 2026-08-30

import gzip
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from src.services.map_service import MapService
from src.handlers.map_handler import MapCommandHandler
from src.ipc.ipc_protocol import IpcMessage
from src.infrastructure.dialog_service import NativeDialogService


SAMPLE_NET_XML = """<?xml version="1.0" encoding="UTF-8"?>
<net version="1.16" junctionCornerDetail="5" limitTurnSpeed="5.50" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <location netOffset="0.00,0.00" convBoundary="0.00,0.00,200.00,200.00" origBoundary="0.00,0.00,200.00,200.00" projParameter="!"/>

    <edge id="edge_1" from="node_1" to="node_2" priority="-1">
        <lane id="edge_1_0" index="0" speed="13.89" length="100.00" shape="0.00,0.00 100.00,0.00"/>
    </edge>
    <edge id="edge_2" from="node_2" to="node_3" priority="-1">
        <lane id="edge_2_0" index="0" speed="13.89" length="100.00" shape="100.00,0.00 200.00,0.00"/>
    </edge>

    <junction id="node_1" type="dead_end" x="0.00" y="0.00" incLanes="" intLanes="" shape="0.00,0.00 0.00,3.20"/>
    <junction id="node_2" type="traffic_light" x="100.00" y="0.00" incLanes="edge_1_0" intLanes="" shape="100.00,3.20 100.00,0.00" tl="TLS_1"/>
    <junction id="node_3" type="priority" x="200.00" y="0.00" incLanes="edge_2_0" intLanes="" shape="200.00,3.20 200.00,0.00"/>
</net>
"""


@pytest.fixture
def sample_xml_file(tmp_path):
    f = tmp_path / "test_city.net.xml"
    f.write_text(SAMPLE_NET_XML, encoding="utf-8")
    return str(f)


@pytest.fixture
def sample_gz_file(tmp_path):
    f = tmp_path / "test_city.net.xml.gz"
    with gzip.open(f, "wb") as gz_out:
        gz_out.write(SAMPLE_NET_XML.encode("utf-8"))
    return str(f)


def test_load_network_plain_xml(sample_xml_file):
    service = MapService()
    ok = service.load_network(sample_xml_file)
    assert ok is True
    assert len(service.nodes) == 3
    assert len(service.edges) == 2
    assert service.last_error is None

    # Check node properties
    n2 = service._node_lookup["node_2"]
    assert n2.x == 100.0
    assert n2.y == 0.0
    assert n2.node_type == "traffic_light"
    assert n2.tl_logic_id == "TLS_1"

    # Check edge properties
    e1 = next(e for e in service.edges if e.id == "edge_1")
    assert e1.from_node == "node_1"
    assert e1.to_node == "node_2"
    assert e1.length == 100.0


def test_load_network_gzip_compressed(sample_gz_file):
    service = MapService()
    ok = service.load_network(sample_gz_file)
    assert ok is True
    assert len(service.nodes) == 3
    assert len(service.edges) == 2
    assert service.last_error is None


def test_load_network_gzip_extension_fallback(tmp_path):
    """File named .gz but containing uncompressed XML should still parse gracefully."""
    f = tmp_path / "fake_compressed.net.xml.gz"
    f.write_text(SAMPLE_NET_XML, encoding="utf-8")

    service = MapService()
    ok = service.load_network(str(f))
    assert ok is True
    assert len(service.nodes) == 3


def test_load_network_non_existent_file():
    service = MapService()
    ok = service.load_network("/non/existent/path/map.net.xml")
    assert ok is False
    assert "não encontrado" in service.last_error


def test_load_network_file_uri_and_url_encoding(sample_xml_file):
    service = MapService()
    uri = f"file://{sample_xml_file}"
    ok = service.load_network(uri)
    assert ok is True
    assert len(service.nodes) == 3


def test_load_network_empty_nodes(tmp_path):
    f = tmp_path / "empty.net.xml"
    f.write_text("<net><edge id='e1'/></net>", encoding="utf-8")

    service = MapService()
    ok = service.load_network(str(f))
    assert ok is False
    assert "Nenhum nó viário" in service.last_error


def test_map_command_handler_success(sample_xml_file):
    mock_app_state = MagicMock()
    handler = MapCommandHandler(app_state=mock_app_state)

    responses = []
    def responder(success, result=None, error=None):
        responses.append({"success": success, "result": result, "error": error})

    msg = IpcMessage(action="load_map", payload={"path": sample_xml_file})
    handler.handle_load_map(msg, responder)

    assert len(responses) == 1
    assert responses[0]["success"] is True
    assert responses[0]["error"] is None
    assert mock_app_state.set_map_data.called


def test_map_command_handler_non_existent_file():
    mock_app_state = MagicMock()
    handler = MapCommandHandler(app_state=mock_app_state)

    responses = []
    def responder(success, result=None, error=None):
        responses.append({"success": success, "result": result, "error": error})

    msg = IpcMessage(action="load_map", payload={"path": "/invalid/missing.net.xml"})
    handler.handle_load_map(msg, responder)

    assert len(responses) == 1
    assert responses[0]["success"] is False
    assert "não encontrado" in responses[0]["error"]
