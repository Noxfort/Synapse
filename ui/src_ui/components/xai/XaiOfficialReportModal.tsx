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
// File: ui/src_ui/components/xai/XaiOfficialReportModal.tsx
// Author: Gabriel Moraes
// Date: 2026-09-02

import React, { useState, useMemo } from 'react';
import {
  X,
  FileCheck,
  Printer,
  ShieldCheck,
  FileText,
  Loader2,
  SlidersHorizontal,
} from 'lucide-react';
import { XaiResultItem } from '../../types/xai';
import { IReportBuilder, IReportExportService, OfficialReportData } from '../../types/report';
import { useSensorsStore } from '../../stores';
import { useReportTypographyStore } from '../../stores/useReportTypographyStore';
import { defaultReportBuilder } from '../../services/report/reportBuilder';
import { defaultReportExportService } from '../../services/report/reportExportService';

import { ReportTypographyToolbar } from './report/ReportTypographyToolbar';
import { Page1ExecutiveSummary } from './report/pages/Page1ExecutiveSummary';
import { Page2TechnicalAudit } from './report/pages/Page2TechnicalAudit';
import { Page3SafetyAndAttribution } from './report/pages/Page3SafetyAndAttribution';
import { Page4FormulasAndCounterfactual } from './report/pages/Page4FormulasAndCounterfactual';
import { Page5QuesitosAndLegal } from './report/pages/Page5QuesitosAndLegal';
import { Page6SignaturesAndReferences } from './report/pages/Page6SignaturesAndReferences';

interface XaiOfficialReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  result?: XaiResultItem | null;
  savedReport?: OfficialReportData | null;
  reportBuilder?: IReportBuilder;
  exportService?: IReportExportService;
}

/**
 * Official Traffic Engineering & Municipal Operations Audit Report Modal.
 * Standardized in strict compliance with ABNT NBR 10719, NBR 14724, CTB Art. 24, and CONTRAN Manual Vol. V.
 * Refactored in strict accordance with SOLID principles (SRP, OCP, LSP, ISP, DIP).
 */
