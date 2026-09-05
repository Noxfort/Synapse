# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# File: src/formatters/abnt_markdown_formatter.py
# Author: Gabriel Moraes
# Date: 2026-09-04

"""
ABNT NBR 10719 & NBR 14724 Standardized Markdown Report Formatter.

SOLID Compliance:
- [SRP] Single Responsibility: Exclusively converts OfficialReportData into ABNT-compliant Markdown.
- [OCP] Open for extension via IReportFormatter (new formats do not require changes here).
- [LSP] Full compliance with IReportFormatter protocol.
"""

from datetime import datetime
from typing import Dict, Any

from src.interfaces.reports import IReportFormatter


class AbntMarkdownReportFormatter(IReportFormatter):
    """
    Renders official traffic engineering reports in strict compliance with ABNT NBR 10719:2015.
    """

    def format(self, report_data: Dict[str, Any]) -> str:
        """Renders complete 6-part ABNT NBR 10719 text representation."""
        r = report_data
        timestamp_raw = r.get("timestamp", datetime.now().isoformat())
        try:
            dt_str = datetime.fromisoformat(timestamp_raw).strftime("%d/%m/%Y às %H:%M:%S")
        except Exception:
            dt_str = str(timestamp_raw)

        sensors = r.get("sensors", [])
        sensors_md = "\n\n".join(
            f"[Dispositivo {i+1}] {s.get('id', '')}\n"
            f"  - Localização / Interseção: {s.get('junction', '')}\n"
            f"  - Tecnologia do Detector: {s.get('equipmentType', '')}\n"
            f"  - Grandezas Medidas: Velocidade={s.get('measuredSpeed', '')} | Fluxo={s.get('measuredFlow', '')} | Ocupação={s.get('occupancyRate', '')}\n"
            f"  - Grau de Saturação: {s.get('saturationDegree', '')}\n"
            f"  - Metrologia Legal: {s.get('inmetroReport', '')}\n"
            f"  - Status Operacional: {s.get('operationalStatus', '')}"
            for i, s in enumerate(sensors)
        )

        interventions = r.get("safetyInterventions", [])
        safety_lines = []
        for it in interventions:
            if isinstance(it, dict):
                safety_lines.append(
                    f"[{it.get('id', '')}] Registro às {it.get('timeRecorded', '')} — {it.get('junction', '')}\n"
                    f"  - Dispositivo de Referência: {it.get('equipmentId', '')}\n"
                    f"  - Irregularidade Detectada: {it.get('irregularityDetected', '')}\n"
                    f"  - Risco à Segurança Viária: {it.get('trafficSafetyRisk', '')}\n"
                    f"  - Padrão CONTRAN: {it.get('contranStandardViolated', '')}\n"
                    f"  - Trava Regulamentar: {it.get('correctiveGuardrail', '')}\n"
                    f"  - Estado de Homologação: {it.get('finalState', '')}"
                )
            else:
                safety_lines.append(f"- {it}")
        safety_md = "\n\n".join(safety_lines)

        attributions = r.get("attributions", [])
        attrs_md = "\n\n".join(
            f"{i+1}. {a.get('parameterName', '')} ({a.get('detectorId', '')})\n"
            f"   - Localização: {a.get('junctionLocation', '')}\n"
            f"   - Peso Causal (Gradiente Integrado): {a.get('causalWeightPercent', 0)}%\n"
            f"   - Direção do Gradiente: {a.get('gradientDirection', '')}\n"
            f"   - Diagnóstico de Impacto: {a.get('trafficImpactAnalysis', '')}"
            for i, a in enumerate(attributions)
        )

        quesitos = r.get("quesitos", [])
        quesitos_md = "\n\n".join(
            f"QUESITO Nº {q.get('number', i+1)}:\n"
            f"{q.get('question', '')}\n"
            f"RESPOSTA DO AUDITOR PERITO: [{q.get('answer', '')}]\n"
            f"FUNDAMENTAÇÃO TÉCNICO-PERICIAL:\n"
            f"{q.get('technicalJustification', '')}"
            for i, q in enumerate(quesitos)
        )

        legal = r.get("legalFraming", [])
        legal_md = "\n\n".join(
            f"* {lf.get('article', '')}:\n  {lf.get('desc', '')}"
            for lf in legal
        )

        refs = r.get("references", [])
        refs_md = "\n".join(f"* {ref}" for ref in refs)

        location = r.get("location", {})
        net = r.get("networkSummary", {})

        return f"""================================================================================
REPÚBLICA FEDERATIVA DO BRASIL • PODER EXECUTIVO MUNICIPAL
{r.get('cityHall', '')}
{r.get('department', '')}
================================================================================

RELATÓRIO TÉCNICO OPERACIONAL DE ENGENHARIA E FISCALIZAÇÃO DE TRÁFEGO
Auditoria de Conformidade Operacional e Segurança de Controle Semafórico Adaptativo
Normas Aplicadas: CTB Art. 24, Resolução CONTRAN nº 995/2023, ABNT NBR 13752:1996 e NBR 10719:2015

PROCESSO ADMINISTRATIVO Nº : {r.get('processNumber', '')}
PROTOCOLO OFICIAL          : {r.get('protocol', '')}
AUTORIDADE / RESPONSÁVEL   : {r.get('authorityName', '')} ({r.get('authorityRole', '')})
MATRÍCULA / REGISTRO       : {r.get('registrationNumber', '')}
DATA E HORA DA AUDITORIA   : {dt_str}

================================================================================
PARTE I — SUMÁRIO EXECUTIVO PARA GESTÃO PÚBLICA E TOMADORES DE DECISÃO
================================================================================
1. OBJETIVO DA GESTÃO:
{r.get('auditObjective', '')}

2. DESTAQUES OPERACIONAIS:
* Volume Total Atendido: {net.get('totalHourlyFlow', '')}
* Grau de Saturação: {net.get('networkMeanSaturation', '')}
* Velocidade Média: {net.get('networkMeanSpeed', '')}
* Nível de Serviço da Rede: {net.get('networkLevelOfService', '')}

================================================================================
PARTE II — RELATÓRIO TÉCNICO E AUDITORIA DA MALHA SEMAFÓRICA
================================================================================

1. PREÂMBULO E CARACTERIZAÇÃO DA MALHA
1.1. Objeto da Auditoria:
{r.get('auditObjective', '')}

1.2. Diagnóstico Operacional do Tráfego:
{r.get('observedTrafficDiagnosis', '')}

1.3. Ação Semafórica Executada:
{r.get('adaptiveActionExecuted', '')}

1.4. Caracterização do Corredor e Interseções Vistoriadas:
- Corredor Principal: {location.get('corridorName', '')}
- Jurisdição: {location.get('jurisdiction', '')}
- Interseções Controladas: {location.get('centralNodes', '')}
- Delimitação Geográfica: {location.get('geographicBounds', '')}
- Capacidade da Malha: {location.get('nominalNetworkCapacity', '')}
- Programação Base: {location.get('baselineSignalPlan', '')}

--------------------------------------------------------------------------------
2. PANORAMA MACROSCÓPICO DA MALHA ARTERIAL (HIGHWAY CAPACITY MANUAL - HCM)
--------------------------------------------------------------------------------
- Corredores Monitorados: {net.get('corridorsMonitored', '')} eixos arteriais ({net.get('networkLengthKm', '')} km de extensão total)
- Interseções Semafóricas: {net.get('controlledIntersections', '')} cruzamentos coordenados
- Volume Horário Global: {net.get('totalHourlyFlow', '')}
- Velocidade Média Espacial da Rede: {net.get('networkMeanSpeed', '')}
- Grau Médio de Saturação (x = V/C): {net.get('networkMeanSaturation', '')}
- Nível de Serviço da Rede (LOS): {net.get('networkLevelOfService', '')}

--------------------------------------------------------------------------------
3. INVENTÁRIO METROLÓGICO DOS DETECTORES E EQUIPAMENTOS DE CAMPO
--------------------------------------------------------------------------------
{sensors_md}

================================================================================
PARTE III — SEGURANÇA VIÁRIA, GUARDRAILS E ANÁLISE DE ATRIBUIÇÃO
================================================================================

4. TRAVAS RÍGIDAS DE SEGURANÇA VIÁRIA (GUARDRAILS REGULAMENTARES DO CONTRAN)
{safety_md}

--------------------------------------------------------------------------------
5. ANÁLISE DE ATRIBUIÇÃO CAUSAL DE DECISÃO
--------------------------------------------------------------------------------
{attrs_md}

================================================================================
PARTE IV — FORMULAÇÃO MATEMÁTICA E ANÁLISE CONTRAFATUAL
================================================================================
6. MEMORIAL DE CÁLCULO E MODELAGEM DE TRÁFEGO
- Saturação da Aproximação (HCM): x = V / (S * (g/C))
- Ciclo Ótimo de Webster: Co = (1.5 * L + 5) / (1 - Y)
- Intervalo de Mudança de Gazis: y = tr + v / (2 * a) + (w + L) / v
- Conservação Hidrodinâmica (LWR): dq/dx + dk/dt = 0

7. ANÁLISE CONTRAFATUAL DE CONDICIONANTES:
{r.get('counterfactualAnalysis', '')}

================================================================================
PARTE V — QUESITOS TÉCNICOS PERICIAIS E ENQUADRAMENTO JURÍDICO
================================================================================
{quesitos_md}

--------------------------------------------------------------------------------
8. ENQUADRAMENTO NORMATIVO E JURÍDICO APLICADO
--------------------------------------------------------------------------------
{legal_md}

================================================================================
PARTE VI — CERTIFICAÇÃO DIGITAL, SUPERVISÃO OPERACIONAL E REFERÊNCIAS
================================================================================
9. DECLARAÇÃO DE SUPERVISÃO OPERACIONAL:
{r.get('operationalSupervision', '')}

10. CERTIFICAÇÃO DIGITAL ICP-BRASIL:
{r.get('digitalCertification', '')}

11. REFERÊNCIAS NORMATIVAS E BIBLIOGRÁFICAS (ABNT NBR 10719):
{refs_md}
================================================================================
"""
