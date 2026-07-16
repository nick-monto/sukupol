/** Procedural table generation — structural invariants on generated layouts */

import { describe, it, expect } from "vitest";
import { CABINET_SPECS, BIOME_CONFIGS } from "../src/pinball";
import { generatePinballTable } from "../src/pinball";
import { SAMPLE_DESCRIPTOR, descriptorForBiome, flattenPegs, dist } from "./helpers";
import { PEG } from "../src/pinball/geometry";
import { ORB_LABEL_ORDER, WEAPON_BUMPER_SHAPE } from "../src/pinballCombat/weapons";

describe("procedural table generation", () => {
	// ── Every biome produces a valid layout ────────────────────────────────
	for (const biomeId of Object.keys(BIOME_CONFIGS)) {
		it(`${biomeId} generates without throwing`, () => {
			expect(() => generatePinballTable(descriptorForBiome(biomeId))).not.toThrow();
		});
	}

	it("deterministic output for the same seed", () => {
		const a = generatePinballTable(SAMPLE_DESCRIPTOR);
		const b = generatePinballTable(SAMPLE_DESCRIPTOR);
		expect(a.obstacles.length).toBe(b.obstacles.length);
		for (let i = 0; i < a.obstacles.length; i++) {
			expect(a.obstacles[i].pegs).toEqual(b.obstacles[i].pegs);
		}
	});

	it("different seeds produce different layouts", () => {
		const a = generatePinballTable({ ...SAMPLE_DESCRIPTOR, floor_seed: 1 });
		const b = generatePinballTable({ ...SAMPLE_DESCRIPTOR, floor_seed: 999 });
		let diff = false;
		const maxLen = Math.max(a.obstacles.length, b.obstacles.length);
		for (let i = 0; i < maxLen && !diff; i++) {
			if (!a.obstacles[i] || !b.obstacles[i]) { diff = true; continue; }
			if (a.obstacles[i].pegs.length !== b.obstacles[i].pegs.length) { diff = true; continue; }
			for (const [pa, pb] of a.obstacles[i].pegs.map((p, j) => [p, b.obstacles[i].pegs[j]])) {
				if (pa.x !== pb.x || pa.y !== pb.y) diff = true;
			}
		}
		expect(diff).toBe(true);
		// Also confirm weakPoint position OR obstacle count differs
		const countDiff = a.obstacles.length !== b.obstacles.length;
		const wpDiff = a.weakPoint.x !== b.weakPoint.x || a.weakPoint.y !== b.weakPoint.y;
		expect(countDiff || wpDiff).toBe(true);
	});

	it("weak point exists and is within placement bounds", () => {
		const layout = generatePinballTable(SAMPLE_DESCRIPTOR);
		const pb = layout.cabinet.placementBounds;
		const wp = layout.weakPoint;
		expect(wp.x).toBeGreaterThanOrEqual(pb.x);
		expect(wp.x).toBeLessThanOrEqual(pb.x + pb.w);
		expect(wp.y).toBeGreaterThanOrEqual(pb.y);
		expect(wp.y).toBeLessThanOrEqual(pb.y + pb.h);
		expect(wp.radius).toBeGreaterThan(0);
	});

	it("all pegs are within placement bounds", () => {
		const layout = generatePinballTable(SAMPLE_DESCRIPTOR);
		const pb = layout.cabinet.placementBounds;
		const pegs = flattenPegs(layout);
		for (const p of pegs) {
			expect(p.x - p.radius).toBeGreaterThanOrEqual(pb.x);
			expect(p.x + p.radius).toBeLessThanOrEqual(pb.x + pb.w);
			expect(p.y - p.radius).toBeGreaterThanOrEqual(pb.y);
			expect(p.y + p.radius).toBeLessThanOrEqual(pb.y + pb.h);
		}
	});

	it("no peg overlaps another peg", () => {
		const layout = generatePinballTable(SAMPLE_DESCRIPTOR);
		const pegs = flattenPegs(layout);
		const minClearance = PEG.PEG_CLEARANCE;
		for (let i = 0; i < pegs.length; i++) {
			for (let j = i + 1; j < pegs.length; j++) {
				const a = pegs[i];
				const b = pegs[j];
				const d = dist(a.x, a.y, b.x, b.y);
				expect(d).toBeGreaterThanOrEqual(a.radius + b.radius + minClearance - 1); // -1 for rounding tolerance
			}
		}
	});

	it("no peg inside an exclusion zone", () => {
		const layout = generatePinballTable(SAMPLE_DESCRIPTOR);
		const pegs = flattenPegs(layout);
		for (const p of pegs) {
			for (const ez of layout.cabinet.exclusionZones) {
				const d = dist(p.x, p.y, ez.x, ez.y);
				expect(d).toBeGreaterThanOrEqual(ez.radius + p.radius);
			}
		}
	});

	it("weak point does not overlap any peg", () => {
		const layout = generatePinballTable(SAMPLE_DESCRIPTOR);
		const wp = layout.weakPoint;
		const minClearance = PEG.PEG_CLEARANCE;
		for (const p of flattenPegs(layout)) {
			const d = dist(wp.x, wp.y, p.x, p.y);
			expect(d).toBeGreaterThanOrEqual(wp.radius + p.radius + minClearance - 1);
		}
	});

	it("peg budget is respected", () => {
		const biomeId = SAMPLE_DESCRIPTOR.biome_id;
		const config = BIOME_CONFIGS[biomeId];
		const layout = generatePinballTable(SAMPLE_DESCRIPTOR);
		let used = 0;
		for (const o of layout.obstacles) {
			if (o.kind === "bumper") used += config.pegConfig.bumperCost;
			else if (o.kind === "post") used += config.pegConfig.postCost;
			else if (o.kind === "enemy") used += o.pegs.length * config.pegConfig.enemyPegCost;
		}
		expect(used).toBeLessThanOrEqual(config.pegConfig.pegBudget);
	});

	it("has at least some obstacles placed", () => {
		const layout = generatePinballTable(SAMPLE_DESCRIPTOR);
		expect(layout.obstacles.length).toBeGreaterThan(0);
	});

	it("traversability: every y-band has a passage gap", () => {
		const layout = generatePinballTable(SAMPLE_DESCRIPTOR);
		const pegs = flattenPegs(layout);
		const pb = layout.cabinet.placementBounds;
		const ballR = PEG.BALL_R;
		const minPassage = PEG.MIN_PASSAGE;
		const bandH = PEG.BAND_H;

		for (let bandY = pb.y + bandH / 2; bandY <= pb.y + pb.h; bandY += bandH) {
			const halfBand = bandH / 2;
			const pbRight = pb.x + pb.w;
			const intervals: [number, number][] = [];
			for (const p of pegs) {
				if (p.y + p.radius < bandY - halfBand) continue;
				if (p.y - p.radius > bandY + halfBand) continue;
				intervals.push([Math.max(pb.x, p.x - p.radius - ballR), Math.min(pbRight, p.x + p.radius + ballR)]);
			}
			intervals.sort((a, b) => a[0] - b[0]);

			// Merge
			const merged: [number, number][] = [];
			for (const iv of intervals) {
				const last = merged.at(-1);
				if (!last || iv[0] > last[1]) merged.push([...iv] as [number, number]);
				else last[1] = Math.max(last[1], iv[1]);
			}

			// Check gaps
			let cursor = pb.x;
			let hasGap = false;
			for (const [l, r] of merged) {
				if (l - cursor >= minPassage) { hasGap = true; break; }
				cursor = r;
			}
			if (!hasGap && pbRight - cursor >= minPassage) hasGap = true;
			expect(hasGap).toBe(true);
		}
	});

	it("all cabinet specs are reachable from biome configs", () => {
		const usedCabinets = new Set(Object.values(BIOME_CONFIGS).map((c) => c.cabinetId));
		for (const cid of usedCabinets) {
			expect(CABINET_SPECS[cid]).toBeDefined();
		}
	});

	it("across all biomes and weapon types, layout meets regression guards", () => {
		for (const biomeId of Object.keys(BIOME_CONFIGS)) {
			for (const weapon of Object.keys(WEAPON_BUMPER_SHAPE)) {
				const descriptor = {
					...descriptorForBiome(biomeId),
					enemy_pinball: {
						obstacles: [
							{
								id: "e1",
								label: "Lich",
								pegs: [{ angle: 0, distance: 0, radius: 14 }],
								scoreValue: 20,
							},
						],
					},
				};
				const layout = generatePinballTable(descriptor);
				const orbs = layout.obstacles.filter(
					(o) => o.kind === "bumper" && o.weaponLabel && ORB_LABEL_ORDER.includes(o.weaponLabel),
				);
			expect(orbs.length).toBe(3); // orbs canonical — every biome emits all 3
				const enemies = layout.obstacles.filter((o) => o.kind === "enemy");
				expect(enemies.length).toBeGreaterThanOrEqual(1);
				expect(layout.weakPoint.radius).toBeGreaterThan(0);
			}
		}
	});
});
