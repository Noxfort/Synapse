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
// File: ui/src_ui/components/map/renderers/types.ts
// Author: Gabriel Moraes
// Date: 2026-08-31

import { MapNodeData, MapEdgeData, Point2D } from '../../../types/topology';
import { EngineDataPayload, DataSourceItem } from '../../../types/sensors';
import { DesignTokens } from '../../../theme';

export type CanvasColors = DesignTokens['themes']['dark']['colors']['canvas'];

export interface MapRenderContext {
  ctx: CanvasRenderingContext2D;
  width: number;
  height: number;
  pan: Point2D;
  zoom: number;
  isDark: boolean;
  canvasColors: CanvasColors;
  nodes: MapNodeData[];
  edges: MapEdgeData[];
  nodeMap: Map<string, MapNodeData>;
  edgeMap: Map<string, MapEdgeData>;
  opposingEdgeMap: Map<string, MapEdgeData>;
  sources: DataSourceItem[];
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  latestEngineData: EngineDataPayload | null;
  isElementAssociated: (elementId: string) => boolean;
}

export interface MapLayerRenderer {
  render(context: MapRenderContext): void;
}
