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
// File: ui/src_ui/components/xai/report/ReportFormulasCard.tsx
// Author: Gabriel Moraes
// Date: 2026-09-01

import React from 'react';
import { LatexRenderer } from '../../common/LatexRenderer';

interface ReportFormulasCardProps {
  convergenceDelta?: number;
}

export const ReportFormulasCard: React.FC<ReportFormulasCardProps> = () => {
  return (
    <div className="space-y-3 font-serif text-black">
      <div className="border-b border-black pb-0.5">
        <h3 className="text-[11px] font-bold uppercase text-black">
          6. Memorial de Cálculo e Formulação Matemática da Engenharia de Tráfego
        </h3>
        <p className="text-[10px] text-black italic">
          Equações canônicas de dimensionamento semafórico, saturação, segurança e hidrodinâmica viária (ABNT NBR 10719).
        </p>
      </div>

      <div className="space-y-2.5 text-xs text-justify leading-relaxed">
        {/* Equação 1: Grau de Saturação (HCM) */}
        <div className="space-y-0.5">
          <p className="font-bold text-[10.5px] text-black">
            6.1. Grau de Saturação da Aproximação (Highway Capacity Manual — HCM)
          </p>
          <p className="indent-4 text-[10px] text-black">
            O grau de saturação <LatexRenderer math="x" displayMode={false} /> relaciona o volume medido <LatexRenderer math="V" displayMode={false} /> à capacidade real <LatexRenderer math="c = S \cdot (g/C)" displayMode={false} />:
          </p>
          <div className="py-1 text-center">
            <LatexRenderer
              math="x = \frac{V}{c} = \frac{V}{S \cdot \left(\frac{g}{C}\right)} \tag{1}"
              displayMode={true}
            />
          </div>
        </div>

        {/* Equação 2: Ciclo Ótimo de Webster */}
        <div className="space-y-0.5">
          <p className="font-bold text-[10.5px] text-black">
            6.2. Tempo de Ciclo Ótimo para Minimização de Atrasos (Método de Webster)
          </p>
          <p className="indent-4 text-[10px] text-black">
            Minimiza o atraso médio veicular com base no tempo perdido total <LatexRenderer math="L" displayMode={false} /> e na soma das razões críticas <LatexRenderer math="Y" displayMode={false} />:
          </p>
          <div className="py-1 text-center">
            <LatexRenderer
              math="C_{\text{ótimo}} = \frac{1,5 \cdot L + 5}{1 - Y} \tag{2}"
              displayMode={true}
            />
          </div>
        </div>

        {/* Equação 3: Tempo de Amarelo (Gazis / CONTRAN) */}
        <div className="space-y-0.5">
          <p className="font-bold text-[10.5px] text-black">
            6.3. Cinemática do Tempo de Amarelo (Gazis-Herman / Resolução CONTRAN nº 995/2023)
          </p>
          <p className="indent-4 text-[10px] text-black">
            Elimina a zona de dilema para velocidade limite <LatexRenderer math="v_0 = 13,89\text{ m/s}" displayMode={false} />, desaceleração <LatexRenderer math="a = 3,0\text{ m/s}^2" displayMode={false} /> e percepção <LatexRenderer math="t_r = 1,0\text{ s}" displayMode={false} />:
          </p>
          <div className="py-1 text-center">
            <LatexRenderer
              math="y = t_r + \frac{v_0}{2a} = 1,0\text{ s} + \frac{13,89}{2 \times 3,0} \approx 3,32\text{ s} \implies y_{\text{adotado}} = 4,0\text{ s} \tag{3}"
              displayMode={true}
            />
          </div>
        </div>

        {/* Equação 4: Vermelho de Limpeza / All-Red */}
        <div className="space-y-0.5">
          <p className="font-bold text-[10.5px] text-black">
            6.4. Intervalo de Vermelho de Limpeza / All-Red (Manual Brasileiro de Sinalização)
          </p>
          <p className="indent-4 text-[10px] text-black">
            Garante a desobstrução da área de conflito (<LatexRenderer math="w = 18,0\text{ m}" displayMode={false} /> e <LatexRenderer math="L_v = 5,0\text{ m}" displayMode={false} />) antes do estágio conflitante:
          </p>
          <div className="py-1 text-center">
            <LatexRenderer
              math="r_{\text{limpeza}} = \frac{w + L_v}{v_0} = \frac{18,0 + 5,0}{13,89} \approx 1,66\text{ s} \implies r_{\text{adotado}} = 2,0\text{ s} \tag{4}"
              displayMode={true}
            />
          </div>
        </div>

        {/* Equação 5: Tempo de Pedestres NBR 9050 */}
        <div className="space-y-0.5">
          <p className="font-bold text-[10.5px] text-black">
            6.5. Tempo Mínimo de Travessia para Pedestres (ABNT NBR 9050 / CONTRAN)
          </p>
          <p className="indent-4 text-[10px] text-black">
            Adota velocidade de caminhada reduzida de <LatexRenderer math="v_p = 1,0\text{ m/s}" displayMode={false} /> para acessibilidade universal:
          </p>
          <div className="py-1 text-center">
            <LatexRenderer
              math="T_{\text{pedestre}} = t_{\text{reação}} + \frac{D_{\text{largura}}}{v_{\text{pedestre}}} = 3,0\text{ s} + \frac{15,0\text{ m}}{1,0\text{ m/s}} = 18,0\text{ s} \tag{5}"
              displayMode={true}
            />
          </div>
        </div>

        {/* Equação 6: Onda de Choque LWR */}
        <div className="space-y-0.5">
          <p className="font-bold text-[10.5px] text-black">
            6.6. Propagação da Onda de Choque de Tráfego (Lighthill-Whitham-Richards — LWR)
          </p>
          <p className="indent-4 text-[10px] text-black">
            A velocidade da onda de choque <LatexRenderer math="W" displayMode={false} /> entre seções de fluxo e densidade:
          </p>
          <div className="py-1 text-center">
            <LatexRenderer
              math="W = \frac{q_2 - q_1}{k_2 - k_1} = \frac{\Delta q}{\Delta k} \tag{6}"
              displayMode={true}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
