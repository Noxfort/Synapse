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
// File: ui/src_ui/components/wizard/MapImportModal.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React, { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { X, FolderOpen, ArrowRight } from 'lucide-react';
import { topologyService, systemService } from '../../services/api';

interface MapImportModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const MapImportModal: React.FC<MapImportModalProps> = ({ isOpen, onClose }) => {
  const { t } = useTranslation();
  const [filePath, setFilePath] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const isValidSumoExtension = (path: string) => {
    const lower = path.toLowerCase().trim();
    return lower.endsWith('.net.xml') || lower.endsWith('.net.xml.gz');
  };

  const handleBrowseFile = async () => {
    setErrorMessage(null);
    try {
      const res = await systemService.pickFile({
        title: 'Selecionar Rede Viária SUMO (.net.xml / .net.xml.gz)',
        filter: 'Rede Viária SUMO (*.net.xml, *.net.xml.gz) | *.net.xml *.net.xml.gz',
        filterName: 'Rede Viária SUMO (*.net.xml, *.net.xml.gz)',
        extensions: ['net.xml', 'net.xml.gz'],
      });
      if (res && res.path && !res.cancelled) {
        if (!isValidSumoExtension(res.path)) {
          setErrorMessage('Por favor, selecione um arquivo válido de rede viária SUMO (.net.xml ou .net.xml.gz).');
          return;
        }
        setFilePath(res.path);
      } else if (res?.cancelled) {
        // User closed or cancelled dialog
      } else {
        fileInputRef.current?.click();
      }
    } catch (err) {
      console.warn('[MapImportModal] Falha ao invocar seletor nativo, usando fallback HTML:', err);
      fileInputRef.current?.click();
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const fileName = file.name;
      if (!isValidSumoExtension(fileName)) {
        setErrorMessage(`O arquivo '${fileName}' não é uma rede viária SUMO válida (.net.xml ou .net.xml.gz).`);
        e.target.value = '';
        return;
      }
      const path = (file as any).path || fileName;
      setFilePath(path);
      setErrorMessage(null);
    }
  };

  const handleLoadMap = async () => {
    const cleanPath = filePath.trim();
    if (!cleanPath) return;

    if (!isValidSumoExtension(cleanPath)) {
      setErrorMessage('O arquivo selecionado deve ter a extensão .net.xml ou .net.xml.gz.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    try {
      console.log('[MapImportModal] Carregando mapa SUMO:', cleanPath);
      await topologyService.loadMap(cleanPath);
      onClose();
    } catch (err: any) {
      console.error('[MapImportModal] Falha ao carregar mapa SUMO:', err);
      setErrorMessage(err?.message || 'Falha ao carregar arquivo de mapa SUMO.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in select-none">
      <div className="w-full max-w-2xl glass-panel bg-surface p-6 rounded-2xl shadow-2xl border border-border space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border/80 pb-4">
          <h2 className="text-base font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
            <FolderOpen className="w-5 h-5 text-primary-500 dark:text-primary-400" />
            <span>Carregar Rede Viária SUMO</span>
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-surfaceHover transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Hidden file input for web fallback */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".net.xml,.net.xml.gz"
          onChange={handleFileInputChange}
          className="hidden"
        />

        {/* Content */}
        <div className="space-y-4 text-xs">
          <div className="p-3 bg-primary-50 dark:bg-primary-500/10 border border-primary-200 dark:border-primary-500/20 rounded-xl text-primary-800 dark:text-primary-300">
            Informe o caminho absoluto para a rede viária SUMO (<code className="font-mono font-bold text-primary-900 dark:text-white">.net.xml</code> ou{' '}
            <code className="font-mono font-bold text-primary-900 dark:text-white">.net.xml.gz</code>).
          </div>

          <div className="space-y-1.5">
            <label className="text-slate-700 dark:text-slate-300 font-semibold">Caminho do Arquivo no Disco (.net.xml / .net.xml.gz):</label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                placeholder="/caminho/para/mapa.net.xml ou .net.xml.gz"
                value={filePath}
                onChange={(e) => setFilePath(e.target.value)}
                className="flex-1 h-10 px-3 bg-surface dark:bg-background border border-border rounded-xl text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:border-primary-500 font-mono text-xs"
              />
              <button
                type="button"
                onClick={handleBrowseFile}
                title={t('wizard.browseTooltip')}
                className="h-10 px-3.5 bg-surface border border-border hover:border-primary-500 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm group"
              >
                <FolderOpen className="w-4 h-4 text-primary-500 dark:text-primary-400 group-hover:scale-110 transition-transform" />
                <span>{t('wizard.browse')}</span>
              </button>
            </div>
          </div>

          {errorMessage && (
            <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-500/40 text-rose-700 dark:text-rose-300">
              {errorMessage}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 border-t border-border/80 pt-4">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
          >
            {t('settings.cancel')}
          </button>
          <button
            onClick={handleLoadMap}
            disabled={!filePath.trim()}
            className="px-5 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white text-xs font-bold shadow-md shadow-primary-600/20 transition-all flex items-center gap-1.5"
          >
            <span>Carregar Mapa</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
