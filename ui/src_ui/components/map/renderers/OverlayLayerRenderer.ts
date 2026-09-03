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
// File: ui/src_ui/components/map/renderers/OverlayLayerRenderer.ts
// Author: Gabriel Moraes
// Date: 2026-08-31

import { MapLayerRenderer, MapRenderContext } from './types';
import { computeCenterline } from '../../../utils/geometry';

export class OverlayLayerRenderer implements MapLayerRenderer {
  public render(context: MapRenderContext): void {
    const {
      ctx,
      edges,
      opposingEdgeMap,
      nodeMap,
      selectedEdgeId,
      latestEngineData,
      isElementAssociated,
      canvasColors,
      isDark,
      zoom,
    } = context;

    edges.forEach((edge) => {
      const isSelected =
        selectedEdgeId === edge.id ||
        selectedEdgeId === `-${edge.id}` ||
        `-${selectedEdgeId}` === edge.id;

      const hasSensor = isElementAssociated(edge.id);
      const live =
        latestEngineData?.edge_data?.[edge.id] ||
        latestEngineData?.edge_data?.[edge.id.replace(/^-/, '')] ||
        latestEngineData?.edge_data?.[`-${edge.id}`];

      if (!isSelected && !hasSensor && !live) return;

      const fromNode = nodeMap.get(edge.from);
      const toNode = nodeMap.get(edge.to);
      const opp = opposingEdgeMap.get(edge.id);

      let polyline: number[][] = [];
      if (opp && opp.shape && edge.shape && edge.shape.length > 0 && opp.shape.length > 0) {
        polyline = computeCenterline(edge.shape, opp.shape);
      } else if (edge.shape && edge.shape.length > 0) {
        polyline = edge.shape;
      } else if (fromNode && toNode) {
        polyline = [[fromNode.x, fromNode.y], [toNode.x, toNode.y]];
      }

      if (polyline.length === 0) return;

      if (isSelected) {
        const color = hasSensor ? canvasColors.roadSelected : canvasColors.roadActive;
        ctx.strokeStyle = color;
        ctx.shadowColor = color;
        ctx.shadowBlur = isDark ? 16 : 10;
        ctx.lineWidth = 9.5 / zoom;
      } else if (hasSensor) {
        ctx.strokeStyle = canvasColors.roadMonitored;
        ctx.shadowColor = isDark ? 'rgba(14, 165, 233, 0.45)' : 'rgba(2, 132, 199, 0.35)';
        ctx.shadowBlur = 6;
        ctx.lineWidth = 8.2 / zoom;
      } else if (live) {
        const speed = live.speed;
        ctx.strokeStyle = speed > 45
          ? (isDark ? '#10b981' : '#059669')
          : speed > 20
          ? (isDark ? '#f59e0b' : '#d97706')
          : (isDark ? '#f43f5e' : '#e11d48');
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
        ctx.lineWidth = 7.5 / zoom;
      }

      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      ctx.beginPath();
      const connectFrom =
        fromNode &&
        Math.hypot(fromNode.x - polyline[0][0], fromNode.y - polyline[0][1]) < 30.0;
      const lastIdx = polyline.length - 1;
      const connectTo =
        toNode &&
        Math.hypot(toNode.x - polyline[lastIdx][0], toNode.y - polyline[lastIdx][1]) < 30.0;

      if (connectFrom && fromNode) {
        ctx.moveTo(fromNode.x, fromNode.y);
        ctx.lineTo(polyline[0][0], polyline[0][1]);
      } else {
        ctx.moveTo(polyline[0][0], polyline[0][1]);
      }

      for (let i = 1; i < polyline.length; i++) {
        ctx.lineTo(polyline[i][0], polyline[i][1]);
      }

      if (connectTo && toNode) {
        ctx.lineTo(toNode.x, toNode.y);
      }
      ctx.stroke();
    });
  }
}
