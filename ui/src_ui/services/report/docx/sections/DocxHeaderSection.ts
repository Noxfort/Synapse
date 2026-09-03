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
// File: ui/src_ui/services/report/docx/sections/DocxHeaderSection.ts
// Author: Gabriel Moraes
// Date: 2026-09-02

import {
  Paragraph,
  TextRun,
  Table,
  TableRow,
  TableCell,
  WidthType,
  AlignmentType,
} from 'docx';
import { OfficialReportData } from '../../../../types/report';
import {
  DocxTypographyConfig,
  ABNT_TABLE_BORDERS,
  createSectionHeading,
  createCarinaTableCell,
} from '../abntDocxStyles';

/**
 * Builds the official institutional header, date, title, and operational environment table
 * in identical conformity with the Carina benchmark (sas.docx / mfd.docx).
 */
export class DocxHeaderSection {
  public static build(report: OfficialReportData, config: DocxTypographyConfig): (Paragraph | Table)[] {
    const formattedDate = new Date(report.timestamp).toLocaleDateString('pt-BR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });

    return [
      // 1. Tabela 1 de Cabeçalho Institucional (Timbre Municipal)
      this.createInstitutionalHeaderTable(report, config),

      // Linha em branco separadora
      new Paragraph({ spacing: { before: 120, after: 120 } }),

      // Data e Localidade Alinhada à Direita
      new Paragraph({
        alignment: AlignmentType.RIGHT,
        spacing: { after: 140 },
        children: [
          new TextRun({
            text: `São Paulo - SP, ${formattedDate}`,
            size: config.noteSize,
            font: config.font,
            color: '000000',
          }),
        ],
      }),

      // Título do Laudo
      new Paragraph({
        alignment: AlignmentType.LEFT,
        spacing: { after: 80 },
        children: [
          new TextRun({
            text: `LAUDO TÉCNICO OPERACIONAL DE ENGENHARIA DE TRÁFEGO Nº ${report.protocol}`,
            bold: true,
            size: config.titleSize,
            font: config.font,
            color: '000000',
          }),
        ],
      }),

      // Assunto
      new Paragraph({
        alignment: AlignmentType.LEFT,
        spacing: { after: 240 },
        children: [
          new TextRun({
            text: 'Assunto: ',
            bold: true,
            size: config.noteSize,
            font: config.font,
            color: '000000',
          }),
          new TextRun({
            text: 'Análise da Capacidade Operacional, Conformidade com as Resoluções do CONTRAN e Auditoria da Programação Semafórica Adaptativa da Malha Arterial.',
            size: config.noteSize,
            font: config.font,
            color: '3C3C3C',
          }),
        ],
      }),

      // 2. Seção 1: IDENTIFICAÇÃO E AMBIENTE OPERACIONAL
      createSectionHeading('1. IDENTIFICAÇÃO E AMBIENTE OPERACIONAL', config),
      this.createOperationalEnvironmentTable(report, config),
    ];
  }

  private static createInstitutionalHeaderTable(
    report: OfficialReportData,
    config: DocxTypographyConfig
  ): Table {
    return new Table({
      width: { size: 100, type: WidthType.PERCENTAGE },
      borders: ABNT_TABLE_BORDERS.frameless,
      rows: [
        new TableRow({
          children: [
            new TableCell({
              width: { size: 18, type: WidthType.PERCENTAGE },
              children: [
                new Paragraph({
                  alignment: AlignmentType.CENTER,
                  spacing: { before: 40, after: 40 },
                  children: [
                    new TextRun({
                      text: 'BRASÃO OFICIAL',
                      bold: true,
                      size: config.microSize,
                      font: config.font,
                      color: '505050',
                    }),
                  ],
                }),
              ],
            }),

            new TableCell({
              width: { size: 82, type: WidthType.PERCENTAGE },
              children: [
                new Paragraph({
                  alignment: AlignmentType.LEFT,
                  spacing: { after: 40 },
                  children: [
                    new TextRun({
                      text: report.cityHall.toUpperCase(),
                      bold: true,
                      size: config.bodySize,
                      font: config.font,
                      color: '000000',
                    }),
                  ],
                }),
                new Paragraph({
                  alignment: AlignmentType.LEFT,
                  spacing: { after: 20 },
                  children: [
                    new TextRun({
                      text: report.department,
                      size: config.noteSize,
                      font: config.font,
                      color: '3C3C3C',
                    }),
                  ],
                }),
                new Paragraph({
                  alignment: AlignmentType.LEFT,
                  children: [
                    new TextRun({
                      text: 'Supervisão de Engenharia de Tráfego e Controle Semafórico em Tempo Real',
                      italics: true,
                      size: config.smallSize,
                      font: config.font,
                      color: '505050',
                    }),
                  ],
                }),
              ],
            }),
          ],
        }),
      ],
    });
  }

  private static createOperationalEnvironmentTable(
    report: OfficialReportData,
    config: DocxTypographyConfig
  ): Table {
    const row = (label: string, value: string, isAlternate: boolean = false) =>
      new TableRow({
        children: [
          createCarinaTableCell(label, 40, config, {
            bold: true,
            fill: isAlternate ? 'F8FAFC' : 'FFFFFF',
          }),
          createCarinaTableCell(value, 60, config, {
            fill: isAlternate ? 'F8FAFC' : 'FFFFFF',
          }),
        ],
      });

    return new Table({
      width: { size: 100, type: WidthType.PERCENTAGE },
      borders: ABNT_TABLE_BORDERS.carinaGrid,
      rows: [
        row('Identificador do Agente / Sistema:', 'SYNAPSE Core v2.0 Enterprise', false),
        row('Cenário de Operação:', 'Sessão de Operação e Supervisão em Tempo Real (CCO)', true),
        row('Motor Analítico de Percepção:', 'SYNAPSE Adaptive Traffic Perception Engine', false),
        row('Processo Administrativo:', report.processNumber, true),
        row('Autoridade de Trânsito Responsável:', `${report.authorityName} (${report.authorityRole})`, false),
        row('Identificação Funcional / Portaria:', report.registrationNumber, true),
        row('Corredor Viário Fiscalizado:', report.location.corridorName, false),
        row('Data e Horário da Auditoria:', new Date(report.timestamp).toLocaleString('pt-BR'), true),
      ],
    });
  }
}
