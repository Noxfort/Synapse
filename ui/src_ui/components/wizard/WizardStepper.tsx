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
// File: ui/src_ui/components/wizard/WizardStepper.tsx
// Author: Gabriel Moraes
// Date: 2026-08-29

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Network, Database, Radio, CheckCircle2 } from 'lucide-react';

interface WizardStepperProps {
  currentStep: 1 | 2 | 3;
  onSelectStep: (step: 1 | 2 | 3) => void;
  isMapCompleted: boolean;
  isParquetCompleted: boolean;
  hasSensors: boolean;
}

export const WizardStepper: React.FC<WizardStepperProps> = ({
  currentStep,
  onSelectStep,
  isMapCompleted,
  isParquetCompleted,
  hasSensors,
}) => {
  const { t } = useTranslation();

  const steps = [
    {
      number: 1 as const,
      key: 'map',
      title: t('wizard.stepMap'),
      icon: Network,
      isCompleted: isMapCompleted || currentStep > 1,
    },
    {
      number: 2 as const,
      key: 'parquet',
      title: t('wizard.stepParquet'),
      icon: Database,
      isCompleted: isParquetCompleted || currentStep > 2,
    },
    {
      number: 3 as const,
      key: 'sensors',
      title: t('wizard.stepSensors'),
      icon: Radio,
      isCompleted: hasSensors,
    },
  ];

  return (
    <div className="py-4 border-b border-border/60 flex items-center justify-between flex-shrink-0">
      {steps.map((st, idx) => {
        const Icon = st.icon;
        const isActive = currentStep === st.number;

        return (
          <React.Fragment key={st.key}>
            <div
              onClick={() => onSelectStep(st.number)}
              className={`flex items-center gap-2.5 px-3 py-1.5 rounded-xl cursor-pointer transition-all ${
                isActive
                  ? 'bg-primary-600/20 border border-primary-500 text-primary-700 dark:text-white font-bold shadow-sm shadow-primary-500/10'
                  : st.isCompleted
                  ? 'bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-300 dark:border-emerald-500/30 text-emerald-700 dark:text-emerald-400 font-semibold'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200 font-medium'
              }`}
            >
              <div
                className={`w-6 h-6 rounded-lg flex items-center justify-center text-xs font-bold ${
                  isActive
                    ? 'bg-primary-600 text-white'
                    : st.isCompleted
                    ? 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-400'
                    : 'bg-surface border border-border text-slate-500 dark:text-slate-400'
                }`}
              >
                {st.isCompleted && !isActive ? (
                  <CheckCircle2 className="w-3.5 h-3.5" />
                ) : (
                  <Icon className="w-3.5 h-3.5" />
                )}
              </div>
              <span className="text-xs">{st.title}</span>
            </div>

            {idx < steps.length - 1 && (
              <div className="flex-1 h-[2px] mx-3 bg-border/60 relative">
                <div
                  className="h-full bg-gradient-to-r from-primary-500 to-emerald-500 transition-all duration-300"
                  style={{
                    width: currentStep > st.number ? '100%' : '0%',
                  }}
                />
              </div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};
