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
// File: ui/src_ui/components/xai/report/pages/Page1ExecutiveSummary.tsx
// Author: Gabriel Moraes
// Date: 2026-09-01

import React from 'react';
import { OfficialReportData } from '../../../../types/report';
import { ReportHeaderCard } from '../ReportHeaderCard';
import { ReportExecutiveSummaryCard } from '../ReportExecutiveSummaryCard';

interface PageProps {
  report: OfficialReportData;
  pageNumber: number;
  totalPages: number;
}

export const Page1ExecutiveSummary: React.FC<PageProps> = ({ report, pageNumber, totalPages }) => {
  return (
    <div
      className="abnt-a4-page bg-white text-slate-950 font-serif shadow-xl mx-auto flex flex-col justify-between"
      style={{
        width: '210mm',
        minHeight: '297mm',
        padding: '25mm 20mm 20mm 25mm',
        boxSizing: 'border-box',
        marginBottom: '20mm',
      }}
    >
      <div className="space-y-4">
        {/* Timbre Institucional e Autuação */}
        <ReportHeaderCard report={report} />

        {/* PARTE I: Sumário Executivo para Gestão Pública */}
        <ReportExecutiveSummaryCard report={report} />
      </div>

      {/* Rodapé Padronizado ABNT */}
      <div className="pt-3 border-t border-slate-400 flex justify-between items-center text-[10px] text-slate-700 font-sans">
        <span>Processo: <strong>{report.processNumber}</strong> • Protocolo: {report.protocol}</span>
        <span className="font-bold">Folha {pageNumber} de {totalPages}</span>
      </div>
    </div>
  );
};
