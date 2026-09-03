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
// File: ui/src_ui/services/transport/index.ts
// Author: Gabriel Moraes
// Date: 2026-08-29

import { ITransportClient } from './ITransportClient';
import { TauriTransportClient } from './TauriTransportClient';

export * from './ITransportClient';
export * from './TauriTransportClient';

let clientInstance: ITransportClient | null = null;

export function isTauriEnvironment(): boolean {
  if (typeof window === 'undefined') return false;
  return Boolean(
    (window as any).__TAURI_INTERNALS__ ||
    (window as any).__TAURI__ ||
    (window as any).__TAURI_IPC__
  );
}

export function getTransportClient(): ITransportClient {
  if (!clientInstance) {
    clientInstance = new TauriTransportClient();
  }
  return clientInstance;
}

export function setTransportClient(customClient: ITransportClient) {
  clientInstance = customClient;
}
