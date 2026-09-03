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
// File: ui/src_ui/types/system.ts
// Author: Gabriel Moraes
// Date: 2026-08-29

export type SystemPhase = 
  | 'IDLE_OPTIMIZATION'
  | 'RUNNING_OPTIMIZATION'
  | 'IDLE_OFFLINE'
  | 'RUNNING_OFFLINE'
  | 'IDLE_ONLINE'
  | 'RUNNING_ONLINE';

export type LogLevel = 'INFO' | 'WARN' | 'ERROR' | 'SYSTEM';

export interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  message: string;
}

export interface DatabaseConfig {
  host: string;
  port: number;
  dbname: string;
  schema?: string;
  user: string;
  password: string;
}

export interface DatabaseStatus {
  connected: boolean;
  message: string;
  checking: boolean;
}

export interface MonitorConfig {
  ip: string;
  host?: string;
  port?: number;
  connected?: boolean;
}

export interface MonitorStatus {
  connected: boolean;
  ip: string;
  host: string;
  port: number;
  message?: string;
}
