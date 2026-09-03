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
// File: ui/src_ui/utils/geometry.ts
// Author: Gabriel Moraes
// Date: 2026-08-29

import { Point2D, BoundingBox, MapNodeData } from '../types/topology';

/**
 * Calculates Euclidean distance from point p to line segment (v, w).
 */
export function distToSegment(p: Point2D, v: Point2D, w: Point2D): number {
  const l2 = (v.x - w.x) ** 2 + (v.y - w.y) ** 2;
  if (l2 === 0) return Math.hypot(p.x - v.x, p.y - v.y);
  let t = ((p.x - v.x) * (w.x - v.x) + (p.y - v.y) * (w.y - v.y)) / l2;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(p.x - (v.x + t * (w.x - v.x)), p.y - (v.y + t * (w.y - v.y)));
}

/**
 * Calculates the shortest distance from point p to any segment in a polyline.
 */
export function distToPolyline(p: Point2D, points: number[][]): number {
  if (!points || points.length === 0) return Infinity;
  if (points.length === 1) return Math.hypot(p.x - points[0][0], p.y - points[0][1]);

  let minDist = Infinity;
  for (let i = 0; i < points.length - 1; i++) {
    const v: Point2D = { x: points[i][0], y: points[i][1] };
    const w: Point2D = { x: points[i + 1][0], y: points[i + 1][1] };
    const d = distToSegment(p, v, w);
    if (d < minDist) {
      minDist = d;
    }
  }
  return minDist;
}


/**
 * Calculates the bounding box of a collection of 2D nodes.
 */
export function calculateBoundingBox(nodes: MapNodeData[]): BoundingBox {
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;

  for (const n of nodes) {
    if (n.x < minX) minX = n.x;
    if (n.x > maxX) maxX = n.x;
    if (n.y < minY) minY = n.y;
    if (n.y > maxY) maxY = n.y;
  }

  return {
    minX: minX === Infinity ? 0 : minX,
    maxX: maxX === -Infinity ? 100 : maxX,
    minY: minY === Infinity ? 0 : minY,
    maxY: maxY === -Infinity ? 100 : maxY,
  };
}

/**
 * Calculates initial zoom and pan parameters to center and fit the map within viewport.
 */
export function calculateFitTransform(
  box: BoundingBox,
  viewportWidth: number,
  viewportHeight: number
): { zoom: number; pan: Point2D } {
  const rangeX = box.maxX - box.minX || 100;
  const rangeY = box.maxY - box.minY || 100;

  const scaleX = (viewportWidth * 0.8) / rangeX;
  const scaleY = (viewportHeight * 0.8) / rangeY;
  const initialZoom = Math.min(scaleX, scaleY, 5);

  const centerX = (box.minX + box.maxX) / 2;
  const centerY = (box.minY + box.maxY) / 2;

  return {
    zoom: initialZoom,
    pan: {
      x: viewportWidth / 2 - centerX * initialZoom,
      y: viewportHeight / 2 + centerY * initialZoom, // Invert SUMO Y axis
    },
  };
}

/**
 * Converts screen coordinates to SUMO Cartesian coordinates.
 */
export function screenToSumoCoords(screenPos: Point2D, pan: Point2D, zoom: number): Point2D {
  return {
    x: (screenPos.x - pan.x) / zoom,
    y: -(screenPos.y - pan.y) / zoom,
  };
}

/**
 * Samples a point at normalized fraction t (0 <= t <= 1) along a polyline.
 */
export function samplePolyline(points: number[][], t: number): [number, number] {
  if (!points || points.length === 0) return [0, 0];
  if (points.length === 1 || t <= 0) return [points[0][0], points[0][1]];
  if (t >= 1) return [points[points.length - 1][0], points[points.length - 1][1]];

  let totalLength = 0;
  const segLengths: number[] = [];
  for (let i = 0; i < points.length - 1; i++) {
    const len = Math.hypot(points[i + 1][0] - points[i][0], points[i + 1][1] - points[i][1]);
    segLengths.push(len);
    totalLength += len;
  }

  if (totalLength === 0) return [points[0][0], points[0][1]];

  const targetDist = t * totalLength;
  let accumulated = 0;

  for (let i = 0; i < segLengths.length; i++) {
    const nextAcc = accumulated + segLengths[i];
    if (targetDist <= nextAcc || i === segLengths.length - 1) {
      const segFraction = segLengths[i] > 0 ? (targetDist - accumulated) / segLengths[i] : 0;
      const x = points[i][0] + segFraction * (points[i + 1][0] - points[i][0]);
      const y = points[i][1] + segFraction * (points[i + 1][1] - points[i][1]);
      return [x, y];
    }
    accumulated = nextAcc;
  }

  return [points[points.length - 1][0], points[points.length - 1][1]];
}

/**
 * Computes the exact centerline polyline between two opposing lane polylines,
 * perfectly averaging bends and curves.
 */
export function computeCenterline(
  shapeA: number[][],
  shapeB: number[][],
  samples: number = 10
): number[][] {
  if (!shapeA || shapeA.length === 0) return shapeB || [];
  if (!shapeB || shapeB.length === 0) return shapeA;

  // shapeB runs in the opposite direction (from toNode to fromNode), so we reverse it
  const reversedB = [...shapeB].reverse();

  if (shapeA.length === 2 && reversedB.length === 2) {
    return [
      [(shapeA[0][0] + reversedB[0][0]) / 2, (shapeA[0][1] + reversedB[0][1]) / 2],
      [(shapeA[1][0] + reversedB[1][0]) / 2, (shapeA[1][1] + reversedB[1][1]) / 2],
    ];
  }

  const sampleCount = Math.max(samples, Math.max(shapeA.length, reversedB.length));
  const result: number[][] = [];

  for (let i = 0; i <= sampleCount; i++) {
    const t = i / sampleCount;
    const ptA = samplePolyline(shapeA, t);
    const ptB = samplePolyline(reversedB, t);
    result.push([(ptA[0] + ptB[0]) / 2, (ptA[1] + ptB[1]) / 2]);
  }

  return result;
}
