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
// File: ui/src_ui/components/xai/XaiAttributionChart.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import ReactECharts from 'echarts-for-react';
import { createAttributionChartOption } from '../../utils/chartOptions';
import { useSystemStore } from '../../stores';

interface XaiAttributionChartProps {
  attributions: number[];
  featureNames?: string[];
}

export const XaiAttributionChart: React.FC<XaiAttributionChartProps> = ({
  attributions,
  featureNames,
}) => {
  const { t } = useTranslation();
  const theme = useSystemStore((s) => s.theme);
  const isDark = theme === 'dark';

  const attributionOption = useMemo(
    () => createAttributionChartOption(attributions, isDark, featureNames),
    [attributions, isDark, featureNames]
  );

  return (
    <div className="glass-panel p-6 rounded-2xl space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold text-slate-800 dark:text-white uppercase tracking-wider">
          {t('xai.temporalAttribution')} (Integrated Gradients)
        </h3>
        <span className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
          Janela Temporal de Entrada: {attributions.length} timesteps (t-{attributions.length - 1} até t0)
        </span>
      </div>
      <div className="h-64 w-full">
        <ReactECharts option={attributionOption} style={{ height: '100%', width: '100%' }} />
      </div>
    </div>
  );
};

