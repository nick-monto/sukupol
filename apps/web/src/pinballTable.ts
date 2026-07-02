import type { ObstacleTemplate, PegDef, PinballDescriptor } from "./types";

// ---------------------------------------------------------------------------
// Cabinet geometry types
// ---------------------------------------------------------------------------

export interface CabinetWallDef {
	x: number;
	y: number;
	w: number;
	h: number;
	angle: number;
	chamfer?: number;
}

export interface CabinetFlipperDef {
	paddleX: number;
	paddleY: number;
	hingeX: number;
	hingeY: number;
	blockX: number;
	blockY: number;
	pivotOffset: { x: number; y: number };
	weightOffset: { x: number; y: number };
	angularVelocity: number; // sign: -1 for left, +1 for right
}

export interface CabinetSpec {
	id: string;
	width: number;
	height: number;
	outerWalls: CabinetWallDef[];
	hatch: { x: number; y: number };
	hatchTranslateY: number;
	launchX: number;
	launchY: number;
	shooterLaneGuardX: number;
	flipperLeft: CabinetFlipperDef;
	flipperRight: CabinetFlipperDef;
	buffers: Array<{ x: number; y: number }>;
	drainY: number;
	orbSlots: Array<{ label: string; x: number; y: number }>;
	/** Open mid-field area — procgen populates obstacles inside here */
	placementBounds: { x: number; y: number; w: number; h: number };
	/** Regions to keep clear (flipper approach, drain gap) */
	exclusionZones: Array<{ x: number; y: number; radius: number }>;
	/** Short wall segments flanking each flipper hinge — guide balls toward the paddle face */
	inlaneWalls: CabinetWallDef[];
}

// ---------------------------------------------------------------------------
// Biome types
// ---------------------------------------------------------------------------

export interface BiomePegConfig {
	/** Total peg budget per table — each placed peg costs from this pool */
	pegBudget: number;
	/** Cost per post obstacle (usually 1) */
	postCost: number;
	/** Cost per bumper obstacle (usually 2) */
	bumperCost: number;
	/** Cost multiplier per enemy obstacle peg (usually 1, distinct from postCost for clarity) */
	enemyPegCost: number;
	/** Number of bonus bumpers to place alongside weapon orbs */
	bonusBumpers: number;
}

export interface BiomePhysics {
	gravity: number;
	ballDrag: number;
	bumperRestitution: number;
}

export interface BiomeTheme {
	bg: string;
	walls: string;
	orbs: string;
	orbHit: string;
	paddle: string;
	ball: string;
	weakPoint: string;
	obstacle: string;
	obstacleStyle: "bones" | "moss" | "stone" | "archive" | "default";
}

export interface BiomeConfig {
	cabinetId: string;
	physics: BiomePhysics;
	theme: BiomeTheme;
	pegConfig: BiomePegConfig;
}

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
	shape?: BumperShape;
	effect?: string;
	effectValue?: number;
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
// Standard cabinet spec (550 × 650 — exact fishshiz/pinball-wizard geometry)
// ---------------------------------------------------------------------------

