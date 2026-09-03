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
// File: ui/src_ui/components/map/MapOverlays.tsx
// Author: Gabriel Moraes
// Date: 2026-08-31

import React from 'react';
import { DataSourceItem, EngineDataPayload } from '../../types/sensors';
import { MapEdgeData } from '../../types/topology';
import { sensorService } from '../../services/api';
import { useSensorsStore } from '../../stores';
import {
  MapAssociationBanner,
  MapFluidEdgeInspector,
  MapNodeInspector,
  MapHoverBadge,
  MapTrafficLegend,
  MapZoomControls,
  MapEmptyState,
} from './overlays';

interface MapOverlaysProps {
  mapLoaded: boolean;
  isAssociatingSourceId: string | null;
  associationNotice: string | null;
  hoveredInfo: string | null;
  selectedEdgeId?: string | null;
  selectedNodeId?: string | null;
  edges?: MapEdgeData[];
  sources?: DataSourceItem[];
  latestEngineData?: EngineDataPayload | null;
  onCancelAssociation: () => void;
  onSelectEdge?: (id: string | null) => void;
  onSelectNode?: (id: string | null) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
}

export const MapOverlays: React.FC<MapOverlaysProps> = ({
  mapLoaded,
  isAssociatingSourceId,
  associationNotice,
  hoveredInfo,
  selectedEdgeId,
  selectedNodeId,
  edges = [],
  sources = [],
  latestEngineData,
  onCancelAssociation,
  onSelectEdge,
  onSelectNode,
  onZoomIn,
  onZoomOut,
}) => {
  const disassociateSource = useSensorsStore((s) => s.disassociateSource);

  const selectedElementId = selectedEdgeId || selectedNodeId;
  const currentEdge = selectedEdgeId ? edges.find((e) => e.id === selectedEdgeId) : null;

  const associatedSensor = selectedElementId
    ? sources.find(
        (s) =>
          s.associated_element === selectedElementId ||
          s.associated_element === `-${selectedElementId}` ||
          s.associated_element === selectedElementId.replace(/^-/, '')
      )
    : null;

  const liveEdge = selectedEdgeId
    ? latestEngineData?.edge_data?.[selectedEdgeId] ||
      latestEngineData?.edge_data?.[selectedEdgeId.replace(/^-/, '')] ||
      latestEngineData?.edge_data?.[`-${selectedEdgeId}`]
    : null;

  const handleDisassociate = async (sensorId: string) => {
    disassociateSource(sensorId);
    await sensorService.associateSource(sensorId, '');
  };

  return (
    <>
      {/* Association Crosshair Mode & Notifications */}
      <MapAssociationBanner
        isAssociatingSourceId={isAssociatingSourceId}
        associationNotice={associationNotice}
        onCancelAssociation={onCancelAssociation}
      />

      {/* Selected Edge: Comprehensive Fluid Dynamics Inspector */}
      {selectedEdgeId && (
        <MapFluidEdgeInspector
          edgeId={selectedEdgeId}
          currentEdge={currentEdge}
          liveEdgeData={liveEdge}
          associatedSensor={associatedSensor}
          onClose={() => onSelectEdge?.(null)}
          onDisassociate={handleDisassociate}
        />
      )}

      {/* Selected Node: Intersection Inspector */}
      {!selectedEdgeId && selectedNodeId && (
        <MapNodeInspector
          nodeId={selectedNodeId}
          infoText={hoveredInfo}
          onClose={() => onSelectNode?.(null)}
        />
      )}

      {/* Hover Information Badge */}
      {!selectedEdgeId && !selectedNodeId && (
        <MapHoverBadge hoveredInfo={hoveredInfo} />
      )}

      {/* Fluid Dynamics Heatmap Legend */}
      <MapTrafficLegend visible={mapLoaded} />

      {/* Canvas Zoom Controls */}
      <MapZoomControls onZoomIn={onZoomIn} onZoomOut={onZoomOut} />

      {/* Empty State Banner */}
      <MapEmptyState mapLoaded={mapLoaded} />
    </>
  );
};


