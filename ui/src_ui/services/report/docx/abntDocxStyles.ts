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
// File: ui/src_ui/services/report/docx/abntDocxStyles.ts
// Author: Gabriel Moraes
// Date: 2026-09-02

import {
  Paragraph,
  TextRun,
  TableCell,
  WidthType,
  AlignmentType,
  BorderStyle,
} from 'docx';
import { ReportTypographyOptions, DEFAULT_REPORT_TYPOGRAPHY } from '../../../types/report';

export type DocxTypographyConfig = ReturnType<typeof getDocxTypographyConfig>;

/**
 * Computes dynamic typography rules (Font Family, Font Size, Line Spacing, Alignment)
 * respecting user preferences and ABNT/Carina conventions.
 */
export function getDocxTypographyConfig(options?: ReportTypographyOptions) {
  const opts = options || DEFAULT_REPORT_TYPOGRAPHY;
  const baseSizeHalfPoints = opts.fontSize * 2; // e.g. 12pt -> 24 half-points
  const lineSpacingTwips = Math.round(opts.lineSpacing * 240); // 1.0 -> 240, 1.15 -> 276, 1.5 -> 360
  const alignmentType = opts.alignment === 'left' ? AlignmentType.LEFT : AlignmentType.JUSTIFIED;

  return {
    font: opts.fontFamily,
    bodySize: baseSizeHalfPoints,
    titleSize: baseSizeHalfPoints + 1,
    subheadingSize: Math.max(18, baseSizeHalfPoints - 1),
    nameSize: Math.max(18, baseSizeHalfPoints - 2),
    noteSize: Math.max(16, baseSizeHalfPoints - 4),
    smallSize: Math.max(14, baseSizeHalfPoints - 6),
    microSize: Math.max(12, baseSizeHalfPoints - 8),
    lineSpacing: lineSpacingTwips,
    singleLineSpacing: 240,
    alignment: alignmentType,
    paragraphIndent: opts.alignment === 'left' ? 0 : 708, // 1.25 cm
    margins: {
      top: 1701, // 30 mm
      left: 1701, // 30 mm
      bottom: 1134, // 20 mm
      right: 1134, // 20 mm
    },
  };
}

export const ABNT_TABLE_BORDERS = {
  carinaGrid: {
    top: { style: BorderStyle.SINGLE, size: 4, color: 'B0BEC5' },
    bottom: { style: BorderStyle.SINGLE, size: 4, color: 'B0BEC5' },
    left: { style: BorderStyle.SINGLE, size: 4, color: 'B0BEC5' },
    right: { style: BorderStyle.SINGLE, size: 4, color: 'B0BEC5' },
    insideHorizontal: { style: BorderStyle.SINGLE, size: 4, color: 'E0E0E0' },
    insideVertical: { style: BorderStyle.SINGLE, size: 4, color: 'E0E0E0' },
  },
  openIbge: {
    top: { style: BorderStyle.SINGLE, size: 6, color: '000000' },
    bottom: { style: BorderStyle.SINGLE, size: 6, color: '000000' },
    left: { style: BorderStyle.NONE, size: 0, color: 'auto' },
    right: { style: BorderStyle.NONE, size: 0, color: 'auto' },
    insideHorizontal: { style: BorderStyle.SINGLE, size: 4, color: 'E0E0E0' },
    insideVertical: { style: BorderStyle.NONE, size: 0, color: 'auto' },
  },
  frameless: {
    top: { style: BorderStyle.NONE, size: 0, color: 'auto' },
    bottom: { style: BorderStyle.NONE, size: 0, color: 'auto' },
    left: { style: BorderStyle.NONE, size: 0, color: 'auto' },
    right: { style: BorderStyle.NONE, size: 0, color: 'auto' },
    insideHorizontal: { style: BorderStyle.NONE, size: 0, color: 'auto' },
    insideVertical: { style: BorderStyle.NONE, size: 0, color: 'auto' },
  },
};

