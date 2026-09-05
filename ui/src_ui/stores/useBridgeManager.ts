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
// Date: 2026-08-29 (Refactored to SOLID: 2026-09-04)

import { UnlistenFn } from '../services/transport';
import { SynapseBridge } from '../services/bridge';

/**
 * Backward-Compatibility Facade (SOLID: DIP / Facade Pattern).
 * Preserves the public API contract for existing components (AppLayout, useSynapseStore)
 * while delegating all lifecycle, health watching, state hydration, and domain event routing
 * to decoupled, testable SOLID services in `services/bridge/`.
 */
export async function initSynapseBridge(): Promise<UnlistenFn> {
  const bridge = SynapseBridge.createDefault();
  return await bridge.initialize();
}

// Re-export bridge architecture for consumers
export * from '../services/bridge';
