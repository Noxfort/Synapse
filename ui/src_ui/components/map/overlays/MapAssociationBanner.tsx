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
// File: ui/src_ui/components/map/overlays/MapAssociationBanner.tsx
// Author: Gabriel Moraes
// Date: 2026-08-31

import React from 'react';
import { Crosshair, CheckCircle2 } from 'lucide-react';

interface MapAssociationBannerProps {
  isAssociatingSourceId: string | null;
  associationNotice: string | null;
  onCancelAssociation: () => void;
}

export const MapAssociationBanner: React.FC<MapAssociationBannerProps> = ({
  isAssociatingSourceId,
  associationNotice,
  onCancelAssociation,
}) => {
  return (
    <>
      {/* Association Crosshair Mode Banner */}
      {isAssociatingSourceId && (
        <div className="absolute top-4 left-6 z-20 glass-panel bg-primary-600/90 text-white px-4 py-2.5 rounded-xl shadow-2xl flex items-center gap-3 border border-primary-400 animate-pulse select-none">
          <Crosshair className="w-5 h-5 text-accent-cyan" />
          <div>
            <p className="text-xs font-bold">Modo de Associação Espacial Ativo</p>
            <p className="text-[11px] opacity-90">
              Clique em qualquer via ou cruzamento no mapa para vincular o sensor <b>{isAssociatingSourceId}</b>.
            </p>
          </div>
          <button
            onClick={onCancelAssociation}
            className="ml-2 px-2.5 py-1 text-[11px] bg-black/40 hover:bg-black/60 rounded-lg font-semibold transition-colors"
          >
            Cancelar
          </button>
        </div>
      )}

      {/* Association Success Notification */}
      {associationNotice && (
        <div className="absolute top-4 left-6 z-20 glass-panel bg-emerald-950/90 text-emerald-300 px-4 py-2.5 rounded-xl shadow-2xl flex items-center gap-2 border border-emerald-500/50 animate-in fade-in select-none">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-semibold">{associationNotice}</span>
        </div>
      )}
    </>
  );
};
