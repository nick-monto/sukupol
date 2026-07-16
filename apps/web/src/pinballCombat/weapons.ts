import type { BumperShape } from "../pinball";

// Weapon type → orb obstacle id (for 2× score bonus when weapon matches orb)
export const WEAPON_ORB: Record<string, string> = {
	sword: "orb-left",
	axe: "orb-left",
	staff: "orb-center",
	wand: "orb-center",
	bow: "orb-right",
	dagger: "orb-right",
};

// Weapon type → bumper shape + how many orbs (by ORB_LABEL_ORDER index) are reshaped
export const WEAPON_BUMPER_SHAPE: Record<
	string,
	{ shape: BumperShape; count: number }
> = {
	sword: { shape: "triangle", count: 2 },
	axe: { shape: "square", count: 3 },
	staff: { shape: "pentagon", count: 1 },
	wand: { shape: "pentagon", count: 2 },
	bow: { shape: "triangle", count: 1 },
	dagger: { shape: "square", count: 2 },
};

export const ORB_LABEL_ORDER = ["orb-center", "orb-left", "orb-right"];
