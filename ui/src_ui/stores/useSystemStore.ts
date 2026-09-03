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
// File: ui/src_ui/stores/useSystemStore.ts
// Author: Gabriel Moraes
// Date: 2026-08-29

import { create } from 'zustand';
import { SystemPhase, LogEntry, LogLevel, DatabaseStatus, MonitorStatus } from '../types/system';

export type ThemeMode = 'dark' | 'light';

const getInitialTheme = (): ThemeMode => {
  try {
    const saved = localStorage.getItem('synapse_theme');
    if (saved === 'light' || saved === 'dark') {
      return saved;
    }
  } catch {
    // fallback if localStorage not accessible
  }
  return 'dark';
};

const applyThemeClass = (theme: ThemeMode) => {
  if (typeof document !== 'undefined') {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
      root.classList.remove('light');
    } else {
      root.classList.add('light');
      root.classList.remove('dark');
    }
  }
};

const initialTheme = getInitialTheme();
applyThemeClass(initialTheme);

interface SystemState {
  connected: boolean;
  phase: SystemPhase;
  logs: LogEntry[];
  dbStatus: DatabaseStatus;
  monitorStatus: MonitorStatus;
  theme: ThemeMode;
  latencyMs: number;

  // Actions
  setConnected: (connected: boolean) => void;
  setPhase: (phase: SystemPhase) => void;
  addLog: (level: LogLevel, message: string) => void;
  clearLogs: () => void;
  setDbStatus: (status: Partial<DatabaseStatus>) => void;
  setMonitorStatus: (status: Partial<MonitorStatus>) => void;
  setTheme: (theme: ThemeMode) => void;
  toggleTheme: () => void;
  setLatencyMs: (latencyMs: number) => void;
}

export const useSystemStore = create<SystemState>((set) => ({
  connected: false,
  phase: 'IDLE_OPTIMIZATION',
  logs: [],
  dbStatus: { connected: false, message: '', checking: false },
  monitorStatus: { connected: false, ip: 'localhost', host: 'localhost', port: 1883, message: 'Desconectado' },
  theme: initialTheme,
  latencyMs: 0.0,

  setConnected: (connected) => set({ connected }),
  setPhase: (phase) => set({ phase }),
  setLatencyMs: (latencyMs) => set({ latencyMs }),

  addLog: (level, message) => {
    const entry: LogEntry = {
      id: Math.random().toString(36).substring(2, 9),
      timestamp: new Date().toLocaleTimeString(),
      level,
      message,
    };
    set((state) => ({ logs: [entry, ...state.logs].slice(0, 1000) }));
  },

  clearLogs: () => set({ logs: [] }),

  setDbStatus: (status) =>
    set((state) => ({ dbStatus: { ...state.dbStatus, ...status } })),

  setMonitorStatus: (status) =>
    set((state) => ({ monitorStatus: { ...state.monitorStatus, ...status } })),

  setTheme: (theme) => {
    try {
      localStorage.setItem('synapse_theme', theme);
    } catch {
      // ignore
    }
    applyThemeClass(theme);
    set({ theme });
  },

  toggleTheme: () => {
    set((state) => {
      const nextTheme = state.theme === 'dark' ? 'light' : 'dark';
      try {
        localStorage.setItem('synapse_theme', nextTheme);
      } catch {
        // ignore
      }
      applyThemeClass(nextTheme);
      return { theme: nextTheme };
    });
  },
}));