function makeStandardSpec(): CabinetSpec {
	return {
		id: "standard",
		width: 550,
		height: 650,
		outerWalls: [
			// Perimeter
			{ x: 0, y: 325, w: 650, h: 20, angle: Math.PI / 2 },
			{ x: 550, y: 325, w: 650, h: 20, angle: Math.PI / 2 },
			{ x: 275, y: 0, w: 550, h: 20, angle: 0 },
			// Shooter-lane guard (right side)
			{ x: 490, y: 455, w: 400, h: 20, angle: Math.PI / 2, chamfer: 10 },
			// Lower sling ramps above each flipper
			{ x: 90, y: 560, w: 220, h: 20, angle: Math.PI / 6, chamfer: 10 },
			{ x: 400, y: 560, w: 220, h: 20, angle: (5 * Math.PI) / 6, chamfer: 10 },
			// Upper corner diagonals
			{ x: 100, y: 0, w: 350, h: 200, angle: (5 * Math.PI) / 6, chamfer: 10 },
			{ x: 420, y: 0, w: 400, h: 200, angle: Math.PI / 6, chamfer: 10 },
			// Left side kicker — two angled faces meeting at a tip ~(95, 430)
			{ x: 47, y: 402, w: 112, h: 14, angle: Math.PI / 6, chamfer: 6 }, // top face
			{ x: 47, y: 460, w: 114, h: 14, angle: (5 * Math.PI) / 6, chamfer: 6 }, // bottom face
			// Right side kicker — mirror of left
			{ x: 503, y: 402, w: 112, h: 14, angle: (5 * Math.PI) / 6, chamfer: 6 }, // top face
			{ x: 503, y: 460, w: 114, h: 14, angle: Math.PI / 6, chamfer: 6 }, // bottom face
		],
		hatch: { x: 490, y: 210 },
		hatchTranslateY: 100,
		launchX: 510,
		launchY: 625,
		shooterLaneGuardX: 450,
		flipperLeft: {
			paddleX: 190,
			paddleY: 540,
			hingeX: 172,
			hingeY: 529,
			blockX: 200,
			blockY: 550,
			pivotOffset: { x: -18, y: -11 },
			weightOffset: { x: 13, y: 11 },
			angularVelocity: -1,
		},
		flipperRight: {
			paddleX: 300,
			paddleY: 540,
			hingeX: 318,
			hingeY: 529,
			blockX: 290,
			blockY: 550,
			pivotOffset: { x: 18, y: -11 },
			weightOffset: { x: -13, y: 11 },
			angularVelocity: 1,
		},
		buffers: [
			{ x: 190, y: 605 },
			{ x: 300, y: 605 },
		],
		drainY: 670,
		orbSlots: [],
		// Open mid-field: matches the red safe-zone outline in the foundation sketch.
		// Left/right edges pulled inward to clear the side kicker tips (~x=95 and ~x=455).
		// Top clears upper diagonal wall inner faces (~y=87); bottom stays above the
		// lower sling / flipper approach zone.
		placementBounds: { x: 100, y: 100, w: 310, h: 360 },
		// Keep flipper approach, drain gap, upper corners, side kickers, and hatch exit clear.
		// Flipper radius 120 (was 90) ensures the exclusion reaches the bottom of the
		// placement area on all scaled cabinets, closing the 15–29px gap that allowed
		// obstacles to wedge directly above the paddles.
		exclusionZones: [
			{ x: 172, y: 529, radius: 120 }, // left flipper approach (expanded)
			{ x: 318, y: 529, radius: 120 }, // right flipper approach (expanded)
			{ x: 245, y: 600, radius: 50 }, // drain gap
			{ x: 80, y: 40, radius: 80 }, // upper-left diagonal wall corner
			{ x: 440, y: 40, radius: 80 }, // upper-right diagonal wall corner
			{ x: 47, y: 432, radius: 80 }, // left side kicker body
			{ x: 503, y: 432, radius: 80 }, // right side kicker body
			{ x: 400, y: 160, radius: 80 }, // hatch exit / launch transition zone
		],
		// Inlane guide walls — short vertical wall segments flanking each flipper hinge,
		// replacing the old circular posts. One pair per side.
		inlaneWalls: [
			{ x: 128, y: 513, w: 62, h: 10, angle: Math.PI / 2 }, // left outer guide
			{ x: 153, y: 508, w: 56, h: 10, angle: Math.PI / 2 }, // left inner guide
			{ x: 397, y: 508, w: 56, h: 10, angle: Math.PI / 2 }, // right inner guide
			{ x: 422, y: 513, w: 62, h: 10, angle: Math.PI / 2 }, // right outer guide
		],
	};
}

// ---------------------------------------------------------------------------
// Scale helper — derive alternate cabinet shapes from the standard spec
// ---------------------------------------------------------------------------

