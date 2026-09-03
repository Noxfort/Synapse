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
// File: ui/src_ui/components/layout/Header.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Activity, 
  Globe, 
  Settings as SettingsIcon, 
  ShieldCheck, 
  Terminal,
  BarChart3,
  Network,
  Sun,
  Moon,
  Maximize2,
  Minimize2,
  Minus
} from 'lucide-react';
import { useSystemStore } from '../../stores';
import { toggleFullscreen, minimizeToTray } from '../../utils/windowControls';

interface HeaderProps {
  activeTab: 'map' | 'dashboard' | 'xai';
  setActiveTab: (tab: 'map' | 'dashboard' | 'xai') => void;
  openSettings: () => void;
  openLogs: () => void;
  isLogsOpen: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  openSettings,
  openLogs,
  isLogsOpen,
}) => {
  const { t, i18n } = useTranslation();
  const { phase, theme, toggleTheme } = useSystemStore();
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    const checkFs = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', checkFs);
    return () => document.removeEventListener('fullscreenchange', checkFs);
  }, []);

  const handleToggleFullscreen = async () => {
    const nextFs = await toggleFullscreen();
    setIsFullscreen(nextFs);
  };

  const toggleLanguage = () => {
    const nextLang = i18n.language.startsWith('pt') ? 'en_US' : 'pt_BR';
    i18n.changeLanguage(nextLang);
  };

  const getPhaseBadge = () => {
    switch (phase) {
      case 'RUNNING_ONLINE':
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-500/30 rounded-full animate-pulse">
            <span className="w-2 h-2 rounded-full bg-emerald-500 dark:bg-emerald-400"></span> ONLINE HFT
          </span>
        );
      case 'RUNNING_OPTIMIZATION':
      case 'RUNNING_OFFLINE':
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 border border-amber-300 dark:border-amber-500/30 rounded-full animate-pulse">
            <span className="w-2 h-2 rounded-full bg-amber-500 dark:bg-amber-400"></span> COMPUTING
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 text-xs font-medium text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-full">
            <span className="w-2 h-2 rounded-full bg-slate-400 dark:bg-slate-500"></span> IDLE
          </span>
        );
    }
  };

  return (
    <header className="h-16 border-b border-border bg-surface/90 backdrop-blur-md px-6 flex items-center justify-between z-30 select-none">
      {/* Brand & Logo */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500/20 via-amber-500/10 to-transparent p-1 shadow-md shadow-primary-500/10 flex items-center justify-center border border-primary-500/20 bg-background/50">
          <img src="/logo.png" alt="SYNAPSE Logo" className="w-full h-full object-contain drop-shadow" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-bold text-lg tracking-tight bg-gradient-to-r from-slate-900 via-slate-700 to-slate-500 dark:from-white dark:via-slate-200 dark:to-slate-400 bg-clip-text text-transparent">
              {t('app.title')}
            </h1>
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-primary-500/15 text-primary-600 dark:text-primary-300 border border-primary-500/25">
              v2.0
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">{t('app.subtitle')}</p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <nav className="flex items-center gap-1 p-1 bg-background/80 border border-border rounded-xl">
        <button
          onClick={() => setActiveTab('map')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
            activeTab === 'map'
              ? 'bg-primary-600 text-white shadow-md shadow-primary-600/20'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-surfaceHover'
          }`}
        >
          <Network className="w-4 h-4" />
          {t('nav.map')}
        </button>

        <button
          onClick={() => setActiveTab('dashboard')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
            activeTab === 'dashboard'
              ? 'bg-primary-600 text-white shadow-md shadow-primary-600/20'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-surfaceHover'
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          {t('nav.dashboard')}
        </button>

        <button
          onClick={() => setActiveTab('xai')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
            activeTab === 'xai'
              ? 'bg-primary-600 text-white shadow-md shadow-primary-600/20'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-surfaceHover'
          }`}
        >
          <ShieldCheck className="w-4 h-4" />
          {t('nav.xai')}
        </button>
      </nav>

      {/* Action Indicators & Tools */}
      <div className="flex items-center gap-2.5">
        {getPhaseBadge()}

        {/* Theme Switcher Button (Light / Dark) */}
        <button
          onClick={toggleTheme}
          title={theme === 'dark' ? 'Mudar para Modo Claro' : 'Mudar para Modo Escuro'}
          className="p-2 rounded-lg bg-surface border border-border text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:border-primary-500/50 transition-all flex items-center justify-center shadow-sm"
        >
          {theme === 'dark' ? (
            <Sun className="w-4 h-4 text-accent-amber animate-spin-slow" />
          ) : (
            <Moon className="w-4 h-4 text-primary-600" />
          )}
        </button>

        {/* Language Switcher */}
        <button
          onClick={toggleLanguage}
          title={t('settings.language')}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-surface border border-border rounded-lg text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:border-primary-500/50 transition-all shadow-sm"
        >
          <Globe className="w-3.5 h-3.5 text-accent-cyan" />
          <span>{i18n.language.startsWith('pt') ? 'PT-BR' : 'EN-US'}</span>
        </button>

        {/* Toggle Logs Drawer */}
        <button
          onClick={openLogs}
          title={t('nav.logs')}
          className={`p-2 rounded-lg border transition-all ${
            isLogsOpen
              ? 'bg-primary-600/15 border-primary-500/50 text-primary-600 dark:text-primary-400'
              : 'bg-surface border-border text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:border-slate-400 dark:hover:border-slate-600'
          }`}
        >
          <Terminal className="w-4 h-4" />
        </button>

        {/* Settings Dialog */}
        <button
          onClick={openSettings}
          title={t('nav.settings')}
          className="p-2 rounded-lg bg-surface border border-border text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:border-slate-400 dark:hover:border-slate-600 transition-all"
        >
          <SettingsIcon className="w-4 h-4" />
        </button>

        <div className="w-[1px] h-5 bg-border mx-0.5" />

        {/* Fullscreen Toggle (F11) */}
        <button
          onClick={handleToggleFullscreen}
          title={isFullscreen ? 'Sair da Tela Cheia (F11)' : 'Tela Cheia (F11)'}
          className="p-2 rounded-lg bg-surface border border-border text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:border-primary-500/50 transition-all flex items-center justify-center shadow-sm"
        >
          {isFullscreen ? (
            <Minimize2 className="w-4 h-4 text-accent-cyan" />
          ) : (
            <Maximize2 className="w-4 h-4" />
          )}
        </button>

        {/* Minimize to Tray */}
        <button
          onClick={minimizeToTray}
          title="Minimizar para a Bandeja"
          className="p-2 rounded-lg bg-surface border border-border text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:border-amber-500/50 transition-all flex items-center justify-center shadow-sm"
        >
          <Minus className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};

