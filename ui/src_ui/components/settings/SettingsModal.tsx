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
// File: ui/src_ui/components/settings/SettingsModal.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Globe, Database, Radio, Sliders, Landmark } from 'lucide-react';
import { DatabaseSettingsTab } from './tabs/DatabaseSettingsTab';
import { MonitorSettingsTab } from './tabs/MonitorSettingsTab';
import { GeneralSettingsTab } from './tabs/GeneralSettingsTab';
import { MunicipalSettingsTab } from './tabs/MunicipalSettingsTab';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<'municipal' | 'db' | 'monitor' | 'general'>('municipal');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in select-none">
      <div className="w-full max-w-3xl glass-panel bg-surface p-6 rounded-2xl shadow-2xl border border-border space-y-6 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border/80 pb-4">
          <h2 className="text-base font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
            <Sliders className="w-5 h-5 text-primary-500 dark:text-primary-400" />
            {t('settings.title')}
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-surfaceHover transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 border-b border-border/80 pb-2 overflow-x-auto">
          <button
            onClick={() => setActiveTab('municipal')}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 shrink-0 ${
              activeTab === 'municipal'
                ? 'bg-primary-600 text-white shadow-md shadow-primary-600/20'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-surfaceHover'
            }`}
          >
            <Landmark className="w-4 h-4" />
            <span>Identidade Municipal & Laudos</span>
          </button>

          <button
            onClick={() => setActiveTab('db')}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 shrink-0 ${
              activeTab === 'db'
                ? 'bg-primary-600 text-white shadow-md shadow-primary-600/20'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-surfaceHover'
            }`}
          >
            <Database className="w-4 h-4" />
            <span>Banco de Dados</span>
          </button>

          <button
            onClick={() => setActiveTab('monitor')}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 shrink-0 ${
              activeTab === 'monitor'
                ? 'bg-primary-600 text-white shadow-md shadow-primary-600/20'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-surfaceHover'
            }`}
          >
            <Radio className="w-4 h-4" />
            <span>Telemetria Externa</span>
          </button>

          <button
            onClick={() => setActiveTab('general')}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 shrink-0 ${
              activeTab === 'general'
                ? 'bg-primary-600 text-white shadow-md shadow-primary-600/20'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-surfaceHover'
            }`}
          >
            <Globe className="w-4 h-4" />
            <span>Geral & Tema</span>
          </button>
        </div>

        {/* Tab Content */}
        <div className="min-h-[280px]">
          {activeTab === 'municipal' && <MunicipalSettingsTab />}
          {activeTab === 'db' && <DatabaseSettingsTab />}
          {activeTab === 'monitor' && <MonitorSettingsTab />}
          {activeTab === 'general' && <GeneralSettingsTab />}
        </div>
      </div>
    </div>
  );
};
