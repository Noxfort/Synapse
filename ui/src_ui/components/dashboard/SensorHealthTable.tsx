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
// File: ui/src_ui/components/dashboard/SensorHealthTable.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React from 'react';
import { useTranslation } from 'react-i18next';
import { RadioTower } from 'lucide-react';
import { DataSourceItem } from '../../types/sensors';

interface SensorHealthTableProps {
  sources: DataSourceItem[];
  selectedSourceId: string | null;
  onSelectSource: (id: string) => void;
}

export const SensorHealthTable: React.FC<SensorHealthTableProps> = ({
  sources,
  selectedSourceId,
  onSelectSource,
}) => {
  const { t } = useTranslation();

  const getStatusBadge = (src: DataSourceItem) => {
    switch (src.status) {
      case 'Active':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950/80 text-emerald-400 border border-emerald-500/30">
            ACTIVE
          </span>
        );
      case 'Quarantine':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950/80 text-amber-400 border border-amber-500/30">
            QUARANTINE ({src.quarantine_count ?? 1})
          </span>
        );
      case 'Validating':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-primary-950/80 text-primary-400 border border-primary-500/30">
            VALIDATING
          </span>
        );
      case 'Rejected':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950/80 text-rose-400 border border-rose-500/30">
            REJECTED
          </span>
        );
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400">OFFLINE</span>;
    }
  };

  const formatSensorValue = (src: DataSourceItem) => {
    if (src.latest_value === null || src.latest_value === undefined || isNaN(Number(src.latest_value))) {
      return '--';
    }
    const val = Number(src.latest_value);
    const sem = (src.semantic_type || '').toLowerCase();
    if (sem.includes('count') || sem.includes('veículo') || sem.includes('veic')) {
      return `${val.toFixed(0)} veíc/min`;
    }
    if (sem.includes('flow') || sem.includes('fluxo')) {
      return `${val.toFixed(1)} fl/s`;
    }
    return `${val.toFixed(1)} km/h`;
  };

  const getSourceQuality = (src: DataSourceItem) => {
    if (src.quality !== undefined && src.quality !== null && !isNaN(src.quality)) {
      return Math.min(100, Math.max(0, Math.round(src.quality)));
    }
    if (src.confidence_score !== undefined && src.confidence_score !== null) {
      return Math.min(100, Math.max(0, Math.round(src.confidence_score * 100)));
    }
    return 95;
  };

  return (
    <div className="glass-panel p-6 rounded-2xl space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-slate-800 dark:text-white tracking-tight flex items-center gap-2">
          <RadioTower className="w-4 h-4 text-primary-500 dark:text-primary-400" />
          {t('dashboard.sensorHealth')} (Zero-Trust Monitor)
        </h3>
        <span className="text-xs text-slate-500 dark:text-slate-400">Clique em uma linha para inspecionar a telemetria do sensor</span>
      </div>

      <div className="overflow-x-auto rounded-xl border border-border/80">
        <table className="w-full text-left text-xs">
          <thead className="bg-surface/80 text-slate-500 dark:text-slate-400 border-b border-border/80 uppercase font-mono text-[10px]">
            <tr>
              <th className="py-3 px-4">{t('dashboard.tableSource')}</th>
              <th className="py-3 px-4">Tipo Semântico (NLP)</th>
              <th className="py-3 px-4">{t('dashboard.tableStatus')}</th>
              <th className="py-3 px-4">Valor Atual</th>
              <th className="py-3 px-4">Qualidade / Confiança</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/40 font-mono">
            {sources.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-6 text-center text-slate-400 dark:text-slate-500 text-xs">
                  Nenhum sensor cadastrado. Carregue uma rede SUMO ou adicione um sensor.
                </td>
              </tr>
            ) : (
              sources.map((src) => {
                const isSelected = src.id === selectedSourceId;
                const qualityPct = getSourceQuality(src);
                return (
                  <tr
                    key={src.id}
                    onClick={() => onSelectSource(src.id)}
                    className={`cursor-pointer transition-colors ${
                      isSelected ? 'bg-primary-600/15 text-primary-900 dark:text-white font-bold' : 'hover:bg-surfaceHover text-slate-800 dark:text-slate-300'
                    }`}
                  >
                    <td className="py-3 px-4 font-sans font-semibold flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${src.is_local ? 'bg-accent-cyan' : 'bg-primary-500 dark:bg-primary-400'}`} />
                      <div>
                        <span>{src.name}</span>
                        {src.associated_element && (
                          <span className="ml-2 text-[10px] text-accent-cyan font-mono font-normal">
                            (Via: {src.associated_element})
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-accent-cyan">{src.semantic_type || 'Scanning...'}</td>
                    <td className="py-3 px-4">{getStatusBadge(src)}</td>
                    <td className="py-3 px-4 font-bold text-slate-900 dark:text-white">
                      {formatSensorValue(src)}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-2 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-primary-500 to-emerald-400 rounded-full transition-all duration-300"
                            style={{ width: `${qualityPct}%` }}
                          />
                        </div>
                        <span className="text-[11px] text-slate-500 dark:text-slate-400">{qualityPct}%</span>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
