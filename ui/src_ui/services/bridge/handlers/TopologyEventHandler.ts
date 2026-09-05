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
// File: ui/src_ui/services/bridge/handlers/TopologyEventHandler.ts
// Author: Gabriel Moraes
// Date: 2026-09-04

import { IBridgeEventHandler, LogLevel } from '../types';

export interface ITopologyEventSink {
  setTopology: (nodes: any[], edges: any[]) => void;
  addLog: (level: LogLevel, message: string) => void;
}

/**
 * Single Responsibility (SRP): Processes road network topology loading events.
 */
export class TopologyEventHandler implements IBridgeEventHandler {
  readonly events = ['synapse:map_loaded'] as const;

  constructor(private readonly sink: ITopologyEventSink) {}

  handle(event: string, payload: any): void {
    if (event === 'synapse:map_loaded') {
      if (payload?.nodes && payload?.edges) {
        this.sink.setTopology(payload.nodes, payload.edges);
        this.sink.addLog('INFO', `Map loaded: ${payload.nodes.length} nodes, ${payload.edges.length} edges`);
      }
    }
  }
}
