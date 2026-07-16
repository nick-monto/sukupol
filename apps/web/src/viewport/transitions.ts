import { Application, Container } from "pixi.js";
import type { ViewportTransition } from "../types";

function easeOutCubic(progress: number): number { return 1 - (1 - progress) ** 3; }

function resetPlayerMarker(playerMarker: { scale: { set: (s: number) => void }; alpha: number }, layer?: Container): void {
  playerMarker.scale.set(1);
  playerMarker.alpha = 1;
  if (layer) { layer.x = 0; layer.y = 0; }
}

export function animate(app: Application, durationMs: number, onFrame: (progress: number) => void, reset: () => void, onComplete?: () => void): () => void {
  const startedAt = performance.now();
  const finish = (completed: boolean) => { app.ticker.remove(tick); reset(); if (completed) onComplete?.(); };
  const tick = () => {
    const progress = Math.min(1, (performance.now() - startedAt) / durationMs);
    onFrame(progress);
    if (progress >= 1) finish(true);
  };
  app.ticker.add(tick);
  return () => finish(false);
}

function animateCombatEnter(app: Application, pm: { scale: { set: (s: number) => void }; alpha: number }): () => void {
  return animate(app, 220, (p) => { const e = easeOutCubic(p); pm.scale.set(1.34 - 0.34 * e); pm.alpha = 0.72 + 0.28 * e; }, () => resetPlayerMarker(pm));
}

function animateCombatImpact(app: Application, layer: Container, pm: { scale: { set: (s: number) => void }; alpha: number }): () => void {
  return animate(app, 150, (p) => { const osc = Math.sin(p * Math.PI * 4); const d = 1 - p; layer.x = osc * 5 * d; pm.alpha = 0.86 + 0.14 * p; pm.scale.set(1.06 - 0.06 * p); }, () => resetPlayerMarker(pm, layer));
}

function animateCombatExit(app: Application, layer: Container, pm: { scale: { set: (s: number) => void }; alpha: number }, onComplete?: () => void): () => void {
  return animate(app, 180, (p) => { const e = easeOutCubic(p); pm.alpha = 1 - 0.24 * e; pm.scale.set(1 - 0.08 * e); layer.y = -3 * e; }, () => resetPlayerMarker(pm, layer), onComplete);
}

function animateDefault(app: Application, pm: { scale: { set: (s: number) => void }; alpha: number }): () => void {
  return animate(app, 180, (p) => { const e = easeOutCubic(p); pm.alpha = 1 - 0.18 * (1 - e); pm.scale.set(1 - 0.06 * (1 - e)); }, () => resetPlayerMarker(pm));
}

export function applyMapTransition(app: Application, layer: Container, transition: ViewportTransition, onTransitionComplete?: () => void): (() => void) | undefined {
  if (transition === "none") return undefined;
  const playerMarker = layer.getChildByName("player-marker");
  if (!playerMarker) { onTransitionComplete?.(); return undefined; }
  if (transition === "combat-enter") return animateCombatEnter(app, playerMarker);
  if (transition === "combat-impact") return animateCombatImpact(app, layer, playerMarker);
  if (transition === "combat-exit") return animateCombatExit(app, layer, playerMarker, onTransitionComplete);
  return animateDefault(app, playerMarker);
}
