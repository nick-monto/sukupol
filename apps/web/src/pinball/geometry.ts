import type { CabinetSpec } from "./cabinet";
import type { ObstacleSpec, PlacedPeg } from "./types";

// ---------------------------------------------------------------------------
// Seeded PRNG (mulberry32)
// ---------------------------------------------------------------------------

function hashStr(s: string): number {
	let h = 0x9e3779b9;
	for (let i = 0; i < s.length; i++) {
		h = Math.imul(h ^ s.charCodeAt(i), 0x9e3779b1) >>> 0;
	}
	return h >>> 0;
}

function mulberry32(seed: number): () => number {
	let s = seed >>> 0;
	return (): number => {
		s |= 0;
		s = (s + 0x6d2b79f5) | 0;
		let t = Math.imul(s ^ (s >>> 15), 1 | s);
		t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const BALL_R = 14;
const MIN_PASSAGE = BALL_R * 3; // 42 px — minimum clear gap in any y-band
const PEG_CLEARANCE = BALL_R * 2.5; // 35 px — extra gap between peg edges
const BAND_H = BALL_R * 4; // 56 px — height of each y-band
export const PEG = { BALL_R: 14, MIN_PASSAGE: 42, PEG_CLEARANCE: 35, BAND_H: 56 } as const;

export { PEG_CLEARANCE, hashStr, mulberry32, BALL_R, MIN_PASSAGE, BAND_H };

// ---------------------------------------------------------------------------
// Traversability — peg-aware interval merging per y-band
// ---------------------------------------------------------------------------

/** Collects all placed peg circles into a flat array */
export function flattenPegs(obstacles: ObstacleSpec[]): PlacedPeg[] {
	const out: PlacedPeg[] = [];
	for (const o of obstacles) {
		out.push(...o.pegs);
	}
	return out;
}

/**
 * Returns true if the horizontal band centred at `bandY` still has at least
 * one gap ≥ MIN_PASSAGE, given all placed peg circles.
 */
export function bandHasPassage(
	pegsA: PlacedPeg[],
	pegsB: PlacedPeg[],
	bandY: number,
	pb: CabinetSpec["placementBounds"],
): boolean {
	const halfBand = BAND_H / 2;
	const pbRight = pb.x + pb.w;

	const intervals: [number, number][] = [];
	for (const p of pegsA) {
		if (p.y + p.radius < bandY - halfBand) continue;
		if (p.y - p.radius > bandY + halfBand) continue;
		const left = Math.max(pb.x, p.x - p.radius - BALL_R);
		const right = Math.min(pbRight, p.x + p.radius + BALL_R);
		if (right > left) intervals.push([left, right]);
	}
	for (const p of pegsB) {
		if (p.y + p.radius < bandY - halfBand) continue;
		if (p.y - p.radius > bandY + halfBand) continue;
		const left = Math.max(pb.x, p.x - p.radius - BALL_R);
		const right = Math.min(pbRight, p.x + p.radius + BALL_R);
		if (right > left) intervals.push([left, right]);
	}

	if (!intervals.length) return true;

	intervals.sort((a, b) => a[0] - b[0]);
	const merged: [number, number][] = [];
	for (const iv of intervals) {
		const last = merged.at(-1);
		if (!last || iv[0] > last[1]) {
			merged.push([...iv] as [number, number]);
		} else {
			last[1] = Math.max(last[1], iv[1]);
		}
	}

	let cursor = pb.x;
	for (const [l, r] of merged) {
		if (l - cursor >= MIN_PASSAGE) return true;
		cursor = r;
	}
	return pbRight - cursor >= MIN_PASSAGE;
}

/**
 * Returns true if adding `candidatePegs` to existing pegs still leaves a
 * traversable passage in every y-band any candidate peg overlaps.
 */
export function hasPassage(
	existingPegs: PlacedPeg[],
	candidatePegs: PlacedPeg[],
	pb: CabinetSpec["placementBounds"],
): boolean {
	let minY = Infinity;
	let maxY = -Infinity;
	for (const p of candidatePegs) {
		minY = Math.min(minY, p.y - p.radius);
		maxY = Math.max(maxY, p.y + p.radius);
	}
	const firstBand =
		Math.floor((minY - pb.y) / BAND_H) * BAND_H + pb.y + BAND_H / 2;
	const lastBand =
		Math.floor((maxY - pb.y) / BAND_H) * BAND_H + pb.y + BAND_H / 2;
	for (let bandY = firstBand; bandY <= lastBand + 1; bandY += BAND_H) {
		if (!bandHasPassage(existingPegs, candidatePegs, bandY, pb)) return false;
	}
	return true;
}
