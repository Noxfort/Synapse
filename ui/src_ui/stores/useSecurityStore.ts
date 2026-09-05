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
// File: ui/src_ui/stores/useSecurityStore.ts
// Author: Gabriel Moraes
// Date: 2026-09-03

import { create } from 'zustand';
import { securityService, UserAccount } from '../services/api';

export interface UserSession {
  username: string;
  role: 'OPERATOR' | 'SUPERUSER' | 'MASTER';
}

export interface AuditLogEntry {
  timestamp: string;
  username: string;
  action: string;
  details: string;
}

interface SecurityState {
  currentUser: UserSession | null;
  isAuthenticated: boolean;
  isLockedDown: boolean;
  isAuthModalOpen: boolean;
  pendingAction: (() => void | Promise<any>) | null;
  isAuthenticating: boolean;
  authError: string | null;
  registeredUsers: UserAccount[];
  isLoadingUsers: boolean;
  auditLogs: AuditLogEntry[];
  isLoadingAuditLogs: boolean;

  // Actions
  requestAuth: (action: () => void | Promise<any>) => void;
  cancelAuth: () => void;
  submitAuth: (username: string, password: string) => Promise<boolean>;
  submitUnlock: (username: string, password: string) => Promise<boolean>;
  checkLockdown: () => Promise<boolean>;
  setLockedDown: (locked: boolean) => void;
  fetchUsers: () => Promise<void>;
  addUser: (username: string, password: string, role: 'OPERATOR' | 'SUPERUSER') => Promise<boolean>;
  removeUser: (username: string) => Promise<boolean>;
  fetchAuditLogs: (limit?: number) => Promise<void>;
  logout: () => void;
}

export const useSecurityStore = create<SecurityState>((set, get) => ({
  currentUser: null,
  isAuthenticated: false,
  isLockedDown: false,
  isAuthModalOpen: false,
  pendingAction: null,
  isAuthenticating: false,
  authError: null,
  registeredUsers: [],
  isLoadingUsers: false,
  auditLogs: [],
  isLoadingAuditLogs: false,

  requestAuth: (action) => {
    // If system is in lockdown, do not open standard auth modal
    if (get().isLockedDown) {
      return;
    }
    set({
      pendingAction: action,
      isAuthModalOpen: true,
      authError: null,
      isAuthenticating: false,
    });
  },

  cancelAuth: () => {
    set({
      isAuthModalOpen: false,
      pendingAction: null,
      authError: null,
      isAuthenticating: false,
    });
  },

  submitAuth: async (username: string, password: string) => {
    set({ isAuthenticating: true, authError: null });
    try {
      const res = await securityService.authenticate(username, password);
      if (res && res.success) {
        const session: UserSession = { username: res.username, role: res.role };
        const action = get().pendingAction;
        set({
          currentUser: session,
          isAuthenticated: true,
          isAuthModalOpen: false,
          pendingAction: null,
          isAuthenticating: false,
          authError: null,
        });

        if (action) {
          try {
            await action();
          } catch (err) {
            console.error('[SecurityStore] Error executing pending action:', err);
          }
        }
        return true;
      }
      set({
        isAuthenticating: false,
        authError: 'Credenciais inválidas.',
      });
      return false;
    } catch (err: any) {
      const errMsg = err?.message || 'Falha de autenticação.';
      set({
        isAuthenticating: false,
        authError: errMsg,
      });
      // Check if this failure triggered lockdown
      await get().checkLockdown();
      return false;
    }
  },

  submitUnlock: async (username: string, password: string) => {
    set({ isAuthenticating: true, authError: null });
    try {
      const res = await securityService.authenticate(username, password);
      if (res && res.success) {
        if (res.role === 'SUPERUSER' || res.role === 'MASTER') {
          const session: UserSession = { username: res.username, role: res.role };
          set({
            currentUser: session,
            isAuthenticated: true,
            isLockedDown: false,
            isAuthenticating: false,
            authError: null,
          });
          return true;
        } else {
          set({
            isAuthenticating: false,
            authError: 'Apenas Super Usuários ou a Chave Mestra podem desbloquear o sistema.',
          });
          return false;
        }
      }
      set({
        isAuthenticating: false,
        authError: 'Credenciais inválidas.',
      });
      return false;
    } catch (err: any) {
      set({
        isAuthenticating: false,
        authError: err?.message || 'Falha ao autenticar para desbloqueio.',
      });
      return false;
    }
  },

  checkLockdown: async () => {
    try {
      const res = await securityService.checkLockdown();
      const active = Boolean(res?.active);
      set({ isLockedDown: active });
      if (active) {
        set({ isAuthModalOpen: false, pendingAction: null });
      }
      return active;
    } catch (err) {
      console.warn('[SecurityStore] Could not check lockdown status:', err);
      return false;
    }
  },

  setLockedDown: (locked: boolean) => {
    set({ isLockedDown: locked });
    if (locked) {
      set({ isAuthModalOpen: false, pendingAction: null });
    }
  },

  fetchUsers: async () => {
    set({ isLoadingUsers: true });
    try {
      const res = await securityService.listUsers();
      set({ registeredUsers: res.users || [], isLoadingUsers: false });
    } catch (err) {
      console.error('[SecurityStore] Failed to fetch users:', err);
      set({ isLoadingUsers: false });
    }
  },

  addUser: async (username, password, role) => {
    try {
      const res = await securityService.addUser(username, password, role);
      if (res && res.success) {
        set({ registeredUsers: res.users || [] });
        return true;
      }
      return false;
    } catch (err) {
      console.error('[SecurityStore] Failed to add user:', err);
      return false;
    }
  },

  removeUser: async (username) => {
    try {
      const res = await securityService.removeUser(username);
      if (res && res.success) {
        set({ registeredUsers: res.users || [] });
        return true;
      }
      return false;
    } catch (err) {
      console.error('[SecurityStore] Failed to remove user:', err);
      return false;
    }
  },

  fetchAuditLogs: async (limit = 100) => {
    set({ isLoadingAuditLogs: true });
    try {
      const res = await securityService.getAuditLogs(limit);
      set({ auditLogs: (res && res.logs) || [], isLoadingAuditLogs: false });
    } catch (err) {
      console.error('[SecurityStore] Failed to fetch audit logs:', err);
      set({ isLoadingAuditLogs: false });
    }
  },

  logout: () => {
    set({
      currentUser: null,
      isAuthenticated: false,
      pendingAction: null,
      authError: null,
    });
  },
}));
