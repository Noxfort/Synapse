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
// File: ui/src_ui/components/xai/XaiSemanticPanel.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React from 'react';
import { FileText, FileCheck } from 'lucide-react';
import { XaiResultItem } from '../../types/xai';

interface XaiSemanticPanelProps {
  result: XaiResultItem;
  onOpenReport?: () => void;
}

export const XaiSemanticPanel: React.FC<XaiSemanticPanelProps> = ({ result, onOpenReport }) => {
  return (
    <div className="glass-panel p-6 rounded-2xl space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider flex items-center gap-2">
          <FileText className="w-4 h-4 text-accent-cyan" />
          Relatório Semântico (Agente Linguist NLP)
        </h3>
        <div className="flex items-center gap-3 text-xs font-mono">
          <span className="text-slate-500 dark:text-slate-400">
            Alvo: <b className="text-slate-900 dark:text-white">{result.target}</b>
          </span>
          <span className="text-slate-500 dark:text-slate-400">
            Δ Convergência: <b className="text-emerald-600 dark:text-emerald-400">{result.convergence_delta.toFixed(4)}</b>
          </span>
          {result.timestamp && (
            <span className="text-slate-400 dark:text-slate-500 text-[11px]">
              {result.timestamp}
            </span>
          )}
          {onOpenReport && (
            <button
              onClick={onOpenReport}
              className="ml-2 px-2.5 py-1 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 text-[11px] font-bold font-sans flex items-center gap-1 transition-all"
              title="Abrir Laudo Pericial Detalhado"
            >
              <FileCheck className="w-3.5 h-3.5" />
              <span>Ver Laudo Completo</span>
            </button>
          )}
        </div>
      </div>

      <div className="p-4 rounded-xl bg-surface dark:bg-background/80 border border-border text-xs text-slate-800 dark:text-slate-300 leading-relaxed font-sans shadow-xs">
        {result.semantic_text}
      </div>
    </div>
  );
};
