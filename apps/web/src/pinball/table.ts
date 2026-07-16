import type { PinballDescriptor } from "../types";

import {
	PEG_CLEARANCE,
	hasPassage,
	hashStr,
	mulberry32,
} from "./geometry";
import { CABINET_SPECS } from "./cabinet";
import type { CabinetSpec } from "./cabinet";
import type { BiomePhysics, BiomeTheme } from "./biomes";
import { BIOME_CONFIGS, DEFAULT_BIOME } from "./biomes";
import {
	resolveEnemyObstacles,
	expandPegs,
} from "./types";
import type {
	PlacedPeg,
	ObstacleSpec,
	WeakPointSpec,
	PinballTableLayout,
} from "./types";

// ---------------------------------------------------------------------------
// generatePinballTable — seeded peg-budget obstacle procgen
// ---------------------------------------------------------------------------

export function generatePinballTable(
	descriptor: PinballDescriptor,
): PinballTableLayout {
	const biomeConfig = BIOME_CONFIGS[descriptor.biome_id] ?? DEFAULT_BIOME;
	const cabinet =
		CABINET_SPECS[biomeConfig.cabinetId] ?? CABINET_SPECS["standard"];
	const { physics, theme, pegConfig } = biomeConfig;
	const pb = cabinet.placementBounds;

	const seed =
		((descriptor.floor_seed ?? 0) ^ hashStr(descriptor.enemy_id ?? "")) >>> 0;
	const rng = mulberry32(seed);

	// ── State ───────────────────────────────────────────────────────────────
	const placed: ObstacleSpec[] = [];
	let budgetLeft = pegConfig.pegBudget;
	const pegList: PlacedPeg[] = [];

	// Check if a single peg collides with any existing peg (squared distance)
	function pegClearOf(x: number, y: number, r: number): boolean {
		for (const p of pegList) {
			const dx = p.x - x;
			const dy = p.y - y;
			if (dx * dx + dy * dy < (p.radius + r + PEG_CLEARANCE) * (p.radius + r + PEG_CLEARANCE))
				return false;
		}
		return true;
	}

	// Check if a peg is inside any exclusion zone (squared distance)
	function pegNotExcluded(x: number, y: number, r: number): boolean {
		for (const ez of cabinet.exclusionZones) {
			const dx = ez.x - x;
			const dy = ez.y - y;
			if (dx * dx + dy * dy < (ez.radius + r) * (ez.radius + r)) return false;
		}
		return true;
	}

	// Accept a pre-built obstacle spec — validates all its pegs at once
	function tryAccept(spec: ObstacleSpec, cost: number): boolean {
		if (cost > budgetLeft) return false;
		for (const p of spec.pegs) {
			if (p.x - p.radius < pb.x || p.x + p.radius > pb.x + pb.w) return false;
			if (p.y - p.radius < pb.y || p.y + p.radius > pb.y + pb.h) return false;
			if (!pegNotExcluded(p.x, p.y, p.radius)) return false;
			if (!pegClearOf(p.x, p.y, p.radius)) return false;
		}
		if (!hasPassage(pegList, spec.pegs, pb)) return false;
		placed.push(spec);
		pegList.push(...spec.pegs);
		budgetLeft -= cost;
		return true;
	}

	// ── 1. Weapon orbs — from cabinet.orbSlots, validated (cost: 0) ──────────
	const orbCount = cabinet.orbSlots.length;
	for (let oi = 0; oi < orbCount; oi++) {
		const slot = cabinet.orbSlots[oi];
		const fallbackX = Math.round(pb.x + (pb.w * (oi + 1)) / (orbCount + 1));
		const fallbackY = Math.round(pb.y + pb.h * (0.2 + 0.25 * oi));
		const orbSpec: ObstacleSpec = {
			id: slot.label,
			kind: "bumper",
			x: slot.x,
			y: slot.y,
			pegs: [
				{
					id: `${slot.label}:peg0`,
					parentId: slot.label,
					x: slot.x,
					y: slot.y,
					radius: slot.radius,
				},
			],
			scoreValue: 10,
			weaponLabel: slot.label,
		};
		if (!tryAccept(orbSpec, 0)) {
			// Relocate to a distinct interior fallback spread across the band so
			// co-failing orbs don't collide with each other.
			orbSpec.x = fallbackX;
			orbSpec.y = fallbackY;
			orbSpec.pegs[0].x = fallbackX;
			orbSpec.pegs[0].y = fallbackY;
			tryAccept(orbSpec, 0);
		}
	}

	// ── Helpers: generate and shuffle candidate positions ────────────────────
	const NUM_CANDIDATES = 72;
	const CANDIDATE_MARGIN = 35;

	function generateCandidates(): [number, number][] {
		const cands: [number, number][] = [];
		for (let i = 0; i < NUM_CANDIDATES; i++) {
			const cx = pb.x + CANDIDATE_MARGIN + rng() * (pb.w - CANDIDATE_MARGIN * 2);
			const cy = pb.y + CANDIDATE_MARGIN + rng() * (pb.h - CANDIDATE_MARGIN * 2);
			cands.push([cx, cy]);
		}
		for (let i = cands.length - 1; i > 0; i--) {
			const j = Math.floor(rng() * (i + 1));
			[cands[i], cands[j]] = [cands[j], cands[i]];
		}
		return cands;
	}

	let candidates = generateCandidates();
	let candidateIdx = 0;

	// Helper: try placing a single-peg obstacle at the next candidate position
	function tryPlaceSinglePeg(
		id: string,
		kind: "bumper" | "post",
		radius: number,
		scoreValue: number,
		weaponLabel?: string,
	): boolean {
		while (candidateIdx < candidates.length) {
			const [cx, cy] = candidates[candidateIdx++];
			return tryAccept(
				{
					id,
					kind,
					x: Math.round(cx),
					y: Math.round(cy),
					pegs: [
						{
							id: `${id}:peg0`,
							parentId: id,
							x: Math.round(cx),
							y: Math.round(cy),
							radius,
						},
					],
					scoreValue,
					weaponLabel,
				},
				kind === "bumper" ? pegConfig.bumperCost : pegConfig.postCost,
			);
		}
		return false;
	}

	// ── 2. Enemy obstacles (cost: number of pegs × enemyPegCost each) ──────
	const enemyObs = resolveEnemyObstacles(descriptor.enemy_pinball);
	let enemyPlaced = 0;
	let enemyRegenCount = 0;
	for (const template of enemyObs) {
		if (enemyPlaced >= 2) break;
		const cost = template.pegs.length * pegConfig.enemyPegCost;
		if (cost > budgetLeft) continue;

		let placedEnemy = false;
		// Bounded regeneration: at most 2 fresh candidate batches across the enemy loop
		while (true) {
			// Try each remaining candidate with jitter
			while (!placedEnemy && candidateIdx < candidates.length) {
				const [cx, cy] = candidates[candidateIdx++];
				const jx = Math.round((rng() - 0.5) * 30);
				const jy = Math.round((rng() - 0.5) * 30);
				const px = Math.round(cx + jx);
				const py = Math.round(cy + jy);
				const pegs = expandPegs(template.id, px, py, template.pegs);

				placedEnemy = tryAccept(
					{
						id: `enemy-${template.id}-${enemyPlaced}`,
						kind: "enemy",
						parentId: template.id,
						x: px,
						y: py,
						pegs,
						scoreValue: template.scoreValue ?? 15,
					},
					cost,
				);
			}
			if (placedEnemy) break;
			// Not placed — regenerate candidates if retries remain
			if (enemyRegenCount >= 2) break;
			enemyRegenCount++;
			candidates = generateCandidates();
			candidateIdx = 0;
		}
		if (placedEnemy) enemyPlaced++;
	}

	// ── 3. Bonus bumpers (cost: bumperCost each) ───────────────────────────
	for (let i = 0; i < pegConfig.bonusBumpers; i++) {
		tryPlaceSinglePeg(`bumper-bonus-${i}`, "bumper", 26, 12);
	}

	// ── 4. Posts — fill remaining budget (cost: postCost each) ─────────────
	const postRadiusRange = [9, 14];
	while (budgetLeft >= pegConfig.postCost) {
		const r =
			postRadiusRange[0] +
			Math.floor(rng() * (postRadiusRange[1] - postRadiusRange[0] + 1));
		if (
			!tryPlaceSinglePeg(
				`post-${placed.filter((o) => o.kind === "post").length}`,
				"post",
				r,
				3,
			)
		) {
			break; // no more candidates fit
		}
	}

	// ── 5. Weak-point — lower-centre of placement bounds ──────────────────
	const wpXMin = pb.x + pb.w * 0.2;
	const wpXMax = pb.x + pb.w * 0.8;
	const wpYMin = pb.y + pb.h * 0.55;
	const wpYMax = pb.y + pb.h * 0.9;
	const WP_RADIUS = 18;

	let weakPoint: WeakPointSpec = {
		x: Math.round(pb.x + pb.w * 0.5),
		y: Math.round(pb.y + pb.h * 0.72),
		radius: WP_RADIUS,
	};

	for (let attempt = 0; attempt < 30; attempt++) {
		const wx = Math.round(wpXMin + rng() * (wpXMax - wpXMin));
		const wy = Math.round(wpYMin + rng() * (wpYMax - wpYMin));

		let tooClose = false;
		for (const p of pegList) {
			const dx = p.x - wx,
				dy = p.y - wy;
			if (dx * dx + dy * dy < (p.radius + WP_RADIUS + PEG_CLEARANCE) * (p.radius + WP_RADIUS + PEG_CLEARANCE)) {
				tooClose = true;
				break;
			}
		}
		let inExclusion = false;
		for (const ez of cabinet.exclusionZones) {
			const dx = ez.x - wx,
				dy = ez.y - wy;
			if (dx * dx + dy * dy < (ez.radius + WP_RADIUS) * (ez.radius + WP_RADIUS)) {
				inExclusion = true;
				break;
			}
		}
		if (!tooClose && !inExclusion) {
			weakPoint = { x: wx, y: wy, radius: WP_RADIUS };
			break;
		}
	}

	return { cabinet, physics, theme, obstacles: placed, weakPoint };
}
