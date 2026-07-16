/** Shared fixtures for pinball tests */

import type { PinballDescriptor } from "../src/types";

export const SAMPLE_DESCRIPTOR: PinballDescriptor = {
	biome_id: "ashen_fields",
	floor_seed: 42,
	enemy_id: "test_enemy",
	enemy_pinball: { obstacles: [] },
};

export function descriptorForBiome(biomeId: string): PinballDescriptor {
	return { ...SAMPLE_DESCRIPTOR, biome_id: biomeId };
}

// ---------------------------------------------------------------------------

import type { PlacedPeg } from "../src/pinball";
import type { generatePinballTable } from "../src/pinball";

/** All pegs across all obstacles */
export function flattenPegs(layout: ReturnType<typeof generatePinballTable>): PlacedPeg[] {
	const out: PlacedPeg[] = [];
	for (const o of layout.obstacles) out.push(...o.pegs);
	return out;
}

/** Distance between two points */
export function dist(ax: number, ay: number, bx: number, by: number) {
	const dx = ax - bx;
	const dy = ay - by;
	return Math.sqrt(dx * dx + dy * dy);
}
