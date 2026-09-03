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
// File: ui/src_ui/services/api/TopologyService.ts
// Author: Gabriel Moraes
// Date: 2026-08-29

import { ITransportClient, getTransportClient } from '../transport';
import { TopologyPayload } from '../../types/topology';
import { useTopologyStore } from '../../stores/useTopologyStore';

export class TopologyService {
  constructor(private transport: ITransportClient = getTransportClient()) {}

  async loadMap(path: string): Promise<TopologyPayload> {
    const res = await this.transport.invoke<any, TopologyPayload>('load_map', { path });
    if (res && Array.isArray(res.nodes) && Array.isArray(res.edges)) {
      useTopologyStore.getState().setTopology(res.nodes, res.edges);
    }
    return res;
  }

  async getTopology(): Promise<TopologyPayload> {
    const res = await this.transport.invoke<any, TopologyPayload>('get_topology');
    if (res && Array.isArray(res.nodes) && Array.isArray(res.edges)) {
      useTopologyStore.getState().setTopology(res.nodes, res.edges);
    }
    return res;
  }
}

export const topologyService = new TopologyService();
