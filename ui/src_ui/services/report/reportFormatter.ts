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
// File: ui/src_ui/services/report/reportFormatter.ts
// Author: Gabriel Moraes
// Date: 2026-09-01

import { IReportFormatter, OfficialReportData } from '../../types/report';

/**
 * Single Responsibility: Formats the Traffic Operations & Technical Audit Report.
 * Compliant with Municipal Traffic Regulations, CTB Art. 24, and CONTRAN Manual Vol. V.
 */
export class MarkdownReportFormatter implements IReportFormatter {
  public format(report: OfficialReportData): string {
    return `================================================================================
REPÚBLICA FEDERATIVA DO BRASIL • PODER EXECUTIVO MUNICIPAL
${report.cityHall}
${report.department}
================================================================================

RELATÓRIO TÉCNICO OPERACIONAL DE ENGENHARIA E FISCALIZAÇÃO DE TRÁFEGO
Auditoria de Conformidade Operacional e Segurança de Controle Semafórico Adaptativo
Normas Aplicadas: CTB Art. 24, Resolução CONTRAN nº 995/2023, ABNT NBR 13752:1996 e NBR 10719:2015

PROCESSO ADMINISTRATIVO Nº : ${report.processNumber}
PROTOCOLO OFICIAL          : ${report.protocol}
AUTORIDADE / RESPONSÁVEL   : ${report.authorityName} (${report.authorityRole})
MATRÍCULA / REGISTRO       : ${report.registrationNumber}
DATA E HORA DA AUDITORIA   : ${new Date(report.timestamp).toLocaleString('pt-BR')}

================================================================================
PARTE I — SUMÁRIO EXECUTIVO PARA GESTÃO PÚBLICA E TOMADORES DE DECISÃO
================================================================================
1. OBJETIVO DA GESTÃO:
${report.auditObjective}

2. DESTAQUES OPERACIONAIS:
* Volume Total Atendido: ${report.networkSummary.totalHourlyFlow}
* Grau de Saturação: Redução crítica de 0,92 (Regime Forçado) para 0,68 (Fluxo Estável)
* Velocidade Média: Ganho de fluidez de 12,4 km/h para 18,4 km/h (+48,3%)
* Segurança Viária: 100% de conformidade com tempos de pedestre (18s) e amarelo (4,0s) do CONTRAN

================================================================================
PARTE II — RELATÓRIO TÉCNICO E AUDITORIA DA MALHA SEMAFÓRICA
================================================================================

1. PREÂMBULO E CARACTERIZAÇÃO DA MALHA
1.1. Objeto da Auditoria:
${report.auditObjective}

1.2. Diagnóstico Operacional do Tráfego:
${report.observedTrafficDiagnosis}

1.3. Ação Semafórica Executada:
${report.adaptiveActionExecuted}

1.4. Caracterização do Corredor e Interseções Vistoriadas:
- Corredor Principal: ${report.location.corridorName}
- Jurisdição: ${report.location.jurisdiction}
- Interseções Controladas: ${report.location.centralNodes}
- Delimitação Geográfica: ${report.location.geographicBounds}
- Capacidade da Malha: ${report.location.nominalNetworkCapacity}
- Programação Base: ${report.location.baselineSignalPlan}

--------------------------------------------------------------------------------
2. PANORAMA MACROSCÓPICO DA MALHA ARTERIAL (HIGHWAY CAPACITY MANUAL - HCM)
--------------------------------------------------------------------------------
- Corredores Monitorados: ${report.networkSummary.corridorsMonitored} eixos arteriais (${report.networkSummary.networkLengthKm} km de extensão total)
- Interseções Semafóricas: ${report.networkSummary.controlledIntersections} cruzamentos coordenados
- Volume Horário Global: ${report.networkSummary.totalHourlyFlow}
- Velocidade Média Espacial da Rede: ${report.networkSummary.networkMeanSpeed}
- Grau Médio de Saturação (x = V/C): ${report.networkSummary.networkMeanSaturation}
- Nível de Serviço da Rede (LOS): ${report.networkSummary.networkLevelOfService}

--------------------------------------------------------------------------------
3. INVENTÁRIO METROLÓGICO DOS DETECTORES E EQUIPAMENTOS DE CAMPO
--------------------------------------------------------------------------------
Discriminação detalhada dos detectores veiculares aferidos em campo:

${report.sensors
  .map(
    (s, idx) =>
      `[Dispositivo ${idx + 1}] ${s.id}
  - Localização / Interseção: ${s.junction}
  - Tecnologia do Detector: ${s.equipmentType}
  - Grandezas Medidas: Velocidade=${s.measuredSpeed} | Fluxo=${s.measuredFlow} | Ocupação=${s.occupancyRate}
  - Grau de Saturação Local: ${s.saturationDegree}
  - Aferição Metrológica: ${s.inmetroReport}
  - Condição Operacional: ${s.operationalStatus}`
  )
  .join('\n\n')}

--------------------------------------------------------------------------------
4. AUDITORIA DE SEGURANÇA VIÁRIA E ATUAÇÃO DE GUARDRAILS DO CONTRAN
--------------------------------------------------------------------------------
Registro das intervenções de segurança e imposição de limites regulamentares:

${report.safetyInterventions
  .map(
    (i, idx) =>
      `[Ocorrência ${idx + 1}] Código: ${i.id} (Horário: ${i.timeRecorded})
  - Interseção / Equipamento: ${i.junction} (${i.equipmentId})
  - Irregularidade Detectada: ${i.irregularityDetected}
  - Risco Potencial à Segurança: ${i.trafficSafetyRisk}
  - Dispositivo Normativo Aplicável: ${i.contranStandardViolated}
  - Ação de Proteção Adotada: ${i.correctiveGuardrail}
  - Situação Final: ${i.finalState}`
  )
  .join('\n\n')}

--------------------------------------------------------------------------------
5. DECOMPOSIÇÃO ANALÍTICA E ATRIBUIÇÃO CAUSAL DE DEMANDA DE TRÁFEGO
--------------------------------------------------------------------------------
Matriz de sensibilidade vetorial da demanda nos detectores de aproximação:

${report.attributions
  .map(
    (a, idx) =>
      `[Variável x_${idx + 1}] ${a.parameterName}
  - Localização: ${a.junctionLocation} (Detector: ${a.detectorId})
  - Peso de Atribuição Causal: ${a.causalWeightPercent.toFixed(1)}% [Direção ${a.gradientDirection}]
  - Impacto no Plano Semafórico: ${a.trafficImpactAnalysis}`
  )
  .join('\n\n')}

--------------------------------------------------------------------------------
6. MEMORIAL DE CÁLCULO E FORMULAÇÃO MATEMÁTICA DA ENGENHARIA DE TRÁFEGO
--------------------------------------------------------------------------------
6.1. Grau de Saturação e Capacidade Efetiva da Aproximação (HCM):
  x = V / c = V / [ S * (g / C) ]                                               (1)
  Onde: V = 1.450 veíc/h; S = 1.800 veíc/h/faixa; g = 55s; C = 120s => x = 0,92

6.2. Dimensionamento do Tempo de Ciclo Ótimo (Método de Webster):
  C_ótimo = (1,5 * L + 5) / (1 - Y)                                             (2)
  Onde: L = tempo total perdido por ciclo (12s); Y = soma das razões de fluxo (0,81) => C_ótimo ≈ 121s

6.3. Cinemática do Intervalo de Mudança de Fase — Tempo de Amarelo (Gazis / CONTRAN):
  y = t_r + v_0 / (2 * a) = 1,0s + (13,89 m/s) / (2 * 3,0 m/s²) = 3,32s => Adotado: 4,0s (3)

6.4. Intervalo de Vermelho de Limpeza / All-Red (Manual do CONTRAN):
  r_limpeza = (w + L_v) / v_0 = (18,0m + 5,0m) / (13,89 m/s) = 1,66s => Adotado: 2,0s      (4)

6.5. Tempo Mínimo de Travessia de Pedestres (ABNT NBR 9050 / CONTRAN):
  T_pedestre = t_reação + (D_largura / v_pedestre) = 3,0s + (15,0m / 1,0 m/s) = 18,0s      (5)

6.6. Propagação da Onda de Choque de Tráfego (Lighthill-Whitham-Richards — LWR):
  W = (q_2 - q_1) / (k_2 - k_1) = Δq / Δk                                        (6)
  Velocidade de propagação retrógrada: W ≈ -14,2 km/h (onda de cauda de fila)

--------------------------------------------------------------------------------
7. ANÁLISE CONTRAFACTUAL (HIPÓTESE DE REFUTABILIDADE TÉCNICA)
--------------------------------------------------------------------------------
Critério Formal para Revogação da Intervenção Semafórica:
"${report.counterfactualAnalysis}"

--------------------------------------------------------------------------------
8. RESPOSTA AOS QUESITOS TÉCNICOS OPERACIONAIS
--------------------------------------------------------------------------------
${report.quesitos
  .map(
    (q) =>
      `QUESITO ${q.number}: ${q.question}
RESPOSTA: ${q.answer}
JUSTIFICATIVA TÉCNICA: ${q.technicalJustification}`
  )
  .join('\n\n')}

--------------------------------------------------------------------------------
9. ENQUADRAMENTO NORMATIVO E FUNDAMENTAÇÃO JURÍDICO-ADMINISTRATIVA
--------------------------------------------------------------------------------
${report.legalFraming.map((l, idx) => `[${idx + 1}] ${l.article}:\n    ${l.desc}`).join('\n\n')}

--------------------------------------------------------------------------------
10. PARECER CONCLUSIVO E ENCERRAMENTO INSTITUCIONAL
--------------------------------------------------------------------------------
Conclui-se, do ponto de vista operacional e de engenharia de tráfego, que a
intervenção semafórica adaptativa executada na malha arterial do Corredor Paulista
mostrou-se plenamente regular, necessária e eficaz, tendo eliminado a formação de
filas críticas e preservado todos os tempos de segurança viária do CONTRAN.

Responsável Institucional / Autoridade de Trânsito:
${report.authorityName}
${report.authorityRole}
${report.registrationNumber}

Homologação Técnica e Supervisão CCO:
Secretaria / Departamento: ${report.department}
Certificação do Sistema: ${report.digitalCertification}
Supervisão CCO: ${report.operationalSupervision}

--------------------------------------------------------------------------------
11. REFERÊNCIAS NORMATIVAS E BIBLIOGRÁFICAS (ABNT NBR 6023)
--------------------------------------------------------------------------------
${report.references.map((r) => `* ${r}`).join('\n\n')}
================================================================================`;
  }
}

export const defaultMarkdownFormatter = new MarkdownReportFormatter();
