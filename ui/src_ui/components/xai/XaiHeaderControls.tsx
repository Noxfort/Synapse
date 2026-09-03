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
// File: ui/src_ui/components/xai/XaiHeaderControls.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Brain, Sparkles, Layers, Radio, Loader2, FileCheck } from 'lucide-react';
import { DataSourceItem } from '../../types/sensors';
import { XaiExplainMode } from '../../types/xai';

interface XaiHeaderControlsProps {
  sources: DataSourceItem[];
  selectedSensorForTcn: string;
  loadingAction: XaiExplainMode | null;
  onSelectSensorForTcn: (sensorId: string) => void;
  onTriggerExplain: (type: XaiExplainMode) => void;
  onOpenReport: () => void;
}

export const XaiHeaderControls: React.FC<XaiHeaderControlsProps> = ({
  sources,
  selectedSensorForTcn,
  loadingAction,
  onSelectSensorForTcn,
  onTriggerExplain,
  onOpenReport,
}) => {
  const { t } = useTranslation();

  return (
    <div className="glass-panel p-6 rounded-2xl flex items-center justify-between">
      <div>
        <h2 className="text-base font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
          <Brain className="w-5 h-5 text-primary-500 dark:text-primary-400" />
          {t('xai.title')}
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Interpretabilidade e auditoria de consistência física dos modelos neurais (iTransformer + GATv2).
        </p>
      </div>

      {/* 3 Action Buttons */}
      <div className="flex items-center gap-3">
        {/* Action 1: Auditor / Buffer */}
        <button
          onClick={() => onTriggerExplain('buffer')}
          disabled={loadingAction !== null}
          className="px-4 py-2 rounded-xl bg-surface border border-border text-xs font-semibold text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:border-primary-500/50 transition-all flex items-center gap-2 disabled:opacity-60 shadow-xs"
        >
          {loadingAction === 'buffer' ? (
            <Loader2 className="w-3.5 h-3.5 text-accent-cyan animate-spin" />
          ) : (
            <Sparkles className="w-3.5 h-3.5 text-accent-cyan" />
          )}
          <span>{loadingAction === 'buffer' ? 'Auditando...' : t('xai.requestBuffer')}</span>
        </button>

        {/* Action 2: Fuser Global */}
        <button
          onClick={() => onTriggerExplain('global')}
          disabled={loadingAction !== null}
          className="px-4 py-2 rounded-xl bg-surface border border-border text-xs font-semibold text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:border-primary-500/50 transition-all flex items-center gap-2 disabled:opacity-60 shadow-xs"
        >
          {loadingAction === 'global' ? (
            <Loader2 className="w-3.5 h-3.5 text-primary-500 animate-spin" />
          ) : (
            <Layers className="w-3.5 h-3.5 text-primary-500 dark:text-primary-400" />
          )}
          <span>{loadingAction === 'global' ? 'Calculando...' : t('xai.requestGlobal')}</span>
        </button>

        {/* Action 3: Local Sensor TCN */}
        <div className="flex items-center gap-1.5 p-1 bg-surface border border-border rounded-xl shadow-xs">
          <select
            value={selectedSensorForTcn}
            onChange={(e) => onSelectSensorForTcn(e.target.value)}
            disabled={loadingAction !== null || sources.length === 0}
            className="h-8 px-2 bg-background border border-border rounded-lg text-xs text-slate-800 dark:text-slate-200 focus:outline-none"
          >
            {sources.length === 0 ? (
              <option value="">Sem sensores</option>
            ) : (
              sources.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))
            )}
          </select>
          <button
            onClick={() => onTriggerExplain('local')}
            disabled={loadingAction !== null || sources.length === 0}
            className="px-3 py-1.5 rounded-lg bg-primary-600 hover:bg-primary-500 text-white text-xs font-bold transition-all flex items-center gap-1.5 disabled:opacity-60"
          >
            {loadingAction === 'local' ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Radio className="w-3.5 h-3.5" />
            )}
            <span>{loadingAction === 'local' ? 'Analisando...' : 'Explicar Sensor'}</span>
          </button>
        </div>

        {/* Action 4: Official Municipal Report (Laudo da Prefeitura) */}
        <button
          onClick={onOpenReport}
          className="px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold transition-all flex items-center gap-2 shadow-md shadow-emerald-600/20 border border-emerald-400/30 active:scale-95"
          title="Abrir laudo pericial oficial para prefeitura e órgãos reguladores"
        >
          <FileCheck className="w-4 h-4" />
          <span>{t('xai.generateReport', 'Gerar Laudo Oficial')}</span>
        </button>
      </div>
    </div>
  );
};
