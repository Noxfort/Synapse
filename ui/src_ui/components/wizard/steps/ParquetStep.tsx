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
// File: ui/src_ui/components/wizard/steps/ParquetStep.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React, { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Database, CheckCircle2, ArrowRight, AlertCircle, FolderOpen } from 'lucide-react';
import { useEtlStore } from '../../../stores';
import { systemService } from '../../../services/api';

export const ParquetStep: React.FC = () => {
  const { t } = useTranslation();
  const { parquetInspection, importProgress, setParquetInspection, setImportProgress } = useEtlStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [parquetPath, setParquetPath] = useState('');
  const [subStep, setSubStep] = useState<'SELECT' | 'INSPECTED' | 'IMPORTING'>('SELECT');
  const [isLoading, setIsLoading] = useState(false);
  const [isBrowsing, setIsBrowsing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isValidParquetExtension = (path: string) => {
    return path.toLowerCase().trim().endsWith('.parquet');
  };

  const handleBrowseFile = async () => {
    if (isBrowsing) return;
    setIsBrowsing(true);
    setError(null);
    try {
      const res = await systemService.pickFile({
        title: 'Selecionar Base Histórica Parquet (.parquet)',
        filter: 'Base Parquet (*.parquet) | *.parquet',
        filterName: 'Base Parquet (*.parquet)',
        extensions: ['parquet'],
      });
      if (res && res.path && !res.cancelled) {
        if (!isValidParquetExtension(res.path)) {
          setError('Por favor, selecione um arquivo válido no formato Parquet (.parquet).');
          return;
        }
        setParquetPath(res.path);
      }
    } catch (err) {
      console.warn('[ParquetStep] Falha ao invocar seletor de arquivos:', err);
    } finally {
      setIsBrowsing(false);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const fileName = file.name;
      if (!isValidParquetExtension(fileName)) {
        setError(`O arquivo '${fileName}' não é uma base Parquet válida (.parquet).`);
        e.target.value = '';
        return;
      }
      const path = (file as any).path || fileName;
      setParquetPath(path);
      setError(null);
    }
  };

  const handleInspect = async () => {
    const cleanPath = parquetPath.trim();
    if (!cleanPath) return;

    if (!isValidParquetExtension(cleanPath)) {
      setError('O arquivo selecionado deve ter a extensão .parquet.');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const res = await systemService.inspectParquet(cleanPath);
      if (res?.num_rows !== undefined) {
        setParquetInspection(res);
        setSubStep('INSPECTED');
      } else {
        setError('Formato Parquet inválido ou arquivo não encontrado.');
      }
    } catch (err: any) {
      setError(err?.message || 'Erro ao inspecionar dataset.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleExecuteImport = async () => {
    const cleanPath = parquetPath.trim();
    if (!cleanPath) return;

    if (!isValidParquetExtension(cleanPath)) {
      setError('O arquivo selecionado deve ter a extensão .parquet.');
      return;
    }

    setSubStep('IMPORTING');
    setImportProgress({ isImporting: true, progress: 0 });
    await systemService.importParquet(cleanPath);
  };

  return (
    <div className="space-y-4 animate-in fade-in">
      {/* Information Header */}
      <div className="p-3.5 bg-sky-50 dark:bg-accent-cyan/10 border border-sky-200 dark:border-accent-cyan/20 rounded-xl text-sky-800 dark:text-accent-cyan flex items-start gap-2.5">
        <Database className="w-4 h-4 text-sky-600 dark:text-accent-cyan flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-bold text-slate-900 dark:text-white">{t('wizard.parquetTitle')}</p>
          <p className="text-[11px] text-slate-600 dark:text-slate-300 mt-0.5">{t('wizard.parquetDesc')}</p>
        </div>
      </div>

      {/* Hidden file input for web fallback */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".parquet"
        onChange={handleFileInputChange}
        className="hidden"
      />

      {/* Sub-step 1: File selection & inspection trigger */}
      {subStep === 'SELECT' && (
        <div className="space-y-3">
          <div className="space-y-1.5">
            <label className="text-slate-700 dark:text-slate-300 font-semibold">Caminho da Base Parquet (.parquet):</label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                placeholder="/caminho/para/dados_historicos.parquet"
                value={parquetPath}
                onChange={(e) => setParquetPath(e.target.value)}
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
                    : 'hover:border-accent-cyan hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <FolderOpen className={`w-4 h-4 text-accent-cyan ${isBrowsing ? 'animate-pulse' : 'group-hover:scale-110'} transition-transform`} />
                <span>{isBrowsing ? 'Aguarde...' : t('wizard.browse')}</span>
              </button>
              <button
                onClick={handleInspect}
                disabled={!parquetPath.trim() || isLoading}
                className="px-4 h-10 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white font-bold rounded-xl shadow-md shadow-primary-600/20 transition-all flex items-center gap-2"
              >
                {isLoading ? (
                  <span className="animate-spin text-white">⏳</span>
                ) : (
                  <ArrowRight className="w-4 h-4" />
                )}
                <span>{t('wizard.inspectParquet')}</span>
              </button>
            </div>
          </div>

          {error && (
            <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-500/40 text-rose-700 dark:text-rose-300 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>
      )}

      {/* Sub-step 2: Inspection results & confirmation */}
      {subStep === 'INSPECTED' && parquetInspection && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              {t('wizard.parquetInspected')}
            </span>
            <button
              onClick={() => setSubStep('SELECT')}
              className="text-[11px] text-primary-600 dark:text-slate-400 hover:underline font-semibold"
            >
              Alterar Arquivo
            </button>
          </div>

          <div className="grid grid-cols-3 gap-3 font-mono">
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
            <div className="p-2.5 rounded-xl bg-surface dark:bg-background border border-border flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
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

          <button
            onClick={handleExecuteImport}
            className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl shadow-md shadow-emerald-600/30 transition-all flex items-center justify-center gap-2"
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>{t('wizard.startParquetImport')}</span>
          </button>
        </div>
      )}

      {/* Sub-step 3: Real-time Ingestion Progress */}
      {subStep === 'IMPORTING' && (
        <div className="space-y-4 text-center py-4">
          <div className="w-12 h-12 rounded-2xl bg-accent-cyan/10 border border-accent-cyan/30 flex items-center justify-center mx-auto mb-2 animate-bounce">
            <Database className="w-6 h-6 text-accent-cyan" />
          </div>
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">
            {importProgress.progress === 100
              ? t('wizard.parquetSuccess')
              : !importProgress.isImporting && importProgress.status
              ? 'Falha na Importação'
              : t('wizard.parquetIngesting')}
          </h3>

          <div className="w-full h-3 bg-slate-200 dark:bg-background rounded-full overflow-hidden border border-border">
            <div
              className={`h-full transition-all duration-300 ${
                !importProgress.isImporting && importProgress.progress < 100
                  ? 'bg-rose-500'
                  : 'bg-gradient-to-r from-primary-500 to-accent-cyan'
              }`}
              style={{ width: `${Math.max(importProgress.progress, 5)}%` }}
            />
          </div>
          
          <span className="text-xs font-mono text-slate-600 dark:text-slate-400 block font-semibold">
            {importProgress.progress}% Concluído {importProgress.status ? `(${importProgress.status})` : ''}
          </span>

          {!importProgress.isImporting && importProgress.progress < 100 && (
            <div className="pt-2 space-y-3">
              <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-500/40 text-rose-700 dark:text-rose-300 text-xs flex items-center gap-2 text-left">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{importProgress.status || 'Erro no processamento da base Parquet.'}</span>
              </div>
              <button
                onClick={() => setSubStep('SELECT')}
                className="px-4 py-2 bg-surface hover:bg-surfaceHover border border-border text-slate-700 dark:text-slate-200 hover:text-slate-900 dark:hover:text-white rounded-xl text-xs font-semibold"
              >
                Voltar e Selecionar Outro Arquivo
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
