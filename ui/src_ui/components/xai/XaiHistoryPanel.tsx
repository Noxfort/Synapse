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
// File: ui/src_ui/components/xai/XaiHistoryPanel.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React, { useState } from 'react';
import { History, Bookmark, FileText, Trash2, ExternalLink, ShieldCheck } from 'lucide-react';
import { XaiAuditVerdict, XaiResultItem } from '../../types/xai';
import { OfficialReportData } from '../../types/report';
import { useReportStore } from '../../stores';

interface XaiHistoryPanelProps {
  latestVerdict: XaiAuditVerdict;
  xaiHistory: XaiResultItem[];
  selectedResultId: string;
  onSelectResult: (id: string | null) => void;
  onOpenReport: (report?: OfficialReportData | null) => void;
}

export const XaiHistoryPanel: React.FC<XaiHistoryPanelProps> = ({
  latestVerdict,
  xaiHistory,
  selectedResultId,
  onSelectResult,
  onOpenReport,
}) => {
  const [activeTab, setActiveTab] = useState<'stream' | 'saved'>('stream');
  const { savedReports, deleteReport } = useReportStore();

  return (
    <div className="glass-panel p-4 rounded-2xl space-y-3 flex flex-col h-[560px]">
      {/* Tab Switcher Header */}
      <div className="flex items-center justify-between border-b border-border/80 pb-2">
        <div className="flex items-center gap-1 bg-surfaceHover p-0.5 rounded-lg text-xs font-semibold">
          <button
            onClick={() => setActiveTab('stream')}
            className={`px-2.5 py-1 rounded-md transition-all flex items-center gap-1 ${
              activeTab === 'stream'
                ? 'bg-primary-600 text-white shadow-xs'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <History className="w-3.5 h-3.5" />
            <span>Tempo Real</span>
          </button>

          <button
            onClick={() => setActiveTab('saved')}
            className={`px-2.5 py-1 rounded-md transition-all flex items-center gap-1 ${
              activeTab === 'saved'
                ? 'bg-primary-600 text-white shadow-xs'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Bookmark className="w-3.5 h-3.5" />
            <span>Salvos ({savedReports.length})</span>
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="space-y-2 flex-1 overflow-y-auto pr-1">
        {activeTab === 'stream' ? (
          <>
            {/* Pending Vetos / Buffer Root */}
            <div
              onClick={() => onSelectResult(null)}
              className="p-3 rounded-xl bg-background/80 border border-border hover:border-slate-400 dark:hover:border-slate-600 cursor-pointer transition-all"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-800 dark:text-slate-200">
                  Zero-Trust Buffer
                </span>
                <span
                  className={`w-2 h-2 rounded-full ${
                    latestVerdict.safe ? 'bg-emerald-500 dark:bg-emerald-400' : 'bg-rose-500'
                  }`}
                />
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                Status: {latestVerdict.safe ? 'Consistência Aprovada' : 'Anomalia Vetada'}
              </p>
            </div>

            {/* Previous Requests */}
            {xaiHistory.length === 0 ? (
              <div className="p-4 rounded-xl border border-dashed border-border/80 text-center text-[11px] text-slate-400 dark:text-slate-500">
                Nenhuma análise recente. Execute uma inferência para registrar.
              </div>
            ) : (
              xaiHistory.map((item) => (
                <div
                  key={item.id}
                  onClick={() => onSelectResult(item.id)}
                  className={`p-3 rounded-xl border cursor-pointer transition-all ${
                    selectedResultId === item.id
                      ? 'bg-primary-600/20 border-primary-500/50 text-primary-900 dark:text-white font-bold'
                      : 'bg-background/80 border-border hover:border-slate-400 dark:hover:border-slate-700 text-slate-700 dark:text-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold truncate">{item.target}</span>
                    <span className="font-mono text-[10px] text-slate-400 dark:text-slate-500">
                      {item.timestamp}
                    </span>
                  </div>
                  <div className="text-[11px] text-accent-cyan mt-1 font-mono">
                    Δ: {item.convergence_delta.toFixed(4)}
                  </div>
                </div>
              ))
            )}
          </>
        ) : (
          /* Saved Reports Dossier (Dossiê de Laudos Salvos para Análise) */
          <>
            {savedReports.length === 0 ? (
              <div className="p-6 rounded-xl border border-dashed border-border/80 text-center space-y-2 text-slate-400 dark:text-slate-500">
                <FileText className="w-6 h-6 mx-auto opacity-50" />
                <p className="text-xs font-semibold">Nenhum laudo arquivado</p>
                <p className="text-[11px]">
                  Ao abrir um laudo oficial, clique em "Salvar para Análise" para arquivá-lo aqui.
                </p>
              </div>
            ) : (
              savedReports.map((report) => (
                <div
                  key={report.protocol}
                  className="p-3 rounded-xl bg-surface border border-border hover:border-primary-500/50 transition-all space-y-2 group"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono font-bold text-[11px] text-primary-600 dark:text-primary-400">
                      {report.protocol.split('-').slice(0, 4).join('-')}
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">
                      {new Date(report.timestamp).toLocaleDateString('pt-BR')}
                    </span>
                  </div>

                  <p className="text-[11px] font-semibold text-slate-800 dark:text-slate-200 line-clamp-2">
                    {report.auditObjective}
                  </p>

                  <div className="flex items-center justify-between pt-1 border-t border-border/50 text-[10px]">
                    <span className="text-emerald-700 dark:text-emerald-400 flex items-center gap-1 font-semibold">
                      <ShieldCheck className="w-3 h-3" /> ABNT NBR 13752
                    </span>

                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => deleteReport(report.protocol)}
                        className="p-1 text-slate-400 hover:text-rose-500 rounded transition-colors"
                        title="Excluir laudo do dossiê"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>

                      <button
                        onClick={() => onOpenReport(report)}
                        className="px-2 py-0.5 bg-primary-600 hover:bg-primary-500 text-white rounded font-bold flex items-center gap-1 transition-all"
                        title="Abrir laudo salvo para análise pericial completa"
                      >
                        <span>Analisar</span>
                        <ExternalLink className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </>
        )}
      </div>
    </div>
  );
};
