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
// File: ui/src_ui/components/wizard/steps/SensorsStep.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Radio,
  Cloud,
  Database,
  FolderOpen,
  PlusCircle,
  CheckCircle2,
  Trash2,
  Copy,
  Check
} from 'lucide-react';
import { useSensorsStore, useSecurityStore } from '../../../stores';
import { sensorService, systemService } from '../../../services/api';

export const SensorsStep: React.FC = () => {
  const { t } = useTranslation();
  const { sources } = useSensorsStore();
  const requestAuth = useSecurityStore((s) => s.requestAuth);

  const [sensorType, setSensorType] = useState<'PARQUET' | 'LOCAL' | 'GLOBAL'>('PARQUET');
  const [sensorName, setSensorName] = useState('');
  const [globalUrl, setGlobalUrl] = useState('');
  const [parquetPath, setParquetPath] = useState('');
  const [localIp, setLocalIp] = useState('127.0.0.1');
  const [sensorId, setSensorId] = useState('');
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [isBrowsing, setIsBrowsing] = useState(false);
  const [isImportingParquet, setIsImportingParquet] = useState(false);

  const getNextLocalId = (currentSources: typeof sources) => {
    const existingNums = currentSources
      .map((s) => {
        const m = s.id.match(/^src_(\d+)$/i);
        return m ? parseInt(m[1], 10) : 0;
      })
      .filter((n) => n > 0);

    let nextNum = 1;
    while (existingNums.includes(nextNum)) {
      nextNum++;
    }
    return `src_${nextNum}`;
  };

  useEffect(() => {
    if (sensorType === 'LOCAL') {
      setSensorId(getNextLocalId(sources));
    } else if (sensorType === 'GLOBAL') {
      setSensorId(`api_global_${Math.random().toString(36).substring(2, 7)}`);
    } else {
      setSensorId('historical_base');
    }
  }, [sources, sensorType]);

  useEffect(() => {
    systemService
      .getNetworkInfo()
      .then((res) => {
        if (res?.local_ip) setLocalIp(res.local_ip);
      })
      .catch(() => {});
  }, []);

  const handleCopy = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const handleBrowseParquet = async () => {
    if (isBrowsing) return;
    setIsBrowsing(true);
    try {
      const res = await systemService.pickFile({
        title: 'Selecionar Base de Sensores Parquet (.parquet)',
        filter: 'Base Parquet (*.parquet) | *.parquet',
        filterName: 'Base Parquet (*.parquet)',
        extensions: ['parquet'],
      });
      if (res && res.path && !res.cancelled) {
        if (!res.path.toLowerCase().endsWith('.parquet')) {
          setSuccessMsg('O arquivo selecionado deve ter extensão .parquet');
          return;
        }
        setParquetPath(res.path);
        if (!sensorName.trim()) {
          const fileName = res.path.split(/[\/\\]/).pop()?.replace(/\.parquet$/i, '') || 'Sensores Parquet';
          setSensorName(fileName);
        }
      }
    } catch (err) {
      console.warn('[SensorsStep] Falha ao selecionar arquivo:', err);
    } finally {
      setIsBrowsing(false);
    }
  };

  const handleRegisterSensor = async () => {
    const finalName =
      sensorName.trim() ||
      (sensorType === 'LOCAL'
        ? `Fonte Local (${sensorId})`
        : sensorType === 'GLOBAL'
        ? `Fonte Global (${sensorId})`
        : `Base de Sensores Parquet (${sensorId})`);

    if (sensorType === 'PARQUET') {
      const cleanPath = parquetPath.trim();
      if (!cleanPath) return;

      setIsImportingParquet(true);
      try {
        await systemService.importParquet(cleanPath);
        await sensorService.addSource({
          id: sensorId,
          name: finalName,
          is_local: false,
          connection: cleanPath,
          source_type: 'Parquet',
        });
        setSuccessMsg(`Base de sensores Parquet "${finalName}" cadastrada com sucesso!`);
        setParquetPath('');
        setSensorName('');
      } catch (err: any) {
        setSuccessMsg(`Erro ao registrar base Parquet: ${err?.message || err}`);
      } finally {
        setIsImportingParquet(false);
      }
    } else if (sensorType === 'GLOBAL') {
      await sensorService.addSource({
        id: sensorId,
        name: finalName,
        is_local: false,
        connection: globalUrl.trim(),
        source_type: 'API',
      });
      setSuccessMsg(`Sensor "${finalName}" registrado com sucesso!`);
      setSensorName('');
      setGlobalUrl('');
    } else {
      const endpoint = `http://${localIp}:8080/${sensorId}`;
      await sensorService.addSource({
        id: sensorId,
        name: finalName,
        is_local: true,
        connection: endpoint,
        source_type: 'MQTT',
      });
      setSuccessMsg(`Sensor "${finalName}" registrado com sucesso!`);
      setSensorName('');
    }

    setTimeout(() => setSuccessMsg(null), 3500);
  };

  return (
    <div className="space-y-4 animate-in fade-in">
      {/* Information Header */}
      <div className="p-3.5 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 rounded-xl text-emerald-800 dark:text-emerald-300 flex items-start gap-2.5">
        <Radio className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-bold text-slate-900 dark:text-white">{t('wizard.sensorsTitle')}</p>
          <p className="text-[11px] text-slate-600 dark:text-slate-300 mt-0.5">{t('wizard.sensorsDesc')}</p>
        </div>
      </div>

      {/* Sensor Registration Form Card */}
      <div className="p-4 rounded-xl bg-surface dark:bg-background/80 border border-border space-y-4 shadow-sm">
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={() => setSensorType('PARQUET')}
            className={`flex-1 py-2 px-3 rounded-xl border text-xs font-bold flex items-center justify-center gap-2 transition-all ${
              sensorType === 'PARQUET'
                ? 'bg-sky-50 dark:bg-accent-cyan/20 border-accent-cyan text-sky-900 dark:text-white shadow-sm'
                : 'bg-surface border-border text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Database className="w-4 h-4 text-accent-cyan" />
            <span>{t('wizard.sensorTypeParquet')}</span>
          </button>

          <button
            type="button"
            onClick={() => setSensorType('LOCAL')}
            className={`flex-1 py-2 px-3 rounded-xl border text-xs font-bold flex items-center justify-center gap-2 transition-all ${
              sensorType === 'LOCAL'
                ? 'bg-sky-50 dark:bg-accent-cyan/20 border-accent-cyan text-sky-900 dark:text-white shadow-sm'
                : 'bg-surface border-border text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Radio className="w-4 h-4 text-accent-cyan" />
            <span>{t('wizard.sensorTypeLocal')}</span>
          </button>

          <button
            type="button"
            onClick={() => setSensorType('GLOBAL')}
            className={`flex-1 py-2 px-3 rounded-xl border text-xs font-bold flex items-center justify-center gap-2 transition-all ${
              sensorType === 'GLOBAL'
                ? 'bg-primary-50 dark:bg-primary-600/30 border-primary-500 text-primary-900 dark:text-white shadow-sm'
                : 'bg-surface border-border text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Cloud className="w-4 h-4 text-primary-500 dark:text-primary-400" />
            <span>{t('wizard.sensorTypeGlobal')}</span>
          </button>
        </div>

        <div className="space-y-1.5">
          <label className="text-slate-700 dark:text-slate-300 font-semibold">Nome de Identificação da Fonte:</label>
          <input
            type="text"
            placeholder={
              sensorType === 'PARQUET'
                ? 'Ex: Base Histórica de Radares'
                : sensorType === 'LOCAL'
                ? 'Ex: Câmera Av. Paulista Norte'
                : 'Ex: Feed Tráfego Waze'
            }
            value={sensorName}
            onChange={(e) => setSensorName(e.target.value)}
            className="w-full h-9 px-3 bg-surface dark:bg-background border border-border rounded-xl text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 font-sans text-xs"
          />
        </div>

        {sensorType === 'PARQUET' ? (
          <div className="space-y-1.5">
            <label className="text-slate-700 dark:text-slate-300 font-semibold">
              Arquivo da Base Parquet com Sensores (.parquet):
            </label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                placeholder="/caminho/para/dados_sensores.parquet"
                value={parquetPath}
                onChange={(e) => setParquetPath(e.target.value)}
                className="flex-1 h-9 px-3 bg-surface dark:bg-background border border-border rounded-xl text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:border-accent-cyan font-mono text-xs"
              />
              <button
                type="button"
                onClick={handleBrowseParquet}
                disabled={isBrowsing}
                title={isBrowsing ? 'Abrindo seletor de arquivos...' : t('wizard.browseTooltip')}
                className={`h-9 px-3 bg-surface border border-border text-slate-700 dark:text-slate-300 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm ${
                  isBrowsing
                    ? 'opacity-50 cursor-not-allowed'
                    : 'hover:border-accent-cyan hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <FolderOpen className={`w-3.5 h-3.5 text-accent-cyan ${isBrowsing ? 'animate-pulse' : ''}`} />
                <span>{isBrowsing ? 'Aguarde...' : t('wizard.browse')}</span>
              </button>
            </div>
          </div>
        ) : sensorType === 'GLOBAL' ? (
          <div className="space-y-1.5">
            <label className="text-slate-700 dark:text-slate-300 font-semibold">Endpoint URL (REST / Stream):</label>
            <input
              type="text"
              placeholder="https://api.provedor.com/v1/traffic"
              value={globalUrl}
              onChange={(e) => setGlobalUrl(e.target.value)}
              className="w-full h-9 px-3 bg-surface dark:bg-background border border-border rounded-xl text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:border-primary-500 font-mono text-xs"
            />
          </div>
        ) : (
          <div className="space-y-2 p-3 bg-slate-50 dark:bg-surface/80 border border-border rounded-xl">
            <div className="space-y-1">
              <span className="text-slate-500 dark:text-slate-400 text-[10px] font-semibold">URL de Envio (POST):</span>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={`http://${localIp}:8080/${sensorId}`}
                  className="w-full h-7 px-2 bg-surface dark:bg-background border border-border rounded-lg text-accent-cyan font-mono text-xs font-semibold"
                />
                <button
                  type="button"
                  onClick={() => handleCopy(`http://${localIp}:8080/${sensorId}`, 'url')}
                  className="px-2 h-7 bg-surface dark:bg-background border border-border hover:border-slate-400 dark:hover:border-slate-500 rounded-lg text-slate-700 dark:text-slate-300 flex items-center gap-1"
                >
                  {copiedField === 'url' ? (
                    <Check className="w-3 h-3 text-emerald-500 dark:text-emerald-400" />
                  ) : (
                    <Copy className="w-3 h-3" />
                  )}
                </button>
              </div>
            </div>

            <div className="space-y-1">
              <span className="text-slate-500 dark:text-slate-400 text-[10px] font-semibold">ID do Sensor (payload JSON):</span>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={sensorId}
                  className="w-full h-7 px-2 bg-surface dark:bg-background border border-border rounded-lg text-accent-cyan font-mono text-xs font-bold"
                />
                <button
                  type="button"
                  onClick={() => handleCopy(sensorId, 'id')}
                  className="px-2 h-7 bg-surface dark:bg-background border border-border hover:border-slate-400 dark:hover:border-slate-500 rounded-lg text-slate-700 dark:text-slate-300 flex items-center gap-1"
                >
                  {copiedField === 'id' ? (
                    <Check className="w-3 h-3 text-emerald-500 dark:text-emerald-400" />
                  ) : (
                    <Copy className="w-3 h-3" />
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="flex items-center justify-end">
          <button
            type="button"
            onClick={handleRegisterSensor}
            disabled={
              sensorType === 'PARQUET'
                ? !parquetPath.trim() || isImportingParquet
                : !sensorName.trim()
            }
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold rounded-xl shadow-md shadow-emerald-600/30 transition-all flex items-center gap-2"
          >
            {isImportingParquet ? (
              <span className="animate-spin text-white">⏳</span>
            ) : (
              <PlusCircle className="w-4 h-4" />
            )}
            <span>
              {sensorType === 'PARQUET'
                ? isImportingParquet
                  ? 'Importando...'
                  : t('wizard.importParquetSensor')
                : t('wizard.addAnotherSensor')}
            </span>
          </button>
        </div>
      </div>

      {/* Success Alert */}
      {successMsg && (
        <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-500/40 text-emerald-800 dark:text-emerald-300 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Registered Sources Summary List */}
      <div className="space-y-2 pt-2">
        <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
          {t('wizard.registeredSensors')} ({sources.length})
        </span>
        {sources.length === 0 ? (
          <div className="p-3 border border-dashed border-border rounded-xl text-center text-slate-400 dark:text-slate-500 text-xs">
            Nenhum sensor cadastrado até o momento.
          </div>
        ) : (
          <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
            {sources.map((src) => {
              const isParquet =
                src.source_type === 'Parquet' ||
                src.connection_string?.toLowerCase().endsWith('.parquet') ||
                src.id === 'historical_base';

              return (
                <div
                  key={src.id}
                  className="p-2 rounded-lg bg-surface dark:bg-background/80 border border-border flex items-center justify-between shadow-xs"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    {isParquet ? (
                      <Database className="w-3.5 h-3.5 flex-shrink-0 text-accent-cyan" />
                    ) : (
                      <Radio
                        className={`w-3.5 h-3.5 flex-shrink-0 ${
                          src.is_local ? 'text-accent-cyan' : 'text-primary-500 dark:text-primary-400'
                        }`}
                      />
                    )}
                    <span className="font-medium text-slate-800 dark:text-slate-200 truncate">{src.name}</span>
                    <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500">({src.id})</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[9px] font-bold px-2 py-0.5 rounded border ${
                        isParquet
                          ? 'bg-accent-cyan/10 text-accent-cyan border-accent-cyan/30'
                          : src.is_local
                          ? 'bg-accent-cyan/10 text-accent-cyan border-accent-cyan/30'
                          : 'bg-primary-500/10 text-primary-600 dark:text-primary-400 border-primary-500/30'
                      }`}
                    >
                      {isParquet ? 'PARQUET' : src.is_local ? 'LOCAL' : 'GLOBAL'}
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        requestAuth(async () => {
                          await sensorService.removeSource(src.id);
                        });
                      }}
                      className="p-1 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 transition-colors"
                      title="Remover Sensor"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
