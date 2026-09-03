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
// File: ui/src_ui/components/wizard/ImportWizardModal.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Sparkles, ArrowRight, ArrowLeft, CheckCircle2 } from 'lucide-react';
import { useTopologyStore, useEtlStore, useSensorsStore } from '../../stores';
import { WizardStepper } from './WizardStepper';
import { MapStep } from './steps/MapStep';
import { ParquetStep } from './steps/ParquetStep';
import { SensorsStep } from './steps/SensorsStep';

interface ImportWizardModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialStep?: 1 | 2 | 3;
}

/**
 * Orchestrator Modal for the sequential 3-step Ingestion Pipeline (SOLID / SRP compliant)
 * Step 1: SUMO Map (MapStep)
 * Step 2: Parquet Dataset (ParquetStep)
 * Step 3: Sensors & Streams (SensorsStep)
 */
export const ImportWizardModal: React.FC<ImportWizardModalProps> = ({
  isOpen,
  onClose,
  initialStep = 1,
}) => {
  const { t } = useTranslation();

  const mapLoaded = useTopologyStore((s) => s.mapLoaded);
  const { importProgress, resetEtlState } = useEtlStore();
  const sources = useSensorsStore((s) => s.sources);

  const [currentStep, setCurrentStep] = useState<1 | 2 | 3>(initialStep);

  useEffect(() => {
    if (isOpen) {
      setCurrentStep(initialStep);
    }
  }, [isOpen, initialStep]);

  if (!isOpen) return null;

  const handleClose = () => {
    onClose();
  };

  const hasParquetSource = sources.some(
    (s) => s.connection_string?.toLowerCase().endsWith('.parquet') || s.source_type === 'Parquet'
  );
  const isParquetDone = importProgress.progress === 100 || hasParquetSource;
  const hasLiveSensors = sources.some(
    (s) => s.source_type !== 'Parquet' && !s.connection_string?.toLowerCase().endsWith('.parquet') && s.source_type !== 'SUMO Network'
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md p-4 animate-in fade-in select-none">
      <div className="w-full max-w-3xl glass-panel bg-surface p-6 rounded-2xl shadow-2xl border border-border flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-border/80 pb-4 flex-shrink-0">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary-500 dark:text-primary-400" />
              <span>{t('wizard.title')}</span>
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{t('wizard.subtitle')}</p>
          </div>
          <button
            onClick={handleClose}
            className="p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-surfaceHover transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Stepper Navigation */}
        <WizardStepper
          currentStep={currentStep}
          onSelectStep={setCurrentStep}
          isMapCompleted={mapLoaded}
          isParquetCompleted={isParquetDone}
          hasSensors={hasLiveSensors}
        />

        {/* Modular Step Content */}
        <div className="py-5 overflow-y-auto flex-1 text-xs space-y-4 pr-1">
          {currentStep === 1 && <MapStep />}
          {currentStep === 2 && <ParquetStep />}
          {currentStep === 3 && <SensorsStep />}
        </div>

        {/* Footer Navigation Controls */}
        <div className="flex items-center justify-between border-t border-border/80 pt-4 flex-shrink-0">
          {currentStep > 1 ? (
            <button
              onClick={() => setCurrentStep((currentStep - 1) as 1 | 2 | 3)}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white bg-surface border border-border flex items-center gap-1.5 hover:border-slate-400 dark:hover:border-slate-500 transition-all"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>{t('wizard.back')}</span>
            </button>
          ) : (
            <div />
          )}

          <div className="flex items-center gap-2">
            {currentStep < 3 ? (
              <button
                onClick={() => setCurrentStep((currentStep + 1) as 1 | 2 | 3)}
                className="px-5 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-bold shadow-md shadow-primary-600/20 transition-all flex items-center gap-1.5"
              >
                <span>{t('wizard.next')}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={handleClose}
                className="px-6 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-md shadow-emerald-600/30 transition-all flex items-center gap-2"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>{t('wizard.finish')}</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ImportWizardModal;
