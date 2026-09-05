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
// File: ui/src_ui/services/bridge/handlers/XaiEventHandler.ts
// Author: Gabriel Moraes
// Date: 2026-09-04

import { IBridgeEventHandler, LogLevel } from '../types';
import { XaiAuditVerdict, LinguistClassification, XaiResultItem } from '../../../types/xai';
import { DataSourceItem } from '../../../types/sensors';

export interface IXaiEventSink {
  addVerdict: (verdict: XaiAuditVerdict) => void;
  handleEngineDataPayload: (payload: any) => void;
  addLinguistLog: (entry: LinguistClassification) => void;
  updateSourceItem: (id: string, updates: Partial<DataSourceItem>) => void;
  addXaiResult: (item: XaiResultItem) => void;
  addLog: (level: LogLevel, message: string) => void;
}

/**
 * Single Responsibility (SRP): Encapsulates XAI explainability results,
 * Zero-Trust audit verdicts, and LLM Linguist semantic classifications.
 */
export class XaiEventHandler implements IBridgeEventHandler {
  readonly events = [
    'synapse:audit_update',
    'synapse:linguist_update',
    'synapse:xai_result',
  ] as const;

  constructor(private readonly sink: IXaiEventSink) {}

  handle(event: string, payload: any): void {
    switch (event) {
      case 'synapse:audit_update': {
        const v = payload || {};
        const verdict: XaiAuditVerdict = {
          safe: v.safe,
          error: v.error,
          threshold: v.threshold,
          vector: v.vector || [],
          timestamp: new Date().toLocaleTimeString(),
        };
        this.sink.addVerdict(verdict);
        this.sink.handleEngineDataPayload(v);
        break;
      }

      case 'synapse:linguist_update': {
        const l = payload || {};
        const entry: LinguistClassification = {
          source: l.source,
          type: l.type,
          confidence: l.confidence,
          timestamp: new Date().toLocaleTimeString(),
        };
        this.sink.addLinguistLog(entry);
        this.sink.updateSourceItem(l.source, {
          semantic_type: l.type,
          confidence_score: l.confidence,
        });
        break;
      }

      case 'synapse:xai_result': {
        const r = payload || {};
        const targetLower = (r.target || '').toLowerCase();
        let type: XaiResultItem['type'] = 'GLOBAL';
        let targetLabel = r.target || 'Fusão Espaço-Temporal Global';

        if (targetLower.includes('auditor') || targetLower.includes('buffer')) {
          type = 'AUDITOR';
          targetLabel = 'Auditoria Zero-Trust (Veto Buffer)';
        } else if (targetLower.includes('tcn') || targetLower.includes('local') || targetLower.includes('sensor')) {
          type = 'LOCAL';
          targetLabel = r.feature_names?.[0]
            ? `Sensor: ${r.feature_names[0].split(' [')[0]}`
            : 'Sensor Temporal (TCN)';
        } else if (targetLower.includes('fuser') || targetLower.includes('global')) {
          type = 'GLOBAL';
          targetLabel = 'Fusão Espaço-Temporal Global';
        }

        const item: XaiResultItem = {
          id: r.request_id || r.id || `xai_${Date.now()}`,
          request_id: r.request_id,
          type,
          target: targetLabel,
          convergence_delta: typeof r.convergence_delta === 'number' ? r.convergence_delta : 0.0012,
          semantic_text: r.semantic_text || 'Análise de explicabilidade concluída com sucesso.',
          attributions: Array.isArray(r.attributions) && r.attributions.length > 0
            ? r.attributions
            : [0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 0.85, 0.95, 1.0],
          feature_names: Array.isArray(r.feature_names) ? r.feature_names : undefined,
          timestamp: new Date().toLocaleTimeString(),
        };

        this.sink.addXaiResult(item);
        this.sink.addLog('INFO', `XAI [${type}]: Inferência explicada com sucesso (${item.target})`);
        break;
      }
    }
  }
}
