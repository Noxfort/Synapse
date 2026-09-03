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
// File: ui/src_ui/types/sensors.ts
// Author: Gabriel Moraes
// Date: 2026-08-29

export type SourceStatusType = 
  | 'Active' 
  | 'Quarantine' 
  | 'Validating' 
  | 'Rejected' 
  | 'Fallback' 
  | 'Offline';

export interface BaseDataSource {
  id: string;
  name: string;
  status: SourceStatusType;
  quality?: number;
  semantic_type?: string;
  confidence_score?: number;
  latest_value?: number | string | null;
  quarantine_count?: number;
  associated_element?: string;
  source_type?: string;
  connection_string?: string;
}

export interface LocalSensorSource extends BaseDataSource {
  is_local: true;
  lat?: number;
  lon?: number;
}

export interface GlobalApiSource extends BaseDataSource {
  is_local: false;
  endpoint_url?: string;
}

export type DataSourceItem = LocalSensorSource | GlobalApiSource;

export interface TelemetryPoint {
  time: string;
  value: number;
}

export interface EngineDataPayload {
  timestamp?: number;
  cycle?: number;
  active_sensors_count?: number;
  mean_speed?: number;
  mean_occupancy?: number;
  loss?: number;
  losses?: Record<string, number>;
  drift?: number;
  drift_scores?: Record<string, number>;
  qualities?: Record<string, number>;
  edge_data?: Record<string, { speed: number; occupancy: number; density?: number; queue?: number }>;
  sensor_snapshot?: Record<string, any>;
  source_values?: Record<string, number>;
}
