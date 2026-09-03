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
// File: ui/src_ui/components/xai/report/pages/Page5QuesitosAndLegal.tsx
// Author: Gabriel Moraes
// Date: 2026-09-01

import React from 'react';
import { OfficialReportData } from '../../../../types/report';
import { ReportQuesitosCard } from '../ReportQuesitosCard';
import { ReportLegalCard } from '../ReportLegalCard';

interface PageProps {
  report: OfficialReportData;
  pageNumber: number;
  totalPages: number;
}

export const Page5QuesitosAndLegal: React.FC<PageProps> = ({ report, pageNumber, totalPages }) => {
  return (
    <div
      className="abnt-a4-page bg-white text-black font-serif shadow-xl mx-auto flex flex-col justify-between"
      style={{
        width: '210mm',
        minHeight: '297mm',
        padding: '25mm 20mm 20mm 25mm',
        boxSizing: 'border-box',
        marginBottom: '20mm',
      }}
    >
      <div className="space-y-4">
        {/* Cabeçalho Sutil de Continuação ABNT */}
        <div className="border-b border-black pb-1 flex justify-between items-center text-[9.5px] text-black font-sans uppercase tracking-wider">
          <span>{report.cityHall} • {report.department}</span>
          <span>{report.processNumber}</span>
        </div>

        {/* 8. Resposta aos Quesitos Técnicos Operacionais */}
        <ReportQuesitosCard quesitos={report.quesitos} />

        {/* 9. Enquadramento Normativo e Fundamentação Jurídico-Administrativa */}
        <ReportLegalCard legalFraming={report.legalFraming} />
      </div>

      {/* Rodapé Padronizado ABNT */}
      <div className="pt-3 border-t border-black flex justify-between items-center text-[9.5px] text-black font-sans">
        <span>Processo: <strong>{report.processNumber}</strong> • Protocolo: {report.protocol}</span>
        <span className="font-bold">Folha {pageNumber} de {totalPages}</span>
      </div>
    </div>
  );
};
