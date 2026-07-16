import { Application } from "pixi.js";
import type { PixiMapInstance, PixiMapRenderOptions } from "./types";
import { mapInstances } from "./types";
import { drawPixiMap } from "./draw";

export function renderPixiMap(options: PixiMapRenderOptions): void {
  const { container, lines, metadata, transition, styles, onTransitionComplete } = options;
  const instance = getOrCreateMapInstance(container);
  instance.lastRender = { container, lines, metadata, transition, onTransitionComplete };
  drawPixiMap(instance, styles);
}

export function teardownPixiMap(container: HTMLDivElement): void {
  const instance = mapInstances.get(container);
  if (!instance) return;
  instance.stopAnimation?.();
  window.removeEventListener("resize", instance.handleWindowResize);
  instance.app.destroy(true, { children: true });
  container.replaceChildren();
  mapInstances.delete(container);
}

function createPixiApp(): Application {
  return new Application({
    backgroundAlpha: 0, antialias: true, autoDensity: true, resolution: window.devicePixelRatio || 1,
  });
}

function getOrCreateMapInstance(container: HTMLDivElement): PixiMapInstance {
  const existing = mapInstances.get(container);
  if (existing) return existing;
  const app = createPixiApp();
  const canvas = app.view as HTMLCanvasElement;
  canvas.classList.add("map-pixi-canvas");
  container.replaceChildren(canvas);
  const handleWindowResize = () => { drawPixiMap(created, getComputedStyle(container)); };
  const created: PixiMapInstance = { app, handleWindowResize, lastRender: null };
  window.addEventListener("resize", handleWindowResize);
  mapInstances.set(container, created);
  return created;
}

export function resolveRenderHeight(boundsHeight: number, width: number): number {
  return Math.max(1, Math.floor(boundsHeight || width * (13 / 27) || 220));
}
