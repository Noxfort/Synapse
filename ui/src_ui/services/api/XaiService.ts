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
// File: ui/src_ui/services/api/XaiService.ts
// Author: Gabriel Moraes
// Date: 2026-08-29

import { ITransportClient, getTransportClient } from '../transport';
import { OfficialReportData } from '../../types/report';

export class XaiService {
  constructor(private transport: ITransportClient = getTransportClient()) {}

  async explainBuffer(): Promise<{ success: boolean; message?: string }> {
    return await this.transport.invoke('explain_buffer');
  }

  async explainGlobal(): Promise<{ success: boolean; message?: string }> {
    return await this.transport.invoke('explain_global');
  }

  async explainLocal(nodeId: string): Promise<{ success: boolean; message?: string }> {
    return await this.transport.invoke('explain_local', { node_id: nodeId });
  }

  async generateOfficialReport(params?: Record<string, any>): Promise<{
    success: boolean;
    report: OfficialReportData;
    formatted_markdown?: string;
    error?: string;
  }> {
    return await this.transport.invoke('generate_official_report', params || {});
  }
}

export const xaiService = new XaiService();
