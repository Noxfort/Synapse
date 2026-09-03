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
// File: ui/src_ui/components/map/SumoMapCanvas.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React, { useRef, useState } from 'react';
import { useTopologyStore, useSensorsStore } from '../../stores';
import { sensorService } from '../../services/api';
import { useMapRenderer } from './hooks/useMapRenderer';
import { useMapInteraction } from './hooks/useMapInteraction';
import { MapOverlays } from './MapOverlays';

export const SumoMapCanvas: React.FC = () => {
  const {
    nodes,
    edges,
    mapLoaded,
    selectedNodeId,
    selectedEdgeId,
    isAssociatingSourceId,
    setSelectedNodeId,
    setSelectedEdgeId,
    setAssociatingSourceId,
  } = useTopologyStore();

  const { sources, latestEngineData, associateSourceToElement } = useSensorsStore();

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [associationNotice, setAssociationNotice] = useState<string | null>(null);

  const handleElementClicked = async (elementId: string, type: 'node' | 'edge') => {
    if (isAssociatingSourceId) {
      associateSourceToElement(isAssociatingSourceId, elementId);
      await sensorService.associateSource(isAssociatingSourceId, elementId);
      const label = type === 'node' ? `cruzamento '${elementId}'` : `via '${elementId}'`;
      setAssociationNotice(`Sensor '${isAssociatingSourceId}' vinculado com sucesso a ${label}`);
      setAssociatingSourceId(null);
      if (type === 'edge') {
        setSelectedEdgeId(elementId);
      } else {
        setSelectedNodeId(elementId);
      }
      setTimeout(() => setAssociationNotice(null), 4000);
    }
  };

  const {
    zoom,
    setZoom,
    pan,
    hoveredInfo,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    handleWheel,
    handleClick,
  } = useMapInteraction({
    canvasRef,
    nodes,
    edges,
    sources,
    latestEngineData,
    onSelectNode: setSelectedNodeId,
    onSelectEdge: setSelectedEdgeId,
    onElementClicked: handleElementClicked,
  });

  useMapRenderer({
    canvasRef,
    nodes,
    edges,
    sources,
    pan,
    zoom,
    selectedNodeId,
    selectedEdgeId,
    latestEngineData,
  });

  return (
    <div
      className={`relative w-full h-[calc(100vh-4rem-2rem)] overflow-hidden bg-background select-none flex items-center justify-center ${
        isAssociatingSourceId ? 'cursor-crosshair' : 'cursor-default'
      }`}
    >
      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onClick={handleClick}
        onWheel={handleWheel}
        className="w-full h-full"
      />

      <MapOverlays
        mapLoaded={mapLoaded}
        isAssociatingSourceId={isAssociatingSourceId}
        associationNotice={associationNotice}
        hoveredInfo={hoveredInfo}
        selectedEdgeId={selectedEdgeId}
        selectedNodeId={selectedNodeId}
        edges={edges}
        sources={sources}
        latestEngineData={latestEngineData}
        onCancelAssociation={() => setAssociatingSourceId(null)}
        onSelectEdge={setSelectedEdgeId}
        onSelectNode={setSelectedNodeId}
        onZoomIn={() => setZoom((z) => Math.min(z * 1.25, 80))}
        onZoomOut={() => setZoom((z) => Math.max(z * 0.8, 0.05))}
      />
    </div>
  );
};

