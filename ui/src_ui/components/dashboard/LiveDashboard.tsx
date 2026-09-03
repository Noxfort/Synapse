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
// File: ui/src_ui/components/dashboard/LiveDashboard.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React from 'react';
import { useSystemStore, useSensorsStore } from '../../stores';
import { DashboardKpiCards } from './DashboardKpiCards';
import { SensorHealthTable } from './SensorHealthTable';
import { TelemetryCharts } from './TelemetryCharts';

export const LiveDashboard: React.FC = () => {
  const phase = useSystemStore((s) => s.phase);
  const latencyMs = useSystemStore((s) => s.latencyMs);
  const { sources, selectedSourceId, setSelectedSourceId, lossHistory, driftHistory } = useSensorsStore();

  const activeSource = sources.find((s) => s.id === selectedSourceId) || sources[0];
  const activeLossPoints = activeSource
    ? lossHistory[activeSource.id] || lossHistory[activeSource.name] || Object.values(lossHistory)[0] || []
    : Object.values(lossHistory)[0] || [];
  const activeDriftPoints = activeSource
    ? driftHistory[activeSource.id] || driftHistory[activeSource.name] || Object.values(driftHistory)[0] || []
    : Object.values(driftHistory)[0] || [];

  const allDriftPoints = Object.values(driftHistory).flat();
  const avgPsi =
    activeDriftPoints.length > 0
      ? (activeDriftPoints.reduce((acc, p) => acc + p.value, 0) / activeDriftPoints.length).toFixed(3)
      : allDriftPoints.length > 0
      ? (allDriftPoints.reduce((acc, p) => acc + p.value, 0) / allDriftPoints.length).toFixed(3)
      : '0.000';

  return (
    <div className="h-[calc(100vh-4rem-2rem)] overflow-y-auto p-6 space-y-6 bg-background select-none">
      {/* 1. Header Summary Cards */}
      <DashboardKpiCards
        phase={phase}
        sensorCount={sources.length}
        avgPsi={avgPsi}
        latencyMs={latencyMs > 0 ? latencyMs.toFixed(2) : '--'}
      />

      {/* 2. Zero-Trust Data Sources Health Table */}
      <SensorHealthTable
        sources={sources}
        selectedSourceId={activeSource?.id || null}
        onSelectSource={setSelectedSourceId}
      />

      {/* 3. MLOps Live Charts */}
      <TelemetryCharts
        sensorName={activeSource?.name || 'Geral'}
        lossPoints={activeLossPoints}
        driftPoints={activeDriftPoints}
      />
    </div>
  );
};
