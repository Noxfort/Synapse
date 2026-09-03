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
// File: ui/src_ui/services/report/docx/sections/DocxMathFormulasSection.ts
// Author: Gabriel Moraes
// Date: 2026-09-02

import { Paragraph, TextRun, AlignmentType } from 'docx';
import { OfficialReportData } from '../../../../types/report';
import {
  DocxTypographyConfig,
  createSectionHeading,
  createSubSectionHeading,
  createParagraph,
  createParagraphWithBoldLead,
  createBulletPoint,
} from '../abntDocxStyles';

/**
 * Builds Section 6 (Mathematical Memorial) and Section 7 (Counterfactual Analysis)
 * following the exact Carina benchmark pattern.
 */
export class DocxMathFormulasSection {
  public static build(
    report: OfficialReportData,
    config: DocxTypographyConfig
  ): Paragraph[] {
    return [
      createSectionHeading('6. METODOLOGIA E MEMORIAL DE CÁLCULO MATEMÁTICO', config),
      createParagraph(
        'As intervenções semafóricas adaptativas executadas pelo sistema apoiam-se no memorial de cálculo canônico de engenharia de tráfego, garantindo rastreabilidade pericial e estrita fundamentação científica (ABNT NBR 10719):',
        config
      ),
      ...this.createFormulasList(config),

      new Paragraph({ spacing: { before: 180 } }),

      createSectionHeading('7. ANÁLISE CONTRAFACTUAL (HIPÓTESE DE REFUTABILIDADE TÉCNICA)', config),
      createParagraphWithBoldLead(
        'Condição para Manutenção do Plano Estático Nominal sem Intervenção:',
        report.counterfactualAnalysis,
        config
      ),
    ];
  }

