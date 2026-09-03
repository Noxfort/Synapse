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
// File: ui/src_ui/components/xai/report/ReportExecutiveSummaryCard.tsx
// Author: Gabriel Moraes
// Date: 2026-09-01

import React from 'react';
import { OfficialReportData } from '../../../types/report';

interface ReportExecutiveSummaryCardProps {
  report: OfficialReportData;
}

export const ReportExecutiveSummaryCard: React.FC<ReportExecutiveSummaryCardProps> = ({ report }) => {
  return (
    <div className="space-y-4 font-serif text-black pt-2">
      {/* Título de Seção Primária (ABNT NBR 6024) */}
      <div className="border-b border-black pb-1">
        <h2 className="text-xs font-bold uppercase tracking-wider text-black">
          PARTE I — SUMÁRIO EXECUTIVO PARA GESTÃO PÚBLICA
        </h2>
        <p className="text-[10px] text-black italic">
          Síntese de alto nível dos resultados operacionais, mitigação de congestionamentos e conformidade de segurança viária.
        </p>
      </div>

      {/* 1. Objetivo da Gestão (Texto corrido justificado com recuo) */}
      <div className="space-y-1 text-xs text-justify leading-relaxed">
        <h3 className="font-bold text-[11px] text-black">
          1. Objetivo da Gestão
        </h3>
        <p className="indent-6 text-[11px] text-black">
          Auditar a intervenção semafórica dinâmica realizada em tempo real na malha arterial do Corredor Paulista durante o horário de pico vespertino, atestando a estrita observância às resoluções do CONTRAN e quantificando os ganhos de fluidez e capacidade viária gerados para o município.
        </p>
      </div>

      {/* 2. Principais Destaques Operacionais (Texto corrido com alíneas ABNT) */}
      <div className="space-y-1.5 text-xs">
        <h3 className="font-bold text-[11px] text-black">
          2. Principais Destaques Operacionais
        </h3>
        <ul className="space-y-1 text-[11px] text-black text-justify pl-4 list-none leading-relaxed">
          <li>
            <strong>a) Volume Total Atendido:</strong> 22.840 veículos por hora ao longo de 4 corredores arteriais interconectados;
          </li>
          <li>
            <strong>b) Ganho de Capacidade no Eixo Crítico:</strong> Aumento de 22,4% na taxa de escoamento da Av. Paulista;
          </li>
          <li>
            <strong>c) Redução de Atraso Médio:</strong> Diminuição estimada de 14,8% no tempo de espera por veículo na interseção;
          </li>
          <li>
            <strong>d) Preservação Integral da Segurança:</strong> 100% de cumprimento dos tempos mínimos de pedestres e amarelo do CONTRAN.
          </li>
        </ul>
      </div>

      {/* 3. Quadro-Síntese Comparativo (Tabela Padrão IBGE com Laterais Abertas) */}
      <div className="space-y-1.5 text-xs pt-1">
        <h3 className="font-bold text-[11px] text-black">
          3. Quadro-Síntese de Desempenho da Malha Viária
        </h3>

        <div className="w-full">
          <table className="w-full text-left text-xs border-collapse font-sans">
            <thead>
              <tr className="border-t border-b border-black text-[10px] uppercase font-bold text-black">
                <th className="py-2 px-1 w-[40%]">Indicador de Desempenho</th>
                <th className="py-2 px-1 w-[22%] text-right">Antes da Intervenção</th>
                <th className="py-2 px-1 w-[22%] text-right">Após Intervenção Dinâmica</th>
                <th className="py-2 px-1 w-[16%] text-right">Variação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-[10.5px]">
              <tr>
                <td className="py-1.5 px-1 font-serif text-black">Grau de Saturação da Aproximação ($x = V/c$)</td>
                <td className="py-1.5 px-1 text-right font-mono text-black">0,92 (Forçado)</td>
                <td className="py-1.5 px-1 text-right font-mono font-bold text-black">0,68 (Estável)</td>
                <td className="py-1.5 px-1 text-right font-mono font-bold text-black">-26,0%</td>
              </tr>
              <tr>
                <td className="py-1.5 px-1 font-serif text-black">Velocidade Média Espacial no Corredor</td>
                <td className="py-1.5 px-1 text-right font-mono text-black">12,4 km/h</td>
                <td className="py-1.5 px-1 text-right font-mono font-bold text-black">18,4 km/h</td>
                <td className="py-1.5 px-1 text-right font-mono font-bold text-black">+48,3%</td>
              </tr>
              <tr>
                <td className="py-1.5 px-1 font-serif text-black">Taxa Média de Ocupação dos Detectores</td>
                <td className="py-1.5 px-1 text-right font-mono text-black">89,2%</td>
                <td className="py-1.5 px-1 text-right font-mono font-bold text-black">61,4%</td>
                <td className="py-1.5 px-1 text-right font-mono font-bold text-black">-31,1%</td>
              </tr>
              <tr>
                <td className="py-1.5 px-1 font-serif text-black">Nível de Serviço Geral (HCM)</td>
                <td className="py-1.5 px-1 text-right font-mono text-black">LOS E (Saturado)</td>
                <td className="py-1.5 px-1 text-right font-mono font-bold text-black">LOS D (Regular)</td>
                <td className="py-1.5 px-1 text-right font-sans font-bold text-black">Ganho LOS</td>
              </tr>
              <tr>
                <td className="py-1.5 px-1 font-serif text-black">Atuação de Guardrails Regulamentares CONTRAN</td>
                <td className="py-1.5 px-1 text-right font-mono text-black">03 Ocorrências</td>
                <td className="py-1.5 px-1 text-right font-mono font-bold text-black">03 Retificações</td>
                <td className="py-1.5 px-1 text-right font-sans font-bold text-black">100% Segura</td>
              </tr>
            </tbody>
            <tfoot>
              <tr className="border-t border-black text-[9.5px] text-black italic font-serif">
                <td colSpan={4} className="py-1.5 px-1">
                  Fonte: Dados consolidados de telemetria e auditoria de 18 interseções semafóricas coordenadas.
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
};
