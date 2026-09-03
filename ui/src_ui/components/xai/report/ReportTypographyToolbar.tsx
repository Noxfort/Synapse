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
// File: ui/src_ui/components/xai/report/ReportTypographyToolbar.tsx
// Author: Gabriel Moraes
// Date: 2026-09-02

import React from 'react';
import { AlignJustify, AlignLeft, RotateCcw } from 'lucide-react';
import { useReportTypographyStore } from '../../../stores/useReportTypographyStore';

interface ReportTypographyToolbarProps {
  isVisible: boolean;
}

/**
 * Single Responsibility: Renders and manages the typography configuration controls
 * (Font Family, Font Size, Line Spacing, Text Alignment, and Reset).
 */
export const ReportTypographyToolbar: React.FC<ReportTypographyToolbarProps> = ({ isVisible }) => {
  const {
    fontFamily,
    fontSize,
    lineSpacing,
    alignment,
    setFontFamily,
    setFontSize,
    setLineSpacing,
    setAlignment,
    resetDefaults,
  } = useReportTypographyStore();

  if (!isVisible) return null;

  return (
    <div className="bg-slate-950/95 border-b border-slate-800 px-5 py-3 text-xs text-slate-200 animate-in slide-in-from-top-2 duration-150">
      <div className="flex flex-wrap items-center justify-between gap-4">
        
        {/* Seleção de Fonte */}
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Fonte:</span>
          <div className="inline-flex rounded-lg border border-slate-700 p-0.5 bg-slate-900">
            <button
              onClick={() => setFontFamily('Arial')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                fontFamily === 'Arial'
                  ? 'bg-blue-600 text-white font-bold shadow-xs'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Arial (Carina)
            </button>
            <button
              onClick={() => setFontFamily('Times New Roman')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                fontFamily === 'Times New Roman'
                  ? 'bg-blue-600 text-white font-bold shadow-xs'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Times New Roman (ABNT)
            </button>
          </div>
        </div>

        {/* Tamanho da Fonte */}
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Tamanho:</span>
          <div className="inline-flex rounded-lg border border-slate-700 p-0.5 bg-slate-900">
            {[10, 11, 12, 13, 14].map((sz) => (
              <button
                key={sz}
                onClick={() => setFontSize(sz)}
                className={`px-2 py-1 rounded-md text-[11px] font-medium transition-all ${
                  fontSize === sz
                    ? 'bg-blue-600 text-white font-bold shadow-xs'
                    : 'text-slate-400 hover:text-white'
                }`}
                title={sz === 12 ? 'Padrão Oficial ABNT / Carina (12pt)' : `${sz}pt`}
              >
                {sz}pt {sz === 12 && '★'}
              </button>
            ))}
          </div>
        </div>

        {/* Espaçamento entre Linhas */}
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Entrelinha:</span>
          <div className="inline-flex rounded-lg border border-slate-700 p-0.5 bg-slate-900">
            {[
              { label: '1.0', value: 1.0 as const, title: 'Simples' },
              { label: '1.15', value: 1.15 as const, title: 'Moderado' },
              { label: '1.5 ★', value: 1.5 as const, title: 'Padrão ABNT / Carina' },
            ].map((sp) => (
              <button
                key={sp.value}
                onClick={() => setLineSpacing(sp.value)}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                  lineSpacing === sp.value
                    ? 'bg-blue-600 text-white font-bold shadow-xs'
                    : 'text-slate-400 hover:text-white'
                }`}
                title={sp.title}
              >
                {sp.label}
              </button>
            ))}
          </div>
        </div>

        {/* Alinhamento do Texto */}
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Alinhamento:</span>
          <div className="inline-flex rounded-lg border border-slate-700 p-0.5 bg-slate-900">
            <button
              onClick={() => setAlignment('justify')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium flex items-center gap-1 transition-all ${
                alignment === 'justify'
                  ? 'bg-blue-600 text-white font-bold shadow-xs'
                  : 'text-slate-400 hover:text-white'
              }`}
              title="Justificado (Padrão ABNT NBR 14724)"
            >
              <AlignJustify className="w-3.5 h-3.5" />
              <span>Justificado</span>
            </button>
            <button
              onClick={() => setAlignment('left')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium flex items-center gap-1 transition-all ${
                alignment === 'left'
                  ? 'bg-blue-600 text-white font-bold shadow-xs'
                  : 'text-slate-400 hover:text-white'
              }`}
              title="Alinhado à Esquerda"
            >
              <AlignLeft className="w-3.5 h-3.5" />
              <span>À Esquerda</span>
            </button>
          </div>
        </div>

        {/* Restaurar Padrão */}
        <button
          onClick={resetDefaults}
          className="px-2.5 py-1 rounded-lg border border-slate-700 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors flex items-center gap-1 text-[11px]"
          title="Restaurar parâmetros padrão de tipografia ABNT/Carina"
        >
          <RotateCcw className="w-3 h-3" />
          <span>Padrão</span>
        </button>

      </div>
    </div>
  );
};
