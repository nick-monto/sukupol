import { Container, Graphics } from "pixi.js";
import type { MapCell } from "../types";
import { mapSurfaceColor, mapAccentColor, parseCssColor } from "./color";

function drawMossAccent(surface: Graphics, accent: { color: number; alpha: number }, cx: number, cy: number, cw: number, ch: number): void {
  surface.beginFill(accent.color, accent.alpha);
  surface.drawCircle(cx - cw * 0.12, cy + ch * 0.08, Math.min(cw, ch) * 0.12);
  surface.drawCircle(cx + cw * 0.1, cy - ch * 0.04, Math.min(cw, ch) * 0.08);
  surface.endFill();
}

function drawRubbleAccent(surface: Graphics, accent: { color: number; alpha: number }, cx: number, cy: number, cw: number, ch: number): void {
  surface.beginFill(accent.color, accent.alpha);
  surface.drawRect(cx - cw * 0.16, cy - ch * 0.08, cw * 0.12, ch * 0.12);
  surface.drawRect(cx + cw * 0.02, cy + ch * 0.02, cw * 0.1, ch * 0.1);
  surface.endFill();
}

function drawWetAccent(surface: Graphics, accent: { color: number; alpha: number }, cx: number, cy: number, cw: number, ch: number): void {
  surface.lineStyle(Math.max(1, Math.min(cw, ch) * 0.04), accent.color, accent.alpha, 0.5, true);
  surface.moveTo(cx - cw * 0.18, cy + ch * 0.12);
  surface.lineTo(cx + cw * 0.16, cy - ch * 0.1);
}

function drawDustAccent(surface: Graphics, accent: { color: number; alpha: number }, cx: number, cy: number, cw: number, ch: number): void {
  surface.beginFill(accent.color, accent.alpha);
  surface.drawCircle(cx - cw * 0.1, cy - ch * 0.04, Math.min(cw, ch) * 0.05);
  surface.drawCircle(cx + cw * 0.08, cy + ch * 0.1, Math.min(cw, ch) * 0.04);
  surface.endFill();
}

function drawFloorCellSurface(layer: Container, cell: MapCell, cellWidth: number, cellHeight: number, styles: CSSStyleDeclaration): void {
  if (cell.tone !== "floor" && cell.tone !== "decor" && cell.tone !== "exit") return;
  const surface = new Graphics();
  const toneColor = parseCssColor(mapSurfaceColor(styles, cell.tone, cell.variant));
  const insetX = cellWidth * 0.14;
  const insetY = cellHeight * 0.18;
  const baseX = cell.x * cellWidth;
  const baseY = cell.y * cellHeight;
  surface.beginFill(toneColor.color, toneColor.alpha);
  surface.drawRoundedRect(baseX + insetX, baseY + insetY, Math.max(1, cellWidth - insetX * 2), Math.max(1, cellHeight - insetY * 2), Math.min(cellWidth, cellHeight) * 0.12);
  surface.endFill();
  drawFloorAccent(surface, cell, cellWidth, cellHeight, styles);
  layer.addChild(surface);
}

export function drawFloorSurfaces(layer: Container, cells: MapCell[], cellWidth: number, cellHeight: number, styles: CSSStyleDeclaration): void {
  for (const cell of cells) drawFloorCellSurface(layer, cell, cellWidth, cellHeight, styles);
}

export function drawFloorAccent(surface: Graphics, cell: MapCell, cellWidth: number, cellHeight: number, styles: CSSStyleDeclaration): void {
  const accent = parseCssColor(mapAccentColor(styles, cell.variant));
  const cx = (cell.x + 0.5) * cellWidth;
  const cy = (cell.y + 0.5) * cellHeight;
  switch (cell.variant) {
    case "moss": drawMossAccent(surface, accent, cx, cy, cellWidth, cellHeight); return;
    case "rubble": drawRubbleAccent(surface, accent, cx, cy, cellWidth, cellHeight); return;
    case "wet": drawWetAccent(surface, accent, cx, cy, cellWidth, cellHeight); return;
    case "dust": drawDustAccent(surface, accent, cx, cy, cellWidth, cellHeight); return;
    default: return;
  }
}
