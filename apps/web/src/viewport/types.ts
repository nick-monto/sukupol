import { Application, Container } from "pixi.js";
import type { MapCell, MapMetadata, ViewportTransition } from "../types";

export type PixiMapRenderOptions = {
  container: HTMLDivElement;
  lines: string[];
  metadata: MapMetadata | null;
  transition: ViewportTransition;
  styles: CSSStyleDeclaration;
  onTransitionComplete?: () => void;
};

export type MapRenderSnapshot = Omit<PixiMapRenderOptions, "styles">;

export type PixiMapInstance = {
  app: Application;
  handleWindowResize: () => void;
  lastRender: MapRenderSnapshot | null;
  stopAnimation?: (() => void) | undefined;
};

export type ResolvedMapScene = {
  width: number;
  height: number;
  cells: MapCell[];
};

export const mapInstances = new WeakMap<HTMLDivElement, PixiMapInstance>();
