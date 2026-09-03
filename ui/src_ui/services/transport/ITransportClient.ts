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
// File: ui/src_ui/services/transport/ITransportClient.ts
// Author: Gabriel Moraes
// Date: 2026-08-29

export type UnlistenFn = () => void;

export interface ITransportClient {
  /**
   * Invoke a command on the backend core process (IPC / REST / WebSocket).
   */
  invoke<TPayload = any, TResponse = any>(action: string, payload?: TPayload): Promise<TResponse>;

  /**
   * Listen to an asynchronous event stream emitted by the backend.
   */
  listen<TEvent = any>(event: string, callback: (data: TEvent) => void): Promise<UnlistenFn>;

  /**
   * Returns true if the client is connected to a native runtime (e.g., Tauri).
   */
  isNativeEnvironment(): boolean;
}
