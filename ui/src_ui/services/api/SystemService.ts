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
// File: ui/src_ui/services/api/SystemService.ts
// Author: Gabriel Moraes
// Date: 2026-08-29

import { ITransportClient, getTransportClient } from '../transport';
import { DatabaseConfig } from '../../types/system';
import { ParquetInspectionResult } from '../../types/etl';

export class SystemService {
  constructor(private transport: ITransportClient = getTransportClient()) {}

  async getSystemStatus(): Promise<any> {
    return await this.transport.invoke('get_system_status');
  }

  async startOptimization(): Promise<any> {
    return await this.transport.invoke('start_optimization');
  }

  async stopOptimization(): Promise<any> {
    return await this.transport.invoke('stop_optimization');
  }

  async startOfflineBootstrap(): Promise<any> {
    return await this.transport.invoke('start_offline_bootstrap');
  }

  async stopOfflineBootstrap(): Promise<any> {
    return await this.transport.invoke('stop_offline_bootstrap');
  }

  async startOnlineOperation(): Promise<any> {
    return await this.transport.invoke('start_online_operation');
  }

  async stopOnlineOperation(): Promise<any> {
    return await this.transport.invoke('stop_online_operation');
  }

  async testDbConnection(config: DatabaseConfig): Promise<{ success: boolean; message: string }> {
    return await this.transport.invoke('test_db_connection', { config });
  }

  async initializeDb(rootPassword: string, config: DatabaseConfig): Promise<{ success: boolean; message: string }> {
    return await this.transport.invoke('initialize_db', { root_password: rootPassword, config });
  }

  async getDatabaseConfig(): Promise<any> {
    return await this.transport.invoke('get_database_config');
  }

  async disconnectDb(): Promise<any> {
    return await this.transport.invoke('disconnect_db');
  }

  async getTelemetryConfig(): Promise<any> {
    return await this.transport.invoke('get_telemetry_config');
  }

  async saveTelemetryConfig(config: { ip: string; host?: string; port?: number; connected: boolean }): Promise<any> {
    return await this.transport.invoke('save_telemetry_config', config);
  }

  async inspectParquet(path: string): Promise<ParquetInspectionResult> {
    return await this.transport.invoke('inspect_parquet', { path });
  }

  async importParquet(path: string): Promise<{ success: boolean; message?: string }> {
    return await this.transport.invoke('import_parquet', { path });
  }

  async getNetworkInfo(): Promise<{ local_ip: string }> {
    return await this.transport.invoke('get_network_info');
  }

  async pickFile(options?: {
    title?: string;
    filter?: string;
    filterName?: string;
    extensions?: string[];
  }): Promise<{ path: string | null; cancelled: boolean }> {
    let extensions = options?.extensions;
    let filterName = options?.filterName;

    if (options?.filter) {
      const parts = options.filter.split('|');
      if (!filterName) {
        filterName = parts[0]?.trim() || 'Arquivos';
      }
      if (!extensions && parts.length > 1) {
        extensions = parts[1]
          .trim()
          .split(/\s+/)
          .map((ext) => ext.replace(/^\*\./, '').replace(/^\./, ''))
          .filter(Boolean);
      }
    }

    try {
      const { invoke } = await import('@tauri-apps/api/core');
      const res = await invoke<string | null>('pick_file_dialog', {
        title: options?.title || 'Selecionar Arquivo',
        filterName: filterName || 'Arquivos',
        filterExtensions: extensions && extensions.length > 0 ? extensions : ['parquet'],
      });
      return { path: res, cancelled: res === null };
    } catch (err) {
      console.warn('[SystemService] Falha ao invocar Tauri pick_file_dialog, tentando IPC:', err);
      try {
        return await this.transport.invoke('pick_file', options || {});
      } catch (ipcErr) {
        console.warn('[SystemService] Falha ao invocar pick_file via IPC:', ipcErr);
        return { path: null, cancelled: false };
      }
    }
  }
}

export const systemService = new SystemService();
