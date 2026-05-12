import type { MapMetadata, ViewportTransition } from "./types";

type PixiViewportModule = typeof import("./pixiViewport");

type MapRenderOptions = {
  stage: HTMLDivElement;
  fallback: HTMLPreElement;
  lines: string[];
  metadata: MapMetadata | null;
  transition: ViewportTransition;
};

let pixiViewportModule: PixiViewportModule | null = null;
let pixiViewportModulePromise: Promise<PixiViewportModule> | null = null;

const pendingPixiMapRenders = new WeakMap<HTMLDivElement, MapRenderOptions>();

export function renderMap(options: MapRenderOptions): void {
  const { stage, fallback, lines } = options;
  fallback.textContent = sanitizeMapLines(lines).join("\n");

  pendingPixiMapRenders.set(stage, options);
  if (pixiViewportModule) {
    renderMapWithPixi(options, pixiViewportModule);
    return;
  }

  void ensurePixiViewportModule()
    .then((module) => {
      const latest = pendingPixiMapRenders.get(stage);
      if (!latest) {
        return;
      }

      renderMapWithPixi(latest, module);
    })
    .catch((error) => {
      reportPixiError(stage, error, "map module load failed");
    });
}

export function hideMap(stage: HTMLDivElement): void {
  pendingPixiMapRenders.delete(stage);
  stage.hidden = true;
  delete stage.dataset.rendererStatus;
  delete stage.dataset.rendererMessage;

  if (pixiViewportModule) {
    pixiViewportModule.teardownPixiMap(stage);
  }
}

function renderMapWithPixi(options: MapRenderOptions, module: PixiViewportModule): void {
  const { stage } = options;
  stage.hidden = false;
  stage.dataset.rendererStatus = "pixi";
  delete stage.dataset.rendererMessage;

  try {
    module.renderPixiMap({
      container: stage,
      lines: options.lines,
      metadata: options.metadata,
      transition: options.transition,
      styles: getComputedStyle(stage),
    });
  } catch (error) {
    reportPixiError(stage, error, "map render failed");
  }
}

function ensurePixiViewportModule(): Promise<PixiViewportModule> {
  if (pixiViewportModule) {
    return Promise.resolve(pixiViewportModule);
  }

  if (!pixiViewportModulePromise) {
    pixiViewportModulePromise = import("./pixiViewport").then((module) => {
      pixiViewportModule = module;
      return module;
    });
  }

  return pixiViewportModulePromise;
}

function reportPixiError(
  stage: HTMLDivElement,
  error: unknown,
  context: string,
): void {
  stage.hidden = false;
  stage.dataset.rendererStatus = "error";
  stage.dataset.rendererMessage = buildRendererMessage(error);
  console.error(`Pixi ${context}.`, error);
}

function buildRendererMessage(error: unknown): string {
  if (isRendererAutodetectError(error)) {
    return "Map unavailable: this browser session could not create a WebGL renderer. Check hardware acceleration, GPU support, or browser graphics settings.";
  }

  return "Map unavailable: PixiJS failed to initialize in this browser session. See the console for the renderer error.";
}

function isRendererAutodetectError(error: unknown): boolean {
  return error instanceof Error && error.message.includes("Unable to auto-detect a suitable renderer");
}

function sanitizeMapLines(lines: string[]): string[] {
  return lines.map((line) => Array.from(line, sanitizeMapGlyph).join(""));
}

function sanitizeMapGlyph(glyph: string): string {
  if (glyph === "." || glyph === "," || glyph === ";") {
    return " ";
  }

  return glyph;
}
