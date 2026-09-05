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
// File: ui/src_ui/services/bridge/BridgeEventRouter.ts
// Author: Gabriel Moraes
// Date: 2026-09-04

import { ITransportClient, UnlistenFn } from '../transport';
import { IBridgeEventHandler, IBridgeEventRouter } from './types';

/**
 * Open/Closed Principle (OCP) & Single Responsibility Principle (SRP):
 * Dynamically binds registered event handlers to the underlying transport listener stream.
 * New event domains can be added without modifying this router.
 */
export class BridgeEventRouter implements IBridgeEventRouter {
  private readonly handlers: IBridgeEventHandler[] = [];

  constructor(private readonly transport: ITransportClient) {}

  registerHandler(handler: IBridgeEventHandler): void {
    this.handlers.push(handler);
  }

  async start(): Promise<UnlistenFn> {
    const unlisteners: UnlistenFn[] = [];

    for (const handler of this.handlers) {
      for (const event of handler.events) {
        try {
          const unlisten = await this.transport.listen(event, async (data: any) => {
            try {
              await handler.handle(event, data);
            } catch (err) {
              console.error(`[BridgeEventRouter] Error handling event '${event}':`, err);
            }
          });
          unlisteners.push(unlisten);
        } catch (err) {
          console.error(`[BridgeEventRouter] Failed to attach listener for event '${event}':`, err);
        }
      }
    }

    return () => {
      unlisteners.forEach((unlisten) => {
        try {
          unlisten();
        } catch (err) {
          console.error('[BridgeEventRouter] Error executing unlistener:', err);
        }
      });
    };
  }
}
