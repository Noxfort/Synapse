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
// File: ui/src_ui/components/settings/tabs/MonitorSettingsTab.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React, { useState, useEffect, useRef } from 'react';
import { CheckCircle2, AlertTriangle, Wifi, WifiOff, Radio, Plug, Unplug } from 'lucide-react';
import { systemService } from '../../../services/api';
import { useSystemStore } from '../../../stores';

const MONITOR_STORAGE_KEY = 'synapse_monitor_settings_v1';

const getSavedMonitorSettings = () => {
  try {
    const raw = localStorage.getItem(MONITOR_STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch (e) {
    console.error('Error loading monitor settings from localStorage:', e);
  }
  return null;
};

const parseHostPort = (rawIp: string) => {
  const clean = rawIp.trim();
  if (clean.includes(':')) {
    const parts = clean.split(':');
    return { host: parts[0]?.trim() || 'localhost', port: Number(parts[1]?.trim()) || 1883 };
  }
  return { host: clean || 'localhost', port: 1883 };
};

export const MonitorSettingsTab: React.FC = () => {
  const saved = getSavedMonitorSettings();
  const { setMonitorStatus } = useSystemStore();

  const [telemetryIp, setTelemetryIp] = useState<string>(
    saved?.ip ?? (saved?.host ? (saved?.port && saved.port !== 1883 ? `${saved.host}:${saved.port}` : saved.host) : 'localhost')
  );
  const [isConnected, setIsConnected] = useState<boolean>(saved?.connected ?? false);
  const [testing, setTesting] = useState(false);
  const [feedback, setFeedback] = useState<{ ok: boolean; msg: string } | null>(null);

  // Load persistent telemetry settings from backend settings.ini on mount
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const backendCfg = await systemService.getTelemetryConfig();
        if (mounted && backendCfg) {
          const loadedIp = backendCfg.ip || (backendCfg.host ? (backendCfg.port && backendCfg.port !== 1883 ? `${backendCfg.host}:${backendCfg.port}` : backendCfg.host) : 'localhost');
          setTelemetryIp(loadedIp);
          if (typeof backendCfg.connected === 'boolean') {
            setIsConnected(backendCfg.connected);
            setMonitorStatus({
              connected: backendCfg.connected,
              ip: loadedIp,
              host: backendCfg.host || 'localhost',
              port: backendCfg.port || 1883,
              message: backendCfg.connected ? `Conectado em ${loadedIp}` : 'Desconectado',
            });
          }
        }
      } catch (e) {
        console.warn('Could not load telemetry settings from backend:', e);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [setMonitorStatus]);

  // Persist to localStorage
  useEffect(() => {
    try {
      const { host, port } = parseHostPort(telemetryIp);
      localStorage.setItem(
        MONITOR_STORAGE_KEY,
        JSON.stringify({
          ip: telemetryIp,
          host,
          port,
          connected: isConnected,
        })
      );
    } catch (e) {
      console.error('Error saving monitor settings to localStorage:', e);
    }
  }, [telemetryIp, isConnected]);

  const handleIpChange = (newIp: string) => {
    setTelemetryIp(newIp);
    setIsConnected(false);
    setFeedback(null);
    setMonitorStatus({ connected: false, message: 'Configurações alteradas' });
  };

  const handleConnect = async () => {
    setTesting(true);
    setFeedback(null);
    try {
      const { host, port } = parseHostPort(telemetryIp);
      setIsConnected(true);
      setMonitorStatus({
        connected: true,
        ip: telemetryIp,
        host,
        port,
        message: `Conectado em ${host}:${port}`,
      });
      setFeedback({ ok: true, msg: `Conectado ao broker MQTT em ${host}:${port}. Transmissão ativada.` });
      await systemService.saveTelemetryConfig({ ip: telemetryIp, host, port, connected: true });
    } catch (err: any) {
      setIsConnected(false);
      setMonitorStatus({ connected: false, message: 'Falha na conexão' });
      setFeedback({ ok: false, msg: err?.message || 'Falha ao conectar ao broker MQTT.' });
    } finally {
      setTesting(false);
    }
  };

  const handleDisconnect = async () => {
    setIsConnected(false);
    setMonitorStatus({ connected: false, message: 'Desconectado pelo usuário' });
    setFeedback({ ok: true, msg: 'Telemetria externa desconectada com sucesso.' });
    try {
      const { host, port } = parseHostPort(telemetryIp);
      await systemService.saveTelemetryConfig({ ip: telemetryIp, host, port, connected: false });
    } catch {}
  };

  return (
    <div className="space-y-4 text-xs">
      {/* Telemetry Status Header */}
      <div className="flex items-center justify-between pb-2 border-b border-border/70">
        <div className="flex items-center gap-2">
          <Radio className="w-4 h-4 text-primary-500" />
          <span className="font-semibold text-slate-800 dark:text-slate-200">Status da Telemetria (MQTT):</span>
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

      <div className="space-y-1.5">
        <label className="text-slate-700 dark:text-slate-300 font-semibold">Endereço IP do Servidor / Broker:</label>
        <input
          type="text"
          value={telemetryIp}
          onChange={(e) => handleIpChange(e.target.value)}
          placeholder="Cole aqui o IP (ex: 192.168.1.50 ou localhost)"
          className="w-full h-9 px-3 bg-surface dark:bg-background border border-border rounded-xl font-mono text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
        />
        <span className="text-[11px] text-slate-500 dark:text-slate-400 block">
          A porta padrão MQTT (1883) é atribuída automaticamente. Se necessário, informe <code>IP:porta</code>.
        </span>
      </div>

      {/* Feedback alert */}
      {feedback && (
        <div
          className={`p-3 rounded-xl flex items-center gap-2 border ${
            feedback.ok
              ? 'bg-emerald-50 dark:bg-emerald-950/60 border-emerald-200 dark:border-emerald-500/40 text-emerald-800 dark:text-emerald-300'
              : 'bg-rose-50 dark:bg-rose-950/60 border-rose-200 dark:border-rose-500/40 text-rose-700 dark:text-rose-300'
          }`}
        >
          {feedback.ok ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
          ) : (
            <WifiOff className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0" />
          )}
          <span>{feedback.msg}</span>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center pt-2 border-t border-border/80">
        {isConnected ? (
          <button
            onClick={handleDisconnect}
            disabled={testing}
            className="px-4 py-2 rounded-xl font-semibold flex items-center gap-2 transition-all bg-rose-50 dark:bg-rose-950/40 border border-rose-300 dark:border-rose-700/60 text-rose-700 dark:text-rose-300 hover:bg-rose-100 dark:hover:bg-rose-900/60 shadow-xs cursor-pointer"
          >
            <WifiOff className="w-4 h-4 text-rose-500" />
            Desconectar Telemetria
          </button>
        ) : (
          <button
            onClick={handleConnect}
            disabled={testing}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl font-bold shadow-md shadow-primary-600/20 flex items-center gap-2 transition-all cursor-pointer"
          >
            {testing ? (
              'Conectando...'
            ) : (
              <>
                <Wifi className="w-4 h-4" />
                Conectar Telemetria
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
};
