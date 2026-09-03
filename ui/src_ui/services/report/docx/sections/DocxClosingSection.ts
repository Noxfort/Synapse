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
// File: ui/src_ui/services/report/docx/sections/DocxClosingSection.ts
// Author: Gabriel Moraes
// Date: 2026-09-02

import { Paragraph, TextRun, AlignmentType } from 'docx';
import { OfficialReportData } from '../../../../types/report';
import {
  DocxTypographyConfig,
  createSectionHeading,
  createParagraph,
} from '../abntDocxStyles';

/**
 * Builds Section 9 (Final Considerations & Technical Opinion), Official Signatures Block,
 * and Section 10 (ABNT NBR 6023 Bibliographic References) matching the Carina benchmark.
 */
export class DocxClosingSection {
  public static build(
    report: OfficialReportData,
    config: DocxTypographyConfig
  ): Paragraph[] {
    return [
      createSectionHeading('9. CONSIDERAÇÕES FINAIS E PARECER TÉCNICO CONCLUSIVO', config),

      createParagraph(
        'Conclui-se, do ponto de vista técnico e operacional, que a intervenção semafórica adaptativa executada na malha arterial do Corredor Paulista mostrou-se plenamente regular, necessária e eficaz, tendo eliminado a retenção crítica de veículos e preservado integralmente todos os tempos de segurança viária estabelecidos pelas resoluções do CONTRAN.',
        config
      ),
      createParagraph(
        'O presente Relatório Técnico Operacional é emitido sob a competência expressa do Art. 24 do Código de Trânsito Brasileiro (Lei nº 9.503/1997) e homologado pela equipe técnica de fiscalização e operações de trânsito do município.',
        config
      ),

      new Paragraph({ spacing: { before: 200 } }),

      // Linha de Assinatura Centralizada (Padrão Carina)
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 200, after: 40 },
        children: [
          new TextRun({
            text: '___________________________________________________',
            bold: true,
            font: config.font,
            color: '000000',
          }),
        ],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 20 },
        children: [
          new TextRun({
            text: report.authorityName,
            bold: true,
            size: config.nameSize,
            font: config.font,
            color: '000000',
          }),
        ],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 20 },
        children: [
          new TextRun({
            text: report.authorityRole,
            size: 19,
            font: config.font,
            color: '3C3C3C',
          }),
        ],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 80 },
        children: [
          new TextRun({
            text: `${report.registrationNumber} – ${report.cityHall} / ${report.department}`,
            size: 19,
            font: config.font,
            color: '505050',
          }),
        ],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 240 },
        children: [
          new TextRun({
            text: `Este laudo foi gerado de forma determinística pelo motor de auditoria semafórica SYNAPSE Core v2.0 Enterprise (Certificação: ${report.digitalCertification || 'HOMOLOGADO'}). Ele atesta as métricas operacionais e a conformidade pericial da malha em tempo real.`,
            italics: true,
            size: config.microSize,
            font: config.font,
            color: '505050',
          }),
        ],
      }),

      createSectionHeading('10. REFERÊNCIAS NORMATIVAS E BIBLIOGRÁFICAS (ABNT NBR 6023:2018)', config),
      ...report.references.map(
        (ref) =>
          new Paragraph({
            alignment: config.alignment,
            spacing: { line: config.singleLineSpacing, after: 120 },
            children: [
              new TextRun({
                text: ref,
                size: config.noteSize,
                font: config.font,
                color: '000000',
              }),
            ],
          })
      ),

      new Paragraph({ spacing: { before: 200 } }),

      // Nota Final de Encerramento (Padrão Carina)
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 120, after: 60 },
        children: [
          new TextRun({
            text: 'Fim do Laudo Técnico Oficial de Auditoria de Tráfego – SYNAPSE Core v2.0 Enterprise',
            bold: true,
            size: config.bodySize,
            font: config.font,
            color: '505050',
          }),
        ],
      }),
    ];
  }
}
