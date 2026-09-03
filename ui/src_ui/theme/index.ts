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
// File: ui/src_ui/theme/index.ts
// Author: Gabriel Moraes
// Date: 2026-08-29

import tokensData from './tokens.json';

export type ThemeMode = 'dark' | 'light';

export interface DesignTokens {
  name: string;
  version: string;
  typography: {
    fontFamily: {
      sans: string[];
      mono: string[];
    };
  };
  palette: {
    primary: Record<string, string>;
    accents: Record<string, string>;
  };
  themes: {
    light: {
      name: string;
      colors: {
        bg: {
          background: string;
          surface: string;
          surfaceHover: string;
          surfaceElevated: string;
        };
        border: {
          default: string;
          subtle: string;
        };
        text: {
          primary: string;
          secondary: string;
          muted: string;
          subtle: string;
        };
        canvas: {
          background: string;
          roadDefault: string;
          roadActive: string;
          roadMonitored: string;
          roadSelected: string;
          node: string;
          nodeActive: string;
        };
        charts: {
          tooltipBg: string;
          tooltipBorder: string;
          tooltipText: string;
          axisLine: string;
          axisLabel: string;
          splitLine: string;
          yAxisLabel: string;
        };
      };
    };
    dark: {
      name: string;
      colors: {
        bg: {
          background: string;
          surface: string;
          surfaceHover: string;
          surfaceElevated: string;
        };
        border: {
          default: string;
          subtle: string;
        };
        text: {
          primary: string;
          secondary: string;
          muted: string;
          subtle: string;
        };
        canvas: {
          background: string;
          roadDefault: string;
          roadActive: string;
          roadMonitored: string;
          roadSelected: string;
          node: string;
          nodeActive: string;
        };
        charts: {
          tooltipBg: string;
          tooltipBorder: string;
          tooltipText: string;
          axisLine: string;
          axisLabel: string;
          splitLine: string;
          yAxisLabel: string;
        };
      };
    };
  };
}

export const themeTokens = tokensData as unknown as DesignTokens;

/**
 * Retrieves the theme token configuration for a specific mode ('dark' | 'light')
 */
export function getThemeTokens(mode: ThemeMode = 'dark') {
  return themeTokens.themes[mode] || themeTokens.themes.dark;
}

export default themeTokens;
