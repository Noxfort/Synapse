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
// File: ui/src_ui/services/api/SensorService.ts
// Author: Gabriel Moraes
// Date: 2026-08-29

import { ITransportClient, getTransportClient } from '../transport';
import { DataSourceItem } from '../../types/sensors';

export interface RegisterSourcePayload {
  id: string;
  name: string;
  is_local: boolean;
  connection?: string;
}

export class SensorService {
  constructor(private transport: ITransportClient = getTransportClient()) {}

  async getSources(): Promise<DataSourceItem[]> {
    const res: any = await this.transport.invoke('get_sources');
    if (Array.isArray(res)) return res;
    if (res && Array.isArray(res.sources)) return res.sources;
    return [];
  }

  async addSource(payload: RegisterSourcePayload): Promise<{ success: boolean; message?: string }> {
    return await this.transport.invoke('add_source', payload);
  }

  async removeSource(sourceId: string): Promise<{ success: boolean }> {
    return await this.transport.invoke('remove_source', { source_id: sourceId });
  }

  async toggleOrigin(sourceId: string): Promise<{ success: boolean }> {
    return await this.transport.invoke('toggle_origin', { source_id: sourceId });
  }

  async associateSource(sourceId: string, elementId: string): Promise<{ success: boolean }> {
    return await this.transport.invoke('associate_source', { source_id: sourceId, element_id: elementId });
  }
}

export const sensorService = new SensorService();
