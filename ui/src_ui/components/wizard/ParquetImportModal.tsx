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
// File: ui/src_ui/components/wizard/ParquetImportModal.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React, { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Database, CheckCircle2, ArrowRight, FolderOpen } from 'lucide-react';
import { useEtlStore } from '../../stores';
import { systemService } from '../../services/api';

interface ParquetImportModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ParquetImportModal: React.FC<ParquetImportModalProps> = ({ isOpen, onClose }) => {
  const { t } = useTranslation();
  const { parquetInspection, importProgress, setParquetInspection, setImportProgress, resetEtlState } = useEtlStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [filePath, setFilePath] = useState('');
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const isValidParquetExtension = (path: string) => {
    return path.toLowerCase().trim().endsWith('.parquet');
  };

  const handleBrowseFile = async () => {
    setErrorMessage(null);
    try {
      const res = await systemService.pickFile({
        title: 'Selecionar Base Histórica Parquet (.parquet)',
        filter: 'Base Parquet (*.parquet) | *.parquet',
        filterName: 'Base Parquet (*.parquet)',
        extensions: ['parquet'],
      });
      if (res && res.path && !res.cancelled) {
        if (!isValidParquetExtension(res.path)) {
          setErrorMessage('Por favor, selecione um arquivo válido no formato Parquet (.parquet).');
          return;
        }
        setFilePath(res.path);
      } else if (res?.cancelled) {
        // User closed or cancelled dialog
      } else {
        fileInputRef.current?.click();
      }
    } catch {
      fileInputRef.current?.click();
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const fileName = file.name;
      if (!isValidParquetExtension(fileName)) {
        setErrorMessage(`O arquivo '${fileName}' não é uma base Parquet válida (.parquet).`);
        e.target.value = '';
        return;
      }
      const path = (file as any).path || fileName;
      setFilePath(path);
      setErrorMessage(null);
    }
  };

