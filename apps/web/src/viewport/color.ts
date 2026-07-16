import { Graphics, utils } from "pixi.js";
import type { MapTone } from "../types";

export function mapToneColor(styles: CSSStyleDeclaration, tone: MapTone): string {
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

export function mapSurfaceColor(styles: CSSStyleDeclaration, tone: MapTone, variant?: string): string {
  if (tone === "exit") {
    return getCssVar(styles, "--map-exit-surface", "rgba(140, 195, 179, 0.18)");
  }
  if (tone === "decor") {
    return getCssVar(styles, "--map-decor-surface", "rgba(109, 165, 140, 0.16)");
  }
  switch (variant) {
    case "wet":
      return getCssVar(styles, "--map-floor-wet", "rgba(86, 128, 152, 0.14)");
    case "moss":
      return getCssVar(styles, "--map-floor-moss", "rgba(86, 118, 96, 0.15)");
    default:
      return getCssVar(styles, "--map-floor-surface", "rgba(157, 170, 176, 0.08)");
  }
}

export function mapAccentColor(styles: CSSStyleDeclaration, variant?: string): string {
  switch (variant) {
    case "moss":
      return getCssVar(styles, "--map-floor-moss-accent", "rgba(135, 178, 128, 0.38)");
    case "rubble":
      return getCssVar(styles, "--map-floor-rubble-accent", "rgba(198, 183, 152, 0.28)");
    case "wet":
      return getCssVar(styles, "--map-floor-wet-accent", "rgba(188, 218, 232, 0.28)");
    case "dust":
      return getCssVar(styles, "--map-floor-dust-accent", "rgba(214, 198, 156, 0.24)");
    default:
      return getCssVar(styles, "--map-floor-accent", "rgba(255, 255, 255, 0.08)");
  }
}

export function getCssVar(styles: CSSStyleDeclaration, name: string, fallback: string): string {
  return styles.getPropertyValue(name).trim() || fallback;
}

export function parseCssColor(value: string): { color: number; alpha: number } {
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
