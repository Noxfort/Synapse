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
// File: ui/src_ui/stores/useSensorsStore.ts
// Author: Gabriel Moraes
// Date: 2026-08-29

import { create } from 'zustand';
import { DataSourceItem, EngineDataPayload, TelemetryPoint } from '../types/sensors';

interface SensorsState {
  sources: DataSourceItem[];
  selectedSourceId: string | null;
  latestEngineData: EngineDataPayload | null;
  lossHistory: Record<string, TelemetryPoint[]>;
  driftHistory: Record<string, TelemetryPoint[]>;

  // Actions
  setSources: (sources: DataSourceItem[]) => void;
  addSourceItem: (source: DataSourceItem) => void;
  removeSourceItem: (sourceId: string) => void;
  updateSourceItem: (sourceId: string, updates: Partial<DataSourceItem>) => void;
  associateSourceToElement: (sourceId: string, elementId: string) => void;
  disassociateSource: (sourceId: string) => void;
  setSelectedSourceId: (id: string | null) => void;
  handleEngineDataPayload: (data: EngineDataPayload) => void;
}

export const useSensorsStore = create<SensorsState>((set) => ({
  sources: [],
  selectedSourceId: null,
  latestEngineData: null,
  lossHistory: {},
  driftHistory: {},

  setSources: (sources) => set({ sources }),

  addSourceItem: (source) =>
    set((state) => {
      if (state.sources.some((s) => s.id === source.id)) return state;
      return { sources: [...state.sources, source] };
    }),

  removeSourceItem: (sourceId) =>
    set((state) => ({
      sources: state.sources.filter((s) => s.id !== sourceId),
      selectedSourceId: state.selectedSourceId === sourceId ? null : state.selectedSourceId,
    })),

  updateSourceItem: (sourceId, updates) =>
    set((state) => ({
      sources: state.sources.map((s) => (s.id === sourceId ? ({ ...s, ...updates } as DataSourceItem) : s)),
    })),

  associateSourceToElement: (sourceId, elementId) =>
    set((state) => ({
      sources: state.sources.map((s) => (s.id === sourceId ? ({ ...s, associated_element: elementId } as DataSourceItem) : s)),
    })),

  disassociateSource: (sourceId) =>
    set((state) => ({
      sources: state.sources.map((s) => (s.id === sourceId ? ({ ...s, associated_element: undefined } as DataSourceItem) : s)),
    })),

  setSelectedSourceId: (id) => set({ selectedSourceId: id }),

  handleEngineDataPayload: (data: any) => {
    if (!data) return;
    const now = new Date().toLocaleTimeString();

    set((state) => {
      let currentSources = [...state.sources];
      const nextLoss = { ...state.lossHistory };
      const nextDrift = { ...state.driftHistory };

      const targetSingleId = data.id || data.source_id || data.source;

      const updatedSources = currentSources.map((src) => {
        // 1. Resolve Sensor Value
        let val = src.latest_value;
        if (targetSingleId === src.id || targetSingleId === src.name) {
          if (data.raw !== undefined) val = Number(data.raw);
          else if (data.value !== undefined) val = Number(data.value);
          else if (data.val !== undefined) val = Number(data.val);
        } else if (data.sensor_snapshot?.[src.id] !== undefined) {
          const snap = data.sensor_snapshot[src.id];
          val = typeof snap === 'object' && snap !== null && snap.value !== undefined ? Number(snap.value) : Number(snap);
        } else if (data.sensor_snapshot?.[src.name] !== undefined) {
          const snap = data.sensor_snapshot[src.name];
          val = typeof snap === 'object' && snap !== null && snap.value !== undefined ? Number(snap.value) : Number(snap);
        } else if (src.associated_element && data.sensor_snapshot?.[src.associated_element] !== undefined) {
          const snap = data.sensor_snapshot[src.associated_element];
          val = typeof snap === 'object' && snap !== null && snap.value !== undefined ? Number(snap.value) : Number(snap);
        } else if (data.source_values?.[src.id] !== undefined) {
          val = Number(data.source_values[src.id]);
        } else if (data.edge_data?.[src.id]?.speed !== undefined) {
          val = Number(data.edge_data[src.id].speed);
        } else if (src.associated_element && data.edge_data?.[src.associated_element]?.speed !== undefined) {
          val = Number(data.edge_data[src.associated_element].speed);
        }

        // 2. Resolve Loss / Anomaly Score
        const currentLoss = nextLoss[src.id] || nextLoss[src.name] || [];
        let realLoss = data.losses?.[src.id] ?? data.losses?.[src.name];
        if (realLoss === undefined && (targetSingleId === src.id || targetSingleId === src.name)) {
          realLoss = data.loss ?? data.metrics?.loss ?? data.error;
        } else if (realLoss === undefined && data.loss !== undefined) {
          realLoss = Number(data.loss);
        } else if (realLoss === undefined && data.security_score !== undefined) {
          realLoss = Number(data.security_score);
        }

        if (realLoss !== undefined && !isNaN(Number(realLoss))) {
          const pt = { time: now, value: Number(realLoss) };
          const updatedHistory = [...currentLoss, pt].slice(-30);
          nextLoss[src.id] = updatedHistory;
          nextLoss[src.name] = updatedHistory;
        }

        // 3. Resolve PSI / Drift Score
        const currentDrift = nextDrift[src.id] || nextDrift[src.name] || [];
        let realPsi = data.drift_scores?.[src.id] ?? data.drift_scores?.[src.name];
        if (realPsi === undefined && (targetSingleId === src.id || targetSingleId === src.name)) {
          realPsi = data.drift ?? data.metrics?.psi ?? data.metrics?.drift_score;
        } else if (realPsi === undefined && data.drift !== undefined) {
          realPsi = Number(data.drift);
        }

        if (realPsi !== undefined && !isNaN(Number(realPsi))) {
          const pt = { time: now, value: Number(realPsi) };
          const updatedHistory = [...currentDrift, pt].slice(-30);
          nextDrift[src.id] = updatedHistory;
          nextDrift[src.name] = updatedHistory;
        }

        // 4. Resolve Quality Score (Dynamic)
        let calculatedQuality = src.quality;
        if (data.qualities?.[src.id] !== undefined) {
          calculatedQuality = Number(data.qualities[src.id]);
        } else if (data.qualities?.[src.name] !== undefined) {
          calculatedQuality = Number(data.qualities[src.name]);
        } else if (realLoss !== undefined && !isNaN(Number(realLoss))) {
          calculatedQuality = Math.min(100, Math.max(10, Math.round(100 - Number(realLoss) * 1200)));
        } else if (src.confidence_score !== undefined && src.confidence_score !== null) {
          calculatedQuality = Math.round(src.confidence_score * 100);
        }

        return {
          ...src,
          latest_value: val !== undefined ? Number(val) : src.latest_value,
          quality: calculatedQuality,
        } as DataSourceItem;
      });

      return {
        latestEngineData: data,
        sources: updatedSources,
        lossHistory: nextLoss,
        driftHistory: nextDrift,
      };
    });
  },
}));
