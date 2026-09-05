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
// File: ui/src_ui/services/bridge/handlers/EtlEventHandler.ts
// Author: Gabriel Moraes
// Date: 2026-09-04

import { IBridgeEventHandler, LogLevel } from '../types';

export interface IEtlEventSink {
  setImportProgress: (progress: { progress: number; status?: string; isImporting: boolean }) => void;
  addLog: (level: LogLevel, message: string) => void;
}

/**
 * Single Responsibility (SRP): Processes Parquet / dataset asynchronous ingestion progress and completion.
 */
export class EtlEventHandler implements IBridgeEventHandler {
  readonly events = [
    'synapse:import_progress',
    'synapse:import_finished',
  ] as const;

  constructor(private readonly sink: IEtlEventSink) {}

  handle(event: string, payload: any): void {
    switch (event) {
      case 'synapse:import_progress':
        this.sink.setImportProgress({
          progress: payload?.progress || 0,
          isImporting: true,
        });
        break;

      case 'synapse:import_finished': {
        const res = payload || {};
        this.sink.setImportProgress({
          progress: res.success ? 100 : 0,
          status: res.message,
          isImporting: false,
        });
        this.sink.addLog(res.success ? 'INFO' : 'ERROR', `Dataset Ingestion: ${res.message}`);
        break;
      }
    }
  }
}