  private static createFormulasList(config: DocxTypographyConfig): Paragraph[] {
    const formulas = [
      {
        title: 'Critério 1: Grau de Saturação da Aproximação (Highway Capacity Manual — HCM)',
        desc: 'Determina a taxa de ocupação da capacidade viária pela relação entre o volume medido pelos detectores e a capacidade real do estágio de verde:',
        formula: 'x = V / c = V / [S · (g / C)]    (1)',
        vars: [
          'x: Grau de Saturação da aproximação (adimensional, limite de estabilidade: x < 0,85).',
          'V: Volume horário de veículos aferido em campo (veíc/h).',
          'c: Capacidade real da aproximação semafórica (veíc/h).',
          'S: Fluxo de saturação básico da via (típico: 1.800 a 1.900 veíc/h por faixa).',
          'g / C: Fração de verde efetivo em relação ao tempo de ciclo total.',
        ],
        explanation:
          'Um cruzamento entra em regime de saturação forçada quando x > 0,85. Acima desse patamar, a fila não dissipa no ciclo e passa a se acumular exponencialmente.',
      },
      {
        title: 'Critério 2: Ciclo Semafórico Ótimo para Minimização de Atrasos (Método de Webster)',
        desc: 'Calcula o tempo de ciclo ideal que minimiza o tempo total perdido por todos os condutores na interseção:',
        formula: 'C_ótimo = (1,5 · L + 5) / (1 - Y)    (2)',
        vars: [
          'C_ótimo: Tempo de ciclo ótimo calculado (segundos).',
          'L: Tempo total perdido por ciclo por razões de transição e aceleração (segundos).',
          'Y: Soma das razões críticas de fluxo de saturação dos estágios conflitantes.',
        ],
        explanation:
          'Garante que os semáforos não operem nem com ciclos curtos demais (que geram excesso de perda por transição de fase) nem longos demais (que geram esperas ociosas desnecessárias).',
      },
      {
        title: 'Critério 3: Cinemática do Tempo de Amarelo (Gazis-Herman / Resolução CONTRAN nº 995/2023)',
        desc: 'Elimina a zona de dilema garantindo que o motorista que se aproxima consiga frear com segurança ou desobstruir o cruzamento antes do sinal vermelho:',
        formula: 'y = tr + v0 / (2a) = 1,0 s + 13,89 / (2 × 3,0) ≈ 3,32 s  =>  y_adotado = 4,0 s    (3)',
        vars: [
          'y: Tempo de amarelo regulamentar (segundos).',
          'tr: Tempo de percepção e reação do condutor (1,0 segundo).',
          'v0: Velocidade regulamentada de aproximação (13,89 m/s = 50 km/h).',
          'a: Taxa de desaceleração confortável do veículo (3,0 m/s²).',
        ],
        explanation:
          'O tempo de amarelo é uma restrição rígida de segurança inviolável: mesmo durante aumentos de demanda, o sistema jamais reduz o amarelo abaixo do patamar físico.',
      },
      {
        title: 'Critério 4: Intervalo de Vermelho de Limpeza / All-Red (Manual Brasileiro de Sinalização Semafórica)',
        desc: 'Garante a desobstrução física completa da caixa do cruzamento antes da liberação do estágio transversal conflitante:',
        formula: 'r_limpeza = (w + Lv) / v0 = (18,0 + 5,0) / 13,89 ≈ 1,66 s  =>  r_adotado = 2,0 s    (4)',
        vars: [
          'r_limpeza: Intervalo de vermelho de limpeza geral (segundos).',
          'w: Largura física da caixa de cruzamento a ser desobstruída (18,0 metros).',
          'Lv: Comprimento médio dos veículos do tráfego urbano (5,0 metros).',
          'v0: Velocidade limite permitida no trecho (13,89 m/s).',
        ],
        explanation:
          'Impede colisões laterais em ângulo reto (abalroamentos) entre veículos que estão terminando a travessia e veículos que iniciam a arrancada.',
      },
      {
        title: 'Critério 5: Tempo Mínimo de Travessia para Pedestres (ABNT NBR 9050 / Resolução CONTRAN)',
        desc: 'Adota a velocidade universal de caminhada acessível para garantir a segurança integral de idosos e pessoas com deficiência física:',
        formula: 'T_pedestre = t_reação + D_largura / v_pedestre = 3,0 s + 15,0 m / 1,0 m/s = 18,0 s    (5)',
        vars: [
          'T_pedestre: Tempo de travessia seguro atribuído à fase de pedestre (segundos).',
          't_reação: Tempo inicial para o pedestre perceber o foco verde e iniciar a marcha (3,0 s).',
          'D_largura: Largura total da pista de rolamento na faixa de pedestres (15,0 metros).',
          'v_pedestre: Velocidade de caminhada universal estipulada pela NBR 9050 (1,0 m/s).',
        ],
        explanation:
          'O tempo de pedestres prevalece hierarquicamente sobre a demanda de veículos automotores, sendo blindado contra cortes prematuros pela lógica de inteligência artificial.',
      },
      {
        title: 'Critério 6: Propagação da Onda de Choque de Tráfego (Teoria Hidrodinâmica LWR)',
        desc: 'Calcula a velocidade de propagação e dissipação da onda de congestionamento ao longo da malha contínua de tráfego:',
        formula: 'W = (q2 - q1) / (k2 - k1) = Δq / Δk    (6)',
        vars: [
          'W: Velocidade de deslocamento da frente de onda de choque (km/h).',
          'q: Taxa de fluxo veicular entre as seções a montante e a jusante.',
          'k: Densidade veicular correspondente.',
        ],
        explanation:
          'Permite antecipar a formação do congestionamento e sincronizar a defasagem (offset) dos semáforos vizinhos para drenar a cauda da fila antes do travamento.',
      },
    ];

    const paragraphs: Paragraph[] = [];
    formulas.forEach((f) => {
      paragraphs.push(
        createSubSectionHeading(f.title, config),
        createParagraph(f.desc, config),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 80, after: 120 },
          children: [
            new TextRun({
              text: f.formula,
              bold: true,
              size: config.bodySize,
              font: config.font,
              color: '000000',
            }),
          ],
        }),
        new Paragraph({
          alignment: config.alignment,
          spacing: { before: 60, after: 40, line: config.lineSpacing },
          indent: { firstLine: config.paragraphIndent },
          children: [
            new TextRun({
              text: 'O que são as variáveis na equação:',
              bold: true,
              size: config.bodySize,
              font: config.font,
              color: '000000',
            }),
          ],
        }),
        ...f.vars.map((v) => createBulletPoint(v, config)),
        createParagraphWithBoldLead('Explicação para Gestão Pública:', f.explanation, config)
      );
    });
    return paragraphs;
  }
}
