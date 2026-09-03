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
// File: ui/src_ui/components/xai/report/ReportVetoBufferCard.tsx
// Author: Gabriel Moraes
// Date: 2026-09-01

import React from 'react';
import { TrafficSafetyInterventionItem } from '../../../types/report';

interface ReportVetoBufferCardProps {
  vetoHistory: TrafficSafetyInterventionItem[];
}

export const ReportVetoBufferCard: React.FC<ReportVetoBufferCardProps> = ({ vetoHistory }) => {
  return (
    <div className="space-y-3 font-serif text-black">
      <div className="border-b border-black pb-0.5">
        <h3 className="text-[11px] font-bold uppercase text-black">
          4. Auditoria de Segurança Viária & Atuação de Guardrails do CONTRAN
        </h3>
        <p className="text-[10px] text-black italic">
          Registro das intervenções de segurança, imposição de tempos mínimos regulamentares e retificações de controle.
        </p>
      </div>

      <div className="space-y-3 text-xs leading-relaxed">
        {vetoHistory.map((item, idx) => (
          <div key={item.id} className="space-y-1 text-justify">
            <h4 className="font-bold text-[10.5px] text-black">
              4.{idx + 1}. Intervenção {item.id} — {item.junction} ({item.timeRecorded})
            </h4>
            <p className="indent-4 text-[10.5px] text-black">
              <strong>Equipamento / Sensor:</strong> {item.equipmentId}.{' '}
              <strong>Dispositivo Normativo:</strong> {item.contranStandardViolated}.
            </p>
            <p className="indent-4 text-[10.5px] text-black">
              <strong>Irregularidade Detectada:</strong> {item.irregularityDetected}
            </p>
            <p className="indent-4 text-[10.5px] text-black">
              <strong>Ação Protetiva Aplicada:</strong> {item.correctiveGuardrail} (Status: <em>{item.finalState}</em>).
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};
