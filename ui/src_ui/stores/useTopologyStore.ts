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
// File: ui/src_ui/stores/useTopologyStore.ts
// Author: Gabriel Moraes
// Date: 2026-08-29

import { create } from 'zustand';
import { MapNodeData, MapEdgeData } from '../types/topology';

interface TopologyState {
  nodes: MapNodeData[];
  edges: MapEdgeData[];
  mapLoaded: boolean;
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  isAssociatingSourceId: string | null;

  // Actions
  setTopology: (nodes: MapNodeData[], edges: MapEdgeData[]) => void;
  setSelectedNodeId: (id: string | null) => void;
  setSelectedEdgeId: (id: string | null) => void;
  setAssociatingSourceId: (id: string | null) => void;
  clearTopology: () => void;
}

export const useTopologyStore = create<TopologyState>((set) => ({
  nodes: [],
  edges: [],
  mapLoaded: false,
  selectedNodeId: null,
  selectedEdgeId: null,
  isAssociatingSourceId: null,

  setTopology: (nodes, edges) => set({ nodes, edges, mapLoaded: nodes.length > 0 }),
  setSelectedNodeId: (id) => set({ selectedNodeId: id, selectedEdgeId: null }),
  setSelectedEdgeId: (id) => set({ selectedEdgeId: id, selectedNodeId: null }),
  setAssociatingSourceId: (id) => set({ isAssociatingSourceId: id }),
  clearTopology: () => set({ nodes: [], edges: [], mapLoaded: false, selectedNodeId: null, selectedEdgeId: null }),
}));
