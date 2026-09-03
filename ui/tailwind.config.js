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
// File: ui/tailwind.config.js
// Author: Gabriel Moraes
// Date: 2026-08-29

import tokens from './src_ui/theme/tokens.json';

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src_ui/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: tokens.typography?.fontFamily?.sans || ['Plus Jakarta Sans', 'sans-serif'],
        mono: tokens.typography?.fontFamily?.mono || ['JetBrains Mono', 'monospace'],
      },
      colors: {
        background: "var(--bg-background)",
        surface: "var(--bg-surface)",
        surfaceHover: "var(--bg-surface-hover)",
        surfaceElevated: "var(--bg-surface-elevated)",
        border: "var(--border-color)",
        borderSubtle: "var(--border-subtle)",
        // Semantic text tokens mapped to CSS custom properties
        textPrimary: "var(--text-primary)",
        textSecondary: "var(--text-secondary)",
        textMuted: "var(--text-muted)",
        textSubtle: "var(--text-subtle)",
        primary: tokens.palette.primary,
        accent: tokens.palette.accents,
      },
    },
  },
  plugins: [],
}
