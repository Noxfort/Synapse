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
// File: ui/src_ui/services/api/SecurityService.ts
// Author: Gabriel Moraes
// Date: 2026-09-03

import { ITransportClient, getTransportClient, UnlistenFn } from '../transport';

export interface AuthResponse {
  success: boolean;
  role: 'OPERATOR' | 'SUPERUSER' | 'MASTER';
  username: string;
}

export interface UserAccount {
  username: string;
  role: 'OPERATOR' | 'SUPERUSER';
}

export class SecurityService {
  constructor(private transport: ITransportClient = getTransportClient()) {}

  /**
   * Authenticates user credentials against the security manager.
   */
  async authenticate(username: string, password: string): Promise<AuthResponse> {
    return await this.transport.invoke<
      { username: string; password: string },
      AuthResponse
    >('authenticate', { username, password });
  }

  /**
   * Checks if the system is currently in lockdown failsafe mode.
   */
  async checkLockdown(): Promise<{ active: boolean }> {
    return await this.transport.invoke<undefined, { active: boolean }>('check_lockdown');
  }

  /**
   * Lists all registered user accounts.
   */
  async listUsers(): Promise<{ users: UserAccount[] }> {
    return await this.transport.invoke<undefined, { users: UserAccount[] }>('list_users');
  }

  /**
   * Adds a new user account.
   */
  async addUser(username: string, password: string, role: 'OPERATOR' | 'SUPERUSER'): Promise<{ success: boolean; users: UserAccount[] }> {
    return await this.transport.invoke<
      { username: string; password: string; role: string },
      { success: boolean; users: UserAccount[] }
    >('add_user', { username, password, role });
  }

  /**
   * Removes an existing user account (admin is protected).
   */
  async removeUser(username: string): Promise<{ success: boolean; users: UserAccount[] }> {
    return await this.transport.invoke<
      { username: string },
      { success: boolean; users: UserAccount[] }
    >('remove_user', { username });
  }

  /**
   * Fetches the recent security audit logs.
   */
  async getAuditLogs(limit: number = 100): Promise<{ logs: any[] }> {
    return await this.transport.invoke<{ limit: number }, { logs: any[] }>('get_audit_logs', { limit });
  }

  /**
   * Subscribes to backend lockdown events.
   */
  async onLockdownEvent(callback: (data: { active: boolean }) => void): Promise<UnlistenFn> {
    return await this.transport.listen<{ active: boolean }>('synapse:lockdown_event', callback);
  }
}

export const securityService = new SecurityService();
