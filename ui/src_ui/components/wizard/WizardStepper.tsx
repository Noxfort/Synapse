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
import { Network, Database, Radio, CheckCircle2, Lock } from 'lucide-react';

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

  const isStepAccessible = (stepNumber: 1 | 2 | 3) => {
    if (stepNumber === 1) return true;
    if (stepNumber === 2) return isMapCompleted;
    if (stepNumber === 3) return isMapCompleted && isParquetCompleted;
    return false;
  };

  const steps = [
    {
      number: 1 as const,
      key: 'map',
      title: t('wizard.stepMap'),
      icon: Network,
      isCompleted: isMapCompleted,
    },
    {
      number: 2 as const,
      key: 'parquet',
      title: t('wizard.stepParquet'),
      icon: Database,
      isCompleted: isParquetCompleted,
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
        const isAccessible = isStepAccessible(st.number);

        const getStepTooltip = () => {
          if (isAccessible) return undefined;
          if (st.number === 2) return t('wizard.reqMapToAdvance');
          if (st.number === 3) return t('wizard.reqParquetToAdvance');
          return t('wizard.stepLockedTooltip');
        };

        return (
          <React.Fragment key={st.key}>
            <div
              onClick={() => {
                if (isAccessible) {
                  onSelectStep(st.number);
                }
              }}
              title={getStepTooltip()}
              className={`flex items-center gap-2.5 px-3 py-1.5 rounded-xl transition-all ${
                !isAccessible
                  ? 'opacity-40 cursor-not-allowed text-slate-400 dark:text-slate-600 select-none'
                  : isActive
                  ? 'bg-primary-600/20 border border-primary-500 text-primary-700 dark:text-white font-bold shadow-sm shadow-primary-500/10 cursor-pointer'
                  : st.isCompleted
                  ? 'bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-300 dark:border-emerald-500/30 text-emerald-700 dark:text-emerald-400 font-semibold cursor-pointer'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200 font-medium cursor-pointer'
              }`}
            >
              <div
                className={`w-6 h-6 rounded-lg flex items-center justify-center text-xs font-bold ${
                  !isAccessible
                    ? 'bg-surface border border-border text-slate-400 dark:text-slate-600'
                    : isActive
                    ? 'bg-primary-600 text-white'
                    : st.isCompleted
                    ? 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-400'
                    : 'bg-surface border border-border text-slate-500 dark:text-slate-400'
                }`}
              >
                {!isAccessible ? (
                  <Lock className="w-3 h-3 text-slate-400 dark:text-slate-600" />
                ) : st.isCompleted && !isActive ? (
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
                    width:
                      (idx === 0 && isMapCompleted) || (idx === 1 && isParquetCompleted)
                        ? '100%'
                        : '0%',
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
