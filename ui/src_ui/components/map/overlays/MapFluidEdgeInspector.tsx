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
// File: ui/src_ui/components/map/overlays/MapFluidEdgeInspector.tsx
// Author: Gabriel Moraes
// Date: 2026-08-31

import React from 'react';
import { Radio, Waves, Gauge, Layers, Car, X, Unlink } from 'lucide-react';
import { DataSourceItem } from '../../../types/sensors';
import { MapEdgeData } from '../../../types/topology';

interface MapFluidEdgeInspectorProps {
  edgeId: string;
  currentEdge?: MapEdgeData | null;
  liveEdgeData?: { speed: number; density?: number; occupancy?: number; queue?: number } | null;
  associatedSensor?: DataSourceItem | null;
  onClose: () => void;
  onDisassociate?: (sensorId: string) => void;
}

export const MapFluidEdgeInspector: React.FC<MapFluidEdgeInspectorProps> = ({
  edgeId,
  currentEdge,
  liveEdgeData,
  associatedSensor,
  onClose,
  onDisassociate,
}) => {
  const resolvedSpeed =
    liveEdgeData?.speed !== undefined
      ? liveEdgeData.speed
      : associatedSensor?.latest_value !== undefined && associatedSensor.latest_value !== null
      ? Number(associatedSensor.latest_value)
      : 48.0;

  const resolvedDensity = liveEdgeData?.density ?? 15.0;
  const resolvedOccupancy = liveEdgeData?.occupancy ?? Math.min(0.95, resolvedDensity / 125.0);
  const resolvedQueue = liveEdgeData?.queue ?? 0;
  const macroscopicFlow = Math.round(resolvedDensity * resolvedSpeed);

  return (
    <div className="absolute bottom-4 left-6 z-20 glass-panel p-4 rounded-2xl border border-border/80 bg-surface/95 backdrop-blur-md shadow-2xl space-y-3 min-w-[320px] max-w-[360px] animate-in fade-in select-none">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 border-b border-border/80 pb-2.5">
        <div className="flex items-center gap-2">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              associatedSensor ? 'bg-accent-cyan animate-ping' : 'bg-primary-500'
            }`}
          />
          <div>
            <span className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
              {associatedSensor ? (
                <Radio className="w-3.5 h-3.5 text-accent-cyan" />
              ) : (
                <Waves className="w-3.5 h-3.5 text-primary-400" />
              )}
              Via Viária
            </span>
            {currentEdge && (
              <p className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">
                {currentEdge.from} → {currentEdge.to}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-primary-500/10 text-primary-400 border border-primary-500/30 font-bold">
            {edgeId}
          </span>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-surfaceHover transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Source / Regime Model Info */}
      <div className="flex items-center justify-between text-[11px] px-2.5 py-1.5 rounded-xl bg-surfaceHover/70 border border-border/50 font-mono">
        <span className="text-slate-500 dark:text-slate-400 font-sans">Origem:</span>
        <span className="font-semibold text-accent-cyan text-[10px]">
          {associatedSensor
            ? `Sensor ${associatedSensor.name} (${associatedSensor.id})`
            : 'Modelo Fluidodinâmico (LWR)'}
        </span>
      </div>

      {/* 2x2 Fluid Dynamics Telemetry Grid */}
      <div className="grid grid-cols-2 gap-2">
        {/* Speed Card */}
        <div className="p-2.5 rounded-xl bg-surfaceHover/80 border border-border/40 space-y-0.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase text-slate-500 dark:text-slate-400 font-semibold flex items-center gap-1">
              <Gauge className="w-3 h-3 text-primary-400" /> Velocidade
            </span>
            <span
              className={`text-[9px] font-bold px-1 rounded ${
                resolvedSpeed > 45
                  ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/30'
                  : resolvedSpeed > 20
                  ? 'bg-amber-950/80 text-amber-400 border border-amber-500/30'
                  : 'bg-rose-950/80 text-rose-400 border border-rose-500/30'
              }`}
            >
              {resolvedSpeed > 45 ? 'LIVRE' : resolvedSpeed > 20 ? 'MODERADO' : 'CONGEST.'}
            </span>
          </div>
          <p className="text-base font-black font-mono text-slate-900 dark:text-white">
            {resolvedSpeed.toFixed(1)}{' '}
            <span className="text-[10px] font-normal text-slate-500 dark:text-slate-400">km/h</span>
          </p>
        </div>

        {/* Density Card */}
        <div className="p-2.5 rounded-xl bg-surfaceHover/80 border border-border/40 space-y-0.5">
          <span className="text-[10px] uppercase text-slate-500 dark:text-slate-400 font-semibold flex items-center gap-1">
            <Waves className="w-3 h-3 text-accent-cyan" /> Densidade (ρ)
          </span>
          <p className="text-base font-black font-mono text-slate-900 dark:text-white">
            {resolvedDensity.toFixed(1)}{' '}
            <span className="text-[10px] font-normal text-slate-500 dark:text-slate-400">v/km</span>
          </p>
        </div>

        {/* Occupancy Card */}
        <div className="p-2.5 rounded-xl bg-surfaceHover/80 border border-border/40 space-y-0.5">
          <span className="text-[10px] uppercase text-slate-500 dark:text-slate-400 font-semibold flex items-center gap-1">
            <Layers className="w-3 h-3 text-accent-amber" /> Ocupação
          </span>
          <p className="text-base font-black font-mono text-slate-900 dark:text-white">
            {(resolvedOccupancy * 100).toFixed(1)}{' '}
            <span className="text-[10px] font-normal text-slate-500 dark:text-slate-400">%</span>
          </p>
        </div>

        {/* Queue Card */}
        <div className="p-2.5 rounded-xl bg-surfaceHover/80 border border-border/40 space-y-0.5">
          <span className="text-[10px] uppercase text-slate-500 dark:text-slate-400 font-semibold flex items-center gap-1">
            <Car className="w-3 h-3 text-rose-400" /> Fila (Q)
          </span>
          <p className="text-base font-black font-mono text-slate-900 dark:text-white">
            {resolvedQueue}{' '}
            <span className="text-[10px] font-normal text-slate-500 dark:text-slate-400">veículos</span>
          </p>
        </div>
      </div>

      {/* Macroscopic Flow Indicator */}
      <div className="flex items-center justify-between text-[11px] px-2.5 py-1.5 rounded-xl bg-surfaceHover/40 border border-border/40 font-mono">
        <span className="text-slate-500 dark:text-slate-400 font-sans text-[10px]">
          Fluxo Estimado (q = ρ · v):
        </span>
        <span className="font-bold text-slate-900 dark:text-white text-[11px]">
          {macroscopicFlow} veíc/h
        </span>
      </div>

      {/* Action button if sensor is associated */}
      {associatedSensor && onDisassociate && (
        <div className="pt-1 flex items-center justify-end">
          <button
            onClick={() => onDisassociate(associatedSensor.id)}
            className="text-[10px] px-2.5 py-1 bg-surface border border-border hover:border-rose-500/50 text-slate-500 dark:text-slate-400 hover:text-rose-500 dark:hover:text-rose-400 rounded-lg flex items-center gap-1 transition-colors"
          >
            <Unlink className="w-3 h-3" />
            <span>Desvincular Sensor</span>
          </button>
        </div>
      )}
    </div>
  );
};