  const handleInspectParquet = async () => {
    const cleanPath = filePath.trim();
    if (!cleanPath) return;

    if (!isValidParquetExtension(cleanPath)) {
      setErrorMessage('O arquivo selecionado deve ter a extensão .parquet.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await systemService.inspectParquet(cleanPath);
      if (res?.num_rows !== undefined) {
        setParquetInspection(res);
        setStep(2);
      } else {
        setErrorMessage('Formato Parquet inválido ou arquivo não encontrado.');
      }
    } catch (err: any) {
      setErrorMessage(err?.message || 'Erro ao inspecionar dataset.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleExecuteImport = async () => {
    const cleanPath = filePath.trim();
    if (!cleanPath) return;

    if (!isValidParquetExtension(cleanPath)) {
      setErrorMessage('O arquivo selecionado deve ter a extensão .parquet.');
      return;
    }

    setStep(3);
    setImportProgress({ isImporting: true, progress: 0 });
    await systemService.importParquet(cleanPath);
  };

  const handleModalClose = () => {
    resetEtlState();
    setStep(1);
    setFilePath('');
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in select-none">
      <div className="w-full max-w-2xl glass-panel bg-surface p-6 rounded-2xl shadow-2xl border border-border space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border/80 pb-4">
          <h2 className="text-base font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
            <Database className="w-5 h-5 text-accent-cyan" />
            <span>Assistente de Importação Parquet</span>
          </h2>
          <button
            onClick={handleModalClose}
            className="p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-surfaceHover transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Hidden file input for web fallback */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".parquet"
          onChange={handleFileInputChange}
          className="hidden"
        />

        {/* STEP 1: Path Selection */}
        {step === 1 && (
          <div className="space-y-4 text-xs">
            <div className="p-3 bg-sky-50 dark:bg-primary-500/10 border border-sky-200 dark:border-primary-500/20 rounded-xl text-sky-900 dark:text-primary-300">
              Selecione a base histórica em formato Parquet (<code className="font-mono font-bold text-sky-950 dark:text-white">.parquet</code>) contendo séries temporais de tráfego.
            </div>

            <div className="space-y-1.5">
              <label className="text-slate-700 dark:text-slate-300 font-semibold">Caminho do Arquivo no Disco (.parquet):</label>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  placeholder="/caminho/para/dataset.parquet"
                  value={filePath}
                  onChange={(e) => setFilePath(e.target.value)}
                  className="flex-1 h-10 px-3 bg-surface dark:bg-background border border-border rounded-xl text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:border-primary-500 font-mono text-xs"
                />
                <button
                  type="button"
                  onClick={handleBrowseFile}
                  title={t('wizard.browseTooltip')}
                  className="h-10 px-3.5 bg-surface border border-border hover:border-accent-cyan text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm group"
                >
                  <FolderOpen className="w-4 h-4 text-accent-cyan group-hover:scale-110 transition-transform" />
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
        )}

        {/* STEP 2: Dataset Inspection */}
        {step === 2 && parquetInspection && (
          <div className="space-y-4 text-xs font-mono">
            <div className="grid grid-cols-3 gap-3">
              <div className="p-3 rounded-xl bg-surface dark:bg-background border border-border">
                <span className="text-slate-500 dark:text-slate-400 text-[10px] uppercase font-sans font-semibold">Linhas Totais</span>
                <p className="text-base font-bold text-slate-900 dark:text-white mt-0.5">
                  {parquetInspection.num_rows.toLocaleString()}
                </p>
              </div>
              <div className="p-3 rounded-xl bg-surface dark:bg-background border border-border">
                <span className="text-slate-500 dark:text-slate-400 text-[10px] uppercase font-sans font-semibold">Tamanho do Arquivo</span>
                <p className="text-base font-bold text-accent-cyan mt-0.5">{parquetInspection.size_mb} MB</p>
              </div>
              <div className="p-3 rounded-xl bg-surface dark:bg-background border border-border">
                <span className="text-slate-500 dark:text-slate-400 text-[10px] uppercase font-sans font-semibold">Colunas Detectadas</span>
                <p className="text-base font-bold text-emerald-600 dark:text-emerald-400 mt-0.5">
                  {parquetInspection.columns.length}
                </p>
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-slate-700 dark:text-slate-300 font-semibold font-sans">Colunas do Schema:</label>
              <div className="p-2 rounded-xl bg-surface dark:bg-background border border-border flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
                {parquetInspection.columns.map((c) => (
                  <span
                    key={c}
                    className="px-2 py-0.5 rounded bg-surfaceHover dark:bg-surface border border-border text-[11px] font-mono text-slate-800 dark:text-slate-300"
                  >
                    {c}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* STEP 3: Ingestion Progress */}
        {step === 3 && (
          <div className="space-y-4 text-xs text-center py-6">
            <div className="w-12 h-12 rounded-2xl bg-accent-cyan/10 border border-accent-cyan/30 flex items-center justify-center mx-auto mb-2 animate-bounce">
              <Database className="w-6 h-6 text-accent-cyan" />
            </div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">Ingestão de Dados Históricos em Andamento...</h3>

            <div className="w-full h-3 bg-slate-200 dark:bg-background rounded-full overflow-hidden border border-border">
              <div
                className="h-full bg-gradient-to-r from-primary-500 to-accent-cyan transition-all duration-300"
                style={{ width: `${importProgress.progress}%` }}
              />
            </div>
            <span className="text-xs font-mono text-slate-600 dark:text-slate-400 font-semibold">
              {importProgress.progress}% Concluído {importProgress.status ? `(${importProgress.status})` : ''}
            </span>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 border-t border-border/80 pt-4">
          <button
            onClick={handleModalClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
          >
            {t('settings.cancel')}
          </button>

          {step === 1 && (
            <button
              onClick={handleInspectParquet}
              disabled={!filePath.trim() || isLoading}
              className="px-5 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white text-xs font-bold shadow-md shadow-primary-600/20 transition-all flex items-center gap-1.5"
            >
              <span>Inspecionar Dataset</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          )}

          {step === 2 && (
            <button
              onClick={handleExecuteImport}
              className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-md shadow-emerald-600/30 transition-all flex items-center gap-1.5"
            >
              <span>Iniciar Ingestão no Banco</span>
              <CheckCircle2 className="w-4 h-4" />
            </button>
          )}

          {step === 3 && (
            <button
              onClick={handleModalClose}
              disabled={importProgress.progress < 100}
              className="px-5 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white text-xs font-bold transition-all"
            >
              Concluir
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
