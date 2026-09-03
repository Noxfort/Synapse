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
// File: ui/src_ui/components/map/overlays/MapHoverBadge.tsx
// Author: Gabriel Moraes
// Date: 2026-08-31

import React from 'react';
import { MapPin } from 'lucide-react';

interface MapHoverBadgeProps {
  hoveredInfo: string | null;
}

export const MapHoverBadge: React.FC<MapHoverBadgeProps> = ({ hoveredInfo }) => {
  if (!hoveredInfo) return null;

  return (
    <div className="absolute bottom-4 left-6 z-20 glass-panel px-4 py-2 rounded-xl text-xs font-mono text-slate-800 dark:text-slate-200 border border-border flex items-center gap-2 shadow-xl animate-in fade-in select-none">
      <MapPin className="w-3.5 h-3.5 text-accent-amber" />
      <span>{hoveredInfo}</span>
    </div>
  );
};
