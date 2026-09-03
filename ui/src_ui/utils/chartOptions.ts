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
// File: ui/src_ui/utils/chartOptions.ts
// Author: Gabriel Moraes
// Date: 2026-08-29

import { TelemetryPoint } from '../types/sensors';
import { getThemeTokens } from '../theme';

export function createMseLossChartOption(points: TelemetryPoint[], isDark: boolean = true) {
  const tokens = getThemeTokens(isDark ? 'dark' : 'light');
  const { charts } = tokens.colors;
  const hasData = points && points.length > 0;
  const xData = hasData ? points.map((p) => p.time) : ['t-5', 't-4', 't-3', 't-2', 't-1', 't0'];
  const yData = hasData ? points.map((p) => p.value) : [];

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: charts.tooltipBg,
      borderColor: charts.tooltipBorder,
      textStyle: { color: charts.tooltipText, fontSize: 11 },
      extraCssText: isDark ? 'box-shadow: 0 4px 12px rgba(0,0,0,0.5);' : 'box-shadow: 0 4px 12px rgba(0,0,0,0.1);',
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: xData,
      axisLine: { lineStyle: { color: charts.axisLine } },
      axisLabel: { color: charts.axisLabel, fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      name: 'MSE Loss',
      min: 0,
      max: hasData ? undefined : 0.05,
      nameTextStyle: { color: charts.axisLabel, fontSize: 10 },
      splitLine: { lineStyle: { color: charts.splitLine, type: 'dashed' } },
      axisLabel: { color: charts.yAxisLabel, fontSize: 10 },
    },
    series: [
      {
        name: 'MSE Loss',
        type: 'line',
        smooth: true,
        data: yData,
        showSymbol: true,
        symbolSize: 6,
        lineStyle: { color: '#f43f5e', width: 2.5 },
        itemStyle: { color: '#f43f5e' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(244, 63, 94, 0.25)' },
              { offset: 1, color: 'rgba(244, 63, 94, 0.0)' },
            ],
          },
        },
      },
    ],
  };
}

export function createDriftPsiChartOption(points: TelemetryPoint[], isDark: boolean = true) {
  const tokens = getThemeTokens(isDark ? 'dark' : 'light');
  const { charts } = tokens.colors;
  const hasData = points && points.length > 0;
  const xData = hasData ? points.map((p) => p.time) : ['t-5', 't-4', 't-3', 't-2', 't-1', 't0'];
  const yData = hasData ? points.map((p) => p.value) : [];

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: charts.tooltipBg,
      borderColor: charts.tooltipBorder,
      textStyle: { color: charts.tooltipText, fontSize: 11 },
      extraCssText: isDark ? 'box-shadow: 0 4px 12px rgba(0,0,0,0.5);' : 'box-shadow: 0 4px 12px rgba(0,0,0,0.1);',
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: xData,
      axisLine: { lineStyle: { color: charts.axisLine } },
      axisLabel: { color: charts.axisLabel, fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      name: 'PSI Score',
      min: 0,
      max: hasData ? undefined : 0.10,
      nameTextStyle: { color: charts.axisLabel, fontSize: 10 },
      splitLine: { lineStyle: { color: charts.splitLine, type: 'dashed' } },
      axisLabel: { color: charts.yAxisLabel, fontSize: 10 },
    },
    series: [
      {
        name: 'PSI Value',
        type: 'line',
        smooth: true,
        data: yData,
        showSymbol: true,
        symbolSize: 6,
        lineStyle: { color: '#3b82f6', width: 2.5 },
        itemStyle: { color: '#3b82f6' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(59, 130, 246, 0.25)' },
              { offset: 1, color: 'rgba(59, 130, 246, 0.0)' },
            ],
          },
        },
      },
    ],
  };
}

export function createAttributionChartOption(
  attributions: number[],
  isDark: boolean = true,
  featureNames?: string[]
) {
  const tokens = getThemeTokens(isDark ? 'dark' : 'light');
  const { charts } = tokens.colors;

  const xAxisData =
    featureNames && featureNames.length === attributions.length
      ? featureNames
      : attributions.map((_, i) => `t-${attributions.length - 1 - i}`);

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: charts.tooltipBg,
      borderColor: charts.tooltipBorder,
      textStyle: { color: charts.tooltipText, fontSize: 12 },
      extraCssText: isDark ? 'box-shadow: 0 4px 12px rgba(0,0,0,0.5);' : 'box-shadow: 0 4px 12px rgba(0,0,0,0.1);',
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: xAxisData,
      axisLine: { lineStyle: { color: charts.axisLine } },
      axisLabel: {
        color: charts.axisLabel,
        fontSize: 10,
        interval: 0,
        rotate: xAxisData.length > 8 ? 20 : 0,
      },
    },
    yAxis: {
      type: 'value',
      name: 'Peso de Atribuição',
      nameTextStyle: { color: charts.axisLabel, fontSize: 10 },
      splitLine: { lineStyle: { color: charts.splitLine, type: 'dashed' } },
      axisLabel: { color: charts.yAxisLabel, fontSize: 10 },
    },
    series: [
      {
        name: 'Importância Temporal (Integrated Gradients)',
        type: 'bar',
        barWidth: '45%',
        data: attributions,
        itemStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: '#3b82f6' },
              { offset: 1, color: '#0ea5e9' },
            ],
          },
          borderRadius: [4, 4, 0, 0],
        },
      },
    ],
  };
}


