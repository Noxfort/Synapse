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
// File: ui/src_ui/components/settings/tabs/MunicipalSettingsTab.tsx
// Author: Gabriel Moraes
// Date: 2026-09-01

import React, { useState, useRef } from 'react';
import { Landmark, Upload, Trash2, Check, RefreshCw, Image as ImageIcon } from 'lucide-react';
import { useMunicipalSettingsStore } from '../../../stores/useMunicipalSettingsStore';

export const MunicipalSettingsTab: React.FC = () => {
  const settings = useMunicipalSettingsStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [form, setForm] = useState({
    cityHall: settings.cityHall,
    department: settings.department,
    authorityName: settings.authorityName,
    authorityRole: settings.authorityRole,
    registrationNumber: settings.registrationNumber,
    processPrefix: settings.processPrefix,
  });

  const [logoPreview, setLogoPreview] = useState<string | null>(settings.logoDataUrl);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleLogoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        const result = event.target?.result as string;
        setLogoPreview(result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleRemoveLogo = () => {
    setLogoPreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSave = () => {
    settings.updateSettings({
      ...form,
      logoDataUrl: logoPreview,
    });
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  const handleReset = () => {
    settings.resetToDefaults();
    const def = useMunicipalSettingsStore.getState();
    setForm({
      cityHall: def.cityHall,
      department: def.department,
      authorityName: def.authorityName,
      authorityRole: def.authorityRole,
      registrationNumber: def.registrationNumber,
      processPrefix: def.processPrefix,
    });
    setLogoPreview(def.logoDataUrl);
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  return (
    <div className="space-y-5 select-none animate-in fade-in">
      <div className="flex items-center justify-between border-b border-slate-300 dark:border-slate-700 pb-3">
        <div>
          <h3 className="text-sm font-bold text-slate-950 dark:text-white flex items-center gap-2">
            <Landmark className="w-4 h-4 text-primary-600 dark:text-primary-400" />
            Identidade Municipal & Secretaria Demandante
          </h3>
          <p className="text-xs text-slate-700 dark:text-slate-300 mt-0.5 font-medium">
            Personalize a prefeitura, secretaria demandante, autoridade responsável e logotipo oficial dos relatórios.
          </p>
        </div>

        <button
          onClick={handleReset}
          className="px-2.5 py-1.5 text-[11px] font-bold text-slate-800 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg transition-all flex items-center gap-1.5"
          title="Restaurar dados padrão"
        >
          <RefreshCw className="w-3.5 h-3.5 text-slate-700 dark:text-slate-300" />
          <span>Restaurar Padrão</span>
        </button>
      </div>

      {/* Card de Upload do Brasão / Logotipo Oficial */}
      <div className="p-4 bg-slate-100 dark:bg-slate-900 rounded-2xl border border-slate-300 dark:border-slate-700 space-y-3 shadow-xs">
        <label className="text-xs font-bold text-slate-950 dark:text-slate-100 block uppercase tracking-wide">
          Logotipo Oficial da Prefeitura / Brasão de Armas
        </label>

        <div className="flex items-center gap-4">
          <div className="w-20 h-20 rounded-xl border-2 border-dashed border-slate-400 dark:border-slate-600 bg-white dark:bg-slate-950 flex items-center justify-center overflow-hidden shadow-inner">
            {logoPreview ? (
              <img src={logoPreview} alt="Brasão da Prefeitura" className="w-full h-full object-contain p-1" />
            ) : (
              <ImageIcon className="w-8 h-8 text-slate-500 opacity-80" />
            )}
          </div>

          <div className="space-y-2 flex-1">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleLogoUpload}
              accept="image/png, image/jpeg, image/svg+xml"
              className="hidden"
            />

            <div className="flex items-center gap-2">
              <button
                onClick={() => fileInputRef.current?.click()}
                className="px-3.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 dark:bg-primary-600 dark:hover:bg-primary-500 text-white text-xs font-bold transition-all flex items-center gap-1.5 shadow-xs"
              >
                <Upload className="w-3.5 h-3.5" />
                <span>Carregar Imagem do Brasão</span>
              </button>

              {logoPreview && (
                <button
                  onClick={handleRemoveLogo}
                  className="px-2.5 py-1.5 rounded-lg border border-rose-300 dark:border-rose-800 bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 hover:bg-rose-100 text-xs font-bold transition-all flex items-center gap-1"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Remover</span>
                </button>
              )}
            </div>
            <p className="text-[11px] text-slate-600 dark:text-slate-400 font-medium">
              Formatos aceitos: PNG, JPG, SVG (recomendado arquivo de alta resolução com fundo transparente).
            </p>
          </div>
        </div>
      </div>

      {/* Formulário de Identificação Institucional da Secretaria Demandante */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
        <div className="space-y-1 sm:col-span-2">
          <label className="font-bold text-slate-950 dark:text-slate-100 block">
            Nome do Município / Prefeitura
          </label>
          <input
            type="text"
            value={form.cityHall}
            onChange={(e) => setForm({ ...form, cityHall: e.target.value })}
            placeholder="Ex: PREFEITURA DO MUNICÍPIO DE SÃO PAULO"
            className="w-full px-3.5 py-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-950 dark:text-white text-xs font-semibold focus:ring-2 focus:ring-slate-900 dark:focus:ring-primary-500 outline-hidden shadow-xs"
          />
        </div>

        <div className="space-y-1 sm:col-span-2">
          <label className="font-bold text-slate-950 dark:text-slate-100 block">
            Secretaria Demandante
          </label>
          <input
            type="text"
            value={form.department}
            onChange={(e) => setForm({ ...form, department: e.target.value })}
            placeholder="Ex: SECRETARIA MUNICIPAL DE MOBILIDADE URBANA E TRÂNSITO (SMT)"
            className="w-full px-3.5 py-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-950 dark:text-white text-xs font-semibold focus:ring-2 focus:ring-slate-900 dark:focus:ring-primary-500 outline-hidden shadow-xs"
          />
        </div>

        <div className="space-y-1">
          <label className="font-bold text-slate-950 dark:text-slate-100 block">
            Nome da Autoridade / Responsável
          </label>
          <input
            type="text"
            value={form.authorityName}
            onChange={(e) => setForm({ ...form, authorityName: e.target.value })}
            placeholder="Ex: Gabriel Moraes"
            className="w-full px-3.5 py-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-950 dark:text-white text-xs font-semibold focus:ring-2 focus:ring-slate-900 dark:focus:ring-primary-500 outline-hidden shadow-xs"
          />
        </div>

        <div className="space-y-1">
          <label className="font-bold text-slate-950 dark:text-slate-100 block">
            Cargo / Função Oficial
          </label>
          <input
            type="text"
            value={form.authorityRole}
            onChange={(e) => setForm({ ...form, authorityRole: e.target.value })}
            placeholder="Ex: Autoridade Municipal de Trânsito / Secretário de Mobilidade"
            className="w-full px-3.5 py-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-950 dark:text-white text-xs font-semibold focus:ring-2 focus:ring-slate-900 dark:focus:ring-primary-500 outline-hidden shadow-xs"
          />
        </div>

        <div className="space-y-1">
          <label className="font-bold text-slate-950 dark:text-slate-100 block">
            Matrícula Funcional / Portaria de Nomeação
          </label>
          <input
            type="text"
            value={form.registrationNumber}
            onChange={(e) => setForm({ ...form, registrationNumber: e.target.value })}
            placeholder="Ex: Matrícula Funcional nº 84.102-3 • Portaria SMT nº 142/2025"
            className="w-full px-3.5 py-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-950 dark:text-white text-xs font-mono font-semibold focus:ring-2 focus:ring-slate-900 dark:focus:ring-primary-500 outline-hidden shadow-xs"
          />
        </div>

        <div className="space-y-1">
          <label className="font-bold text-slate-950 dark:text-slate-100 block">
            Prefixo do Processo Administrativo
          </label>
          <input
            type="text"
            value={form.processPrefix}
            onChange={(e) => setForm({ ...form, processPrefix: e.target.value })}
            placeholder="Ex: PA-SMT-2026/"
            className="w-full px-3.5 py-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-950 dark:text-white text-xs font-mono font-semibold focus:ring-2 focus:ring-slate-900 dark:focus:ring-primary-500 outline-hidden shadow-xs"
          />
        </div>
      </div>

      {/* Salvar Configurações */}
      <div className="flex items-center justify-end pt-4 border-t border-slate-300 dark:border-slate-700">
        <button
          onClick={handleSave}
          className="px-6 py-2.5 rounded-xl bg-slate-950 hover:bg-slate-800 dark:bg-primary-600 dark:hover:bg-primary-500 text-white text-xs font-bold transition-all flex items-center gap-2 shadow-md"
        >
          {savedSuccess ? (
            <>
              <Check className="w-4 h-4 text-emerald-400" />
              <span>Configurações Salvas com Sucesso!</span>
            </>
          ) : (
            <span>Salvar Alterações</span>
          )}
        </button>
      </div>
    </div>
  );
};
