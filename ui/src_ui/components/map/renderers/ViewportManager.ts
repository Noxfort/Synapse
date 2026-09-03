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
// File: ui/src_ui/components/map/renderers/ViewportManager.ts
// Author: Gabriel Moraes
// Date: 2026-08-31

import { Point2D } from '../../../types/topology';

export class ViewportManager {
  /**
   * Configures canvas for high-DPI displays and clears the background.
   */
  public static prepareCanvas(
    canvas: HTMLCanvasElement,
    backgroundColor: string
  ): { ctx: CanvasRenderingContext2D; width: number; height: number } | null {
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    ctx.fillStyle = backgroundColor;
    ctx.fillRect(0, 0, rect.width, rect.height);

    return { ctx, width: rect.width, height: rect.height };
  }

  /**
   * Applies the SUMO Cartesian coordinate transformation (with inverted Y-axis).
   */
  public static applyTransform(ctx: CanvasRenderingContext2D, pan: Point2D, zoom: number): void {
    ctx.save();
    ctx.translate(pan.x, pan.y);
    ctx.scale(zoom, -zoom);
  }

  /**
   * Restores the canvas coordinate state.
   */
  public static restoreTransform(ctx: CanvasRenderingContext2D): void {
    ctx.restore();
  }
}
