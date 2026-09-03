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
// File: ui/src_ui/services/transport/TauriTransportClient.ts
// Author: Gabriel Moraes
// Date: 2026-08-29

import { ITransportClient, UnlistenFn } from './ITransportClient';

export class TauriTransportClient implements ITransportClient {
  isNativeEnvironment(): boolean {
    if (typeof window === 'undefined') return false;
    return Boolean(
      (window as any).__TAURI_INTERNALS__ ||
      (window as any).__TAURI__ ||
      (window as any).__TAURI_IPC__
    );
  }

  async invoke<TPayload = any, TResponse = any>(
    action: string,
    payload: TPayload = {} as TPayload
  ): Promise<TResponse> {
    const { invoke } = await import('@tauri-apps/api/core');
    const { listen } = await import('@tauri-apps/api/event');
    const id = Math.random().toString(36).substring(2, 9);

    return new Promise<TResponse>(async (resolve, reject) => {
      let unlisten: (() => void) | undefined;
      const timeoutMs = 60000;

      const timer = setTimeout(() => {
        if (unlisten) unlisten();
        console.error(`[TauriTransport] ⏱️ Timeout (${timeoutMs}ms) aguardando comando '${action}' (id=${id})`);
        reject(new Error(`Command '${action}' timed out after ${timeoutMs}ms`));
      }, timeoutMs);

      try {
        unlisten = await listen<{ id?: string; success?: boolean; result?: any; error?: string }>(
          'synapse:response',
          (event) => {
            if (event.payload?.id === id) {
              clearTimeout(timer);
              if (unlisten) unlisten();
              if (event.payload.success === false) {
                console.error(`[TauriTransport] ❌ Comando '${action}' falhou:`, event.payload.error);
                reject(new Error(event.payload.error || 'Command failed'));
              } else {
                console.debug(`[TauriTransport] ✅ Comando '${action}' concluído com sucesso:`, event.payload.result);
                resolve(event.payload.result ?? ({ success: true } as unknown as TResponse));
              }
            }
          }
        );

        console.debug(`[TauriTransport] 🚀 Enviando comando '${action}' (id=${id}):`, payload);
        await invoke('send_synapse_command', { action, payload, id });
      } catch (err) {
        clearTimeout(timer);
        if (unlisten) unlisten();
        console.error(`[TauriTransport] ❌ Erro ao invocar comando '${action}':`, err);
        reject(err);
      }
    });
  }

  async listen<TEvent = any>(event: string, callback: (data: TEvent) => void): Promise<UnlistenFn> {
    const { listen } = await import('@tauri-apps/api/event');
    return await listen<TEvent>(event, (evt) => {
      callback(evt.payload);
    });
  }
}
