// SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
// Copyright (C) 2026 Noxfort Systems
//
// File: ui/src_ui/components/settings/tabs/AuditLogTab.tsx
// Author: Gabriel Moraes
// Date: 2026-09-03

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  History,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  User,
  Play,
  Square,
  Trash2,
  Sliders,
  Clock,
} from 'lucide-react';
import { useSecurityStore, AuditLogEntry } from '../../../stores/useSecurityStore';

export const AuditLogTab: React.FC = () => {
  const { t } = useTranslation();
  const { auditLogs, isLoadingAuditLogs, fetchAuditLogs } = useSecurityStore();
  const [filterQuery, setFilterQuery] = useState('');

  useEffect(() => {
    fetchAuditLogs();
  }, [fetchAuditLogs]);

  const filteredLogs = auditLogs.filter((log: AuditLogEntry) => {
    if (!filterQuery) return true;
    const q = filterQuery.toLowerCase();
    return (
      log.username?.toLowerCase().includes(q) ||
      log.action?.toLowerCase().includes(q) ||
      log.details?.toLowerCase().includes(q) ||
      log.timestamp?.toLowerCase().includes(q)
    );
  });

  const getActionBadge = (action: string) => {
    const act = action.toUpperCase();
    if (act.includes('LOGIN_SUCCESS') || act.includes('ADD_USER') || act.includes('LOCKDOWN_CLEARED')) {
      return {
        color: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
        icon: <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />,
      };
    }
    if (act.includes('FAILED') || act.includes('LOCKDOWN_TRIGGERED') || act.includes('REMOVE')) {
      return {
        color: 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/30',
        icon: <ShieldAlert className="w-3.5 h-3.5 text-rose-500" />,
      };
    }
    if (act.includes('START_')) {
      return {
        color: 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/30',
        icon: <Play className="w-3.5 h-3.5 text-sky-500" />,
      };
    }
    if (act.includes('STOP_')) {
      return {
        color: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30',
        icon: <Square className="w-3.5 h-3.5 text-amber-500" />,
      };
    }
    return {
      color: 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/30',
      icon: <Sliders className="w-3.5 h-3.5 text-slate-400" />,
    };
  };

  const formatTimestamp = (iso: string) => {
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) return iso;
      return d.toLocaleString('pt-BR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return iso;
    }
  };

  return (
    <div className="space-y-4">
      {/* Header with Search and Refresh */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-surface p-3.5 rounded-xl border border-border">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 flex items-center gap-2">
            <History className="w-4 h-4 text-primary-500" />
            <span>Trilha de Auditoria do Sistema</span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary-500/10 text-primary-500 font-bold border border-primary-500/20">
              {auditLogs.length} eventos
            </span>
          </h3>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
            Registro cronológico imutável de ações críticas, autenticações e operações de tráfego.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative flex-1 sm:w-56">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            <input
              type="text"
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              placeholder="Filtrar por ação, usuário..."
              className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg bg-background border border-border focus:border-primary-500 outline-none text-slate-900 dark:text-white"
            />
          </div>

          <button
            onClick={() => fetchAuditLogs()}
            disabled={isLoadingAuditLogs}
            title="Atualizar Logs"
            className="p-1.5 rounded-lg border border-border bg-background hover:bg-surfaceHover text-slate-600 dark:text-slate-300 hover:text-primary-500 transition-colors shrink-0"
          >
            <RefreshCw className={`w-4 h-4 ${isLoadingAuditLogs ? 'animate-spin text-primary-500' : ''}`} />
          </button>
        </div>
      </div>

      {/* Logs Table */}
      <div className="border border-border rounded-xl bg-background/50 overflow-hidden shadow-inner">
        <div className="max-h-[380px] overflow-y-auto divide-y divide-border/60">
          {filteredLogs.length === 0 ? (
            <div className="p-8 text-center space-y-2">
              <Clock className="w-8 h-8 mx-auto text-slate-400 opacity-50" />
              <p className="text-xs text-slate-400">
                {isLoadingAuditLogs
                  ? 'Carregando trilha de auditoria...'
                  : filterQuery
                  ? 'Nenhum registro encontrado para o filtro aplicado.'
                  : 'Nenhum evento registrado até o momento.'}
              </p>
            </div>
          ) : (
            filteredLogs.map((log, idx) => {
              const badge = getActionBadge(log.action);
              const isMaster = log.username === 'admin' || (log as any).role === 'MASTER';

              return (
                <div
                  key={idx}
                  className="p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 hover:bg-surfaceHover/40 transition-colors text-xs"
                >
                  {/* Left: User, Action, Timestamp */}
                  <div className="flex items-start sm:items-center gap-3">
                    <div className="shrink-0 mt-0.5 sm:mt-0">{badge.icon}</div>

                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span
                          className={`font-bold ${
                            isMaster
                              ? 'text-amber-500'
                              : 'text-slate-900 dark:text-white'
                          }`}
                        >
                          {log.username || 'SISTEMA'}
                        </span>

                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${badge.color}`}
                        >
                          {log.action}
                        </span>
                      </div>

                      <div className="text-[11px] text-slate-600 dark:text-slate-300 mt-0.5 italic">
                        {log.details || '—'}
                      </div>
                    </div>
                  </div>

                  {/* Right: Timestamp */}
                  <div className="shrink-0 text-[10px] text-slate-400 flex items-center gap-1.5 self-end sm:self-center font-mono">
                    <Clock className="w-3 h-3" />
                    <span>{formatTimestamp(log.timestamp)}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
