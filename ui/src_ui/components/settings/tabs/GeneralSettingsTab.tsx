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
// File: ui/src_ui/components/settings/tabs/GeneralSettingsTab.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Globe, Sun, Moon, Palette } from 'lucide-react';
import { useSystemStore } from '../../../stores';

export const GeneralSettingsTab: React.FC = () => {
  const { t, i18n } = useTranslation();
  const { theme, setTheme } = useSystemStore();
  const [logLevel, setLogLevel] = useState(() => {
    try {
      return localStorage.getItem('synapse_log_level') || 'INFO';
    } catch {
      return 'INFO';
    }
  });

  const handleLogLevelChange = (newLevel: string) => {
    setLogLevel(newLevel);
    try {
      localStorage.setItem('synapse_log_level', newLevel);
    } catch {}
  };

  return (
    <div className="space-y-5 text-xs">
      {/* Theme Mode Selector */}
      <div className="space-y-2">
        <label className="text-slate-700 dark:text-slate-300 font-semibold flex items-center gap-1.5">
          <Palette className="w-3.5 h-3.5 text-primary-500" />
          <span>Tema Visual da Interface</span>
        </label>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => setTheme('dark')}
            className={`py-2.5 px-3 rounded-xl border text-xs font-bold transition-all flex items-center justify-center gap-2 ${
              theme === 'dark'
                ? 'bg-primary-600/20 border-primary-500 text-primary-400 dark:text-primary-300 shadow-sm'
                : 'bg-surface border-border text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Moon className="w-4 h-4 text-primary-400" />
            <span>Modo Escuro (Obsidian Slate)</span>
          </button>
          <button
            onClick={() => setTheme('light')}
            className={`py-2.5 px-3 rounded-xl border text-xs font-bold transition-all flex items-center justify-center gap-2 ${
              theme === 'light'
                ? 'bg-primary-600/20 border-primary-500 text-primary-600 dark:text-primary-300 shadow-sm'
                : 'bg-surface border-border text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Sun className="w-4 h-4 text-accent-amber" />
            <span>Modo Claro (Polar Slate)</span>
          </button>
        </div>
      </div>

      {/* Language Selector */}
      <div className="space-y-2">
        <label className="text-slate-700 dark:text-slate-300 font-semibold flex items-center gap-1.5">
          <Globe className="w-3.5 h-3.5 text-accent-cyan" />
          {t('settings.language')}
        </label>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => i18n.changeLanguage('pt_BR')}
            className={`py-2.5 px-3 rounded-xl border text-xs font-bold transition-all ${
              i18n.language.startsWith('pt')
                ? 'bg-primary-600/20 border-primary-500 text-primary-600 dark:text-primary-300'
                : 'bg-surface border-border text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            🇧🇷 Português (Brasil)
          </button>
          <button
            onClick={() => i18n.changeLanguage('en_US')}
            className={`py-2.5 px-3 rounded-xl border text-xs font-bold transition-all ${
              i18n.language.startsWith('en')
                ? 'bg-primary-600/20 border-primary-500 text-primary-600 dark:text-primary-300'
                : 'bg-surface border-border text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            🇺🇸 English (US)
          </button>
        </div>
      </div>

      {/* Log Level */}
      <div className="space-y-1 pt-1">
        <label className="text-slate-700 dark:text-slate-300 font-semibold">Nível de Registro de Logs:</label>
        <select
          value={logLevel}
          onChange={(e) => handleLogLevelChange(e.target.value)}
          className="w-full h-9 px-3 bg-background border border-border rounded-xl text-slate-800 dark:text-slate-200 font-mono"
        >
          <option value="DEBUG">DEBUG (Detalhado)</option>
          <option value="INFO">INFO (Padrão Operacional)</option>
          <option value="WARNING">WARNING (Avisos)</option>
          <option value="ERROR">ERROR (Erros Críticos)</option>
        </select>
      </div>
    </div>
  );
};

