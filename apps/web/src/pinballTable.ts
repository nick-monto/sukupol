import type { PinballDescriptor } from "./types";

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

export interface BiomeObstacleProfile {
	postCount: [number, number];
	postRadius: [number, number];
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
	obstacleProfile: BiomeObstacleProfile;
}

// ---------------------------------------------------------------------------
// Procgen output
// ---------------------------------------------------------------------------

export type BumperShape = "circle" | "square" | "triangle" | "pentagon";

export interface ObstacleSpec {
	id: string;
	kind: "bumper" | "post" | "enemy";
	x: number;
	y: number;
	radius: number;
	scoreValue: number;
	weaponLabel?: string; // if set: 2× score when equipped weapon maps to this label
	shape?: BumperShape; // weapon-driven shape override; absent = circle
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
		const scaleW =
			sinA > 0.7
				? Math.round(w.w * sy)
				: cosA > 0.7
					? Math.round(w.w * sx)
					: Math.round(w.w * avgS);
		const scaleH = sinA > 0.7 || cosA > 0.7 ? w.h : Math.round(w.h * avgS);
		return {
			x: scX(w.x),
			y: scY(w.y),
			w: scaleW,
			h: scaleH,
			angle: w.angle,
			...(w.chamfer != null ? { chamfer: w.chamfer } : {}),
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
		obstacleProfile: {
			postCount: [10, 13],
			postRadius: [9, 13],
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
		obstacleProfile: {
			postCount: [14, 18],
			postRadius: [9, 12],
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
		obstacleProfile: {
			postCount: [10, 14],
			postRadius: [10, 14],
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
		obstacleProfile: {
			postCount: [12, 16],
			postRadius: [9, 13],
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
// Traversability helpers
// ---------------------------------------------------------------------------

const BALL_R = 14;
const MIN_PASSAGE = BALL_R * 3; // 42 px — minimum clear gap in any y-band
const OBS_CLEARANCE = BALL_R * 2.5; // 35 px — extra gap between obstacle edges
const BAND_H = BALL_R * 4; // 56 px — height of each y-band

/**
 * Returns true if the horizontal band centred at `bandY` still has at least
 * one gap ≥ MIN_PASSAGE, given the provided obstacle list.
 */
function bandHasPassage(
	obs: ObstacleSpec[],
	bandY: number,
	pb: CabinetSpec["placementBounds"],
): boolean {
	const halfBand = BAND_H / 2;
	const pbRight = pb.x + pb.w;

	const intervals: [number, number][] = [];
	for (const o of obs) {
		if (o.y + o.radius < bandY - halfBand) continue;
		if (o.y - o.radius > bandY + halfBand) continue;
		const left = Math.max(pb.x, o.x - o.radius - BALL_R);
		const right = Math.min(pbRight, o.x + o.radius + BALL_R);
		if (right > left) intervals.push([left, right]);
	}

	if (!intervals.length) return true;

	intervals.sort((a, b) => a[0] - b[0]);
	const merged: [number, number][] = [];
	for (const iv of intervals) {
		if (!merged.length || iv[0] > merged[merged.length - 1][1]) {
			merged.push([...iv] as [number, number]);
		} else {
			merged[merged.length - 1][1] = Math.max(
				merged[merged.length - 1][1],
				iv[1],
			);
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
 * Returns true if adding `candidate` to `placed` still leaves a traversable
 * passage in every y-band the candidate's circle overlaps.
 */
function hasPassage(
	placed: ObstacleSpec[],
	candidate: ObstacleSpec,
	pb: CabinetSpec["placementBounds"],
): boolean {
	const withCandidate = [...placed, candidate];
	const topY = candidate.y - candidate.radius;
	const botY = candidate.y + candidate.radius;
	const firstBand =
		Math.floor((topY - pb.y) / BAND_H) * BAND_H + pb.y + BAND_H / 2;
	const lastBand =
		Math.floor((botY - pb.y) / BAND_H) * BAND_H + pb.y + BAND_H / 2;
	for (let bandY = firstBand; bandY <= lastBand + 1; bandY += BAND_H) {
		if (!bandHasPassage(withCandidate, bandY, pb)) return false;
	}
	return true;
}

// ---------------------------------------------------------------------------
// generatePinballTable — seeded open-cabinet obstacle procgen
// ---------------------------------------------------------------------------

export function generatePinballTable(
	descriptor: PinballDescriptor,
): PinballTableLayout {
	const biomeConfig = BIOME_CONFIGS[descriptor.biome_id] ?? DEFAULT_BIOME;
	const cabinet =
		CABINET_SPECS[biomeConfig.cabinetId] ?? CABINET_SPECS["standard"];
	const { physics, theme, obstacleProfile: profile } = biomeConfig;
	const pb = cabinet.placementBounds;

	const seed =
		((descriptor.floor_seed ?? 0) ^ hashStr(descriptor.enemy_id ?? "")) >>> 0;
	const rng = mulberry32(seed);

	// ── Placed obstacle list ────────────────────────────────────────────────
	const placed: ObstacleSpec[] = [];

	function clearOf(x: number, y: number, r: number): boolean {
		for (const o of placed) {
			const dx = o.x - x;
			const dy = o.y - y;
			if (Math.sqrt(dx * dx + dy * dy) < o.radius + r + OBS_CLEARANCE)
				return false;
		}
		return true;
	}

	function notExcluded(x: number, y: number, r: number): boolean {
		for (const ez of cabinet.exclusionZones) {
			const dx = ez.x - x;
			const dy = ez.y - y;
			if (Math.sqrt(dx * dx + dy * dy) < ez.radius + r) return false;
		}
		return true;
	}

	function tryAccept(spec: ObstacleSpec): boolean {
		const { x, y, radius: r } = spec;
		if (x - r < pb.x || x + r > pb.x + pb.w) return false;
		if (y - r < pb.y || y + r > pb.y + pb.h) return false;
		if (!notExcluded(x, y, r)) return false;
		if (!clearOf(x, y, r)) return false;
		if (!hasPassage(placed, spec, pb)) return false;
		placed.push(spec);
		return true;
	}

	// ── 1. Weapon orbs — fixed positions, always placed ────────────────────
	for (const slot of cabinet.orbSlots) {
		placed.push({
			id: slot.label,
			kind: "bumper",
			x: slot.x,
			y: slot.y,
			radius: 28,
			scoreValue: 10,
			weaponLabel: slot.label,
		});
	}

	// ── 2. Shuffled candidate grid ─────────────────────────────────────────
	const CELL = 70;
	const cols = Math.floor(pb.w / CELL);
	const rows = Math.floor(pb.h / CELL);
	const candidates: [number, number][] = [];

	for (let row = 0; row < rows; row++) {
		for (let col = 0; col < cols; col++) {
			const cx = pb.x + col * CELL + CELL / 2 + Math.round((rng() - 0.5) * 50);
			const cy = pb.y + row * CELL + CELL / 2 + Math.round((rng() - 0.5) * 50);
			candidates.push([cx, cy]);
		}
	}
	// Fisher-Yates shuffle
	for (let i = candidates.length - 1; i > 0; i--) {
		const j = Math.floor(rng() * (i + 1));
		[candidates[i], candidates[j]] = [candidates[j], candidates[i]];
	}

	// ── 3. Bonus bumpers then posts ────────────────────────────────────────
	const postCount =
		profile.postCount[0] +
		Math.floor(rng() * (profile.postCount[1] - profile.postCount[0] + 1));
	let bumpersPlaced = 0;
	let postsPlaced = 0;

	for (const [cx, cy] of candidates) {
		if (bumpersPlaced >= profile.bonusBumpers && postsPlaced >= postCount)
			break;

		if (bumpersPlaced < profile.bonusBumpers) {
			const orbLabels = ["orb-center", "orb-left", "orb-right"];
			if (
				tryAccept({
					id: `bumper-bonus-${bumpersPlaced}`,
					kind: "bumper",
					x: cx,
					y: cy,
					radius: 26,
					scoreValue: 12,
					weaponLabel: orbLabels[bumpersPlaced],
				})
			) {
				bumpersPlaced++;
			}
		} else if (postsPlaced < postCount) {
			const r =
				profile.postRadius[0] +
				Math.floor(rng() * (profile.postRadius[1] - profile.postRadius[0] + 1));
			if (
				tryAccept({
					id: `post-${postsPlaced}`,
					kind: "post",
					x: cx,
					y: cy,
					radius: r,
					scoreValue: 3,
				})
			) {
				postsPlaced++;
			}
		}
	}

	// ── 4. Enemy unique obstacles (up to 2, re-scan candidates) ───────────
	const uniqueObs = descriptor.enemy_pinball?.unique_obstacles ?? [];
	let enemyPlaced = 0;

	for (const [cx, cy] of candidates) {
		if (enemyPlaced >= Math.min(uniqueObs.length, 2)) break;
		const obs = uniqueObs[enemyPlaced];
		const jx = Math.round((rng() - 0.5) * 30);
		const jy = Math.round((rng() - 0.5) * 30);
		if (
			tryAccept({
				id: `enemy-obs-${enemyPlaced}`,
				kind: "enemy",
				x: cx + jx,
				y: cy + jy,
				radius: 20,
				scoreValue: Math.max(15, (obs.value ?? 1) * 15),
				effect: obs.effect,
				effectValue: obs.value,
			})
		) {
			enemyPlaced++;
		}
	}

	// ── 5. Weak-point — lower-centre of placement bounds ──────────────────
	const wpXMin = pb.x + pb.w * 0.2;
	const wpXMax = pb.x + pb.w * 0.8;
	const wpYMin = pb.y + pb.h * 0.55;
	const wpYMax = pb.y + pb.h * 0.9;

	let weakPoint: WeakPointSpec = {
		x: Math.round(pb.x + pb.w * 0.5),
		y: Math.round(pb.y + pb.h * 0.72),
		radius: 18,
	};

	for (let attempt = 0; attempt < 30; attempt++) {
		const wx = Math.round(wpXMin + rng() * (wpXMax - wpXMin));
		const wy = Math.round(wpYMin + rng() * (wpYMax - wpYMin));

		let tooClose = false;
		for (const o of placed) {
			const dx = o.x - wx,
				dy = o.y - wy;
			if (Math.sqrt(dx * dx + dy * dy) < o.radius + 18 + OBS_CLEARANCE) {
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
