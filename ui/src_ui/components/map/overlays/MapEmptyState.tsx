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
// File: ui/src_ui/components/map/overlays/MapEmptyState.tsx
// Author: Gabriel Moraes
// Date: 2026-08-31

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Compass } from 'lucide-react';

interface MapEmptyStateProps {
  mapLoaded: boolean;
}

export const MapEmptyState: React.FC<MapEmptyStateProps> = ({ mapLoaded }) => {
  const { t } = useTranslation();

  if (mapLoaded) return null;

  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center bg-background/80 backdrop-blur-sm pointer-events-none select-none">
      <div className="w-16 h-16 rounded-2xl bg-primary-500/10 border border-primary-500/20 flex items-center justify-center mb-4">
        <Compass className="w-8 h-8 text-primary-500 dark:text-primary-400 animate-spin-slow" />
      </div>
      <h2 className="text-base font-bold text-slate-900 dark:text-white mb-2">{t('map.title')}</h2>
      <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm">{t('map.noMapLoaded')}</p>
    </div>
  );
};
