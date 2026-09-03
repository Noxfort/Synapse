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
// File: ui/src_ui/components/map/hooks/useMapInteraction.ts
// Author: Gabriel Moraes
// Date: 2026-08-29

import React, { useState, useEffect, RefObject } from 'react';
import { MapNodeData, MapEdgeData, Point2D } from '../../../types/topology';
import { DataSourceItem, EngineDataPayload } from '../../../types/sensors';
import { calculateBoundingBox, calculateFitTransform, screenToSumoCoords, distToSegment, distToPolyline } from '../../../utils/geometry';

interface UseMapInteractionProps {
  canvasRef: RefObject<HTMLCanvasElement | null>;
  nodes: MapNodeData[];
  edges: MapEdgeData[];
  sources?: DataSourceItem[];
  latestEngineData?: EngineDataPayload | null;
  onSelectNode: (id: string | null) => void;
  onSelectEdge: (id: string | null) => void;
  onElementClicked?: (elementId: string, type: 'node' | 'edge') => void;
}

export function useMapInteraction({
  canvasRef,
  nodes,
  edges,
  sources = [],
  latestEngineData,
  onSelectNode,
  onSelectEdge,
  onElementClicked,
}: UseMapInteractionProps) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState<Point2D>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState<Point2D>({ x: 0, y: 0 });
  const [hoveredInfo, setHoveredInfo] = useState<string | null>(null);

  // Auto-fit bounding box on initial map load
  useEffect(() => {
    if (nodes.length === 0 || !canvasRef.current) return;

    const box = calculateBoundingBox(nodes);
    const width = canvasRef.current.width || 800;
    const height = canvasRef.current.height || 600;

    const { zoom: initialZoom, pan: initialPan } = calculateFitTransform(box, width, height);
    setZoom(initialZoom);
    setPan(initialPan);
  }, [nodes, canvasRef]);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0 || e.button === 2) {
      setIsDragging(true);
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => setIsDragging(false);

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
    setZoom((prev) => Math.max(0.05, Math.min(prev * zoomFactor, 80)));
  };

  const handleClick = (e: React.MouseEvent) => {
    if (!canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const screenPos: Point2D = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };

    const sumoCoords = screenToSumoCoords(screenPos, pan, zoom);
    const nodeThreshold = 16 / zoom;
    const edgeThreshold = 14 / zoom;

    const nodeMap = new Map<string, MapNodeData>();
    nodes.forEach((n) => nodeMap.set(n.id, n));

    // 1. Raycast Node Clicks
    let clickedNode: MapNodeData | null = null;
    for (const node of nodes) {
      const dist = Math.hypot(node.x - sumoCoords.x, node.y - sumoCoords.y);
      if (dist <= nodeThreshold) {
        clickedNode = node;
        break;
      }
    }

    if (clickedNode) {
      onSelectNode(clickedNode.id);
      const associatedSensor = sources.find(
        (s) => s.associated_element === clickedNode?.id
      );
      const liveNode = latestEngineData?.sensor_snapshot?.[clickedNode.id];
      const nodeVal =
        typeof liveNode === 'object' && liveNode !== null && liveNode.value !== undefined
          ? Number(liveNode.value)
          : typeof liveNode === 'number'
          ? liveNode
          : null;

      if (associatedSensor) {
        setHoveredInfo(`Cruzamento ${clickedNode.id} • Sensor: ${associatedSensor.name} (${associatedSensor.id})`);
      } else if (nodeVal !== null && !isNaN(nodeVal) && nodeVal > 0) {
        setHoveredInfo(`Cruzamento ${clickedNode.id} • Fluxo Imputado: ${nodeVal.toFixed(1)} veíc/min • TLS: ${clickedNode.is_tls ? 'SIM' : 'NÃO'}`);
      } else {
        setHoveredInfo(`Cruzamento ${clickedNode.id} (Semáforo TLS: ${clickedNode.is_tls ? 'SIM' : 'NÃO'})`);
      }
      if (onElementClicked) {
        onElementClicked(clickedNode.id, 'node');
      }
      return;
    }

    // 2. Raycast Edge Clicks (supporting seamless node-to-node multi-segment shape polylines)
    let clickedEdge: MapEdgeData | null = null;
    for (const edge of edges) {
      const fromNode = nodeMap.get(edge.from);
      const toNode = nodeMap.get(edge.to);

      let polyline: number[][] = [];
      if (edge.shape && edge.shape.length > 0) {
        polyline = [...edge.shape];
        if (fromNode && (polyline[0][0] !== fromNode.x || polyline[0][1] !== fromNode.y)) {
          polyline.unshift([fromNode.x, fromNode.y]);
        }
        if (toNode && (polyline[polyline.length - 1][0] !== toNode.x || polyline[polyline.length - 1][1] !== toNode.y)) {
          polyline.push([toNode.x, toNode.y]);
        }
      } else if (fromNode && toNode) {
        polyline = [[fromNode.x, fromNode.y], [toNode.x, toNode.y]];
      }

      let d = Infinity;
      if (polyline.length > 1) {
        d = distToPolyline(sumoCoords, polyline);
      }

      if (d <= edgeThreshold) {
        clickedEdge = edge;
        break;
      }
    }

    if (clickedEdge) {
      onSelectEdge(clickedEdge.id);
      const associatedSensor = sources.find(
        (s) =>
          s.associated_element === clickedEdge?.id ||
          s.associated_element === `-${clickedEdge?.id}` ||
          s.associated_element === clickedEdge?.id.replace(/^-/, '')
      );

      const live =
        latestEngineData?.edge_data?.[clickedEdge.id] ||
        latestEngineData?.edge_data?.[clickedEdge.id.replace(/^-/, '')] ||
        latestEngineData?.edge_data?.[`-${clickedEdge.id}`];

      if (associatedSensor) {
        const valStr =
          associatedSensor.latest_value !== undefined && associatedSensor.latest_value !== null
            ? ` [${Number(associatedSensor.latest_value).toFixed(1)} km/h]`
            : live
            ? ` [${live.speed.toFixed(1)} km/h]`
            : '';
        setHoveredInfo(`Via ${clickedEdge.id} • Sensor: ${associatedSensor.name}${valStr} • Densidade: ${live?.density ?? 15} v/km`);
      } else if (live) {
        const occPct = ((live.occupancy ?? 0.12) * 100).toFixed(0);
        setHoveredInfo(`Via ${clickedEdge.id} • Vel: ${live.speed.toFixed(1)} km/h • Densidade: ${live.density?.toFixed(1) ?? '15.0'} v/km • Ocupação: ${occPct}% • Fila: ${live.queue ?? 0} veíc [LWR Fluidodinâmico]`);
      } else {
        setHoveredInfo(`Via ${clickedEdge.id} (${clickedEdge.from} → ${clickedEdge.to})`);
      }

      if (onElementClicked) {
        onElementClicked(clickedEdge.id, 'edge');
      }
      return;
    }

    // Deselect if clicked in empty space
    onSelectNode(null);
    onSelectEdge(null);
    setHoveredInfo(null);
  };

  return {
    zoom,
    setZoom,
    pan,
    setPan,
    hoveredInfo,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    handleWheel,
    handleClick,
  };
}
