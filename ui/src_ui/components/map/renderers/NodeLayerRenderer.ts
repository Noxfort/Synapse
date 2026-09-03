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
// File: ui/src_ui/components/map/renderers/NodeLayerRenderer.ts
// Author: Gabriel Moraes
// Date: 2026-08-31

import { MapLayerRenderer, MapRenderContext } from './types';

export class NodeLayerRenderer implements MapLayerRenderer {
  public render(context: MapRenderContext): void {
    const { ctx, nodes, selectedNodeId, isElementAssociated, canvasColors, isDark, zoom } =
      context;

    nodes.forEach((node) => {
      const isSelected = selectedNodeId === node.id;
      const hasSensor = isElementAssociated(node.id);

      ctx.beginPath();

      if (isSelected) {
        const radius = 9.0 / zoom;
        ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
        const color = hasSensor ? canvasColors.roadSelected : canvasColors.roadActive;
        ctx.fillStyle = color;
        ctx.shadowColor = color;
        ctx.shadowBlur = isDark ? 16 : 10;
        ctx.fill();

        ctx.lineWidth = 2.4 / zoom;
        ctx.strokeStyle = '#ffffff';
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
        ctx.stroke();
      } else if (hasSensor) {
        const radius = 7.5 / zoom;
        ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = canvasColors.roadMonitored;
        ctx.shadowColor = canvasColors.roadMonitored;
        ctx.shadowBlur = 12;
        ctx.fill();

        ctx.lineWidth = 2.0 / zoom;
        ctx.strokeStyle = '#ffffff';
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
        ctx.stroke();
      } else if (node.is_tls) {
        // Semáforo (TLS) - Marcador Azul/Ciano elétrico vibrante com anel branco
        const radius = 7.0 / zoom;
        ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = '#0284c7';
        ctx.shadowColor = '#0ea5e9';
        ctx.shadowBlur = 10;
        ctx.fill();

        ctx.lineWidth = 2.0 / zoom;
        ctx.strokeStyle = '#ffffff';
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
        ctx.stroke();
      } else {
        // Cruzamento Comum (Sem Semáforo) - Ponto Branco/Prata Luminoso com anel escuro
        const radius = 5.5 / zoom;
        ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = isDark ? '#e2e8f0' : '#ffffff';
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
        ctx.fill();

        // Anel de contorno de alta definição para nunca se perder na rua
        ctx.lineWidth = 2.0 / zoom;
        ctx.strokeStyle = isDark ? '#020617' : '#0f172a';
        ctx.stroke();
      }
    });
  }
}
