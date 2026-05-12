import { Application, Container, Graphics, Text, TextStyle, utils } from "pixi.js";

import type { MapCell, MapMetadata, MapTone, ViewportTransition } from "./types";

type PixiMapRenderOptions = {
  container: HTMLDivElement;
  lines: string[];
  metadata: MapMetadata | null;
  transition: ViewportTransition;
  styles: CSSStyleDeclaration;
};

type MapRenderSnapshot = Omit<PixiMapRenderOptions, "styles">;

type PixiMapInstance = {
  app: Application;
  handleWindowResize: () => void;
  lastRender: MapRenderSnapshot | null;
  stopAnimation?: (() => void) | undefined;
};

type ResolvedMapScene = {
  width: number;
  height: number;
  cells: MapCell[];
};

const mapInstances = new WeakMap<HTMLDivElement, PixiMapInstance>();

export function renderPixiMap(options: PixiMapRenderOptions): void {
  const { container, lines, metadata, transition, styles } = options;
  const instance = getOrCreateMapInstance(container);
  instance.lastRender = {
    container,
    lines,
    metadata,
    transition,
  };
  drawPixiMap(instance, styles);
}

export function teardownPixiMap(container: HTMLDivElement): void {
  const instance = mapInstances.get(container);
  if (!instance) {
    return;
  }

  instance.stopAnimation?.();
  window.removeEventListener("resize", instance.handleWindowResize);
  instance.app.destroy(true, { children: true });
  container.replaceChildren();
  mapInstances.delete(container);
}

function drawPixiMap(instance: PixiMapInstance, styles: CSSStyleDeclaration): void {
  const { app, lastRender } = instance;
  if (!lastRender) {
    return;
  }

  const { container, lines, metadata, transition } = lastRender;
  const scene = metadata ? mapSceneFromMetadata(metadata) : mapSceneFromLines(lines);
  const bounds = container.getBoundingClientRect();
  const width = Math.max(1, Math.floor(container.clientWidth || bounds.width || 320));
  const height = resolveRenderHeight(container.clientHeight || bounds.height, width);

  app.renderer.resolution = window.devicePixelRatio || 1;
  app.renderer.resize(width, height);

  instance.stopAnimation?.();
  instance.stopAnimation = undefined;
  for (const child of app.stage.removeChildren()) {
    child.destroy();
  }

  const background = new Graphics();
  const bg = parseCssColor(getCssVar(styles, "--map-background-bottom", "#05080c"));
  background.beginFill(bg.color, bg.alpha);
  background.drawRect(0, 0, width, height);
  background.endFill();
  app.stage.addChild(background);

  const mapLayer = new Container();
  app.stage.addChild(mapLayer);

  const cellWidth = width / scene.width;
  const cellHeight = height / scene.height;
  const fontSize = Math.min(cellHeight * 0.92, cellWidth * 0.94);

  for (const cell of scene.cells) {
    if (shouldHideMapGlyph(cell.glyph, cell.tone)) {
      continue;
    }

    const text = new Text(cell.glyph, new TextStyle({
      fill: parseCssColor(mapToneColor(styles, cell.tone)).color,
      fontFamily: "IBM Plex Mono, monospace",
      fontSize,
      fontWeight: cell.tone === "player" ? "700" : "600",
    }));
    text.anchor.set(0.5);
    text.position.set((cell.x + 0.5) * cellWidth, (cell.y + 0.55) * cellHeight);
    if (cell.tone === "player") {
      text.name = "player-marker";
    }
    mapLayer.addChild(text);
  }

  const border = new Graphics();
  border.lineStyle(1, parseCssColor("rgba(255, 255, 255, 0.05)").color, 0.05, 0.5, true);
  border.drawRect(0.5, 0.5, width - 1, height - 1);
  app.stage.addChild(border);

  instance.stopAnimation = applyMapTransition(instance.app, mapLayer, transition);
}

function getOrCreateMapInstance(container: HTMLDivElement): PixiMapInstance {
  const existing = mapInstances.get(container);
  if (existing) {
    return existing;
  }

  const app = new Application({
    backgroundAlpha: 0,
    antialias: true,
    autoDensity: true,
    resolution: window.devicePixelRatio || 1,
  });
  app.view.classList.add("map-pixi-canvas");
  container.replaceChildren(app.view as HTMLCanvasElement);

  const handleWindowResize = () => {
    const styles = getComputedStyle(container);
    drawPixiMap(created, styles);
  };

  const created: PixiMapInstance = {
    app,
    handleWindowResize,
    lastRender: null,
  };
  window.addEventListener("resize", handleWindowResize);

  mapInstances.set(container, created);
  return created;
}

