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
// File: ui/src_ui/components/xai/report/ReportNetworkSummaryCard.tsx
// Author: Gabriel Moraes
// Date: 2026-09-01

import React from 'react';
import { TrafficNetworkMacroSummary, ReportLocationData } from '../../../types/report';

interface ReportNetworkSummaryCardProps {
  summary: TrafficNetworkMacroSummary;
  location: ReportLocationData;
}

export const ReportNetworkSummaryCard: React.FC<ReportNetworkSummaryCardProps> = ({
  summary,
  location,
}) => {
  return (
    <div className="space-y-2 font-serif text-black">
      <div className="border-b border-black pb-0.5">
        <h3 className="text-[11px] font-bold uppercase text-black">
          2. Panorama Macroscópico da Malha Arterial (Highway Capacity Manual — HCM)
        </h3>
      </div>

      <div className="text-xs text-justify leading-relaxed space-y-1.5">
        <p className="indent-6 text-[10.5px] text-black">
          A malha arterial auditada compreende uma extensão de <strong>{summary.networkLengthKm} km</strong> distribuída em <strong>{summary.corridorsMonitored} corredores principais</strong>, totalizando 18 interseções semafóricas coordenadas. Durante o regime de pico de tráfego, o volume horário global aferido atingiu <strong>{summary.totalHourlyFlow}</strong>, com velocidade média espacial de <strong>{summary.networkMeanSpeed}</strong> e grau médio de saturação de <strong>{summary.networkMeanSaturation}</strong>, caracterizando Nível de Serviço <strong>{summary.networkLevelOfService}</strong>.
        </p>

        <p className="text-[10px] text-black italic">
          <strong>Delimitação Territorial:</strong> {location.jurisdiction} ({location.geographicBounds}). Plano nominal base: {location.baselineSignalPlan}.
        </p>
      </div>
    </div>
  );
};
