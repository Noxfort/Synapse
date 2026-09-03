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
// File: ui/src_ui/components/layout/StatusBar.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React from 'react';
import { useTranslation } from 'react-i18next';
import { ShieldCheck } from 'lucide-react';
import { useSystemStore, useTopologyStore, useSensorsStore } from '../../stores';

import { isTauriEnvironment } from '../../services/transport';

export const StatusBar: React.FC = () => {
  const { t } = useTranslation();
  const connected = useSystemStore((s) => s.connected);
  const isNative = isTauriEnvironment();
  const nodesCount = useTopologyStore((s) => s.nodes.length);
  const edgesCount = useTopologyStore((s) => s.edges.length);
  const latestEngineData = useSensorsStore((s) => s.latestEngineData);

  const getStatusText = () => {
    if (!isNative) return 'WEB BROWSER (SEM BRIDGE NATIVA)';
    return connected ? 'IPC PIPE: CONNECTED' : 'IPC PIPE: DISCONNECTED';
  };

  return (
    <footer className="h-8 border-t border-border bg-surface/90 backdrop-blur-md px-4 flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 font-mono select-none z-30">
      {/* Left items */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5" title={!isNative ? 'Para conectar ao Core Python via IPC, use a janela Desktop nativa executando python synapse.py' : ''}>
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-400' : isNative ? 'bg-rose-500 animate-ping' : 'bg-amber-500'}`} />
          <span className={`font-semibold ${connected ? 'text-emerald-500 dark:text-emerald-400' : isNative ? 'text-rose-500 dark:text-rose-400' : 'text-amber-500 dark:text-amber-400'}`}>
            {getStatusText()}
          </span>
        </div>

        <span className="text-slate-300 dark:text-slate-600">|</span>

        <div>
          <span>{t('map.nodesCount')}: </span>
          <span className="text-slate-800 dark:text-slate-200 font-bold">{nodesCount}</span>
          <span className="ml-2">{t('map.edgesCount')}: </span>
          <span className="text-slate-800 dark:text-slate-200 font-bold">{edgesCount}</span>
        </div>
      </div>

      {/* Right items */}
      <div className="flex items-center gap-4">
        {latestEngineData && (
          <>
            <div>
              <span>{t('metrics.meanSpeed')}: </span>
              <span className="text-accent-cyan font-bold">
                {latestEngineData.mean_speed ? `${latestEngineData.mean_speed.toFixed(1)} km/h` : '--'}
              </span>
            </div>
            <span className="text-slate-300 dark:text-slate-600">|</span>
          </>
        )}

        <div className="flex items-center gap-1.5 text-primary-600 dark:text-primary-400 font-bold">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>ZERO-TRUST MEMORY</span>
        </div>
      </div>
    </footer>
  );
};