function resolveRenderHeight(boundsHeight: number, width: number): number {
  const fallbackHeight = width * (13 / 27);
  return Math.max(1, Math.floor(boundsHeight || fallbackHeight || 220));
}

function applyMapTransition(
  app: Application,
  layer: Container,
  transition: ViewportTransition,
): (() => void) | undefined {
  if (transition === "none") {
    return undefined;
  }

  const playerMarker = layer.getChildByName("player-marker") as Text | null;
  if (!playerMarker) {
    return undefined;
  }

  return animate(app, 180, (progress) => {
    const eased = easeOutCubic(progress);
    const scale = 1.28 - 0.28 * eased;
    playerMarker.scale.set(scale);
    playerMarker.alpha = 0.76 + 0.24 * eased;
  }, () => {
    playerMarker.scale.set(1);
    playerMarker.alpha = 1;
    layer.x = 0;
    layer.y = 0;
  });
}

function animate(
  app: Application,
  durationMs: number,
  onFrame: (progress: number) => void,
  onComplete: () => void,
): () => void {
  const startedAt = performance.now();
  let finished = false;

  const finish = () => {
    if (finished) {
      return;
    }

    finished = true;
    app.ticker.remove(tick);
    onComplete();
  };

  const tick = () => {
    const elapsed = performance.now() - startedAt;
    const progress = Math.min(1, elapsed / durationMs);
    onFrame(progress);
    if (progress >= 1) {
      finish();
    }
  };

  app.ticker.add(tick);
  return () => {
    finish();
  };
}

function easeOutCubic(progress: number): number {
  return 1 - (1 - progress) ** 3;
}

function mapToneColor(styles: CSSStyleDeclaration, tone: MapTone): string {
  switch (tone) {
    case "wall":
      return getCssVar(styles, "--map-wall", "#f7d391");
    case "decor":
      return getCssVar(styles, "--map-decor", "#6da58c");
    case "exit":
      return getCssVar(styles, "--map-exit", "#8cc3b3");
    case "player":
      return getCssVar(styles, "--map-player", "#fff4d2");
    case "npc":
      return getCssVar(styles, "--map-npc", "#ffb79c");
    default:
      return getCssVar(styles, "--map-floor", "#9daab0");
  }
}

function getCssVar(styles: CSSStyleDeclaration, name: string, fallback: string): string {
  return styles.getPropertyValue(name).trim() || fallback;
}

function parseCssColor(value: string): { color: number; alpha: number } {
  const normalized = value.trim();
  if (!normalized || normalized === "transparent") {
    return { color: 0x000000, alpha: 0 };
  }

  if (normalized.startsWith("#")) {
    return { color: utils.string2hex(normalized), alpha: 1 };
  }

  const match = normalized.match(/rgba?\(([^)]+)\)/i);
  if (!match) {
    return { color: utils.string2hex(normalized), alpha: 1 };
  }

  const [red, green, blue, alpha = "1"] = match[1].split(",").map((part) => part.trim());
  const color = (Number.parseInt(red, 10) << 16) + (Number.parseInt(green, 10) << 8) + Number.parseInt(blue, 10);
  return { color, alpha: Number.parseFloat(alpha) };
}

function mapSceneFromMetadata(metadata: MapMetadata): ResolvedMapScene {
  return {
    width: metadata.width,
    height: metadata.height,
    cells: metadata.cells,
  };
}

function mapSceneFromLines(lines: string[]): ResolvedMapScene {
  const width = Math.max(...lines.map((line) => line.length), 1);
  const height = Math.max(lines.length, 1);
  const cells: MapCell[] = [];

  lines.forEach((line, y) => {
    Array.from(line).forEach((glyph, x) => {
      cells.push({
        x,
        y,
        glyph,
        tone: inferMapTone(glyph),
      });
    });
  });

  return { width, height, cells };
}

function inferMapTone(glyph: string): MapTone {
  if (glyph === "#") {
    return "wall";
  }
  if (glyph === ">" || glyph === "<") {
    return "exit";
  }
  if (glyph === "," || glyph === ";") {
    return "decor";
  }
  if (glyph === "^" || glyph === "v") {
    return "player";
  }
  if (/[A-Z]/.test(glyph)) {
    return "npc";
  }
  return "floor";
}

function shouldHideMapGlyph(glyph: string, tone: MapTone): boolean {
  if (tone === "player" || tone === "npc" || tone === "exit" || tone === "wall") {
    return false;
  }

  return glyph === "." || glyph === "," || glyph === ";";
}