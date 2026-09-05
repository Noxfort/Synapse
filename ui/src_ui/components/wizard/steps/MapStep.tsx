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
// File: ui/src_ui/components/wizard/steps/MapStep.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React, { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { FolderOpen, Network, CheckCircle2, AlertCircle } from 'lucide-react';
import { useTopologyStore } from '../../../stores';
import { topologyService, systemService } from '../../../services/api';

export const MapStep: React.FC = () => {
  const { t } = useTranslation();
  const { nodes, edges, mapLoaded } = useTopologyStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [mapPath, setMapPath] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isBrowsing, setIsBrowsing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const isValidSumoExtension = (path: string) => {
    const lower = path.toLowerCase().trim();
    return lower.endsWith('.net.xml') || lower.endsWith('.net.xml.gz');
  };

  const handleBrowseFile = async () => {
    if (isBrowsing) return;
    setIsBrowsing(true);
    setError(null);
    try {
      const res = await systemService.pickFile({
        title: 'Selecionar Rede Viária SUMO (.net.xml / .net.xml.gz)',
        filter: 'Rede Viária SUMO (*.net.xml, *.net.xml.gz) | *.net.xml *.net.xml.gz',
        filterName: 'Rede Viária SUMO (*.net.xml, *.net.xml.gz)',
        extensions: ['net.xml', 'net.xml.gz'],
      });
      if (res && res.path && !res.cancelled) {
        if (!isValidSumoExtension(res.path)) {
          setError('Por favor, selecione um arquivo válido de rede viária SUMO (.net.xml ou .net.xml.gz).');
          return;
        }
        setMapPath(res.path);
      }
    } catch (err) {
      console.warn('[MapStep] Falha ao invocar seletor de arquivos:', err);
    } finally {
      setIsBrowsing(false);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const fileName = file.name;
      if (!isValidSumoExtension(fileName)) {
        setError(`O arquivo '${fileName}' não é uma rede viária SUMO válida (.net.xml ou .net.xml.gz).`);
        e.target.value = '';
        return;
      }
      const path = (file as any).path || fileName;
      setMapPath(path);
      setError(null);
    }
  };

  const handleLoadMap = async () => {
    const cleanPath = mapPath.trim();
    if (!cleanPath) return;

    if (!isValidSumoExtension(cleanPath)) {
      setError('O arquivo selecionado deve ter a extensão .net.xml ou .net.xml.gz.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      console.log('[MapStep] Carregando mapa SUMO:', cleanPath);
      await topologyService.loadMap(cleanPath);
      setSuccessMsg(t('wizard.mapLoadedSuccess'));
    } catch (err: any) {
      console.error('[MapStep] Falha ao carregar mapa SUMO:', err);
      setError(err?.message || 'Falha ao carregar rede viária SUMO.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-4 animate-in fade-in">
      {/* Information Header */}
      <div className="p-3.5 bg-primary-50 dark:bg-primary-500/10 border border-primary-200 dark:border-primary-500/20 rounded-xl text-primary-700 dark:text-primary-300 flex items-start gap-2.5">
        <FolderOpen className="w-4 h-4 text-primary-600 dark:text-primary-400 flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-bold text-slate-900 dark:text-white">{t('wizard.mapTitle')}</p>
          <p className="text-[11px] text-slate-600 dark:text-primary-200 mt-0.5">{t('wizard.mapDesc')}</p>
        </div>
      </div>

      {/* Hidden file input for web fallback */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".net.xml,.net.xml.gz"
        onChange={handleFileInputChange}
        className="hidden"
      />

      {/* Path Input & Action */}
      <div className="space-y-1.5">
        <label className="text-slate-700 dark:text-slate-300 font-semibold">Caminho do Arquivo SUMO (.net.xml / .net.xml.gz):</label>
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="/caminho/para/rede_viaria.net.xml ou .net.xml.gz"
            value={mapPath}
            onChange={(e) => setMapPath(e.target.value)}
            className="flex-1 h-10 px-3 bg-surface dark:bg-background border border-border rounded-xl text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:border-primary-500 font-mono text-xs"
          />
          <button
            type="button"
            onClick={handleBrowseFile}
            disabled={isBrowsing}
            title={isBrowsing ? 'Abrindo seletor de arquivos...' : t('wizard.browseTooltip')}
            className={`h-10 px-3.5 bg-surface border border-border text-slate-700 dark:text-slate-300 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm group ${
              isBrowsing
                ? 'opacity-50 cursor-not-allowed'
                : 'hover:border-primary-500 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <FolderOpen className={`w-4 h-4 text-primary-500 dark:text-primary-400 ${isBrowsing ? 'animate-pulse' : 'group-hover:scale-110'} transition-transform`} />
            <span>{isBrowsing ? 'Aguarde...' : t('wizard.browse')}</span>
          </button>
          <button
            onClick={handleLoadMap}
            disabled={!mapPath.trim() || isLoading}
            className="px-4 h-10 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white font-bold rounded-xl shadow-md shadow-primary-600/20 transition-all flex items-center gap-2"
          >
            {isLoading ? (
              <span className="animate-spin text-white">⏳</span>
            ) : (
              <Network className="w-4 h-4" />
            )}
            <span>{t('wizard.loadMap')}</span>
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-500/40 text-rose-700 dark:text-rose-300 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Success / Loaded Info */}
      {(successMsg || mapLoaded) && (
        <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-500/40 space-y-2">
          <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400 font-bold">
            <CheckCircle2 className="w-4 h-4" />
            <span>{successMsg || t('wizard.mapLoadedSuccess')}</span>
          </div>
          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="p-2.5 rounded-lg bg-surface dark:bg-background/80 border border-emerald-200 dark:border-emerald-500/20 flex items-center justify-between">
              <span className="text-slate-500 dark:text-slate-400 text-[11px]">{t('wizard.mapNodesCount')}:</span>
              <span className="font-bold text-slate-900 dark:text-white font-mono text-sm">{nodes.length}</span>
            </div>
            <div className="p-2.5 rounded-lg bg-surface dark:bg-background/80 border border-emerald-200 dark:border-emerald-500/20 flex items-center justify-between">
              <span className="text-slate-500 dark:text-slate-400 text-[11px]">{t('wizard.mapEdgesCount')}:</span>
              <span className="font-bold text-slate-900 dark:text-white font-mono text-sm">{edges.length}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
