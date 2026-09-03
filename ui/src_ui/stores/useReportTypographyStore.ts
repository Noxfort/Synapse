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
// File: ui/src_ui/stores/useReportTypographyStore.ts
// Author: Gabriel Moraes
// Date: 2026-09-02

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { ReportTypographyOptions, DEFAULT_REPORT_TYPOGRAPHY } from '../types/report';

interface ReportTypographyState extends ReportTypographyOptions {
  setFontFamily: (fontFamily: 'Arial' | 'Times New Roman') => void;
  setFontSize: (fontSize: number) => void;
  setLineSpacing: (lineSpacing: 1.0 | 1.15 | 1.5) => void;
  setAlignment: (alignment: 'justify' | 'left') => void;
  resetDefaults: () => void;
}

export const useReportTypographyStore = create<ReportTypographyState>()(
  persist(
    (set) => ({
      ...DEFAULT_REPORT_TYPOGRAPHY,
      setFontFamily: (fontFamily) => set({ fontFamily }),
      setFontSize: (fontSize) => set({ fontSize }),
      setLineSpacing: (lineSpacing) => set({ lineSpacing }),
      setAlignment: (alignment) => set({ alignment }),
      resetDefaults: () => set({ ...DEFAULT_REPORT_TYPOGRAPHY }),
    }),
    {
      name: 'synapse-report-typography-preferences',
    }
  )
);