function scaleSpec(
	std: CabinetSpec,
	id: string,
	W: number,
	H: number,
): CabinetSpec {
	const sx = W / std.width;
	const sy = H / std.height;
	const scX = (v: number) => Math.round(v * sx);
	const scY = (v: number) => Math.round(v * sy);

	function scaleWall(w: CabinetWallDef): CabinetWallDef {
		const sinA = Math.abs(Math.sin(w.angle));
		const cosA = Math.abs(Math.cos(w.angle));
		// Vertical walls (angle ≈ π/2): length spans Y → scale w by sy
		// Horizontal walls (angle ≈ 0): length spans X → scale w by sx
		// Diagonal walls: scale both w and h by average
		const avgS = (sx + sy) / 2;
		let scaleW: number;
		if (sinA > 0.7) {
			scaleW = Math.round(w.w * sy);
		} else if (cosA > 0.7) {
			scaleW = Math.round(w.w * sx);
		} else {
			scaleW = Math.round(w.w * avgS);
		}
		const scaleH = sinA > 0.7 || cosA > 0.7 ? w.h : Math.round(w.h * avgS);
		return {
			x: scX(w.x),
			y: scY(w.y),
			w: scaleW,
			h: scaleH,
			angle: w.angle,
			...(w.chamfer !== null ? { chamfer: w.chamfer } : {}),
		};
	}

	const fl = std.flipperLeft;
	const fr = std.flipperRight;
	const pb = std.placementBounds;

	return {
		id,
		width: W,
		height: H,
		outerWalls: std.outerWalls.map(scaleWall),
		hatch: { x: scX(std.hatch.x), y: scY(std.hatch.y) },
		hatchTranslateY: std.hatchTranslateY,
		launchX: scX(std.launchX),
		launchY: scY(std.launchY),
		shooterLaneGuardX: scX(std.shooterLaneGuardX),
		flipperLeft: {
			paddleX: scX(fl.paddleX),
			paddleY: scY(fl.paddleY),
			hingeX: scX(fl.hingeX),
			hingeY: scY(fl.hingeY),
			blockX: scX(fl.blockX),
			blockY: scY(fl.blockY),
			pivotOffset: fl.pivotOffset,
			weightOffset: fl.weightOffset,
			angularVelocity: fl.angularVelocity,
		},
		flipperRight: {
			paddleX: scX(fr.paddleX),
			paddleY: scY(fr.paddleY),
			hingeX: scX(fr.hingeX),
			hingeY: scY(fr.hingeY),
			blockX: scX(fr.blockX),
			blockY: scY(fr.blockY),
			pivotOffset: fr.pivotOffset,
			weightOffset: fr.weightOffset,
			angularVelocity: fr.angularVelocity,
		},
		buffers: std.buffers.map((b) => ({ x: scX(b.x), y: scY(b.y) })),
		drainY: H + 20,
		orbSlots: std.orbSlots.map((o) => ({ ...o, x: scX(o.x), y: scY(o.y) })),
		placementBounds: {
			x: scX(pb.x),
			y: scY(pb.y),
			w: Math.round(pb.w * sx),
			h: Math.round(pb.h * sy),
		},
		exclusionZones: std.exclusionZones.map((ez) => ({
			x: scX(ez.x),
			y: scY(ez.y),
			radius: Math.round((ez.radius * (sx + sy)) / 2),
		})),
		inlaneWalls: std.inlaneWalls.map(scaleWall),
	};
}

// ---------------------------------------------------------------------------
// Cabinet presets
// ---------------------------------------------------------------------------

const STD = makeStandardSpec();

export const CABINET_SPECS: Record<string, CabinetSpec> = {
	// ~13% larger than the original 550×650 reference
	standard: scaleSpec(STD, "standard", 620, 740),
	// Narrow, tall: whispering_caverns — tight lanes, lower gravity
	narrow: scaleSpec(STD, "narrow", 545, 800),
	// Wide, shorter: ancient_halls — broad mid-field
	wide: scaleSpec(STD, "wide", 680, 700),
	// Standard width, tall: sunken_archive — long plunge, heavier feel
	tall: scaleSpec(STD, "tall", 590, 860),
};

// ---------------------------------------------------------------------------
// Biome configs
// ---------------------------------------------------------------------------

export const BIOME_CONFIGS: Record<string, BiomeConfig> = {
	ashen_fields: {
		cabinetId: "standard",
		physics: { gravity: 0.95, ballDrag: 0.005, bumperRestitution: 1.5 },
		theme: {
			bg: "#212529",
			walls: "#C4CFD4",
			orbs: "#5C43B5",
			orbHit: "#B09150",
			paddle: "#f5a02e",
			ball: "#dee2e6",
			weakPoint: "#E8C547",
			obstacle: "#9B6B8A",
			obstacleStyle: "default",
		},
		pegConfig: {
			pegBudget: 24,
			postCost: 1,
			bumperCost: 2,
			enemyPegCost: 1,
			bonusBumpers: 3,
		},
	},
	whispering_caverns: {
		cabinetId: "narrow",
		physics: { gravity: 0.85, ballDrag: 0.008, bumperRestitution: 1.3 },
		theme: {
			bg: "#141C14",
			walls: "#4A6741",
			orbs: "#2E6B3A",
			orbHit: "#7DC980",
			paddle: "#5E8C5E",
			ball: "#C8DFC8",
			weakPoint: "#B0E84A",
			obstacle: "#6BAA55",
			obstacleStyle: "moss",
		},
		pegConfig: {
			pegBudget: 28,
			postCost: 1,
			bumperCost: 2,
			enemyPegCost: 1,
			bonusBumpers: 3,
		},
	},
	ancient_halls: {
		cabinetId: "wide",
		physics: { gravity: 0.9, ballDrag: 0.004, bumperRestitution: 1.4 },
		theme: {
			bg: "#1E1A14",
			walls: "#9E8B6E",
			orbs: "#7A5F3A",
			orbHit: "#D4A843",
			paddle: "#C4985A",
			ball: "#E8D5B0",
			weakPoint: "#F0C060",
			obstacle: "#A87B44",
			obstacleStyle: "stone",
		},
		pegConfig: {
			pegBudget: 26,
			postCost: 1,
			bumperCost: 2,
			enemyPegCost: 1,
			bonusBumpers: 3,
		},
	},
	sunken_archive: {
		cabinetId: "tall",
		physics: { gravity: 1.05, ballDrag: 0.012, bumperRestitution: 1.6 },
		theme: {
			bg: "#0A1520",
			walls: "#1E4060",
			orbs: "#1A4A6E",
			orbHit: "#4AB8D8",
			paddle: "#3A84A0",
			ball: "#A8D8E8",
			weakPoint: "#40E0C0",
			obstacle: "#2A7080",
			obstacleStyle: "archive",
		},
		pegConfig: {
			pegBudget: 30,
			postCost: 1,
			bumperCost: 2,
			enemyPegCost: 1,
			bonusBumpers: 3,
		},
	},
};

