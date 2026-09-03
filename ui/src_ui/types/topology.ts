// SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
// Copyright (C) 2026 Noxfort Systems
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
// published by the Free Software Foundation, either version 3 of the
// License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.
//
// File: ui/src_ui/types/topology.ts
// Author: Gabriel Moraes
// Date: 2026-08-29

export interface Point2D {
  x: number;
  y: number;
}

export interface BoundingBox {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

export interface MapNodeData {
  id: string;
  x: number;
  y: number;
  is_tls?: boolean;
}

export interface MapEdgeData {
  id: string;
  from: string;
  to: string;
  length?: number;
  shape?: number[][];
}

export interface TopologyPayload {
  nodes: MapNodeData[];
  edges: MapEdgeData[];
  loaded: boolean;
}
