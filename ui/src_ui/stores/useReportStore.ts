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
// File: ui/src_ui/stores/useReportStore.ts
// Author: Gabriel Moraes
// Date: 2026-09-04

import { create } from 'zustand';
import { OfficialReportData } from '../types/report';
import { xaiService } from '../services/api/XaiService';
import { defaultReportBuilder } from '../services/report/reportBuilder';

interface ReportStoreState {
  savedReports: OfficialReportData[];
  selectedReport: OfficialReportData | null;
  isReportModalOpen: boolean;
  isLoadingReport: boolean;
  reportError: string | null;

  // Actions
  saveReport: (report: OfficialReportData) => void;
  deleteReport: (protocol: string) => void;
  openReportModal: (report?: OfficialReportData | null) => void;
  closeReportModal: () => void;
  isReportSaved: (protocol: string) => boolean;
  fetchOfficialReport: (resultId?: string, xaiResult?: any) => Promise<OfficialReportData | null>;
}

export const useReportStore = create<ReportStoreState>((set, get) => ({
  savedReports: [],
  selectedReport: null,
  isReportModalOpen: false,
  isLoadingReport: false,
  reportError: null,

  saveReport: (report) =>
    set((state) => {
      const exists = state.savedReports.some((r) => r.protocol === report.protocol);
      if (exists) {
        return {
          savedReports: state.savedReports.map((r) =>
            r.protocol === report.protocol ? report : r
          ),
        };
      }
      return { savedReports: [report, ...state.savedReports] };
    }),

  deleteReport: (protocol) =>
    set((state) => ({
      savedReports: state.savedReports.filter((r) => r.protocol !== protocol),
      selectedReport:
        state.selectedReport?.protocol === protocol ? null : state.selectedReport,
    })),

  openReportModal: (report = null) => {
    set({
      selectedReport: report || null,
      isReportModalOpen: true,
    });
    if (!report) {
      get().fetchOfficialReport();
    }
  },

  closeReportModal: () =>
    set({
      isReportModalOpen: false,
    }),

  isReportSaved: (protocol) => {
    return get().savedReports.some((r) => r.protocol === protocol);
  },

  fetchOfficialReport: async (resultId?: string, xaiResult?: any) => {
    set({ isLoadingReport: true, reportError: null });
    try {
      const res = await xaiService.generateOfficialReport({
        result_id: resultId,
        xai_result: xaiResult,
      });
      if (res && res.success && res.report) {
        set({ selectedReport: res.report, isLoadingReport: false });
        return res.report;
      }
      throw new Error(res.error || 'Falha ao sintetizar laudo no backend');
    } catch (e: any) {
      console.warn('Erro ao buscar laudo do backend, utilizando construtor de fallback:', e);
      try {
        const fallback = defaultReportBuilder.build(xaiResult);
        set({ selectedReport: fallback, isLoadingReport: false, reportError: e?.message || null });
        return fallback;
      } catch (fallbackErr) {
        set({ isLoadingReport: false, reportError: e?.message || 'Erro ao carregar laudo' });
        return null;
      }
    }
  },
}));
