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
// File: ui/src_ui/services/report/docx/sections/DocxSafetyAttributionSection.ts
// Author: Gabriel Moraes
// Date: 2026-09-02

import { Paragraph, TextRun, Table, TableRow, AlignmentType } from 'docx';
import { OfficialReportData } from '../../../../types/report';
import {
  DocxTypographyConfig,
  ABNT_TABLE_BORDERS,
  createSectionHeading,
  createTableCaption,
  createCarinaTableCell,
} from '../abntDocxStyles';

/**
 * Builds sections for CONTRAN Safety Guardrails and Causal Traffic Demand Attribution.
 */
export class DocxSafetyAttributionSection {
  public static build(
    report: OfficialReportData,
    config: DocxTypographyConfig
  ): (Paragraph | Table)[] {
    return [
      createSectionHeading('4. AUDITORIA DE SEGURANÇA VIÁRIA E GUARDRAILS DO CONTRAN', config),
      ...this.createSafetyGuardrails(report, config),

      new Paragraph({ spacing: { before: 180 } }),

      createSectionHeading('5. DECOMPOSIÇÃO ANALÍTICA E ATRIBUIÇÃO CAUSAL DE DEMANDA', config),
      ...createTableCaption(
        'Tabela 3 – Sensibilidade e peso causal das variáveis de tráfego na tomada de decisão semafórica.',
        config,
        'Fonte: Prefeitura Municipal / Secretaria de Trânsito / Motor de Percepção SYNAPSE (2026).'
      ),
      this.createAttributionsTable(report, config),
    ];
  }

  private static createSafetyGuardrails(
    report: OfficialReportData,
    config: DocxTypographyConfig
  ): Paragraph[] {
    const paragraphs: Paragraph[] = [];
    report.safetyInterventions.forEach((item, idx) => {
      paragraphs.push(
        new Paragraph({
          spacing: { before: 120, after: 40 },
          children: [
            new TextRun({
              text: `4.${idx + 1}. Intervenção ${item.id} — ${item.junction} (${item.timeRecorded}):`,
              bold: true,
              size: config.nameSize,
              font: config.font,
            }),
          ],
        }),
        new Paragraph({
          alignment: config.alignment,
          spacing: { line: config.lineSpacing, after: 40 },
          indent: { firstLine: config.paragraphIndent },
          children: [
            new TextRun({ text: 'Equipamento Auditado: ', bold: true, size: config.nameSize, font: config.font }),
            new TextRun({ text: `${item.equipmentId}. `, size: config.nameSize, font: config.font }),
            new TextRun({ text: 'Dispositivo Normativo Violado: ', bold: true, size: config.nameSize, font: config.font }),
            new TextRun({ text: `${item.contranStandardViolated}.`, size: config.nameSize, font: config.font }),
          ],
        }),
        new Paragraph({
          alignment: config.alignment,
          spacing: { line: config.lineSpacing, after: 40 },
          indent: { firstLine: config.paragraphIndent },
          children: [
            new TextRun({ text: 'Irregularidade Detectada: ', bold: true, size: config.nameSize, font: config.font }),
            new TextRun({ text: item.irregularityDetected, size: config.nameSize, font: config.font }),
          ],
        }),
        new Paragraph({
          alignment: config.alignment,
          spacing: { line: config.lineSpacing, after: 120 },
          indent: { firstLine: config.paragraphIndent },
          children: [
            new TextRun({ text: 'Ação Protetiva Aplicada: ', bold: true, size: config.nameSize, font: config.font }),
            new TextRun({ text: `${item.correctiveGuardrail} (Status: ${item.finalState}).`, size: config.nameSize, font: config.font }),
          ],
        })
      );
    });
    return paragraphs;
  }

  private static createAttributionsTable(
    report: OfficialReportData,
    config: DocxTypographyConfig
  ): Table {
    const header = new TableRow({
      tableHeader: true,
      children: [
        createCarinaTableCell('Var.', 8, config, { bold: true, fill: 'F2F2F2', bottomDarkBorder: true }),
        createCarinaTableCell('Parâmetro de Tráfego / Local', 36, config, { bold: true, fill: 'F2F2F2', bottomDarkBorder: true }),
        createCarinaTableCell('Detector', 16, config, { bold: true, fill: 'F2F2F2', bottomDarkBorder: true }),
        createCarinaTableCell('Peso (%)', 12, config, { bold: true, alignment: AlignmentType.RIGHT, fill: 'F2F2F2', bottomDarkBorder: true }),
        createCarinaTableCell('Impacto na Intervenção', 28, config, { bold: true, fill: 'F2F2F2', bottomDarkBorder: true }),
      ],
    });

    const rows = report.attributions.map(
      (a, idx) =>
        new TableRow({
          children: [
            createCarinaTableCell(`x${idx + 1}`, 8, config, { bold: true, fill: idx % 2 === 1 ? 'F8FAFC' : 'FFFFFF' }),
            createCarinaTableCell(`${a.parameterName} (${a.junctionLocation})`, 36, config, { fill: idx % 2 === 1 ? 'F8FAFC' : 'FFFFFF' }),
            createCarinaTableCell(a.detectorId, 16, config, { fill: idx % 2 === 1 ? 'F8FAFC' : 'FFFFFF' }),
            createCarinaTableCell(`${a.gradientDirection.includes('+') ? '+' : '-'}${a.causalWeightPercent.toFixed(1)}%`, 12, config, { bold: true, alignment: AlignmentType.RIGHT, fill: idx % 2 === 1 ? 'F8FAFC' : 'FFFFFF' }),
            createCarinaTableCell(a.trafficImpactAnalysis, 28, config, { fill: idx % 2 === 1 ? 'F8FAFC' : 'FFFFFF' }),
          ],
        })
    );

    return new Table({
      width: { size: 100, type: 'pct' as any },
      borders: ABNT_TABLE_BORDERS.carinaGrid,
      rows: [header, ...rows],
    });
  }
}
