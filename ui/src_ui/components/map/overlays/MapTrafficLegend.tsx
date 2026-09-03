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
// File: ui/src_ui/components/map/overlays/MapTrafficLegend.tsx
// Author: Gabriel Moraes
// Date: 2026-08-31

import React from 'react';

interface MapTrafficLegendProps {
  visible: boolean;
}

export const MapTrafficLegend: React.FC<MapTrafficLegendProps> = ({ visible }) => {
  if (!visible) return null;

  return (
    <div className="absolute bottom-4 right-4 z-10 glass-panel px-3 py-2 rounded-xl border border-border/70 bg-surface/90 text-[10px] font-mono space-y-1 select-none shadow-xl">
      <div className="text-[9px] uppercase tracking-wider font-sans font-bold text-slate-400">
        Regime Fluidodinâmico
      </div>
      <div className="flex items-center gap-3 text-[10px]">
        <div className="flex items-center gap-1 text-emerald-500 dark:text-emerald-400">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          <span>&gt; 45 km/h</span>
        </div>
        <div className="flex items-center gap-1 text-amber-500 dark:text-amber-400">
          <span className="w-2 h-2 rounded-full bg-amber-500" />
          <span>20–45 km/h</span>
        </div>
        <div className="flex items-center gap-1 text-rose-500 dark:text-rose-400">
          <span className="w-2 h-2 rounded-full bg-rose-500" />
          <span>&lt; 20 km/h</span>
        </div>
        <div className="flex items-center gap-1 text-accent-cyan">
          <span className="w-2 h-2 rounded-full bg-accent-cyan" />
          <span>Sensor</span>
        </div>
      </div>
    </div>
  );
};
