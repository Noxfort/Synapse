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
// File: ui/src_ui/services/report/reportExportService.ts
// Author: Gabriel Moraes
// Date: 2026-09-02

import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import { IReportExportService, OfficialReportData, ReportTypographyOptions } from '../../types/report';
import { DocxReportBuilder } from './docxReportBuilder';

/**
 * Single Responsibility: Encapsulates desktop/browser I/O operations (DOCX, PDF, Print, Markdown).
 */
export class BrowserReportExportService implements IReportExportService {
  public async copyToClipboard(text: string): Promise<boolean> {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      return false;
    }
  }

  public print(): void {
    window.print();
  }

  public downloadMarkdown(filename: string, content: string): void {
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  /**
   * Generates a 100% compliant Microsoft Word (.docx) document and opens native OS "Save As" file picker.
   */
  public async exportToDocx(
    report: OfficialReportData,
    filename: string,
    options?: ReportTypographyOptions
  ): Promise<boolean> {
    try {
      const docxBlob = await DocxReportBuilder.generateBlob(report, options);
      const cleanFilename = filename.endsWith('.docx') ? filename : `${filename}.docx`;

      // Convert blob to base64 Data URI for Tauri bridge
      const base64DataUri = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
          if (typeof reader.result === 'string') {
            resolve(reader.result);
          } else {
            reject(new Error('Failed to convert docx blob to base64'));
          }
        };
        reader.onerror = reject;
        reader.readAsDataURL(docxBlob);
      });

      // 1. Check Tauri Desktop Native Dialog (Linux/Desktop Native Zenity/GTK File Chooser)
      try {
        const { invoke } = await import('@tauri-apps/api/core');
        const chosenPath = await invoke<string | null>('save_file_dialog', {
          defaultFilename: cleanFilename,
          title: 'Salvar Laudo Técnico Oficial (.docx)',
          filterName: 'Documento do Microsoft Word (*.docx)',
          filterExtensions: ['docx'],
        });

        if (!chosenPath) {
          // User cancelled file dialog
          return false;
        }

        await invoke('write_file_bytes', {
          filePath: chosenPath,
          base64Content: base64DataUri,
        });

        return true;
      } catch (tauriErr) {
        // Not in Tauri or Tauri command failed, proceed to Web fallback
      }

      // 2. Web fallback: File System Access API
      if ('showSaveFilePicker' in window) {
        try {
          const pickerOptions = {
            suggestedName: cleanFilename,
            types: [
              {
                description: 'Documento do Microsoft Word (*.docx)',
                accept: { 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'] },
              },
            ],
          };

          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const fileHandle = await (window as any).showSaveFilePicker(pickerOptions);
          const writable = await fileHandle.createWritable();
          await writable.write(docxBlob);
          await writable.close();
          return true;
        } catch (pickerErr: unknown) {
          if (pickerErr instanceof Error && pickerErr.name === 'AbortError') {
            return false;
          }
        }
      }

      // 3. Fallback: Browser download trigger
      const url = URL.createObjectURL(docxBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = cleanFilename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      return true;
    } catch (error) {
      console.error('Failed to export DOCX:', error);
      return false;
    }
  }

  /**
   * Generates a 100% discrete multi-page A4 PDF conforming to ABNT NBR 10719/14724.
   */
  public async exportToPdf(elementId: string, filename: string): Promise<boolean> {
    try {
      const container = document.getElementById(elementId);
      if (!container) {
        window.print();
        return true;
      }

      const pageElements = Array.from(container.querySelectorAll<HTMLElement>('.abnt-a4-page'));

      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4',
        compress: true,
      });

      if (pageElements.length > 0) {
        for (let i = 0; i < pageElements.length; i++) {
          const pageEl = pageElements[i];
          if (i > 0) {
            pdf.addPage();
          }

          const canvas = await html2canvas(pageEl, {
            scale: 2.5,
            useCORS: true,
            logging: false,
            backgroundColor: '#ffffff',
          });

          const imgData = canvas.toDataURL('image/jpeg', 0.95);
          pdf.addImage(imgData, 'JPEG', 0, 0, 210, 297, undefined, 'FAST');
        }
      } else {
        const canvas = await html2canvas(container, {
          scale: 2,
          useCORS: true,
          logging: false,
          backgroundColor: '#ffffff',
        });

        const imgData = canvas.toDataURL('image/png');
        const imgWidth = 210;
        const pageHeight = 297;
        const imgHeight = (canvas.height * imgWidth) / canvas.width;
        let heightLeft = imgHeight;
        let position = 0;

        pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight, undefined, 'FAST');
        heightLeft -= pageHeight;

        while (heightLeft > 0) {
          position = heightLeft - imgHeight;
          pdf.addPage();
          pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight, undefined, 'FAST');
          heightLeft -= pageHeight;
        }
      }

      const cleanFilename = filename.endsWith('.pdf') ? filename : `${filename}.pdf`;

      // 1. Check Tauri Desktop Native Dialog
      try {
        const { invoke } = await import('@tauri-apps/api/core');
        const chosenPath = await invoke<string | null>('save_file_dialog', {
          defaultFilename: cleanFilename,
          title: 'Salvar Laudo Técnico Operacional (PDF)',
          filterName: 'Documento PDF (*.pdf)',
          filterExtensions: ['pdf'],
        });

        if (!chosenPath) {
          return false;
        }

        const base64DataUri = pdf.output('datauristring');
        await invoke('write_file_bytes', {
          filePath: chosenPath,
          base64Content: base64DataUri,
        });

        return true;
      } catch (tauriErr) {
        // Not in Tauri
      }

      // 2. Web fallback
      if ('showSaveFilePicker' in window) {
        try {
          const pickerOptions = {
            suggestedName: cleanFilename,
            types: [
              {
                description: 'Documento PDF (*.pdf)',
                accept: { 'application/pdf': ['.pdf'] },
              },
            ],
          };

          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const fileHandle = await (window as any).showSaveFilePicker(pickerOptions);
          const writable = await fileHandle.createWritable();
          const pdfBlob = pdf.output('blob');
          await writable.write(pdfBlob);
          await writable.close();
          return true;
        } catch (pickerErr: unknown) {
          if (pickerErr instanceof Error && pickerErr.name === 'AbortError') {
            return false;
          }
        }
      }

      // 3. Fallback: Browser download
      pdf.save(cleanFilename);
      return true;
    } catch (error) {
      console.error('Failed to export PDF:', error);
      return false;
    }
  }
}

export const defaultReportExportService = new BrowserReportExportService();
