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
// File: ui/src_ui/types/report.ts
// Author: Gabriel Moraes
// Date: 2026-09-01

/**
 * Domain types and contracts for Official Municipal Traffic Reports & Technical Audits.
 * Compliant with Municipal Traffic Regulations, CTB Art. 24, CONTRAN Manual Vol. V, and Administrative Due Process.
 */

export interface TrafficSensorItem {
  id: string;
  junction: string;
  equipmentType: string;
  measuredSpeed: string;
  measuredFlow: string;
  saturationDegree: string;
  occupancyRate: string;
  inmetroReport: string;
  operationalStatus: string;
}

export interface TrafficSafetyInterventionItem {
  id: string;
  timeRecorded: string;
  junction: string;
  equipmentId: string;
  irregularityDetected: string;
  trafficSafetyRisk: string;
  contranStandardViolated: string;
  correctiveGuardrail: string;
  finalState: 'INTERVENÇÃO HOMOLOGADA' | 'PARÂMETRO RETIFICADO' | 'OPERANDO EM SEGURANÇA';
}

export interface TrafficNetworkMacroSummary {
  corridorsMonitored: number;
  controlledIntersections: number;
  totalSensorsCount: number;
  networkLengthKm: number;
  networkMeanSpeed: string;
  networkMeanSaturation: string;
  totalHourlyFlow: string;
  networkLevelOfService: string; // LOS A, B, C, D, E, F (HCM)
}

export interface TrafficAttributionItem {
  parameterName: string;
  junctionLocation: string;
  detectorId: string;
  causalWeightPercent: number;
  gradientDirection: string;
  trafficImpactAnalysis: string;
}

export interface LegalFramingItem {
  article: string;
  desc: string;
}

export interface PeritialQuesitoItem {
  number: number;
  question: string;
  answer: 'SIM' | 'NÃO' | 'PARCIALMENTE';
  technicalJustification: string;
}

export interface ReportLocationData {
  corridorName: string;
  jurisdiction: string;
  centralNodes: string;
  geographicBounds: string;
  nominalNetworkCapacity: string;
  baselineSignalPlan: string;
}

export interface OfficialReportData {
  protocol: string;
  processNumber: string;
  registrationNumber: string;
  authorityName: string;
  authorityRole: string;
  cityHall: string;
  department: string;
  system: string;
  timestamp: string;
  location: ReportLocationData;
  networkSummary: TrafficNetworkMacroSummary;
  auditObjective: string;
  observedTrafficDiagnosis: string;
  adaptiveActionExecuted: string;
  sensors: TrafficSensorItem[];
  safetyInterventions: TrafficSafetyInterventionItem[];
  attributions: TrafficAttributionItem[];
  counterfactualAnalysis: string;
  quesitos: PeritialQuesitoItem[];
  legalFraming: LegalFramingItem[];
  references: string[];
  operationalSupervision: string;
  digitalCertification: string;
}

export interface ReportTypographyOptions {
  fontFamily: 'Arial' | 'Times New Roman';
  fontSize: number; // in pt: 10, 11, 12, 13, 14
  lineSpacing: 1.0 | 1.15 | 1.5;
  alignment: 'justify' | 'left';
}

export const DEFAULT_REPORT_TYPOGRAPHY: ReportTypographyOptions = {
  fontFamily: 'Arial',
  fontSize: 12,
  lineSpacing: 1.5,
  alignment: 'justify',
};

export interface IReportFormatter {
  format(report: OfficialReportData): string;
}

export interface IReportExportService {
  copyToClipboard(text: string): Promise<boolean>;
  downloadMarkdown(filename: string, content: string): void;
  exportToDocx(
    report: OfficialReportData,
    filename: string,
    options?: ReportTypographyOptions
  ): Promise<boolean>;
  exportToPdf(elementId: string, filename: string): Promise<boolean>;
  print(): void;
}

export interface IReportBuilder {
  build(result?: any, sources?: any[]): OfficialReportData;
}

