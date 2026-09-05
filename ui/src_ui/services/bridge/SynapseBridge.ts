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
// File: ui/src_ui/services/bridge/SynapseBridge.ts
// Author: Gabriel Moraes
// Date: 2026-09-04

import { UnlistenFn, getTransportClient } from '../transport';
import {
  ISynapseBridge,
  IBridgeEventRouter,
  IConnectionHealthWatcher,
  IStateHydrator,
  IConnectionSink,
  IStateHydratorSink,
} from './types';
import { BridgeEventRouter } from './BridgeEventRouter';
import { ConnectionHealthWatcher } from './ConnectionHealthWatcher';
import { StateHydrator } from './StateHydrator';
import { SystemEventHandler, ISystemEventSink } from './handlers/SystemEventHandler';
import { TopologyEventHandler, ITopologyEventSink } from './handlers/TopologyEventHandler';
import { SensorsEventHandler, ISensorsEventSink } from './handlers/SensorsEventHandler';
import { XaiEventHandler, IXaiEventSink } from './handlers/XaiEventHandler';
import { EtlEventHandler, IEtlEventSink } from './handlers/EtlEventHandler';

// Concrete store and service imports for the default production factory
import { systemService, topologyService, sensorService } from '../api';
import { useSystemStore } from '../../stores/useSystemStore';
import { useTopologyStore } from '../../stores/useTopologyStore';
import { useSensorsStore } from '../../stores/useSensorsStore';
import { useXaiStore } from '../../stores/useXaiStore';
import { useEtlStore } from '../../stores/useEtlStore';

/**
 * Dependency Inversion Principle (DIP) & Facade Pattern:
 * Coordinates event routing, connection health monitoring, and state hydration.
 * Receives all collaborators via constructor for 100% isolated unit testability.
 */
export class SynapseBridge implements ISynapseBridge {
  private unlistenRouter: UnlistenFn | null = null;

  constructor(
    private readonly eventRouter: IBridgeEventRouter,
    private readonly healthWatcher: IConnectionHealthWatcher,
    private readonly hydrator: IStateHydrator,
    private readonly connectionSink: IConnectionSink
  ) {}

  async initialize(): Promise<UnlistenFn> {
    this.connectionSink.addLog('SYSTEM', 'Initializing SYNAPSE Native Piped IPC Bridge...');

    // 1. Start event router
    this.unlistenRouter = await this.eventRouter.start();

    // 2. Start connection health monitor & heartbeat (triggers hydration on successful handshake)
    this.healthWatcher.start(async () => {
      await this.hydrator.hydrate();
    });

    return () => this.dispose();
  }

  dispose(): void {
    this.healthWatcher.dispose();
    if (this.unlistenRouter) {
      this.unlistenRouter();
      this.unlistenRouter = null;
    }
  }

  /**
   * Factory method assembling the default production bridge with Zustand stores and API services.
   */
  static createDefault(): SynapseBridge {
    const transport = getTransportClient();

    // 1. Connection Sink
    const connectionSink: IConnectionSink = {
      setConnected: (c) => useSystemStore.getState().setConnected(c),
      setLatencyMs: (l) => useSystemStore.getState().setLatencyMs(l),
      addLog: (lvl, msg) => useSystemStore.getState().addLog(lvl, msg),
      isConnected: () => useSystemStore.getState().connected,
    };

    // 2. State Hydrator Sink
    const hydratorSink: IStateHydratorSink = {
      setPhase: (p) => useSystemStore.getState().setPhase(p as any),
      setTopology: (nodes, edges) => useTopologyStore.getState().setTopology(nodes, edges),
      setSources: (srcs) => useSensorsStore.getState().setSources(srcs),
      setDbStatus: (st) => useSystemStore.getState().setDbStatus(st),
      setMonitorStatus: (st) => useSystemStore.getState().setMonitorStatus(st),
      addLog: (lvl, msg) => useSystemStore.getState().addLog(lvl, msg),
    };

    const hydrator = new StateHydrator(systemService, topologyService, sensorService, hydratorSink);

    // 3. Domain Event Sinks & Handlers
    const systemSink: ISystemEventSink = {
      setConnected: (c) => useSystemStore.getState().setConnected(c),
      setPhase: (p) => useSystemStore.getState().setPhase(p),
      addLog: (lvl, msg) => useSystemStore.getState().addLog(lvl, msg),
    };
    const systemHandler = new SystemEventHandler(systemSink, () => hydrator.hydrate());

    const topologySink: ITopologyEventSink = {
      setTopology: (n, e) => useTopologyStore.getState().setTopology(n, e),
      addLog: (lvl, msg) => useSystemStore.getState().addLog(lvl, msg),
    };
    const topologyHandler = new TopologyEventHandler(topologySink);

    const sensorsSink: ISensorsEventSink = {
      handleEngineDataPayload: (p) => useSensorsStore.getState().handleEngineDataPayload(p),
      addSourceItem: (s) => useSensorsStore.getState().addSourceItem(s),
      removeSourceItem: (id) => useSensorsStore.getState().removeSourceItem(id),
      associateSourceToElement: (sId, eId) => useSensorsStore.getState().associateSourceToElement(sId, eId),
      addLog: (lvl, msg) => useSystemStore.getState().addLog(lvl, msg),
    };
    const sensorsHandler = new SensorsEventHandler(sensorsSink);

    const xaiSink: IXaiEventSink = {
      addVerdict: (v) => useXaiStore.getState().addVerdict(v),
      handleEngineDataPayload: (p) => useSensorsStore.getState().handleEngineDataPayload(p),
      addLinguistLog: (l) => useXaiStore.getState().addLinguistLog(l),
      updateSourceItem: (id, u) => useSensorsStore.getState().updateSourceItem(id, u),
      addXaiResult: (x) => useXaiStore.getState().addXaiResult(x),
      addLog: (lvl, msg) => useSystemStore.getState().addLog(lvl, msg),
    };
    const xaiHandler = new XaiEventHandler(xaiSink);

    const etlSink: IEtlEventSink = {
      setImportProgress: (p) => useEtlStore.getState().setImportProgress(p),
      addLog: (lvl, msg) => useSystemStore.getState().addLog(lvl, msg),
    };
    const etlHandler = new EtlEventHandler(etlSink);

    // 4. Router & Handlers Registration
    const router = new BridgeEventRouter(transport);
    router.registerHandler(systemHandler);
    router.registerHandler(topologyHandler);
    router.registerHandler(sensorsHandler);
    router.registerHandler(xaiHandler);
    router.registerHandler(etlHandler);

    // 5. Connection Health Watcher
    const healthWatcher = new ConnectionHealthWatcher(transport, connectionSink);

    return new SynapseBridge(router, healthWatcher, hydrator, connectionSink);
  }
}
