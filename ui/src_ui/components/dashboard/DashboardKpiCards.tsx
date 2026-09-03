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
// File: ui/src_ui/components/dashboard/DashboardKpiCards.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Activity, Radio, TrendingUp, Clock } from 'lucide-react';
import { SystemPhase } from '../../types/system';

interface DashboardKpiCardsProps {
  phase: SystemPhase;
  sensorCount: number;
  avgPsi: string;
  latencyMs?: string;
}

export const DashboardKpiCards: React.FC<DashboardKpiCardsProps> = ({
  phase,
  sensorCount,
  avgPsi,
  latencyMs = '1.42',
}) => {
  const { t } = useTranslation();

  return (
    <div className="grid grid-cols-4 gap-4">
      {/* Card 1: System Status */}
      <div className="glass-panel p-5 rounded-2xl relative overflow-hidden group">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            {t('metrics.throughput')}
          </span>
          <div className="p-2 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
            <Activity className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3 flex items-center gap-2">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              phase === 'RUNNING_ONLINE' ? 'bg-emerald-500 animate-ping' : 'bg-slate-400 dark:bg-slate-500'
            }`}
          />
          <span className="text-lg font-black text-slate-900 dark:text-white tracking-tight">
            {phase === 'RUNNING_ONLINE' ? 'ONLINE (HFT)' : phase === 'RUNNING_OFFLINE' ? 'BOOTSTRAP' : 'STANDBY'}
          </span>
        </div>
      </div>

      {/* Card 2: Active Sources */}
      <div className="glass-panel p-5 rounded-2xl relative overflow-hidden group">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            {t('metrics.activeSensors')}
          </span>
          <div className="p-2 rounded-xl bg-primary-50 dark:bg-primary-500/10 text-primary-600 dark:text-primary-400">
            <Radio className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">{sensorCount}</span>
          <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">sensores monitorados</span>
        </div>
      </div>

      {/* Card 3: Avg PSI Score (Drift) */}
      <div className="glass-panel p-5 rounded-2xl relative overflow-hidden group">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            {t('metrics.driftScore')}
          </span>
          <div className="p-2 rounded-xl bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400">
            <TrendingUp className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">{avgPsi}</span>
          <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">Estável (&lt; 0.10)</span>
        </div>
      </div>

      {/* Card 4: Avg Latency */}
      <div className="glass-panel p-5 rounded-2xl relative overflow-hidden group">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Latência de Ciclo</span>
          <div className="p-2 rounded-xl bg-accent-cyan/10 text-accent-cyan">
            <Clock className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">{latencyMs}</span>
          <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">ms (HFT Link)</span>
        </div>
      </div>
    </div>
  );
};

