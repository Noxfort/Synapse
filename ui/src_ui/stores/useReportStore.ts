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
// Date: 2026-09-01

import { create } from 'zustand';
import { OfficialReportData } from '../types/report';
import { defaultReportBuilder } from '../services/report/reportBuilder';

interface ReportStoreState {
  savedReports: OfficialReportData[];
  selectedReport: OfficialReportData | null;
  isReportModalOpen: boolean;

  // Actions
  saveReport: (report: OfficialReportData) => void;
  deleteReport: (protocol: string) => void;
  openReportModal: (report?: OfficialReportData | null) => void;
  closeReportModal: () => void;
  isReportSaved: (protocol: string) => boolean;
}

const getInitialMockReports = (): OfficialReportData[] => {
  try {
    const base = defaultReportBuilder.build(null);
    return [
      base,
      {
        ...base,
        protocol: 'SMT-CET-RELATORIO-2026-7819',
        processNumber: 'PA-SMT-2026/07819',
        timestamp: '2026-08-31T17:45:00.000Z',
        auditObjective: 'Auditoria de Pico Vespertino e Alívio de Fila no Corredor Rebouças',
        observedTrafficDiagnosis: 'Saturação severa no entroncamento Av. Rebouças x Av. Brasil decorrente de retenção a jusante. Intervenção de segurança aplicada por radar Doppler com ruído espúrio.',
        adaptiveActionExecuted: 'Readequação de offset em 12 interseções com retenção forçada de verde de 20s no Corredor Rebouças.',
      },
      {
        ...base,
        protocol: 'SMT-CET-RELATORIO-2026-5520',
        processNumber: 'PA-SMT-2026/05520',
        timestamp: '2026-08-30T08:15:00.000Z',
        auditObjective: 'Auditoria de Pico Matutino e Coordenação de Onda Verde Eixo Leste-Oeste',
        observedTrafficDiagnosis: 'Fluxo pendular matutino atingindo 21.400 veíc/h. Interdependência coordenada entre Corredor Consolação e Corredor Paulista sem anomalias críticas.',
        adaptiveActionExecuted: 'Ativação do Plano de Onda Verde Prioritária Leste-Oeste por 120 minutos.',
      },
    ];
  } catch (e) {
    console.error('Error generating initial mock reports in useReportStore:', e);
    return [];
  }
};

export const useReportStore = create<ReportStoreState>((set, get) => ({
  savedReports: getInitialMockReports(),
  selectedReport: null,
  isReportModalOpen: false,

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

  openReportModal: (report = null) =>
    set({
      selectedReport: report || null,
      isReportModalOpen: true,
    }),

  closeReportModal: () =>
    set({
      isReportModalOpen: false,
    }),

  isReportSaved: (protocol) => {
    return get().savedReports.some((r) => r.protocol === protocol);
  },
}));