export function createSectionHeading(text: string, config: DocxTypographyConfig): Paragraph {
  return new Paragraph({
    alignment: AlignmentType.LEFT,
    spacing: { before: 240, after: 120 },
    children: [
      new TextRun({
        text: text.toUpperCase(),
        bold: true,
        size: config.titleSize,
        font: config.font,
        color: '000000',
      }),
    ],
  });
}

export function createSubSectionHeading(text: string, config: DocxTypographyConfig): Paragraph {
  return new Paragraph({
    alignment: AlignmentType.LEFT,
    spacing: { before: 180, after: 80 },
    children: [
      new TextRun({
        text: text,
        bold: true,
        size: config.subheadingSize,
        font: config.font,
        color: '000000',
      }),
    ],
  });
}

export function createParagraph(text: string, config: DocxTypographyConfig, bold: boolean = false): Paragraph {
  return new Paragraph({
    alignment: config.alignment,
    spacing: { line: config.lineSpacing, before: 80, after: 120 },
    indent: { firstLine: config.paragraphIndent },
    children: [
      new TextRun({
        text: text,
        bold: bold,
        size: config.bodySize,
        font: config.font,
        color: '000000',
      }),
    ],
  });
}

export function createParagraphWithBoldLead(
  lead: string,
  text: string,
  config: DocxTypographyConfig
): Paragraph {
  return new Paragraph({
    alignment: config.alignment,
    spacing: { line: config.lineSpacing, before: 80, after: 120 },
    indent: { firstLine: config.paragraphIndent },
    children: [
      new TextRun({
        text: `${lead} `,
        bold: true,
        size: config.bodySize,
        font: config.font,
        color: '000000',
      }),
      new TextRun({
        text: text,
        size: config.bodySize,
        font: config.font,
        color: '000000',
      }),
    ],
  });
}

export function createBulletPoint(text: string, config: DocxTypographyConfig): Paragraph {
  return new Paragraph({
    alignment: config.alignment,
    spacing: { line: config.lineSpacing, before: 40, after: 40 },
    indent: { left: config.paragraphIndent || 360 },
    children: [
      new TextRun({
        text: `• ${text}`,
        size: config.bodySize,
        font: config.font,
        color: '000000',
      }),
    ],
  });
}

export function createTableCaption(
  title: string,
  config: DocxTypographyConfig,
  source?: string
): Paragraph[] {
  const paras = [
    new Paragraph({
      alignment: AlignmentType.LEFT,
      spacing: { before: 120, after: 60 },
      children: [
        new TextRun({
          text: title,
          bold: true,
          size: config.noteSize,
          font: config.font,
          color: '000000',
        }),
      ],
    }),
  ];

  if (source) {
    paras.push(
      new Paragraph({
        alignment: AlignmentType.LEFT,
        spacing: { after: 100 },
        children: [
          new TextRun({
            text: source,
            italics: true,
            size: config.smallSize,
            font: config.font,
            color: '505050',
          }),
        ],
      })
    );
  }

  return paras;
}

export function createCarinaTableCell(
  text: string,
  widthPercent: number,
  config: DocxTypographyConfig,
  options?: {
    bold?: boolean;
    alignment?: (typeof AlignmentType)[keyof typeof AlignmentType];
    fill?: string;
    bottomDarkBorder?: boolean;
  }
): TableCell {
  const {
    bold = false,
    alignment = AlignmentType.LEFT,
    fill = undefined,
    bottomDarkBorder = false,
  } = options || {};

  const borders = bottomDarkBorder
    ? {
        bottom: { style: BorderStyle.SINGLE, size: 8, color: '222222' },
      }
    : undefined;

  return new TableCell({
    width: { size: widthPercent, type: WidthType.PERCENTAGE },
    shading: fill ? { fill } : undefined,
    borders: borders,
    children: [
      new Paragraph({
        alignment: alignment,
        spacing: { before: 60, after: 60, line: config.singleLineSpacing },
        children: [
          new TextRun({
            text: text,
            bold: bold,
            size: config.noteSize,
            font: config.font,
            color: '000000',
          }),
        ],
      }),
    ],
  });
}
