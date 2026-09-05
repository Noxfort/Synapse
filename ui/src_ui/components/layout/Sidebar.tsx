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
// File: ui/src_ui/components/layout/Sidebar.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Play, 
  Square, 
  Database, 
  Radio, 
  Sparkles, 
  Trash2, 
  FolderOpen,
  PlusCircle,
  Crosshair,
  MoreVertical,
  ArrowRight,
  Lock,
  Check
} from 'lucide-react';
import { useSystemStore, useSensorsStore, useTopologyStore, useSecurityStore, useEtlStore } from '../../stores';
import { systemService, sensorService } from '../../services/api';
import { SystemPhase } from '../../types/system';

interface SidebarProps {
  openImportWizard: (step?: 1 | 2 | 3) => void;
  setActiveTab: (tab: 'map' | 'dashboard' | 'xai') => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ 
  openImportWizard, 
  setActiveTab
}) => {
  const { t } = useTranslation();
  const phase = useSystemStore((s) => s.phase);
  const sources = useSensorsStore((s) => s.sources);
  const mapLoaded = useTopologyStore((s) => s.mapLoaded || s.nodes.length > 0);
  const importProgress = useEtlStore((s) => s.importProgress);
  const setAssociatingSourceId = useTopologyStore((s) => s.setAssociatingSourceId);
  const requestAuth = useSecurityStore((s) => s.requestAuth);

  const [activeMenuSourceId, setActiveMenuSourceId] = useState<string | null>(null);

  // Prerequisites for starting Phase 0 (Optimization): Map, Parquet, and Sensors
  const hasMap = mapLoaded;
  const hasParquet = importProgress.progress === 100 || sources.some(
    (s) => s.connection_string?.toLowerCase().endsWith('.parquet') || s.source_type === 'Parquet' || s.id === 'historical_base'
  );
  const hasSensors = sources.some(
    (s) =>
      s.source_type === 'Parquet' ||
      s.connection_string?.toLowerCase().endsWith('.parquet') ||
      s.id === 'historical_base' ||
      (s.source_type !== 'SUMO Network' && s.id !== 'map_main')
  );

  const isOptPrerequisitesMet = hasMap && hasParquet && hasSensors;
  const isStartOptLocked = phase === 'IDLE_OPTIMIZATION' && !isOptPrerequisitesMet;

  const handleControlAction = async () => {
    if (isStartOptLocked) return;

    const executeAction = async () => {
      switch (phase) {
        case 'IDLE_OPTIMIZATION':
          await systemService.startOptimization();
          break;
        case 'RUNNING_OPTIMIZATION':
          await systemService.stopOptimization();
          break;
        case 'IDLE_OFFLINE':
          await systemService.startOfflineBootstrap();
          break;
        case 'RUNNING_OFFLINE':
          await systemService.stopOfflineBootstrap();
          break;
        case 'IDLE_ONLINE':
          await systemService.startOnlineOperation();
          break;
        case 'RUNNING_ONLINE':
          await systemService.stopOnlineOperation();
          break;
      }
    };

    // Sensitive control actions are guarded by the Security Layer
    requestAuth(executeAction);
  };

  const getOptLockTooltip = () => {
    if (!isStartOptLocked) return undefined;
    const missing: string[] = [];
    if (!hasMap) missing.push('Mapa');
    if (!hasParquet) missing.push('Parquet');
    if (!hasSensors) missing.push('Sensores');
    return `Pendente: ${missing.join(', ')}`;
  };

  const getButtonConfig = (currentPhase: SystemPhase) => {
    switch (currentPhase) {
      case 'IDLE_OPTIMIZATION':
        return {
          label: t('controls.btnStartOpt'),
          icon: isStartOptLocked ? Lock : Play,
          color: isStartOptLocked
            ? 'bg-slate-200 dark:bg-surface border border-border text-slate-400 dark:text-slate-500 cursor-not-allowed opacity-60 shadow-none'
            : 'bg-primary-600 hover:bg-primary-500 shadow-primary-600/20 text-white',
          active: false,
          disabled: isStartOptLocked,
        };
      case 'RUNNING_OPTIMIZATION':
        return {
          label: t('controls.btnStopOpt'),
          icon: Square,
          color: 'bg-rose-600 hover:bg-rose-500 shadow-rose-600/20 text-white',
          active: true,
          disabled: false,
        };
      case 'IDLE_OFFLINE':
        return {
          label: t('controls.btnStartOffline'),
          icon: Sparkles,
          color: 'bg-accent-cyan hover:bg-accent-cyan/90 text-slate-900 shadow-cyan-500/20',
          active: false,
          disabled: false,
        };
      case 'RUNNING_OFFLINE':
        return {
          label: t('controls.btnStopOffline'),
          icon: Square,
          color: 'bg-rose-600 hover:bg-rose-500 shadow-rose-600/20 text-white',
          active: true,
          disabled: false,
        };
      case 'IDLE_ONLINE':
        return {
          label: t('controls.btnStartOnline'),
          icon: Radio,
          color: 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-600/20 text-white',
          active: false,
          disabled: false,
        };
      case 'RUNNING_ONLINE':
        return {
          label: t('controls.btnStopOnline'),
          icon: Square,
          color: 'bg-rose-600 hover:bg-rose-500 shadow-rose-600/20 text-white',
          active: true,
          disabled: false,
        };
    }
  };

  const btn = getButtonConfig(phase);
  const Icon = btn.icon;

  const handleStartReassociation = (sourceId: string) => {
    setActiveTab('map');
    setAssociatingSourceId(sourceId);
    setActiveMenuSourceId(null);
  };

  return (
    <aside className="w-80 h-[calc(100vh-4rem-2rem)] border-r border-border bg-surface/60 flex flex-col justify-between select-none">
      <div className="p-4 space-y-4 overflow-y-auto flex-1">
        {/* 1. 3-Phase Lifecycle State Machine Card */}
        <div className="glass-panel p-4 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              {t('controls.phase')}
            </span>
          </div>

          <div className="p-3 bg-background/80 border border-border rounded-lg space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-sm font-bold text-slate-900 dark:text-white tracking-tight">
                {phase === 'IDLE_OPTIMIZATION' && t('controls.idleOptimization')}
                {phase === 'RUNNING_OPTIMIZATION' && t('controls.runningOptimization')}
                {phase === 'IDLE_OFFLINE' && t('controls.idleOffline')}
                {phase === 'RUNNING_OFFLINE' && t('controls.runningOffline')}
                {phase === 'IDLE_ONLINE' && t('controls.idleOnline')}
                {phase === 'RUNNING_ONLINE' && t('controls.runningOnline')}
              </p>
              {phase === 'IDLE_OPTIMIZATION' && !isOptPrerequisitesMet && (
                <span title={`Pré-requisitos pendentes:\n${!hasMap ? '• Mapa SUMO\n' : ''}${!hasParquet ? '• Base Parquet\n' : ''}${!hasSensors ? '• Sensores' : ''}`}>
                  <Lock className="w-3.5 h-3.5 text-amber-500/80" />
                </span>
              )}
            </div>

            {/* Minimalist 3-Pill Status Row */}
            {phase === 'IDLE_OPTIMIZATION' && (
              <div className="flex items-center gap-1.5 pt-0.5">
                <button
                  type="button"
                  onClick={() => openImportWizard(1)}
                  title={hasMap ? 'Mapa SUMO carregado' : 'Clique para carregar o Mapa SUMO (.net.xml / .net.xml.gz)'}
                  className={`flex-1 py-1 px-2 rounded-lg text-[10px] font-medium border flex items-center justify-center gap-1.5 transition-all ${
                    hasMap
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
                      : 'bg-surface/50 border-border text-slate-400 dark:text-slate-500 hover:border-slate-400 dark:hover:border-slate-600 hover:text-slate-700 dark:hover:text-slate-300'
                  }`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${hasMap ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-600'}`} />
                  <span>Mapa</span>
                </button>

                <button
                  type="button"
                  onClick={() => openImportWizard(2)}
                  title={hasParquet ? 'Base Parquet importada' : 'Clique para importar a base Parquet (.parquet)'}
                  className={`flex-1 py-1 px-2 rounded-lg text-[10px] font-medium border flex items-center justify-center gap-1.5 transition-all ${
                    hasParquet
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
                      : 'bg-surface/50 border-border text-slate-400 dark:text-slate-500 hover:border-slate-400 dark:hover:border-slate-600 hover:text-slate-700 dark:hover:text-slate-300'
                  }`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${hasParquet ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-600'}`} />
                  <span>Parquet</span>
                </button>

                <button
                  type="button"
                  onClick={() => openImportWizard(3)}
                  title={hasSensors ? 'Sensores cadastrados' : 'Clique para cadastrar Sensores'}
                  className={`flex-1 py-1 px-2 rounded-lg text-[10px] font-medium border flex items-center justify-center gap-1.5 transition-all ${
                    hasSensors
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
                      : 'bg-surface/50 border-border text-slate-400 dark:text-slate-500 hover:border-slate-400 dark:hover:border-slate-600 hover:text-slate-700 dark:hover:text-slate-300'
                  }`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${hasSensors ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-600'}`} />
                  <span>Sensores</span>
                </button>
              </div>
            )}
          </div>

          <button
            onClick={handleControlAction}
            disabled={btn.disabled}
            title={isStartOptLocked ? getOptLockTooltip() : undefined}
            className={`w-full py-3 px-4 rounded-xl text-xs font-bold flex items-center justify-center gap-2 shadow-lg transition-all transform ${
              btn.disabled ? 'cursor-not-allowed' : 'active:scale-95'
            } ${btn.color} ${btn.active ? 'animate-pulse' : ''}`}
          >
            <Icon className="w-4 h-4" />
            {btn.label}
          </button>
        </div>

        {/* 2. Unified Ingestion Wizard (Map -> Parquet -> Sensors) */}
        <div className="space-y-2">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider px-1">
            {t('wizard.title')}
          </span>
          <button
            onClick={() => openImportWizard(1)}
            title="Iniciar fluxo sequencial de ingestão de dados"
            className="w-full p-3 rounded-xl bg-surface border border-border hover:border-primary-500/50 text-slate-700 dark:text-slate-200 hover:text-slate-900 dark:hover:text-white transition-all flex items-center justify-between group shadow-sm hover:shadow-primary-500/10"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-primary-500/10 border border-primary-500/20 flex items-center justify-center text-primary-500 dark:text-primary-400 group-hover:scale-105 transition-transform">
                <Sparkles className="w-4 h-4" />
              </div>
              <div className="text-left">
                <div className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                  <span>Fluxo de Ingestão</span>
                </div>
                <div className="text-[10px] text-slate-500 dark:text-slate-400 font-medium flex items-center gap-1 mt-0.5">
                  <span className="text-primary-600 dark:text-primary-300">Mapa</span>
                  <span className="text-slate-400 dark:text-slate-500">→</span>
                  <span className="text-accent-cyan">Parquet</span>
                  <span className="text-slate-400 dark:text-slate-500">→</span>
                  <span className="text-emerald-500 dark:text-emerald-400">Sensores</span>
                </div>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-slate-900 dark:group-hover:text-white group-hover:translate-x-0.5 transition-all" />
          </button>
        </div>

        {/* 3. Data Sources List with Context Menu & Re-association */}
        <div className="space-y-2 pt-2">
          <div className="flex items-center justify-between px-1">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              {t('controls.sourcesTitle')} ({sources.length})
            </span>
            <button
              onClick={() => openImportWizard(3)}
              title="Adicionar Sensor"
              className="p-1 rounded-lg text-slate-500 dark:text-slate-400 hover:text-emerald-500 dark:hover:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-950/40 transition-colors"
            >
              <PlusCircle className="w-3.5 h-3.5" />
            </button>
          </div>

          {sources.length === 0 ? (
            <div 
              onClick={() => openImportWizard(1)}
              className="p-4 border border-dashed border-border rounded-xl text-center text-xs text-slate-500 dark:text-slate-400 hover:border-primary-500/40 hover:text-slate-700 dark:hover:text-slate-300 cursor-pointer transition-all"
            >
              {t('controls.noSources')}
            </div>
          ) : (
            <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
              {sources.map((src) => (
                <div
                  key={src.id}
                  className="p-2.5 rounded-lg bg-background/80 border border-border flex items-center justify-between group hover:border-slate-400 dark:hover:border-slate-700 transition-all relative"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <Radio className={`w-3.5 h-3.5 flex-shrink-0 ${src.is_local ? 'text-accent-cyan' : 'text-primary-500 dark:text-primary-400'}`} />
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-slate-800 dark:text-slate-200 truncate" title={src.name}>
                        {src.name}
                      </p>
                      {src.associated_element && (
                        <p className="text-[9px] text-accent-cyan font-mono truncate">
                          ↳ Via: {src.associated_element}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <button
                      onClick={() => sensorService.toggleOrigin(src.id)}
                      title={t('controls.toggleOrigin')}
                      className={`text-[10px] font-bold px-2 py-0.5 rounded border transition-all ${
                        src.is_local 
                          ? 'bg-accent-cyan/10 text-accent-cyan border-accent-cyan/30' 
                          : 'bg-primary-500/10 text-primary-600 dark:text-primary-400 border-primary-500/30'
                      }`}
                    >
                      {src.is_local ? t('controls.local') : t('controls.global')}
                    </button>

                    {/* Options Dropdown */}
                    <div className="relative">
                      <button
                        onClick={() => setActiveMenuSourceId(activeMenuSourceId === src.id ? null : src.id)}
                        className="p-1 text-slate-400 hover:text-white"
                      >
                        <MoreVertical className="w-3.5 h-3.5" />
                      </button>

                      {activeMenuSourceId === src.id && (
                        <div className="absolute right-0 top-6 w-44 bg-surfaceElevated border border-border rounded-xl shadow-2xl p-1 z-30 space-y-1">
                          {src.is_local && (
                            <button
                              onClick={() => handleStartReassociation(src.id)}
                              className="w-full px-2.5 py-1.5 text-left text-xs font-medium text-slate-200 hover:bg-primary-600/20 rounded-lg flex items-center gap-2"
                            >
                              <Crosshair className="w-3.5 h-3.5 text-accent-cyan" />
                              <span>Vincular no Mapa</span>
                            </button>
                          )}
                          <button
                            onClick={() => {
                              requestAuth(async () => {
                                await sensorService.removeSource(src.id);
                              });
                              setActiveMenuSourceId(null);
                            }}
                            className="w-full px-2.5 py-1.5 text-left text-xs font-medium text-rose-400 hover:bg-rose-950/40 rounded-lg flex items-center gap-2"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            <span>Remover Sensor</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};