const DEFAULT_BIOME = BIOME_CONFIGS["ashen_fields"];

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

// ---------------------------------------------------------------------------
// Helper: resolve legacy enemy obstacles to ObstacleTemplate[]
// ponytail: single-line migration — deletes the old format at runtime
//           so bootstrap.json can be updated incrementally per-enemy
// ---------------------------------------------------------------------------

function resolveEnemyObstacles(
	enemyPinball: PinballDescriptor["enemy_pinball"],
): ObstacleTemplate[] {
	if (enemyPinball?.obstacles) {
		// Warn if both formats exist — indicates incomplete migration
		if (enemyPinball.unique_obstacles?.length) {
			// eslint-disable-next-line no-console-except-error -- content-author diagnostic
			console.warn(
				"[pinball] enemy has both 'obstacles' and 'unique_obstacles'; ignoring legacy data",
			);
		}
		return enemyPinball.obstacles;
	}
	const legacy = enemyPinball?.unique_obstacles ?? [];
	return legacy.map((o, i) => ({
		id: o.kind ?? `legacy-${i}`,
		label: o.label ?? "Obstacle",
		pegs: [{ angle: 0, distance: 0, radius: 20 }],
		effect: o.effect,
		effectValue: o.value,
		scoreValue: Math.max(15, (o.value ?? 1) * 15),
		detail: o.detail,
	}));
}

// ---------------------------------------------------------------------------
// Helper: expand PegDef template into PlacedPeg positions at a given center
// ---------------------------------------------------------------------------