export const XaiOfficialReportModal: React.FC<XaiOfficialReportModalProps> = ({
  isOpen,
  onClose,
  result,
  savedReport,
  reportBuilder = defaultReportBuilder,
  exportService = defaultReportExportService,
}) => {
  const [exportingDocx, setExportingDocx] = useState(false);
  const [showFormatControls, setShowFormatControls] = useState(false);
  const sources = useSensorsStore((s) => s.sources);

  // Typography Preferences from Store
  const { fontFamily, fontSize, lineSpacing, alignment } = useReportTypographyStore();

  // Build Domain Model (Delegated to IReportBuilder abstraction)
  const reportData = useMemo<OfficialReportData>(() => {
    if (savedReport) return savedReport;
    return reportBuilder.build(result, sources);
  }, [savedReport, result, sources, reportBuilder]);

  if (!isOpen) return null;

  const handleExportDocx = async () => {
    setExportingDocx(true);
    try {
      const fileName = `Laudo_Tecnico_Trafego_${reportData.protocol}.docx`;
      await exportService.exportToDocx(reportData, fileName, {
        fontFamily,
        fontSize,
        lineSpacing,
        alignment,
      });
    } catch (e) {
      console.error('Error generating DOCX:', e);
    } finally {
      setExportingDocx(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const TOTAL_PAGES = 6;

  // Dynamic CSS styles for on-screen live preview
  const previewFontFamily =
    fontFamily === 'Arial' ? 'Arial, Helvetica, sans-serif' : '"Times New Roman", Times, serif';
  const previewLineHeight = lineSpacing === 1.5 ? '1.75' : lineSpacing === 1.15 ? '1.4' : '1.25';
  const previewTextAlign = alignment === 'left' ? 'left' : 'justify';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-2 sm:p-4 overflow-y-auto animate-in fade-in duration-200">
      <div className="relative w-full max-w-[230mm] max-h-[96vh] flex flex-col bg-slate-200 dark:bg-slate-900 border border-slate-400 dark:border-slate-700 shadow-2xl rounded-2xl overflow-hidden">
        
        {/* Barra de Ferramentas Superior */}
        <div className="flex items-center justify-between px-5 py-3.5 bg-slate-900 text-white border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              <FileCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold tracking-wide">
                  Laudo Técnico & Relatório de Auditoria de Tráfego
                </h2>
                <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30 rounded-xs">
                  Word (.docx) / ABNT
                </span>
              </div>
              <p className="text-[11px] text-slate-300 font-mono">
                Protocolo: {reportData.protocol} • Processo: {reportData.processNumber}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Botão para alternar a Barra de Tipografia */}
            <button
              onClick={() => setShowFormatControls(!showFormatControls)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 border ${
                showFormatControls
                  ? 'bg-blue-600 border-blue-500 text-white shadow-sm'
                  : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
              }`}
              title="Ajustar tamanho da fonte, espaçamento e alinhamento do laudo"
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span>Formatação</span>
              <span className="text-[10px] bg-slate-950/40 px-1.5 py-0.5 rounded-sm font-mono text-slate-300">
                {fontFamily} • {fontSize}pt • {lineSpacing}x
              </span>
            </button>

            {/* Imprimir */}
            <button
              onClick={handlePrint}
              className="p-1.5 rounded-lg bg-slate-800 border border-slate-700 hover:bg-slate-700 text-slate-300 transition-colors"
              title="Imprimir visualização do laudo"
            >
              <Printer className="w-4 h-4" />
            </button>

            {/* Exportar DOCX */}
            <button
              onClick={handleExportDocx}
              disabled={exportingDocx}
              className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 active:scale-95 text-white text-xs font-bold transition-all flex items-center gap-2 shadow-lg shadow-blue-950/40 disabled:opacity-50"
              title="Exportar documento Microsoft Word (.docx) formatado segundo as normas ABNT"
            >
              {exportingDocx ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Gerando Word (.docx)...</span>
                </>
              ) : (
                <>
                  <FileText className="w-4 h-4" />
                  <span>Salvar DOCX (Oficial)</span>
                </>
              )}
            </button>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors ml-1"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Subcomponente Especializado: Barra de Tipografia (SRP) */}
        <ReportTypographyToolbar isVisible={showFormatControls} />

        {/* Banner de Conformidade e Resumo de Configuração */}
        <div className="px-5 py-2 bg-slate-950/90 text-[11px] text-slate-300 flex items-center justify-between border-b border-slate-800 font-mono">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
            <span>Formato Nativo: Microsoft Word (.docx) • Padrão Editorial ABNT NBR 10719 & NBR 6023 • CTB Art. 24</span>
          </div>
          <span className="text-slate-400">
            Configuração Ativa: {fontFamily} • {fontSize}pt • {lineSpacing}x • {alignment === 'justify' ? 'Justificado' : 'À Esquerda'}
          </span>
        </div>

        {/* Conteúdo do Laudo com as 6 Folhas ABNT e Estilos Tipográficos Dinâmicos */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 bg-slate-300 dark:bg-slate-950/70">
          <div
            id="official-traffic-audit-dossier"
            className="space-y-6 transition-all duration-150"
            style={{
              fontFamily: previewFontFamily,
              textAlign: previewTextAlign as any,
              lineHeight: previewLineHeight,
              fontSize: `${fontSize}pt`,
            }}
          >
            {/* Folha 1: Timbre, Autuação e PARTE I (Sumário Executivo e Quadro Comparativo) */}
            <Page1ExecutiveSummary
              report={reportData}
              pageNumber={1}
              totalPages={TOTAL_PAGES}
            />

            {/* Folha 2: PARTE II (Objeto, Diagnóstico de Tráfego, Panorama HCM e Tabela de Detectores) */}
            <Page2TechnicalAudit
              report={reportData}
              pageNumber={2}
              totalPages={TOTAL_PAGES}
            />

            {/* Folha 3: Guardrails CONTRAN e Atribuição Causal de Tráfego */}
            <Page3SafetyAndAttribution
              report={reportData}
              pageNumber={3}
              totalPages={TOTAL_PAGES}
            />

            {/* Folha 4: Memorial de Cálculo Matemático e Análise Contrafactual */}
            <Page4FormulasAndCounterfactual
              report={reportData}
              pageNumber={4}
              totalPages={TOTAL_PAGES}
            />

            {/* Folha 5: Resposta aos Quesitos Técnicos e Enquadramento Normativo */}
            <Page5QuesitosAndLegal
              report={reportData}
              pageNumber={5}
              totalPages={TOTAL_PAGES}
            />

            {/* Folha 6: Parecer Conclusivo, Assinaturas Oficiais e Referências Bibliográficas */}
            <Page6SignaturesAndReferences
              report={reportData}
              pageNumber={6}
              totalPages={TOTAL_PAGES}
            />
          </div>
        </div>

      </div>
    </div>
  );
};
