import { Container, Graphics, Text, TextStyle } from "pixi.js";
import type { PixiMapInstance, ResolvedMapScene } from "./types";
import { drawFloorSurfaces } from "./surfaces";
import { mapToneColor, parseCssColor, getCssVar } from "./color";
import { applyMapTransition } from "./transitions";
import { mapSceneFromMetadata, mapSceneFromLines, shouldHideMapGlyph } from "./scene";
import { resolveRenderHeight } from "./render";
import type { MapCell } from "../types";

function renderMapBg(app: { stage: Container }, w: number, h: number, s: CSSStyleDeclaration): void {
  const bg = new Graphics();
  const c = parseCssColor(getCssVar(s, "--map-background-bottom", "#05080c"));
  bg.beginFill(c.color, c.alpha); bg.drawRect(0, 0, w, h); bg.endFill();
  app.stage.addChild(bg);
}

function renderMapGlyphs(mp: Container, cells: MapCell[], cw: number, ch: number, fs: number, s: CSSStyleDeclaration): void {
  for (const cell of cells) {
    if (shouldHideMapGlyph(cell.glyph, cell.tone)) continue;
    const t = new Text(cell.glyph, new TextStyle({ fill: parseCssColor(mapToneColor(s, cell.tone)).color, fontFamily: "IBM Plex Mono, monospace", fontSize: fs, fontWeight: cell.tone === "player" ? "700" : "600" }));
    t.anchor.set(0.5); t.position.set((cell.x + 0.5) * cw, (cell.y + 0.55) * ch);
    if (cell.tone === "player") t.name = "player-marker";
    mp.addChild(t);
  }
}

function renderMapBorder(app: { stage: Container }, w: number, h: number): void {
  const b = new Graphics();
  b.lineStyle(1, parseCssColor("rgba(255, 255, 255, 0.05)").color, 0.05, 0.5, true);
  b.drawRect(0.5, 0.5, w - 1, h - 1);
  app.stage.addChild(b);
}

function clearStage(app: { stage: Container }, inst: PixiMapInstance): void {
  inst.stopAnimation?.();
  inst.stopAnimation = undefined;
  for (const child of app.stage.removeChildren()) child.destroy();
}

export function drawPixiMap(instance: PixiMapInstance, styles: CSSStyleDeclaration): void {
  const { app, lastRender } = instance;
  if (!lastRender) return;
  const { container, lines, metadata, transition, onTransitionComplete } = lastRender;
  const scene: ResolvedMapScene = metadata ? mapSceneFromMetadata(metadata) : mapSceneFromLines(lines);
  const bounds = container.getBoundingClientRect();
  const w = Math.max(1, Math.floor(container.clientWidth || bounds.width || 320));
  const h = resolveRenderHeight(container.clientHeight || bounds.height, w);
  app.renderer.resolution = window.devicePixelRatio || 1;
  app.renderer.resize(w, h);
  clearStage(app, instance);
  renderMapBg(app, w, h, styles);
  const cw = w / scene.width, ch = h / scene.height, fs = Math.min(ch * 0.92, cw * 0.94);
  const floorLayer = new Container(); app.stage.addChild(floorLayer);
  drawFloorSurfaces(floorLayer, scene.cells, cw, ch, styles);
  const mapLayer = new Container(); app.stage.addChild(mapLayer);
  renderMapGlyphs(mapLayer, scene.cells, cw, ch, fs, styles);
  renderMapBorder(app, w, h);
  instance.stopAnimation = applyMapTransition(app, mapLayer, transition, onTransitionComplete);
}
