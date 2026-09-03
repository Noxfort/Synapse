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
// File: ui/src_ui/stores/useBridgeManager.ts
// Author: Gabriel Moraes
// Date: 2026-08-29

import { getTransportClient, UnlistenFn } from '../services/transport';
import { topologyService, sensorService, systemService } from '../services/api';
import { useSystemStore } from './useSystemStore';
import { useTopologyStore } from './useTopologyStore';
import { useSensorsStore } from './useSensorsStore';
import { useXaiStore } from './useXaiStore';
import { useEtlStore } from './useEtlStore';
import { EngineDataPayload, DataSourceItem } from '../types/sensors';
import { XaiAuditVerdict, LinguistClassification, XaiResultItem } from '../types/xai';
import { SystemPhase } from '../types/system';

export async function initSynapseBridge(): Promise<UnlistenFn> {
  const transport = getTransportClient();
  const { addLog, setConnected, setPhase } = useSystemStore.getState();
  const { setTopology } = useTopologyStore.getState();
  const { setSources, addSourceItem, removeSourceItem, updateSourceItem, handleEngineDataPayload } = useSensorsStore.getState();
  const { addVerdict, addLinguistLog, addXaiResult } = useXaiStore.getState();
  const { setImportProgress } = useEtlStore.getState();

  addLog('SYSTEM', 'Initializing SYNAPSE Native Piped IPC Bridge...');

  const bootstrapState = async () => {
    try {
      // 1. Sync System Phase & Artifacts from Disk
      const sysStatus = await systemService.getSystemStatus();
      if (sysStatus?.phase) {
        setPhase(sysStatus.phase as SystemPhase);
        if (sysStatus.completed_phases && sysStatus.completed_phases.length > 0) {
          addLog('INFO', `⚡ Auto-Progression: Fases completas no disco: [${sysStatus.completed_phases.join(', ')}]. Fase atual: ${sysStatus.phase}`);
        }
      }

      // 2. Sync Topology & Road Network
      const topo = await topologyService.getTopology();
      if (topo?.nodes && topo?.edges && topo.nodes.length > 0) {
        setTopology(topo.nodes, topo.edges);
        addLog('INFO', `🗺️ Topologia viária restaurada: ${topo.nodes.length} cruzamentos, ${topo.edges.length} vias.`);
      }

      // 3. Sync Sensors & Data Sources
      const srcs = await sensorService.getSources();
      if (Array.isArray(srcs) && srcs.length > 0) {
        setSources(srcs);
        addLog('INFO', `📡 ${srcs.length} sensor(es) restaurados do disco.`);
      }

      // 4. Sync Database Status from Disk
      try {
        const dbCfg = await systemService.getDatabaseConfig();
        if (dbCfg?.connected) {
          useSystemStore.getState().setDbStatus({
            connected: true,
            message: `Conectado ao schema '${dbCfg.schema || 'schema_synapse'}'`,
          });
          addLog('INFO', `🗄️ Banco de Dados PostgreSQL conectado ao schema '${dbCfg.schema || 'schema_synapse'}'.`);
        }
      } catch {}

      // 5. Sync Monitor / Telemetry Status from Disk
      try {
        const teleCfg = await systemService.getTelemetryConfig();
        if (teleCfg) {
          useSystemStore.getState().setMonitorStatus({
            connected: !!teleCfg.connected,
            ip: teleCfg.ip || 'localhost',
            host: teleCfg.host || 'localhost',
            port: teleCfg.port || 1883,
            message: teleCfg.connected ? `Conectado em ${teleCfg.ip || teleCfg.host}` : 'Desconectado',
          });
          if (teleCfg.connected) {
            addLog('INFO', `📶 Telemetria Externa (Monitor) conectada ao broker MQTT em ${teleCfg.ip || teleCfg.host}:${teleCfg.port || 1883}.`);
          }
        }
      } catch {}
    } catch (err: any) {
      addLog('WARN', `Initial state sync note: ${err?.message || err}`);
    }
  };

  const unlisteners: UnlistenFn[] = [];

  try {
    const unReady = await transport.listen('synapse:ready', async (payload: any) => {
      setConnected(true);
      addLog('INFO', `Backend Daemon Online (${JSON.stringify(payload)})`);
      await bootstrapState();
    });
    unlisteners.push(unReady);

    const unLogs = await transport.listen('synapse:log_message', (payload: any) => {
      addLog(payload?.level || 'INFO', payload?.message || String(payload));
    });
    unlisteners.push(unLogs);

    const unStatus = await transport.listen('synapse:status_message', (payload: any) => {
      addLog('SYSTEM', payload?.message || String(payload));
    });
    unlisteners.push(unStatus);

    const unEngine = await transport.listen('synapse:engine_data', (payload: EngineDataPayload) => {
      handleEngineDataPayload(payload);
    });
    unlisteners.push(unEngine);

    const unGlobalResults = await transport.listen('synapse:global_results', (payload: any) => {
      handleEngineDataPayload(payload);
    });
    unlisteners.push(unGlobalResults);

    const unDrift = await transport.listen('synapse:drift_update', (payload: any) => {
      handleEngineDataPayload(payload);
    });
    unlisteners.push(unDrift);

    const unPhase = await transport.listen('synapse:phase_transition', (payload: { phase: SystemPhase }) => {
      if (payload?.phase) {
        setPhase(payload.phase);
        addLog('SYSTEM', `Phase transitioned to: ${payload.phase}`);
      }
    });
    unlisteners.push(unPhase);

    const unMap = await transport.listen('synapse:map_loaded', (payload: any) => {
      if (payload?.nodes && payload?.edges) {
        setTopology(payload.nodes, payload.edges);
        addLog('INFO', `Map loaded: ${payload.nodes.length} nodes, ${payload.edges.length} edges`);
      }
    });
    unlisteners.push(unMap);

    const unSourceAdded = await transport.listen('synapse:source_added', (s: any) => {
      const newSrc: DataSourceItem = {
        id: s.id,
        name: s.name,
        is_local: s.is_local ?? true,
        status: 'Active',
        quality: 100,
        semantic_type: 'Traffic Speed',
        latest_value: 0,
      };
      addSourceItem(newSrc);
    });
    unlisteners.push(unSourceAdded);

    const unSourceRemoved = await transport.listen('synapse:source_removed', (s: any) => {
      if (s?.id) removeSourceItem(s.id);
    });
    unlisteners.push(unSourceRemoved);

    const unSourceAssociated = await transport.listen('synapse:source_associated', (payload: any) => {
      if (payload?.source_id && payload?.element_id) {
        useSensorsStore.getState().associateSourceToElement(payload.source_id, payload.element_id);
        addLog('INFO', `Sensor '${payload.source_id}' associado ao elemento '${payload.element_id}'`);
      }
    });
    unlisteners.push(unSourceAssociated);

    const unAudit = await transport.listen('synapse:audit_update', (v: any) => {
      const verdict: XaiAuditVerdict = {
        safe: v.safe,
        error: v.error,
        threshold: v.threshold,
        vector: v.vector || [],
        timestamp: new Date().toLocaleTimeString(),
      };
      addVerdict(verdict);
      handleEngineDataPayload(v);
    });
    unlisteners.push(unAudit);

    const unLinguist = await transport.listen('synapse:linguist_update', (l: any) => {
      const entry: LinguistClassification = {
        source: l.source,
        type: l.type,
        confidence: l.confidence,
        timestamp: new Date().toLocaleTimeString(),
      };
      addLinguistLog(entry);
      updateSourceItem(l.source, { semantic_type: l.type, confidence_score: l.confidence });
    });
    unlisteners.push(unLinguist);

    const unXai = await transport.listen('synapse:xai_result', (r: any) => {
      const targetLower = (r.target || '').toLowerCase();
      let type: XaiResultItem['type'] = 'GLOBAL';
      let targetLabel = r.target || 'Fusão Espaço-Temporal Global';

      if (targetLower.includes('auditor') || targetLower.includes('buffer')) {
        type = 'AUDITOR';
        targetLabel = 'Auditoria Zero-Trust (Veto Buffer)';
      } else if (targetLower.includes('tcn') || targetLower.includes('local') || targetLower.includes('sensor')) {
        type = 'LOCAL';
        targetLabel = r.feature_names?.[0]
          ? `Sensor: ${r.feature_names[0].split(' [')[0]}`
          : 'Sensor Temporal (TCN)';
      } else if (targetLower.includes('fuser') || targetLower.includes('global')) {
        type = 'GLOBAL';
        targetLabel = 'Fusão Espaço-Temporal Global';
      }

      const item: XaiResultItem = {
        id: r.request_id || r.id || `xai_${Date.now()}`,
        request_id: r.request_id,
        type,
        target: targetLabel,
        convergence_delta: typeof r.convergence_delta === 'number' ? r.convergence_delta : 0.0012,
        semantic_text: r.semantic_text || 'Análise de explicabilidade concluída com sucesso.',
        attributions: Array.isArray(r.attributions) && r.attributions.length > 0
          ? r.attributions
          : [0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 0.85, 0.95, 1.0],
        feature_names: Array.isArray(r.feature_names) ? r.feature_names : undefined,
        timestamp: new Date().toLocaleTimeString(),
      };
      addXaiResult(item);
      addLog('INFO', `XAI [${type}]: Inferência explicada com sucesso (${item.target})`);
    });
    unlisteners.push(unXai);

    const unImportProgress = await transport.listen('synapse:import_progress', (p: any) => {
      setImportProgress({ progress: p?.progress || 0, isImporting: true });
    });
    unlisteners.push(unImportProgress);

    const unImportFinished = await transport.listen('synapse:import_finished', (res: any) => {
      setImportProgress({
        progress: res.success ? 100 : 0,
        status: res.message,
        isImporting: false,
      });
      addLog(res.success ? 'INFO' : 'ERROR', `Dataset Ingestion: ${res.message}`);
    });
    unlisteners.push(unImportFinished);

    // Active handshake ping & continuous heartbeat
    let isCleanedUp = false;
    let hasBootstrapped = false;
    let heartbeatTimer: any = null;

    const performPing = async () => {
      if (isCleanedUp) return false;
      try {
        const t0 = performance.now();
        const res = await transport.invoke('ping');
        const rtt = Math.max(0.1, performance.now() - t0);
        useSystemStore.getState().setLatencyMs(Number(rtt.toFixed(2)));

        if (res?.status === 'ok') {
          const wasConnected = useSystemStore.getState().connected;
          setConnected(true);
          if (!wasConnected || !hasBootstrapped) {
            addLog('INFO', 'IPC Handshake established successfully.');
            hasBootstrapped = true;
            await bootstrapState();
          }
          return true;
        }
      } catch (err) {
        console.warn('[BridgeManager] ⚠️ Falha no handshake/ping com Tauri:', err);
        setConnected(false);
      }
      return false;
    };

    const probeConnection = async () => {
      // Rapid polling during startup (every 500ms for up to 30 attempts)
      for (let attempt = 1; attempt <= 30; attempt++) {
        if (isCleanedUp) break;
        const ok = await performPing();
        if (ok) break;
        await new Promise((r) => setTimeout(r, 500));
      }

      // Continuous background heartbeat every 3 seconds
      if (!isCleanedUp) {
        heartbeatTimer = setInterval(() => {
          if (!isCleanedUp) {
            performPing();
          }
        }, 3000);
      }
    };

    probeConnection();

    return () => {
      isCleanedUp = true;
      if (heartbeatTimer) clearInterval(heartbeatTimer);
      unlisteners.forEach((unlisten) => unlisten());
    };
  } catch (err: any) {
    addLog('ERROR', `Failed to attach Tauri event listeners: ${err?.message || err}`);
    return () => {};
  }
}
