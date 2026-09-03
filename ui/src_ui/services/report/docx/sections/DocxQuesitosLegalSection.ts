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
// File: ui/src_ui/services/report/docx/sections/DocxQuesitosLegalSection.ts
// Author: Gabriel Moraes
// Date: 2026-09-02

import { Paragraph, TextRun, AlignmentType } from 'docx';
import { OfficialReportData } from '../../../../types/report';
import {
  DocxTypographyConfig,
  createSectionHeading,
} from '../abntDocxStyles';

/**
 * Builds sections for Peritial Quesitos responses and Legal/Normative framing.
 */
export class DocxQuesitosLegalSection {
  public static build(
    report: OfficialReportData,
    config: DocxTypographyConfig
  ): Paragraph[] {
    return [
      createSectionHeading('7. RESPOSTA AOS QUESITOS TÉCNICOS OPERACIONAIS', config),
      ...this.createQuesitos(report, config),

      new Paragraph({ spacing: { before: 180 } }),

      createSectionHeading('8. ENQUADRAMENTO NORMATIVO E FUNDAMENTAÇÃO JURÍDICO-ADMINISTRATIVA', config),
      ...this.createLegalFraming(report, config),
    ];
  }

  private static createQuesitos(
    report: OfficialReportData,
    config: DocxTypographyConfig
  ): Paragraph[] {
    const paragraphs: Paragraph[] = [];
    report.quesitos.forEach((q) => {
      paragraphs.push(
        new Paragraph({
          spacing: { before: 120, after: 40 },
          children: [
            new TextRun({
              text: `Quesito ${q.number}: ${q.question}`,
              bold: true,
              size: config.nameSize,
              font: config.font,
              color: '000000',
            }),
          ],
        }),
        new Paragraph({
          alignment: config.alignment,
          spacing: { line: config.lineSpacing, after: 100 },
          indent: { firstLine: config.paragraphIndent },
          children: [
            new TextRun({ text: 'Resposta Técnica: ', bold: true, size: config.nameSize, font: config.font, color: '000000' }),
            new TextRun({ text: `${q.answer}. `, bold: true, size: config.nameSize, font: config.font, color: '000000' }),
            new TextRun({ text: 'Justificativa Técnica: ', bold: true, size: config.nameSize, font: config.font, color: '000000' }),
            new TextRun({ text: q.technicalJustification, size: config.nameSize, font: config.font, color: '3C3C3C' }),
          ],
        })
      );
    });
    return paragraphs;
  }

  private static createLegalFraming(
    report: OfficialReportData,
    config: DocxTypographyConfig
  ): Paragraph[] {
    const paragraphs: Paragraph[] = [];
    report.legalFraming.forEach((l, idx) => {
      paragraphs.push(
        new Paragraph({
          spacing: { before: 100, after: 40 },
          children: [
            new TextRun({
              text: `8.${idx + 1}. ${l.article}:`,
              bold: true,
              size: config.nameSize,
              font: config.font,
              color: '000000',
            }),
          ],
        }),
        new Paragraph({
          alignment: config.alignment,
          spacing: { line: config.lineSpacing, after: 80 },
          indent: { firstLine: config.paragraphIndent },
          children: [
            new TextRun({ text: l.desc, size: config.nameSize, font: config.font, color: '3C3C3C' }),
          ],
        })
      );
    });
    return paragraphs;
  }
}
