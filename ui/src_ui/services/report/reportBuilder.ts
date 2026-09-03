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
// File: ui/src_ui/services/report/reportBuilder.ts
// Author: Gabriel Moraes
// Date: 2026-09-01

import { OfficialReportData, IReportBuilder } from '../../types/report';
import { XaiResultItem } from '../../types/xai';
import { DataSourceItem } from '../../types/sensors';
import { useMunicipalSettingsStore } from '../../stores/useMunicipalSettingsStore';
import { getMockBackendReportPayload } from './trafficAuditMockBackend';

const getMunicipalConfig = () => {
  try {
    if (typeof useMunicipalSettingsStore?.getState === 'function') {
      return useMunicipalSettingsStore.getState();
    }
  } catch {}
  return {
    cityHall: 'PREFEITURA DO MUNICÍPIO DE SÃO PAULO',
    department: 'SECRETARIA MUNICIPAL DE MOBILIDADE URBANA E TRÂNSITO (SMT)',
    authorityName: 'Gabriel Moraes',
    authorityRole: 'Autoridade Municipal de Trânsito / Secretário de Mobilidade',
    registrationNumber: 'Matrícula Funcional nº 84.102-3 • Portaria de Nomeação SMT nº 142/2025',
    processPrefix: 'PA-SMT-2026/',
    logoDataUrl: null,
  };
};

/**
 * Single Responsibility: Builds an authentic Municipal Traffic Operations & Technical Audit Report
 * by consuming the Backend DTO and injecting municipal identity parameters.
 */
export class OfficialReportBuilder implements IReportBuilder {
  public build(result?: XaiResultItem | null, sources?: DataSourceItem[]): OfficialReportData {
    const timestampStr = result?.timestamp ? `2026-09-01T${result.timestamp}` : new Date().toISOString();
    const randomSeq = Math.floor(1000 + Math.random() * 9000);
    const municipal = getMunicipalConfig();
    const backendData = getMockBackendReportPayload();

    const protocolCode = `RELATORIO-TRAFEGO-2026-${randomSeq}`;
    const processNumber = `${municipal.processPrefix}0${randomSeq}`;

    return {
      protocol: protocolCode,
      processNumber: processNumber,
      registrationNumber: municipal.registrationNumber,
      authorityName: municipal.authorityName,
      authorityRole: municipal.authorityRole,
      cityHall: municipal.cityHall,
      department: municipal.department,
      system: backendData.systemVersion,
      timestamp: timestampStr,
      location: backendData.location,
      networkSummary: backendData.networkSummary,
      auditObjective: backendData.auditObjective,
      observedTrafficDiagnosis: backendData.observedTrafficDiagnosis,
      adaptiveActionExecuted: backendData.adaptiveActionExecuted,
      sensors: backendData.sensors,
      safetyInterventions: backendData.safetyInterventions,
      attributions: backendData.attributions,
      counterfactualAnalysis: backendData.counterfactualAnalysis,
      quesitos: backendData.quesitos,
      legalFraming: backendData.legalFraming,
      references: backendData.references,
      operationalSupervision: backendData.operationalSupervision,
      digitalCertification: backendData.digitalCertification,
    };
  }
}

export const defaultReportBuilder = new OfficialReportBuilder();
