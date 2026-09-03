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
// File: ui/src_ui/components/xai/report/ReportReferencesCard.tsx
// Author: Gabriel Moraes
// Date: 2026-09-01

import React from 'react';

interface ReportReferencesCardProps {
  references: string[];
}

export const ReportReferencesCard: React.FC<ReportReferencesCardProps> = ({ references }) => {
  return (
    <div className="space-y-2 font-serif text-black pt-2">
      <div className="border-b border-black pb-0.5">
        <h3 className="text-[11px] font-bold uppercase text-black">
          11. Referências Normativas e Bibliográficas (ABNT NBR 6023:2018)
        </h3>
      </div>

      <div className="text-[9.5px] leading-relaxed text-black text-justify space-y-1.5 pl-0">
        {references.map((ref, idx) => (
          <p key={idx} className="text-black">
            {ref}
          </p>
        ))}
      </div>
    </div>
  );
};
