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
// File: ui/src_ui/components/common/LatexRenderer.tsx
// Author: Gabriel Moraes
// Date: 2026-09-01

import React, { useMemo } from 'react';
import katex from 'katex';

interface LatexRendererProps {
  math: string;
  displayMode?: boolean;
  className?: string;
}

/**
 * Reusable LaTeX mathematical renderer leveraging KaTeX.
 * Handles display equations (block) and inline formulas cleanly for HTML and PDF rendering.
 */
export const LatexRenderer: React.FC<LatexRendererProps> = ({
  math,
  displayMode = true,
  className = '',
}) => {
  const html = useMemo(() => {
    try {
      return katex.renderToString(math, {
        displayMode,
        throwOnError: false,
        output: 'html', // Output pure HTML to avoid MathML artifacts in html2canvas
        strict: false,
      });
    } catch (e) {
      console.error('KaTeX rendering error:', e);
      return math;
    }
  }, [math, displayMode]);

  return (
    <span
      className={`katex-renderer select-none ${className}`}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
};
