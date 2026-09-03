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
// File: ui/src_ui/components/xai/report/ReportQuesitosCard.tsx
// Author: Gabriel Moraes
// Date: 2026-09-01

import React from 'react';
import { PeritialQuesitoItem } from '../../../types/report';

interface ReportQuesitosCardProps {
  quesitos: PeritialQuesitoItem[];
}

export const ReportQuesitosCard: React.FC<ReportQuesitosCardProps> = ({ quesitos }) => {
  return (
    <div className="space-y-3 font-serif text-black">
      <div className="border-b border-black pb-0.5">
        <h3 className="text-[11px] font-bold uppercase text-black">
          8. Resposta aos Quesitos Técnicos Operacionais
        </h3>
        <p className="text-[10px] text-black italic">
          Respostas objetivas e fundamentadas em estrito atendimento à Norma ABNT NBR 13752:1996 e ao CTB.
        </p>
      </div>

      <div className="space-y-2.5 text-xs text-justify leading-relaxed">
        {quesitos.map((q) => (
          <div key={q.number} className="space-y-0.5">
            <p className="text-[10.5px] text-black font-bold">
              8.{q.number}. Quesito {q.number}: {q.question}
            </p>
            <p className="indent-4 text-[10.5px] text-black">
              <strong>Resposta:</strong> {q.answer}. <strong>Justificativa Técnica:</strong> {q.technicalJustification}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};
