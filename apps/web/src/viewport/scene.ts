import type { MapCell, MapMetadata, MapTone } from "../types";
import type { ResolvedMapScene } from "./types";

export function mapSceneFromMetadata(metadata: MapMetadata): ResolvedMapScene {
  return {
    width: metadata.width,
    height: metadata.height,
    cells: metadata.cells,
  };
}

export function mapSceneFromLines(lines: string[]): ResolvedMapScene {
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

export function inferMapTone(glyph: string): MapTone {
  if (glyph === "#") {
    return "wall";
  }
  if (glyph === "<" || glyph === "∪" || glyph === "∩") {
    return "exit";
  }
  if (glyph === "^" || glyph === "v") {
    return "player";
  }
  if (/[A-Z]/.test(glyph)) {
    return "npc";
  }
  return "floor";
}

export function shouldHideMapGlyph(glyph: string, tone: MapTone): boolean {
  if (tone === "player" || tone === "npc" || tone === "exit" || tone === "wall") {
    return false;
  }

  return glyph === ".";
}
