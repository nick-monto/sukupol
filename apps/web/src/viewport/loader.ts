import type { MapMetadata, ViewportTransition } from "../types";

type PixiViewportModule = typeof import("./render");

type MapRenderOptions = {
  stage: HTMLDivElement;
  fallback: HTMLPreElement;
  lines: string[];
  metadata: MapMetadata | null;
  transition: ViewportTransition;
  onTransitionComplete?: () => void;
};

let pixiViewportModule: PixiViewportModule | null = null;
let pixiViewportModulePromise: Promise<PixiViewportModule> | null = null;
const pendingPixiMapRenders = new WeakMap<HTMLDivElement, MapRenderOptions>();

function sanitizeMapGlyph(glyph: string): string { return glyph === "\t" ? " " : glyph; }
function sanitizeMapLines(lines: string[]): string[] { return lines.map((line) => Array.from(line, sanitizeMapGlyph).join("")); }

function renderMapWithPixi(options: MapRenderOptions, module: PixiViewportModule): void {
  const { stage } = options;
  stage.hidden = false;
  stage.dataset.rendererStatus = "pixi";
  module.renderPixiMap({
    container: stage, lines: options.lines, metadata: options.metadata,
    transition: options.transition, styles: getComputedStyle(stage),
    onTransitionComplete: () => { pendingPixiMapRenders.delete(stage); options.onTransitionComplete?.(); },
  });
}

function ensurePixiViewportModule(): Promise<PixiViewportModule> {
  if (pixiViewportModule) return Promise.resolve(pixiViewportModule);
  if (!pixiViewportModulePromise) {
    pixiViewportModulePromise = import("./render").then((module) => { pixiViewportModule = module; return module; });
  }
  return pixiViewportModulePromise;
}

function reportPixiError(stage: HTMLDivElement, error: unknown, context: string): void {
  const message = error instanceof Error && error.message ? error.message : "Unknown error loading Pixi.js renderer";
  delete stage.dataset.rendererStatus;
  console.error(`[pixi-viewport] ${context}:`, message, error);
}

export function renderMap(options: MapRenderOptions): void {
  const { stage, fallback, lines } = options;
  fallback.textContent = sanitizeMapLines(lines).join("\n");
  pendingPixiMapRenders.set(stage, options);
  if (pixiViewportModule) {
    try {
      renderMapWithPixi(options, pixiViewportModule);
    } catch (error) {
      reportPixiError(stage, error, "render");
    }
    return;
  }
  ensurePixiViewportModule()
    .then((module) => { const latest = pendingPixiMapRenders.get(stage); if (latest) renderMapWithPixi(latest, module); })
    .catch((error) => { options.onTransitionComplete?.(); reportPixiError(stage, error, "render"); });
}

export function hideMap(stage: HTMLDivElement): void {
  pendingPixiMapRenders.delete(stage);
  stage.hidden = true;
  delete stage.dataset.rendererStatus;
  if (pixiViewportModule) pixiViewportModule.teardownPixiMap(stage);
}
