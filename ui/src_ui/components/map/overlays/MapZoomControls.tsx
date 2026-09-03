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
// File: ui/src_ui/components/map/overlays/MapZoomControls.tsx
// Author: Gabriel Moraes
// Date: 2026-08-31

import React from 'react';
import { useTranslation } from 'react-i18next';
import { ZoomIn, ZoomOut } from 'lucide-react';

interface MapZoomControlsProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
}

export const MapZoomControls: React.FC<MapZoomControlsProps> = ({
  onZoomIn,
  onZoomOut,
}) => {
  const { t } = useTranslation();

  return (
    <div className="absolute top-4 right-4 flex flex-col gap-2 z-10 select-none">
      <button
        onClick={onZoomIn}
        title={t('map.zoomIn')}
        className="p-2.5 rounded-xl glass-panel text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white glass-panel-hover transition-colors"
      >
        <ZoomIn className="w-4 h-4" />
      </button>
      <button
        onClick={onZoomOut}
        title={t('map.zoomOut')}
        className="p-2.5 rounded-xl glass-panel text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white glass-panel-hover transition-colors"
      >
        <ZoomOut className="w-4 h-4" />
      </button>
    </div>
  );
};
