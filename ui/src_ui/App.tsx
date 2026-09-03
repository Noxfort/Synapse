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
// File: ui/src_ui/App.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React, { useEffect } from 'react';
import { AppLayout } from './components/layout/AppLayout';
import { useSystemStore } from './stores';
import { toggleFullscreen } from './utils/windowControls';
import { systemService } from './services/api';

export const App: React.FC = () => {
  const theme = useSystemStore((s) => s.theme);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
      root.classList.remove('light');
    } else {
      root.classList.add('light');
      root.classList.remove('dark');
    }
  }, [theme]);

  // Global F11 shortcut listener for fullscreen toggle
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'F11') {
        e.preventDefault();
        toggleFullscreen();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Restore database connection state from settings.ini on application startup
  useEffect(() => {
    (async () => {
      try {
        const dbCfg = await systemService.getDatabaseConfig();
        if (dbCfg?.connected) {
          useSystemStore.getState().setDbStatus({
            connected: true,
            message: `Conectado ao schema '${dbCfg.schema || 'schema_synapse'}'`,
          });
        }
      } catch (e) {
        console.warn('Initial config sync skipped:', e);
      }
    })();
  }, []);

  return <AppLayout />;
};

export default App;

