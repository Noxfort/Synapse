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
// File: ui/src_ui/components/settings/tabs/DatabaseSettingsTab.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React, { useState, useEffect, useRef } from 'react';
import { CheckCircle2, AlertTriangle, Database, Plug, Unplug, Wrench } from 'lucide-react';
import { systemService } from '../../../services/api';
import { useSystemStore } from '../../../stores';

const DB_STORAGE_KEY = 'synapse_database_settings_v1';

const getSavedDbSettings = () => {
  try {
    const raw = localStorage.getItem(DB_STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch (e) {
    console.error('Error loading db settings from localStorage:', e);
  }
  return null;
};

export const DatabaseSettingsTab: React.FC = () => {
  const saved = getSavedDbSettings();
  const { setDbStatus } = useSystemStore();

  const [dbHost, setDbHost] = useState(saved?.host ?? 'localhost');
  const [dbPort, setDbPort] = useState(saved?.port ?? 5432);
  const [dbName, setDbName] = useState(saved?.dbname ?? 'banco_de_dados_noxfort');
  const [dbSchema, setDbSchema] = useState(saved?.schema ?? 'schema_synapse');
  const [dbUser, setDbUser] = useState(saved?.user ?? 'user_synapse');
  const [dbPass, setDbPass] = useState(saved?.password ?? 'synapse123');
  const [dbRootPass, setDbRootPass] = useState('');
  const [dbFeedback, setDbFeedback] = useState<{ ok: boolean; msg: string } | null>(null);
  const [dbLoading, setDbLoading] = useState(false);
  const [isConnected, setIsConnected] = useState<boolean>(saved?.connected ?? false);
  const [isSetupDone, setIsSetupDone] = useState<boolean>(saved?.setupDone ?? false);

  const isFirstMount = useRef(true);

  // Load persistent settings directly from backend settings.ini on mount
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const backendCfg = await systemService.getDatabaseConfig();
        if (mounted && backendCfg) {
          if (backendCfg.host) setDbHost(backendCfg.host);
          if (backendCfg.port) setDbPort(backendCfg.port);
          if (backendCfg.dbname) setDbName(backendCfg.dbname);
          if (backendCfg.schema) setDbSchema(backendCfg.schema);
          if (backendCfg.user) setDbUser(backendCfg.user);
          if (backendCfg.password) setDbPass(backendCfg.password);
          if (typeof backendCfg.connected === 'boolean') {
            setIsConnected(backendCfg.connected);
            if (backendCfg.connected) {
              setDbStatus({ connected: true, message: `Conectado ao schema '${backendCfg.schema || 'schema_synapse'}'` });
            }
          }
          if (typeof backendCfg.setup_done === 'boolean') {
            setIsSetupDone(backendCfg.setup_done);
          }
        }
      } catch (e) {
        console.warn('Could not load database settings from backend:', e);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [setDbStatus]);

  // Auto-persist settings to localStorage on any modification
  useEffect(() => {
    try {
      localStorage.setItem(
        DB_STORAGE_KEY,
        JSON.stringify({
          host: dbHost,
          port: dbPort,
          dbname: dbName,
          schema: dbSchema,
          user: dbUser,
          password: dbPass,
          connected: isConnected,
          setupDone: isSetupDone,
        })
      );
    } catch (e) {
      console.error('Error saving db settings to localStorage:', e);
    }
  }, [dbHost, dbPort, dbName, dbSchema, dbUser, dbPass, isConnected, isSetupDone]);

  const handleFieldChange = (setter: (val: any) => void) => (val: any) => {
    setter(val);
    setIsConnected(false);
    setIsSetupDone(false);
    setDbFeedback(null);
    setDbStatus({ connected: false, message: 'Configurações alteradas' });
  };

  const handleConnect = async () => {
    setDbLoading(true);
    setDbFeedback(null);
    try {
      const res = await systemService.testDbConnection({
        host: dbHost,
        port: Number(dbPort),
        dbname: dbName,
        schema: dbSchema,
        user: dbUser,
        password: dbPass,
      });
      setIsConnected(true);
      setDbStatus({ connected: true, message: `Conectado ao schema '${dbSchema}'` });
      setDbFeedback({ ok: true, msg: res?.message || 'Conexão estabelecida com sucesso ao banco PostgreSQL!' });
    } catch (err: any) {
      setIsConnected(false);
      setDbStatus({ connected: false, message: err?.message || 'Falha na conexão' });
      setDbFeedback({ ok: false, msg: err?.message || 'Falha ao conectar no PostgreSQL.' });
    } finally {
      setDbLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setIsConnected(false);
    setDbStatus({ connected: false, message: 'Desconectado pelo usuário' });
    setDbFeedback({ ok: true, msg: 'Desconectado do banco de dados com sucesso.' });
    try {
      await systemService.disconnectDb();
    } catch {}
  };

  const handleInitializeDb = async () => {
    setDbLoading(true);
    setDbFeedback(null);
    try {
      const res = await systemService.initializeDb(dbRootPass, {
        host: dbHost,
        port: Number(dbPort),
        dbname: dbName,
        schema: dbSchema,
        user: dbUser,
        password: dbPass,
      });
      setIsSetupDone(true);
      setIsConnected(true);
      setDbStatus({ connected: true, message: `Schema '${dbSchema}' provisionado e ativo` });
      setDbFeedback({ ok: true, msg: res?.message || 'Estrutura do banco inicializada com sucesso!' });
    } catch (err: any) {
      setIsSetupDone(false);
      setDbFeedback({ ok: false, msg: err?.message || 'Erro ao inicializar infraestrutura.' });
    } finally {
      setDbLoading(false);
    }
  };

  return (
    <div className="space-y-4 text-xs">
      {/* Connection Status Header */}
      <div className="flex items-center justify-between pb-2 border-b border-border/70">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-primary-500" />
          <span className="font-semibold text-slate-800 dark:text-slate-200">Status do PostgreSQL:</span>
          {isConnected ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700/60 shadow-xs">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              Conectado
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-border">
              <span className="w-2 h-2 rounded-full bg-slate-400" />
              Desconectado
            </span>
          )}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="text-slate-700 dark:text-slate-300 font-semibold">Host:</label>
          <input
            type="text"
            value={dbHost}
            onChange={(e) => handleFieldChange(setDbHost)(e.target.value)}
            className="w-full h-9 px-3 bg-surface dark:bg-background border border-border rounded-xl font-mono text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
          />
        </div>
        <div className="space-y-1">
          <label className="text-slate-700 dark:text-slate-300 font-semibold">Porta:</label>
          <input
            type="number"
            value={dbPort}
            onChange={(e) => handleFieldChange(setDbPort)(Number(e.target.value))}
            className="w-full h-9 px-3 bg-surface dark:bg-background border border-border rounded-xl font-mono text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
          />
        </div>
        <div className="space-y-1">
          <label className="text-slate-700 dark:text-slate-300 font-semibold">Nome do Banco:</label>
          <input
            type="text"
            value={dbName}
            onChange={(e) => handleFieldChange(setDbName)(e.target.value)}
            className="w-full h-9 px-3 bg-surface dark:bg-background border border-border rounded-xl font-mono text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
          />
        </div>
        <div className="space-y-1">
          <label className="text-slate-700 dark:text-slate-300 font-semibold">Schema do SYNAPSE:</label>
          <input
            type="text"
            value={dbSchema}
            onChange={(e) => handleFieldChange(setDbSchema)(e.target.value)}
            placeholder="schema_synapse"
            className="w-full h-9 px-3 bg-surface dark:bg-background border border-border rounded-xl font-mono text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
          />
        </div>
        <div className="space-y-1">
          <label className="text-slate-700 dark:text-slate-300 font-semibold">Usuário:</label>
          <input
            type="text"
            value={dbUser}
            onChange={(e) => handleFieldChange(setDbUser)(e.target.value)}
            className="w-full h-9 px-3 bg-surface dark:bg-background border border-border rounded-xl font-mono text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
          />
        </div>
        <div className="space-y-1">
          <label className="text-slate-700 dark:text-slate-300 font-semibold">Senha:</label>
          <input
            type="password"
            value={dbPass}
            onChange={(e) => handleFieldChange(setDbPass)(e.target.value)}
            className="w-full h-9 px-3 bg-surface dark:bg-background border border-border rounded-xl font-mono text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
          />
        </div>
        <div className="col-span-2 space-y-1">
          <label className="text-slate-700 dark:text-slate-300 font-semibold">
            Senha do Usuário Root / Postgres (necessária apenas para criar usuário e schema):
          </label>
          <input
            type="password"
            value={dbRootPass}
            placeholder="Digite a senha master se for criar novo usuário/schema"
            onChange={(e) => setDbRootPass(e.target.value)}
            className="w-full h-9 px-3 bg-surface dark:bg-background border border-border rounded-xl font-mono text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
          />
        </div>
      </div>

      {/* Feedback alert */}
      {dbFeedback && (
        <div
          className={`p-3 rounded-xl flex items-center gap-2 border ${
            dbFeedback.ok
              ? 'bg-emerald-50 dark:bg-emerald-950/60 border-emerald-200 dark:border-emerald-500/40 text-emerald-800 dark:text-emerald-300'
              : 'bg-rose-50 dark:bg-rose-950/60 border-rose-200 dark:border-rose-500/40 text-rose-700 dark:text-rose-300'
          }`}
        >
          {dbFeedback.ok ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-rose-600 dark:text-rose-400" />
          )}
          <span>{dbFeedback.msg}</span>
        </div>
      )}

      {/* DB Actions */}
      <div className="flex items-center justify-between pt-2 border-t border-border/80">
        {isConnected ? (
          <button
            onClick={handleDisconnect}
            disabled={dbLoading}
            className="px-4 py-2 rounded-xl font-semibold flex items-center gap-2 transition-all bg-rose-50 dark:bg-rose-950/40 border border-rose-300 dark:border-rose-700/60 text-rose-700 dark:text-rose-300 hover:bg-rose-100 dark:hover:bg-rose-900/60 shadow-xs cursor-pointer"
          >
            <Unplug className="w-4 h-4 text-rose-500" />
            Desconectar
          </button>
        ) : (
          <button
            onClick={handleConnect}
            disabled={dbLoading}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl font-bold shadow-md shadow-primary-600/20 flex items-center gap-2 transition-all cursor-pointer"
          >
            {dbLoading ? (
              'Conectando...'
            ) : (
              <>
                <Plug className="w-4 h-4" />
                Conectar ao Banco
              </>
            )}
          </button>
        )}

        <button
          onClick={handleInitializeDb}
          disabled={dbLoading || isSetupDone}
          className={`px-4 py-2 rounded-xl font-bold shadow-md flex items-center gap-2 transition-all ${
            isSetupDone
              ? 'bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-400 dark:border-emerald-500/60 text-emerald-700 dark:text-emerald-300 shadow-none cursor-default'
              : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/20 cursor-pointer'
          }`}
        >
          {dbLoading ? (
            'Processando...'
          ) : isSetupDone ? (
            <>
              <CheckCircle2 className="w-4 h-4" /> Configurado ✓
            </>
          ) : (
            <>
              <Wrench className="w-4 h-4" /> Criar Usuário, Schema e Tabelas
            </>
          )}
        </button>
      </div>
    </div>
  );
};
