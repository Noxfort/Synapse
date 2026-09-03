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
// File: ui/src_ui/stores/useEtlStore.ts
// Author: Gabriel Moraes
// Date: 2026-08-29

import { create } from 'zustand';
import { ParquetInspectionResult, ParquetImportProgress } from '../types/etl';

interface EtlState {
  parquetInspection: ParquetInspectionResult | null;
  importProgress: ParquetImportProgress;

  // Actions
  setParquetInspection: (result: ParquetInspectionResult | null) => void;
  setImportProgress: (progress: Partial<ParquetImportProgress>) => void;
  resetEtlState: () => void;
}

export const useEtlStore = create<EtlState>((set) => ({
  parquetInspection: null,
  importProgress: { progress: 0, status: '', isImporting: false },

  setParquetInspection: (result) => set({ parquetInspection: result }),
  setImportProgress: (progress) =>
    set((state) => ({ importProgress: { ...state.importProgress, ...progress } })),
  resetEtlState: () =>
    set({
      parquetInspection: null,
      importProgress: { progress: 0, status: '', isImporting: false },
    }),
}));
