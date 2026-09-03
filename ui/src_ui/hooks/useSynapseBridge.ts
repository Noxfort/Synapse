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
// File: ui/src_ui/hooks/useSynapseBridge.ts
// Author: Gabriel Moraes
// Date: 2026-08-29

import { useSystemStore, useTopologyStore, useSensorsStore, useXaiStore, useEtlStore, initSynapseBridge } from '../stores';
import { getTransportClient } from '../services/transport';

/**
 * Facade Store for backward-compatibility.
 * Delegates all state and actions to granular SOLID stores and services.
 */
export const useSynapseStore = () => {
  const system = useSystemStore();
  const topology = useTopologyStore();
  const sensors = useSensorsStore();
  const xai = useXaiStore();
  const etl = useEtlStore();

  const transport = getTransportClient();

  const sendCommand = async (action: string, payload: any = {}) => {
    try {
      return await transport.invoke(action, payload);
    } catch (err: any) {
      system.addLog('ERROR', `IPC Command failed (${action}): ${err?.message || err}`);
      throw err;
    }
  };

  return {
    // System
    connected: system.connected,
    phase: system.phase,
    logs: system.logs,
    dbStatus: system.dbStatus,
    addLog: system.addLog,
    clearLogs: system.clearLogs,

    // Topology
    nodes: topology.nodes,
    edges: topology.edges,
    mapLoaded: topology.mapLoaded,
    selectedNodeId: topology.selectedNodeId,
    selectedEdgeId: topology.selectedEdgeId,
    isAssociatingSourceId: topology.isAssociatingSourceId,
    setTopology: topology.setTopology,
    setAssociatingSource: topology.setAssociatingSourceId,

    // Sensors & Telemetry
    sources: sensors.sources,
    selectedSourceId: sensors.selectedSourceId,
    latestEngineData: sensors.latestEngineData,
    lossHistory: sensors.lossHistory,
    driftHistory: sensors.driftHistory,
    setSelectedSource: sensors.setSelectedSourceId,

    // XAI
    verdicts: xai.verdicts,
    linguistLogs: xai.linguistLogs,
    xaiHistory: xai.xaiHistory,
    selectedXaiResultId: xai.selectedXaiResultId,
    setSelectedXaiResult: xai.setSelectedXaiResultId,

    // ETL
    parquetInspection: etl.parquetInspection,
    parquetProgress: etl.importProgress.progress,
    parquetStatus: etl.importProgress.status,

    // Actions & Bridge
    sendCommand,
    initBridge: initSynapseBridge,
  };
};
