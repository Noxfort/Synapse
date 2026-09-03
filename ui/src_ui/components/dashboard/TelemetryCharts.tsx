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
// File: ui/src_ui/components/dashboard/TelemetryCharts.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { ShieldAlert, TrendingUp } from 'lucide-react';
import { TelemetryPoint } from '../../types/sensors';
import { createMseLossChartOption, createDriftPsiChartOption } from '../../utils/chartOptions';
import { useSystemStore } from '../../stores';

interface TelemetryChartsProps {
  sensorName: string;
  lossPoints: TelemetryPoint[];
  driftPoints: TelemetryPoint[];
}

export const TelemetryCharts: React.FC<TelemetryChartsProps> = ({
  sensorName,
  lossPoints,
  driftPoints,
}) => {
  const theme = useSystemStore((s) => s.theme);
  const phase = useSystemStore((s) => s.phase);
  const isDark = theme === 'dark';
  const isOnline = phase === 'RUNNING_ONLINE';

  const lossChartOption = useMemo(() => createMseLossChartOption(lossPoints, isDark), [lossPoints, isDark]);
  const driftChartOption = useMemo(() => createDriftPsiChartOption(driftPoints, isDark), [driftPoints, isDark]);

  return (
    <div className="grid grid-cols-2 gap-6">
      <div className="glass-panel p-6 rounded-2xl space-y-2 relative overflow-hidden">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-bold text-slate-800 dark:text-white uppercase tracking-wider flex items-center gap-1.5">
            <ShieldAlert className="w-4 h-4 text-rose-500 dark:text-rose-400" />
            Erro de Reconstrução / Anomalia (MSE Loss)
          </h4>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
              Sensor: <b className="text-rose-600 dark:text-rose-300">{sensorName}</b>
            </span>
            <span className={`px-2 py-0.5 rounded text-[9px] font-bold font-mono ${lossPoints.length > 0 ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30' : 'bg-slate-200 dark:bg-slate-800 text-slate-500 dark:text-slate-400'}`}>
              {lossPoints.length > 0 ? `${lossPoints.length} pts` : isOnline ? 'RECEBENDO...' : 'STANDBY'}
            </span>
          </div>
        </div>
        <div className="h-56 w-full relative">
          <ReactECharts option={lossChartOption} style={{ height: '100%', width: '100%' }} notMerge={true} lazyUpdate={true} />
        </div>
      </div>

      <div className="glass-panel p-6 rounded-2xl space-y-2 relative overflow-hidden">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-bold text-slate-800 dark:text-white uppercase tracking-wider flex items-center gap-1.5">
            <TrendingUp className="w-4 h-4 text-primary-500 dark:text-primary-400" />
            Deriva Estatística Temporal (PSI Score)
          </h4>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
              Sensor: <b className="text-primary-600 dark:text-primary-300">{sensorName}</b>
            </span>
            <span className={`px-2 py-0.5 rounded text-[9px] font-bold font-mono ${driftPoints.length > 0 ? 'bg-primary-500/15 text-primary-600 dark:text-primary-400 border border-primary-500/30' : 'bg-slate-200 dark:bg-slate-800 text-slate-500 dark:text-slate-400'}`}>
              {driftPoints.length > 0 ? `${driftPoints.length} pts` : isOnline ? 'RECEBENDO...' : 'STANDBY'}
            </span>
          </div>
        </div>
        <div className="h-56 w-full relative">
          <ReactECharts option={driftChartOption} style={{ height: '100%', width: '100%' }} notMerge={true} lazyUpdate={true} />
        </div>
      </div>
    </div>
  );
};

