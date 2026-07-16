import type { ObstacleTemplate, PegDef, PinballDescriptor } from "../types";
import type { CabinetSpec } from "./cabinet";
import type { BiomePhysics, BiomeTheme } from "./biomes";

// ---------------------------------------------------------------------------
// Procgen output
// ---------------------------------------------------------------------------

export type BumperShape = "circle" | "square" | "triangle" | "pentagon";

/** A single peg — the atomic collision unit of an obstacle */
export interface PlacedPeg {
	id: string; // "{obstacleId}:peg{N}"
	parentId: string; // references ObstacleSpec.id
	x: number;
	y: number;
	radius: number;
}

export interface ObstacleSpec {
	id: string;
	kind: "bumper" | "post" | "enemy";
	parentId?: string; // if multi-peg obstacle, all pegs share this parent
	x: number; // center X of the obstacle (for rendering)
	y: number; // center Y
	pegs: PlacedPeg[]; // individual collision circles derived from PegDef template
	scoreValue: number;
	weaponLabel?: string;
}

export interface WeakPointSpec {
	x: number;
	y: number;
	radius: number;
}

export interface PinballTableLayout {
	cabinet: CabinetSpec;
	physics: BiomePhysics;
	theme: BiomeTheme;
	obstacles: ObstacleSpec[];
	weakPoint: WeakPointSpec;
}

// ---------------------------------------------------------------------------
// Helper: resolve enemy obstacles to ObstacleTemplate[]
// ---------------------------------------------------------------------------

export function resolveEnemyObstacles(
	enemyPinball: PinballDescriptor["enemy_pinball"],
): ObstacleTemplate[] {
	return enemyPinball?.obstacles ?? [];
}

// ---------------------------------------------------------------------------
// Helper: expand PegDef template into PlacedPeg positions at a given center
// ---------------------------------------------------------------------------

export function expandPegs(
	parentId: string,
	cx: number,
	y: number,
	templatePegs: PegDef[],
): PlacedPeg[] {
	return templatePegs.map((p, i) => ({
		id: `${parentId}:peg${i}`,
		parentId,
		x: Math.round(cx + p.distance * Math.cos(p.angle)),
		y: Math.round(y + p.distance * Math.sin(p.angle)),
		radius: p.radius,
	}));
}
