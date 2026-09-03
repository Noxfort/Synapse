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
// File: ui/src_ui/components/layout/AppLayout.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React, { useState, useEffect } from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { StatusBar } from './StatusBar';
import { LogConsole } from './LogConsole';
import { SumoMapCanvas } from '../map/SumoMapCanvas';
import { LiveDashboard } from '../dashboard/LiveDashboard';
import { XaiInspector } from '../xai/XaiInspector';
import { SettingsModal } from '../settings/SettingsModal';
import { ImportWizardModal } from '../wizard/ImportWizardModal';
import { initSynapseBridge } from '../../stores';

export const AppLayout: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'map' | 'dashboard' | 'xai'>('map');
  const [isLogsOpen, setIsLogsOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isImportWizardOpen, setIsImportWizardOpen] = useState(false);
  const [wizardInitialStep, setWizardInitialStep] = useState<1 | 2 | 3>(1);

  useEffect(() => {
    let unlisten: (() => void) | undefined;
    initSynapseBridge().then((fn) => {
      unlisten = fn;
    });
    return () => {
      if (unlisten) unlisten();
    };
  }, []);

  const handleOpenImportWizard = (step: 1 | 2 | 3 = 1) => {
    setWizardInitialStep(step);
    setIsImportWizardOpen(true);
  };

  return (
    <div className="w-screen h-screen flex flex-col bg-background text-slate-100 overflow-hidden select-none">
      {/* 1. Top Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        openSettings={() => setIsSettingsOpen(true)}
        openLogs={() => setIsLogsOpen(!isLogsOpen)}
        isLogsOpen={isLogsOpen}
      />

      {/* 2. Main Work Area (Sidebar + Active View) */}
      <div className="flex-1 flex overflow-hidden relative">
        <Sidebar 
          openImportWizard={handleOpenImportWizard}
          setActiveTab={setActiveTab}
        />

        <main className="flex-1 relative overflow-hidden">
          {activeTab === 'map' && <SumoMapCanvas />}
          {activeTab === 'dashboard' && <LiveDashboard />}
          {activeTab === 'xai' && <XaiInspector />}
        </main>

        {/* Retractable Log Drawer */}
        <LogConsole isOpen={isLogsOpen} onClose={() => setIsLogsOpen(false)} />
      </div>

      {/* 3. Bottom Status Bar */}
      <StatusBar />

      {/* 4. Modals */}
      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
      
      <ImportWizardModal 
        isOpen={isImportWizardOpen} 
        onClose={() => setIsImportWizardOpen(false)} 
        initialStep={wizardInitialStep}
      />
    </div>
  );
};
