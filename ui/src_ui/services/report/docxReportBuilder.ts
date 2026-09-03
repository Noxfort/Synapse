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
// File: ui/src_ui/services/report/docxReportBuilder.ts
// Author: Gabriel Moraes
// Date: 2026-09-02

import {
  Document,
  Packer,
  Paragraph,
  TextRun,
  Header,
  Footer,
  PageNumber,
  PageBreak,
  AlignmentType,
} from 'docx';
import { OfficialReportData, ReportTypographyOptions } from '../../types/report';
import { getDocxTypographyConfig, DocxTypographyConfig } from './docx/abntDocxStyles';
import {
  DocxHeaderSection,
  DocxExecutiveSummarySection,
  DocxTechnicalAuditSection,
  DocxSafetyAttributionSection,
  DocxMathFormulasSection,
  DocxQuesitosLegalSection,
  DocxClosingSection,
} from './docx/sections';

/**
 * Single Responsibility: Orchestrates high-level ABNT document assembly and compiles OpenXML Blob.
 * Section formatting and domain-specific rules are decoupled into dedicated SOLID builders.
 */
export class DocxReportBuilder {
  public static async generateBlob(
    report: OfficialReportData,
    options?: ReportTypographyOptions
  ): Promise<Blob> {
    const config = getDocxTypographyConfig(options);

    const doc = new Document({
      creator: 'SYNAPSE Core v2.0 Enterprise',
      title: `Relatório Técnico de Tráfego - ${report.protocol}`,
      description: 'Laudo Técnico e Relatório de Auditoria de Tráfego conforme normas da ABNT e CTB Art. 24',
      sections: [
        {
          properties: {
            page: {
              margin: config.margins,
            },
          },
          headers: {
            default: this.createDocumentHeader(report, config),
          },
          footers: {
            default: this.createDocumentFooter(config),
          },
          children: [
            // 1. Timbre Institucional, Título e Autuação do Processo
            ...DocxHeaderSection.build(report, config),

            new Paragraph({ spacing: { before: 240 } }),

            // 2. PARTE I — Sumário Executivo para Gestão Pública e Tabela de Desempenho
            ...DocxExecutiveSummarySection.build(report, config),

            // Quebra de Página Formal para Parte II
            new Paragraph({ children: [new PageBreak()] }),

            // 3. PARTE II — Relatório Técnico, Panorama HCM e Tabela de Detectores
            ...DocxTechnicalAuditSection.build(report, config),

            new Paragraph({ spacing: { before: 180 } }),

            // 4. Auditoria de Segurança do CONTRAN e Atribuição Causal de Tráfego
            ...DocxSafetyAttributionSection.build(report, config),

            // Quebra de Página para Formulações Matemáticas e Quesitos
            new Paragraph({ children: [new PageBreak()] }),

            // 5. Memorial de Cálculo Matemático (Fórmulas 1 a 6) e Contrafactual
            ...DocxMathFormulasSection.build(report, config),

            new Paragraph({ spacing: { before: 180 } }),

            // 6. Resposta aos Quesitos Técnicos e Enquadramento Normativo
            ...DocxQuesitosLegalSection.build(report, config),

            new Paragraph({ spacing: { before: 240 } }),

            // 7. Parecer Técnico Conclusivo, Bloco de Assinaturas e Referências ABNT
            ...DocxClosingSection.build(report, config),
          ],
        },
      ],
    });

    return await Packer.toBlob(doc);
  }

  private static createDocumentHeader(
    report: OfficialReportData,
    config: DocxTypographyConfig
  ): Header {
    return new Header({
      children: [
        new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [
            new TextRun({
              text: `${report.cityHall} • ${report.department} • Processo: ${report.processNumber}`,
              size: config.microSize,
              font: config.font,
              color: '555555',
            }),
          ],
        }),
      ],
    });
  }

  private static createDocumentFooter(config: DocxTypographyConfig): Footer {
    return new Footer({
      children: [
        new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [
            new TextRun({
              text: 'SYNAPSE Percepção de Tráfego • Folha ',
              size: config.microSize,
              font: config.font,
              color: '555555',
            }),
            new TextRun({
              children: [PageNumber.CURRENT],
              size: config.microSize,
              font: config.font,
              color: '555555',
            }),
            new TextRun({
              text: ' de ',
              size: config.microSize,
              font: config.font,
              color: '555555',
            }),
            new TextRun({
              children: [PageNumber.TOTAL_PAGES],
              size: config.microSize,
              font: config.font,
              color: '555555',
            }),
          ],
        }),
      ],
    });
  }
}
