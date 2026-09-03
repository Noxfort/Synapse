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
// File: ui/src_ui/components/xai/report/ReportSensorsTable.tsx
// Author: Gabriel Moraes
// Date: 2026-09-01

import React from 'react';
import { TrafficSensorItem } from '../../../types/report';

interface ReportSensorsTableProps {
  sensors: TrafficSensorItem[];
}

export const ReportSensorsTable: React.FC<ReportSensorsTableProps> = ({ sensors }) => {
  return (
    <div className="space-y-1.5 font-serif text-black pt-1">
      <div className="border-b border-black pb-0.5">
        <h3 className="text-[11px] font-bold uppercase text-black">
          3. Inventário Metrológico dos Detectores e Equipamentos de Campo
        </h3>
      </div>

      <p className="text-[10px] text-black italic">
        Tabela 1 — Discriminação dos detectores veiculares, equipamentos e grandezas aferidas.
      </p>

      {/* Tabela Padrão IBGE (Laterais Abertas, Linhas Horizontais Claras) */}
      <div className="w-full">
        <table className="w-full table-fixed text-left text-xs border-collapse font-sans">
          <thead>
            <tr className="border-t border-b border-black text-[9.5px] uppercase font-bold text-black">
              <th className="py-1.5 px-1 w-[16%]">Identificação</th>
              <th className="py-1.5 px-1 w-[26%]">Interseção / Local</th>
              <th className="py-1.5 px-1 w-[18%]">Tecnologia</th>
              <th className="py-1.5 px-1 w-[11%] text-right">Velocidade</th>
              <th className="py-1.5 px-1 w-[11%] text-right">Volume</th>
              <th className="py-1.5 px-1 w-[8%] text-right">Sat. (x)</th>
              <th className="py-1.5 px-1 w-[10%]">Laudo</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 text-[10px] font-mono">
            {sensors.map((s) => (
              <tr key={s.id}>
                <td className="py-1 px-1 font-bold text-black truncate">{s.id}</td>
                <td className="py-1 px-1 text-black font-serif text-[10px] truncate">{s.junction}</td>
                <td className="py-1 px-1 text-black font-sans text-[9px] truncate">{s.equipmentType}</td>
                <td className="py-1 px-1 text-right text-black font-bold">{s.measuredSpeed}</td>
                <td className="py-1 px-1 text-right text-black font-bold">{s.measuredFlow}</td>
                <td className="py-1 px-1 text-right font-bold text-black">{s.saturationDegree.split(' ')[0]}</td>
                <td className="py-1 px-1 text-black font-sans text-[9px] truncate">{s.inmetroReport}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t border-black text-[9px] text-black italic font-serif">
              <td colSpan={7} className="py-1 px-1">
                Fonte: Registros metrológicos oficiais da fiscalização de tráfego municipal (Disponibilidade: 98,4%).
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
};
