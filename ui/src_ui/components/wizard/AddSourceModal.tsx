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
// File: ui/src_ui/components/wizard/AddSourceModal.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { PlusCircle, Cloud, Radio, Copy, Check, ArrowLeft, X } from 'lucide-react';
import { sensorService, systemService } from '../../services/api';

import { useSensorsStore } from '../../stores';

interface AddSourceModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AddSourceModal: React.FC<AddSourceModalProps> = ({ isOpen, onClose }) => {
  const { t } = useTranslation();
  const { sources } = useSensorsStore();

  const [step, setStep] = useState<1 | 2>(1);
  const [sourceType, setSourceType] = useState<'LOCAL' | 'GLOBAL'>('LOCAL');
  const [sourceName, setSourceName] = useState('');
  const [globalUrl, setGlobalUrl] = useState('');

  // Local Edge generated info
  const [localIp, setLocalIp] = useState('127.0.0.1');
  const [sourceId, setSourceId] = useState('');
  const [copiedField, setCopiedField] = useState<string | null>(null);

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
    if (isOpen) {
      if (sourceType === 'LOCAL') {
        setSourceId(getNextLocalId(sources));
      } else {
        setSourceId(`api_global_${Math.random().toString(36).substring(2, 7)}`);
      }
      systemService
        .getNetworkInfo()
        .then((res) => {
          if (res?.local_ip) setLocalIp(res.local_ip);
        })
        .catch(() => {});
    }
  }, [isOpen, sourceType, sources]);

  if (!isOpen) return null;

  const handleCopy = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const handleRegister = async () => {
    const finalName = sourceName.trim() || (sourceType === 'LOCAL' ? `Fonte Local (${sourceId})` : `Fonte Global (${sourceId})`);

    if (sourceType === 'GLOBAL') {
      await sensorService.addSource({
        id: sourceId,
        name: finalName,
        is_local: false,
        connection: globalUrl.trim(),
      });
    } else {
      await sensorService.addSource({
        id: sourceId,
        name: finalName,
        is_local: true,
        connection: `http://${localIp}:8080/${sourceId}`,
      });
    }

    onClose();
    setStep(1);
    setSourceName('');
    setGlobalUrl('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in select-none">
      <div className="w-full max-w-xl glass-panel bg-surface p-6 rounded-2xl shadow-2xl border border-border space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border/80 pb-4">
          <h2 className="text-base font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
            <PlusCircle className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            <span>Assistente de Cadastro de Nova Fonte</span>
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-surfaceHover transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* STEP 1: Select Type */}
        {step === 1 && (
          <div className="space-y-4 text-xs">
            <p className="text-slate-700 dark:text-slate-300 font-semibold">Selecione a tipologia de origem do dado:</p>

            <div className="grid grid-cols-2 gap-4">
              {/* Option Local */}
              <div
                onClick={() => {
                  setSourceType('LOCAL');
                  setStep(2);
                }}
                className="p-5 rounded-2xl bg-surface dark:bg-background/80 border border-border hover:border-accent-cyan/60 cursor-pointer transition-all flex flex-col items-center text-center space-y-3 group shadow-xs"
              >
                <div className="w-12 h-12 rounded-xl bg-accent-cyan/10 border border-accent-cyan/30 flex items-center justify-center text-accent-cyan group-hover:scale-110 transition-transform">
                  <Radio className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">Dispositivo Local (Push)</h3>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                    Câmeras, laços indutivos ou radares conectados via rede local.
                  </p>
                </div>
              </div>

              {/* Option Global */}
              <div
                onClick={() => {
                  setSourceType('GLOBAL');
                  setStep(2);
                }}
                className="p-5 rounded-2xl bg-surface dark:bg-background/80 border border-border hover:border-primary-500/60 cursor-pointer transition-all flex flex-col items-center text-center space-y-3 group shadow-xs"
              >
                <div className="w-12 h-12 rounded-xl bg-primary-500/10 border border-primary-500/30 flex items-center justify-center text-primary-500 dark:text-primary-400 group-hover:scale-110 transition-transform">
                  <Cloud className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">API Global (Pull)</h3>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                    Serviços em nuvem, feeds externos de trânsito (Waze, TomTom).
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* STEP 2: Configuration */}
        {step === 2 && (
          <div className="space-y-4 text-xs">
            <div className="space-y-1.5">
              <label className="text-slate-700 dark:text-slate-300 font-semibold">1. Nome de Identificação da Fonte:</label>
              <input
                type="text"
                placeholder="Ex: Câmera Av. Paulista Norte"
                value={sourceName}
                onChange={(e) => setSourceName(e.target.value)}
                className="w-full h-10 px-3 bg-surface dark:bg-background border border-border rounded-xl text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:border-primary-500 font-sans text-xs"
              />
            </div>

            {sourceType === 'GLOBAL' ? (
              <div className="space-y-1.5">
                <label className="text-slate-700 dark:text-slate-300 font-semibold">2. Endpoint URL (REST / Stream):</label>
                <input
                  type="text"
                  placeholder="https://api.provedor.com/v1/traffic"
                  value={globalUrl}
                  onChange={(e) => setGlobalUrl(e.target.value)}
                  className="w-full h-10 px-3 bg-surface dark:bg-background border border-border rounded-xl text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:border-primary-500 font-mono text-xs"
                />
              </div>
            ) : (
              <div className="space-y-3 p-4 bg-slate-50 dark:bg-background/80 border border-border rounded-xl">
                <span className="font-bold text-slate-900 dark:text-white block">Instruções para Configuração do Sensor:</span>

                <div className="space-y-1">
                  <span className="text-slate-500 dark:text-slate-400 text-[11px] font-semibold">URL de Envio (POST):</span>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      readOnly
                      value={`http://${localIp}:8080/${sourceId}`}
                      className="w-full h-8 px-2.5 bg-surface dark:bg-background border border-border rounded-lg text-accent-cyan font-mono text-xs font-semibold"
                    />
                    <button
                      onClick={() => handleCopy(`http://${localIp}:8080/${sourceId}`, 'url')}
                      className="px-2.5 h-8 bg-surface dark:bg-background border border-border hover:border-slate-400 dark:hover:border-slate-600 rounded-lg text-slate-700 dark:text-slate-300 flex items-center gap-1 font-semibold"
                    >
                      {copiedField === 'url' ? (
                        <Check className="w-3.5 h-3.5 text-emerald-500 dark:text-emerald-400" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>

                <div className="space-y-1">
                  <span className="text-slate-500 dark:text-slate-400 text-[11px] font-semibold">ID do Sensor (deve constar no JSON):</span>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      readOnly
                      value={sourceId}
                      className="w-full h-8 px-2.5 bg-surface dark:bg-background border border-border rounded-lg text-accent-cyan font-mono text-xs font-bold"
                    />
                    <button
                      onClick={() => handleCopy(sourceId, 'id')}
                      className="px-2.5 h-8 bg-surface dark:bg-background border border-border hover:border-slate-400 dark:hover:border-slate-600 rounded-lg text-slate-700 dark:text-slate-300 flex items-center gap-1 font-semibold"
                    >
                      {copiedField === 'id' ? (
                        <Check className="w-3.5 h-3.5 text-emerald-500 dark:text-emerald-400" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border/80 pt-4">
          {step === 2 ? (
            <button
              onClick={() => setStep(1)}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white flex items-center gap-1.5"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Voltar</span>
            </button>
          ) : (
            <div />
          )}

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
            >
              {t('settings.cancel')}
            </button>

            {step === 2 && (
              <button
                onClick={handleRegister}
                disabled={!sourceName.trim()}
                className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-bold shadow-md shadow-emerald-600/30 transition-all"
              >
                Concluir & Registrar
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
