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
# File: src/services/map_service.py
# Author: Gabriel Moraes
# Date: 2025-12-25

import os
import gzip
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlparse
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from PyQt6.QtCore import QObject, pyqtSignal

from src.logging.facade import get_logger
from src.domain.entities import MapNode, MapEdge

class MapService(QObject):
    """
    The 'Cartographer' of Synapse.
    
    Responsibility:
    - Parses SUMO Network files (.net.xml and .net.xml.gz).
    - Extracts topological ground truth (Nodes & Edges).
    - Filters out internal simulation artifacts to build a clean graph.
    - Provides the 'Spatial Context' for the GATv2 Neural Network.
    
    Refactoring V3: Added robust support for GZIP compressed maps and detailed logging.
    """
    
    # Signals
    map_loaded = pyqtSignal(int, int) # (num_nodes, num_edges)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.logger = get_logger("MapService")
        self.nodes: List[MapNode] = []
        self.edges: List[MapEdge] = []
        self._node_lookup: Dict[str, MapNode] = {}
        self.last_error: Optional[str] = None

    def load_network(self, file_path: str) -> bool:
        """
        Parses a .net.xml (or .net.xml.gz) file and populates the domain entities.
        """
        self.last_error = None

        if not file_path or not str(file_path).strip():
            msg = "Caminho do arquivo de rede viária não foi informado."
            self.logger.error(f"[MapService] ❌ {msg}")
            self.last_error = msg
            self.error_occurred.emit(msg)
            return False

        # Clean and normalize path (handle file:// URL, %20 encoding, ~, quotes)
        clean_path_str = str(file_path).strip().strip('"\'')
        if clean_path_str.startswith("file://"):
            clean_path_str = unquote(urlparse(clean_path_str).path)
        clean_path_str = unquote(clean_path_str)
        clean_path_str = os.path.expanduser(clean_path_str)

        path = Path(clean_path_str).resolve()
        if not path.exists():
            msg = f"Arquivo de mapa não encontrado no disco: {clean_path_str}"
            self.logger.error(f"[MapService] ❌ {msg}")
            self.last_error = msg
            self.error_occurred.emit(msg)
            return False

        self.logger.info(f"[MapService] 🗺️ Carregando Topologia SUMO de: '{path}' (Tamanho: {path.stat().st_size / 1024:.1f} KB)...")

        try:
            # Check gzip magic bytes (0x1f, 0x8b)
            is_gzip = False
            try:
                with open(path, 'rb') as f_check:
                    header = f_check.read(2)
                    if header == b'\x1f\x8b':
                        is_gzip = True
            except Exception as e:
                self.logger.warning(f"[MapService] ⚠️ Não foi possível inspecionar cabeçalho do arquivo: {e}")
                is_gzip = str(path).lower().endswith('.gz')

            tree = None
            if is_gzip or str(path).lower().endswith('.gz'):
                try:
                    with gzip.open(path, 'rb') as source:
                        tree = ET.parse(source)
                except Exception as gz_err:
                    self.logger.warning(f"[MapService] ⚠️ Falha ao abrir como GZIP ({gz_err}). Tentando parser XML direto...")
                    try:
                        tree = ET.parse(str(path))
                    except Exception as xml_err:
                        raise RuntimeError(f"Falha ao processar arquivo GZIP/XML: {gz_err} / {xml_err}") from gz_err
            else:
                try:
                    tree = ET.parse(str(path))
                except Exception as xml_err:
                    self.logger.warning(f"[MapService] ⚠️ Falha ao ler como XML puro ({xml_err}). Tentando como GZIP...")
                    try:
                        with gzip.open(path, 'rb') as source:
                            tree = ET.parse(source)
                    except Exception:
                        raise xml_err

            root = tree.getroot()
            if root is None:
                msg = f"Estrutura XML vazia no arquivo SUMO: {path.name}"
                self.logger.error(f"[MapService] ❌ {msg}")
                self.last_error = msg
                self.error_occurred.emit(msg)
                return False

            self.nodes.clear()
            self.edges.clear()
            self._node_lookup.clear()

            def clean_tag(elem) -> str:
                return elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

            # --- STEP 1: Parse Junctions (Nodes) ---
            junction_elements = [elem for elem in root.iter() if clean_tag(elem) == 'junction']
            for junction in junction_elements:
                j_type = junction.get('type', '')
                if j_type == 'internal':
                    continue

                j_id = junction.get('id')
                if not j_id or j_id.startswith(':'):
                    continue

                x_val: Optional[float] = None
                y_val: Optional[float] = None

                x_attr = junction.get('x')
                y_attr = junction.get('y')
                if x_attr is not None and y_attr is not None:
                    try:
                        x_val = float(x_attr)
                        y_val = float(y_attr)
                    except (ValueError, TypeError):
                        pass

                # Fallback to shape coordinates if x/y missing
                if x_val is None or y_val is None:
                    shape = junction.get('shape')
                    if shape:
                        try:
                            first_pt = shape.strip().split()[0].split(',')
                            x_val = float(first_pt[0])
                            y_val = float(first_pt[1])
                        except (ValueError, TypeError, IndexError):
                            pass

                if x_val is None or y_val is None:
                    continue

                tl_id = junction.get('tl') or junction.get('tlLogic')
                if not tl_id and str(j_type).startswith('traffic_light'):
                    tl_id = j_id

                node = MapNode(id=j_id, x=x_val, y=y_val, node_type=str(j_type), tl_logic_id=tl_id)
                self.nodes.append(node)
                self._node_lookup[j_id] = node

            self.logger.info(f"[MapService] ✅ Extraídos {len(self.nodes)} cruzamentos/nós físicos (Nodes).")

            if len(self.nodes) == 0:
                msg = f"Nenhum nó viário físico válido encontrado no mapa SUMO: {path.name}"
                self.logger.error(f"[MapService] ❌ {msg}")
                self.last_error = msg
                self.error_occurred.emit(msg)
                return False

            # --- STEP 2: Parse Streets (Edges) ---
            edge_elements = [elem for elem in root.iter() if clean_tag(elem) == 'edge']
            for edge in edge_elements:
                func = edge.get('function', '')
                if func in ('internal', 'crossing', 'walkingarea'):
                    continue

                e_id = edge.get('id')
                if not e_id or e_id.startswith(':'):
                    continue

                from_id = edge.get('from')
                to_id = edge.get('to')
                
                # We only want edges connecting valid physical nodes
                if from_id in self._node_lookup and to_id in self._node_lookup:
                    lanes = [child for child in edge if clean_tag(child) == 'lane']
                    
                    # --- A. Extract Geometry (Shape) ---
                    shape_points: List[Tuple[float, float]] = []
                    shape_str = None
                    
                    if lanes:
                        shape_str = lanes[0].get('shape')
                    if not shape_str:
                        shape_str = edge.get('shape')
                    
                    if shape_str:
                        try:
                            for point_str in shape_str.strip().split():
                                coords = point_str.split(',')
                                if len(coords) >= 2:
                                    shape_points.append((float(coords[0]), float(coords[1])))
                        except (ValueError, IndexError):
                            shape_points = []
                    
                    # Fallback: use from/to node coordinates if no shape parsed
                    if not shape_points:
                        fn = self._node_lookup[from_id]
                        tn = self._node_lookup[to_id]
                        shape_points = [(fn.x, fn.y), (tn.x, tn.y)]
                    
                    # --- B. Extract Length ---
                    try:
                        length = float(edge.get('length', 0.0))
                        if length <= 0.0 and lanes:
                            length = float(lanes[0].get('length', 1.0))
                        if length <= 0.0:
                            fn = self._node_lookup[from_id]
                            tn = self._node_lookup[to_id]
                            length = max(1.0, float(((fn.x - tn.x) ** 2 + (fn.y - tn.y) ** 2) ** 0.5))
                    except (ValueError, TypeError):
                        length = 1.0
                    
                    # --- C. Extract Speed & Lane Count ---
                    speed = 13.89  # Default ~50 km/h
                    num_lanes = len(lanes) if lanes else 1
                    try:
                        if lanes:
                            speed = float(lanes[0].get('speed', 13.89))
                    except (ValueError, TypeError):
                        pass

                    map_edge = MapEdge(
                        id=e_id,
                        from_node=from_id,
                        to_node=to_id,
                        shape=shape_points,
                        real_name=edge.get('name'),
                        weight=length,
                        length=length,
                        max_speed=speed,
                        lanes=num_lanes
                    )
                    map_edge._speed = speed
                    map_edge._num_lanes = num_lanes
                    self.edges.append(map_edge)

            self.logger.info(f"[MapService] ✅ Extraídas {len(self.edges)} vias viárias navegáveis (Edges).")
            
            # Emit success
            self.last_error = None
            self.map_loaded.emit(len(self.nodes), len(self.edges))
            return True

        except ET.ParseError as e:
            msg = f"Erro de sintaxe XML ao analisar rede viária ({path.name}): {e}"
            self.logger.error(f"[MapService] ❌ {msg}", exc_info=True)
            self.last_error = msg
            self.error_occurred.emit(msg)
            return False
        except Exception as e:
            msg = f"Erro crítico ao processar rede viária SUMO ({path.name}): {e}"
            self.logger.error(f"[MapService] ❌ {msg}", exc_info=True)
            self.last_error = msg
            self.error_occurred.emit(msg)
            return False

    def get_topology(self) -> Tuple[List[MapNode], List[MapEdge]]:
        """Returns the processed graph data for the Optimizer."""
        return self.nodes, self.edges
