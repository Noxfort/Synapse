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
// File: ui/src_ui/services/bridge/handlers/SystemEventHandler.ts
// Author: Gabriel Moraes
// Date: 2026-09-04

import { IBridgeEventHandler, LogLevel } from '../types';
import { SystemPhase } from '../../../types/system';

export interface ISystemEventSink {
  setConnected: (connected: boolean) => void;
  setPhase: (phase: SystemPhase) => void;
  addLog: (level: LogLevel, message: string) => void;
}

/**
 * Single Responsibility (SRP): Processes core system lifecycle, log messages, and phase transitions.
 */
export class SystemEventHandler implements IBridgeEventHandler {
  readonly events = [
    'synapse:ready',
    'synapse:log_message',
    'synapse:status_message',
    'synapse:phase_transition',
  ] as const;

  constructor(
    private readonly sink: ISystemEventSink,
    private readonly onReady?: () => Promise<void> | void
  ) {}

  async handle(event: string, payload: any): Promise<void> {
    switch (event) {
      case 'synapse:ready':
        this.sink.setConnected(true);
        this.sink.addLog('INFO', `Backend Daemon Online (${JSON.stringify(payload)})`);
        if (this.onReady) {
          await this.onReady();
        }
        break;

      case 'synapse:log_message':
        this.sink.addLog(payload?.level || 'INFO', payload?.message || String(payload));
        break;

      case 'synapse:status_message':
        this.sink.addLog('SYSTEM', payload?.message || String(payload));
        break;

      case 'synapse:phase_transition':
        if (payload?.phase) {
          this.sink.setPhase(payload.phase as SystemPhase);
          this.sink.addLog('SYSTEM', `Phase transitioned to: ${payload.phase}`);
        }
        break;
    }
  }
}
