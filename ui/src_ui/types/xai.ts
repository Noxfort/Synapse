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
// File: ui/src_ui/types/xai.ts
// Author: Gabriel Moraes
// Date: 2026-08-29

export interface XaiAuditVerdict {
  safe: boolean;
  error: number;
  threshold: number;
  vector: number[];
  timestamp: string;
}

export interface LinguistClassification {
  source: string;
  type: string;
  confidence: number;
  timestamp: string;
}

export type XaiResultType = 'AUDITOR' | 'GLOBAL' | 'LOCAL';

export interface XaiResultItem {
  id: string;
  request_id?: string;
  type: XaiResultType;
  target: string;
  convergence_delta: number;
  semantic_text: string;
  attributions: number[];
  feature_names?: string[];
  timestamp: string;
}

export type XaiExplainMode = 'buffer' | 'global' | 'local';