function expandPegs(
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

// ---------------------------------------------------------------------------
// Traversability — peg-aware interval merging per y-band
// ---------------------------------------------------------------------------

/** Collects all placed peg circles into a flat array */
function flattenPegs(obstacles: ObstacleSpec[]): PlacedPeg[] {
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
function bandHasPassage(
	allPegs: PlacedPeg[],
	bandY: number,
	pb: CabinetSpec["placementBounds"],
): boolean {
	const halfBand = BAND_H / 2;
	const pbRight = pb.x + pb.w;

	const intervals: [number, number][] = [];
	for (const p of allPegs) {
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
function hasPassage(
	existingPegs: PlacedPeg[],
	candidatePegs: PlacedPeg[],
	pb: CabinetSpec["placementBounds"],
): boolean {
	const all = [...existingPegs, ...candidatePegs];
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
		if (!bandHasPassage(all, bandY, pb)) return false;
	}
	return true;
}

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

	function allPegs(): PlacedPeg[] {
		return flattenPegs(placed);
	}

	// Check if a single peg collides with any existing peg
	function pegClearOf(x: number, y: number, r: number): boolean {
		for (const p of allPegs()) {
			const dx = p.x - x;
			const dy = p.y - y;
			if (Math.sqrt(dx * dx + dy * dy) < p.radius + r + PEG_CLEARANCE)
				return false;
		}
		return true;
	}

	// Check if a peg is inside any exclusion zone
	function pegNotExcluded(x: number, y: number, r: number): boolean {
		for (const ez of cabinet.exclusionZones) {
			const dx = ez.x - x;
			const dy = ez.y - y;
			if (Math.sqrt(dx * dx + dy * dy) < ez.radius + r) return false;
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
		if (!hasPassage(allPegs(), spec.pegs, pb)) return false;
		placed.push(spec);
		budgetLeft -= cost;
		return true;
	}

	// ── 1. Weapon orbs — fixed positions, always placed (cost: 0) ──────────
	for (const slot of cabinet.orbSlots) {
		placed.push({
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
					radius: 28,
				},
			],
			scoreValue: 10,
			weaponLabel: slot.label,
		});
	}
	// Validate orb placement doesn't overlap existing geometry (authoring guard)
	for (const slot of cabinet.orbSlots) {
		if (!pegNotExcluded(slot.x, slot.y, 28)) {
			// eslint-disable-next-line no-console-except-error -- content-author diagnostic
			console.warn(`[pinball] orb "${slot.label}" overlaps an exclusion zone`);
		}
		if (!pegClearOf(slot.x, slot.y, 28)) {
			// eslint-disable-next-line no-console-except-error -- content-author diagnostic
			console.warn(`[pinball] orb "${slot.label}" overlaps another obstacle`);
		}
	}

	// ── 2. Shuffled candidate positions — continuous (not grid) ────────────
	// ponytail: 72 candidates — enough for dense tables without wasting RNG cycles
	const NUM_CANDIDATES = 72;
	// Margin must clear the largest expected peg spread (distance+radius ≈ 30px)
	const CANDIDATE_MARGIN = 35;
	const candidates: [number, number][] = [];
	for (let i = 0; i < NUM_CANDIDATES; i++) {
		const cx = pb.x + CANDIDATE_MARGIN + rng() * (pb.w - CANDIDATE_MARGIN * 2);
		const cy = pb.y + CANDIDATE_MARGIN + rng() * (pb.h - CANDIDATE_MARGIN * 2);
		candidates.push([cx, cy]);
	}
	// Fisher-Yates shuffle
	for (let i = candidates.length - 1; i > 0; i--) {
		const j = Math.floor(rng() * (i + 1));
		[candidates[i], candidates[j]] = [candidates[j], candidates[i]];
	}

	// ── Helper: try placing a single-peg obstacle at the next candidate ─────
	// ponytail: while loop instead of for-of — stateful index shared across calls
	let candidateIdx = 0;
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

	// ── 3. Bonus bumpers (cost: bumperCost each) ───────────────────────────
	for (let i = 0; i < pegConfig.bonusBumpers; i++) {
		const orbLabels = ["orb-center", "orb-left", "orb-right"];
		tryPlaceSinglePeg(`bumper-bonus-${i}`, "bumper", 26, 12, orbLabels[i % 3]);
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

	// ── 5. Enemy obstacles (cost: number of pegs × postCost each) ─────────
	const enemyObs = resolveEnemyObstacles(descriptor.enemy_pinball);
	let enemyPlaced = 0;
	for (const template of enemyObs) {
		if (enemyPlaced >= 2) break;
		const cost = template.pegs.length * pegConfig.enemyPegCost;
		if (cost > budgetLeft) continue;

		// Try each remaining candidate with jitter
		let placedEnemy = false;
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
					scoreValue:
						template.scoreValue ??
						Math.max(15, (template.effectValue ?? 1) * 15),
					effect: template.effect,
					effectValue: template.effectValue,
				},
				cost,
			);
		}
		if (placedEnemy) enemyPlaced++;
	}

	// ── 6. Weak-point — lower-centre of placement bounds ──────────────────
	const wpXMin = pb.x + pb.w * 0.2;
	const wpXMax = pb.x + pb.w * 0.8;
	const wpYMin = pb.y + pb.h * 0.55;
	const wpYMax = pb.y + pb.h * 0.9;

	let weakPoint: WeakPointSpec = {
		x: Math.round(pb.x + pb.w * 0.5),
		y: Math.round(pb.y + pb.h * 0.72),
		radius: 18,
	};

	const allP = allPegs();
	for (let attempt = 0; attempt < 30; attempt++) {
		const wx = Math.round(wpXMin + rng() * (wpXMax - wpXMin));
		const wy = Math.round(wpYMin + rng() * (wpYMax - wpYMin));

		let tooClose = false;
		for (const p of allP) {
			const dx = p.x - wx,
				dy = p.y - wy;
			if (Math.sqrt(dx * dx + dy * dy) < p.radius + 18 + PEG_CLEARANCE) {
				tooClose = true;
				break;
			}
		}
		let inExclusion = false;
		for (const ez of cabinet.exclusionZones) {
			const dx = ez.x - wx,
				dy = ez.y - wy;
			if (Math.sqrt(dx * dx + dy * dy) < ez.radius + 18) {
				inExclusion = true;
				break;
			}
		}
		if (!tooClose && !inExclusion) {
			weakPoint = { x: wx, y: wy, radius: 18 };
			break;
		}
	}

	return { cabinet, physics, theme, obstacles: placed, weakPoint };
}
