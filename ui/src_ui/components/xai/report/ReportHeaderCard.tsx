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
// File: ui/src_ui/components/xai/report/ReportHeaderCard.tsx
// Author: Gabriel Moraes
// Date: 2026-09-01

import React from 'react';
import { OfficialReportData } from '../../../types/report';
import { useMunicipalSettingsStore } from '../../../stores/useMunicipalSettingsStore';

interface ReportHeaderCardProps {
  report: OfficialReportData;
}

export const ReportHeaderCard: React.FC<ReportHeaderCardProps> = ({ report }) => {
  const logoDataUrl = useMunicipalSettingsStore((s) => s.logoDataUrl);

  return (
    <div className="space-y-3 text-black font-serif">
      {/* Timbre Oficial do Município (ABNT NBR 10719) */}
      <div className="text-center space-y-1 pb-2 border-b border-black">
        <div className="flex justify-center mb-1">
          {logoDataUrl ? (
            <div className="h-12 max-w-[160px] flex items-center justify-center">
              <img
                src={logoDataUrl}
                alt="Brasão Oficial da Prefeitura"
                className="max-h-full max-w-full object-contain"
              />
            </div>
          ) : (
            <div className="w-10 h-10 border border-black rounded-full flex flex-col items-center justify-center p-0.5 font-serif text-[7px] font-bold uppercase tracking-wider text-black">
              <span>BRASÃO</span>
            </div>
          )}
        </div>
        <p className="text-[9.5px] uppercase tracking-widest text-black font-semibold">
          República Federativa do Brasil • Poder Executivo Municipal
        </p>
        <h1 className="text-xs font-bold uppercase tracking-wide text-black">
          {report.cityHall}
        </h1>
        <p className="text-[10.5px] font-bold uppercase text-black">
          {report.department}
        </p>
      </div>

      {/* Identificação do Relatório Técnico e Autuação Processual */}
      <div className="space-y-2 pt-1">
        <div className="text-center space-y-0.5">
          <h2 className="text-xs font-bold uppercase tracking-wide text-black">
            RELATÓRIO TÉCNICO OPERACIONAL DE ENGENHARIA DE TRÁFEGO
          </h2>
          <p className="text-[10px] italic text-black font-medium">
            Auditoria de Conformidade Operacional e Segurança do Controle Semafórico Adaptativo (CTB Art. 24)
          </p>
        </div>

        {/* Metadados Processuais em Lista Tipográfica Sóbria (Sem Caixas) */}
        <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-[10.5px] font-sans pt-1 border-t border-b border-black py-1.5">
          <div>
            <span className="font-bold text-black">Processo Administrativo: </span>
            <span className="font-mono text-black">{report.processNumber}</span>
          </div>

          <div>
            <span className="font-bold text-black">Protocolo Oficial: </span>
            <span className="font-mono text-black">{report.protocol}</span>
          </div>

          <div>
            <span className="font-bold text-black">Autoridade de Trânsito: </span>
            <span className="text-black font-serif">{report.authorityName}</span>
          </div>

          <div>
            <span className="font-bold text-black">Identificação / Portaria: </span>
            <span className="font-mono text-black">{report.registrationNumber}</span>
          </div>

          <div>
            <span className="font-bold text-black">Local Fiscalizado: </span>
            <span className="text-black font-serif text-[10px]">{report.location.corridorName}</span>
          </div>

          <div>
            <span className="font-bold text-black">Data da Auditoria: </span>
            <span className="font-mono text-black">{new Date(report.timestamp).toLocaleString('pt-BR')}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
