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
// File: ui/src_ui/components/xai/XaiInspector.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React, { useState } from 'react';
import { useXaiStore, useSensorsStore, useReportStore } from '../../stores';
import { xaiService } from '../../services/api';
import { XaiHeaderControls } from './XaiHeaderControls';
import { XaiHistoryPanel } from './XaiHistoryPanel';
import { XaiSemanticPanel } from './XaiSemanticPanel';
import { XaiAttributionChart } from './XaiAttributionChart';
import { XaiOfficialReportModal } from './XaiOfficialReportModal';
import { XaiExplainMode, XaiResultItem, XaiAuditVerdict } from '../../types/xai';

export const XaiInspector: React.FC = () => {
  const { verdicts, xaiHistory, selectedXaiResultId, setSelectedXaiResultId } = useXaiStore();
  const { isReportModalOpen, selectedReport, openReportModal, closeReportModal } = useReportStore();
  const sources = useSensorsStore((s) => s.sources);

  const [selectedSensorForTcn, setSelectedSensorForTcn] = useState(sources[0]?.id || '');
  const [loadingAction, setLoadingAction] = useState<XaiExplainMode | null>(null);

  // Sync selected sensor with loaded sources
  React.useEffect(() => {
    if ((!selectedSensorForTcn || !sources.some(s => s.id === selectedSensorForTcn)) && sources.length > 0) {
      setSelectedSensorForTcn(sources[0].id);
    }
  }, [sources, selectedSensorForTcn]);

  // Initial dynamic fallback if no history exists yet
  const dynamicFallbackResult: XaiResultItem = React.useMemo(() => ({
    id: 'initial',
    type: 'AUDITOR',
    target: 'Consistência Física Global (Zero-Trust)',
    convergence_delta: 0.0012,
    semantic_text:
      'Sistema em monitoramento Zero-Trust. Clique em "Explicar Janela Temporal", "Explicar Decisão Global" ou "Explicar Sensor" para rodar a inferência de Integrated Gradients em tempo real.',
    attributions: [0.04, 0.08, 0.12, 0.18, 0.26, 0.35, 0.48, 0.62, 0.78, 0.88, 0.95, 1.0],
    timestamp: new Date().toLocaleTimeString(),
  }), []);

  const dynamicFallbackVerdict: XaiAuditVerdict = React.useMemo(() => ({
    safe: true,
    error: 0.012,
    threshold: 0.045,
    vector: [0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 0.85, 0.95, 1.0],
    timestamp: new Date().toLocaleTimeString(),
  }), []);

  const selectedResult =
    xaiHistory.find((r) => r.id === selectedXaiResultId) || xaiHistory[0] || dynamicFallbackResult;

  const latestVerdict = verdicts[0] || dynamicFallbackVerdict;

  const handleAction = async (type: XaiExplainMode) => {
    setLoadingAction(type);
    try {
      if (type === 'buffer') await xaiService.explainBuffer();
      if (type === 'global') await xaiService.explainGlobal();
      if (type === 'local') await xaiService.explainLocal(selectedSensorForTcn || sources[0]?.id || '');
    } catch (err) {
      console.error('Failed to trigger XAI explanation:', err);
    } finally {
      setTimeout(() => setLoadingAction(null), 800);
    }
  };

  return (
    <div className="h-[calc(100vh-4rem-2rem)] overflow-y-auto p-6 space-y-6 bg-background select-none">
      {/* 1. Header Control Bar */}
      <XaiHeaderControls
        sources={sources}
        selectedSensorForTcn={selectedSensorForTcn}
        loadingAction={loadingAction}
        onSelectSensorForTcn={setSelectedSensorForTcn}
        onTriggerExplain={handleAction}
        onOpenReport={() => openReportModal(null)}
      />

      {/* 2. Main Work Area: Left History Panel + Right Report & Charts */}
      <div className="grid grid-cols-4 gap-6">
        <XaiHistoryPanel
          latestVerdict={latestVerdict}
          xaiHistory={xaiHistory}
          selectedResultId={selectedResult.id}
          onSelectResult={setSelectedXaiResultId}
          onOpenReport={(report) => openReportModal(report)}
        />

        <div className="col-span-3 space-y-6">
          <XaiSemanticPanel
            result={selectedResult}
            onOpenReport={() => openReportModal(null)}
          />
          <XaiAttributionChart
            attributions={selectedResult.attributions}
            featureNames={selectedResult.feature_names}
          />
        </div>
      </div>

      {/* 3. Official Municipal XAI Report Modal */}
      <XaiOfficialReportModal
        isOpen={isReportModalOpen}
        onClose={closeReportModal}
        result={selectedResult}
        savedReport={selectedReport}
      />
    </div>
  );
};
