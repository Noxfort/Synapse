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
// File: ui/src_ui/components/map/overlays/MapNodeInspector.tsx
// Author: Gabriel Moraes
// Date: 2026-08-31

import React from 'react';
import { MapPin, X } from 'lucide-react';

interface MapNodeInspectorProps {
  nodeId: string;
  infoText?: string | null;
  onClose: () => void;
}

export const MapNodeInspector: React.FC<MapNodeInspectorProps> = ({
  nodeId,
  infoText,
  onClose,
}) => {
  return (
    <div className="absolute bottom-4 left-6 z-20 glass-panel p-3.5 rounded-xl border border-primary-500/40 bg-surface/95 shadow-2xl space-y-2 min-w-[280px] animate-in fade-in select-none">
      <div className="flex items-center justify-between gap-2 border-b border-border/80 pb-2">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-primary-500" />
          <span className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1">
            <MapPin className="w-3.5 h-3.5 text-primary-400" />
            Cruzamento / Nó
          </span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-primary-500/10 text-primary-400 border border-primary-500/30 font-bold">
            {nodeId}
          </span>
          <button
            onClick={onClose}
            className="p-0.5 text-slate-400 hover:text-slate-200 rounded hover:bg-surfaceHover transition-colors"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      </div>
      {infoText && (
        <p className="text-xs font-mono text-slate-700 dark:text-slate-300">{infoText}</p>
      )}
    </div>
  );
};
