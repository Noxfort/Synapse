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
// File: ui/src_ui/components/layout/LogConsole.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Terminal, Trash2, X, Search } from 'lucide-react';
import { useSystemStore } from '../../stores';

interface LogConsoleProps {
  isOpen: boolean;
  onClose: () => void;
}

export const LogConsole: React.FC<LogConsoleProps> = ({ isOpen, onClose }) => {
  const { t } = useTranslation();
  const logs = useSystemStore((s) => s.logs);
  const clearLogs = useSystemStore((s) => s.clearLogs);
  const [filter, setFilter] = useState('');

  if (!isOpen) return null;

  const filteredLogs = logs.filter(
    (l) => l.message.toLowerCase().includes(filter.toLowerCase()) || l.level.includes(filter.toUpperCase())
  );

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR':
        return 'text-rose-600 dark:text-rose-400 font-bold';
      case 'WARN':
        return 'text-amber-600 dark:text-amber-400 font-medium';
      case 'SYSTEM':
        return 'text-accent-cyan font-bold';
      default:
        return 'text-slate-700 dark:text-slate-300';
    }
  };

  return (
    <div className="absolute bottom-8 left-80 right-0 h-64 bg-surface/95 backdrop-blur-xl border-t border-border z-20 flex flex-col shadow-2xl animate-in slide-in-from-bottom duration-200">
      {/* Console Bar */}
      <div className="h-10 px-4 border-b border-border/80 flex items-center justify-between bg-background/50 select-none">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-primary-500 dark:text-primary-400" />
          <span className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider">{t('logs.title')}</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-mono">
            {filteredLogs.length} events
          </span>
        </div>

        {/* Search & Actions */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder={t('logs.filter')}
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="h-7 pl-8 pr-3 text-xs bg-surface border border-border rounded-lg text-slate-900 dark:text-slate-200 focus:outline-none focus:border-primary-500 font-mono"
            />
          </div>

          <button
            onClick={clearLogs}
            title={t('logs.clear')}
            className="p-1.5 rounded-lg bg-surface border border-border text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:border-slate-400 dark:hover:border-slate-600 transition-all"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-surface border border-border text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:border-slate-400 dark:hover:border-slate-600 transition-all"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Log Feed */}
      <div className="flex-1 p-3 font-mono text-xs overflow-y-auto space-y-1 select-text">
        {filteredLogs.length === 0 ? (
          <div className="text-center text-slate-400 dark:text-slate-600 py-8">No log events recorded yet.</div>
        ) : (
          filteredLogs.map((l) => (
            <div
              key={l.id}
              className="flex items-start gap-2.5 leading-relaxed hover:bg-black/[0.03] dark:hover:bg-white/[0.02] px-1 py-0.5 rounded"
            >
              <span className="text-slate-400 dark:text-slate-500 flex-shrink-0">{l.timestamp}</span>
              <span className={`flex-shrink-0 text-[10px] px-1 rounded bg-slate-200 dark:bg-slate-800/80 ${getLevelColor(l.level)}`}>
                [{l.level}]
              </span>
              <span className={`break-all ${getLevelColor(l.level)}`}>{l.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
