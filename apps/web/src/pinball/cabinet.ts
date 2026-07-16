

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
	orbSlots: Array<{ label: string; x: number; y: number; radius: number }>;
	/** Open mid-field area — procgen populates obstacles inside here */
	placementBounds: { x: number; y: number; w: number; h: number };
	/** Regions to keep clear (flipper approach, drain gap) */
	exclusionZones: Array<{ x: number; y: number; radius: number }>;
	/** Short wall segments flanking each flipper hinge — guide balls toward the paddle face */
	inlaneWalls: CabinetWallDef[];
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
			{ x: 47, y: 402, w: 112, h: 14, angle: Math.PI / 6, chamfer: 6 },
			{ x: 47, y: 460, w: 114, h: 14, angle: (5 * Math.PI) / 6, chamfer: 6 },
			// Right side kicker — mirror of left
			{ x: 503, y: 402, w: 112, h: 14, angle: (5 * Math.PI) / 6, chamfer: 6 },
			{ x: 503, y: 460, w: 114, h: 14, angle: Math.PI / 6, chamfer: 6 },
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
		orbSlots: [
			{ label: "orb-center", x: 240, y: 220, radius: 28 },
			{ label: "orb-left", x: 140, y: 220, radius: 28 },
			{ label: "orb-right", x: 330, y: 250, radius: 28 },
		],
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
			{ x: 172, y: 529, radius: 120 },
			{ x: 318, y: 529, radius: 120 },
			{ x: 245, y: 600, radius: 50 },
			{ x: 80, y: 40, radius: 80 },
			{ x: 440, y: 40, radius: 80 },
			{ x: 47, y: 432, radius: 80 },
			{ x: 503, y: 432, radius: 80 },
			{ x: 400, y: 160, radius: 80 },
		],
		// Inlane guide walls — short vertical wall segments flanking each flipper hinge,
		// replacing the old circular posts. One pair per side.
		inlaneWalls: [
			{ x: 128, y: 513, w: 62, h: 10, angle: Math.PI / 2 },
			{ x: 153, y: 508, w: 56, h: 10, angle: Math.PI / 2 },
			{ x: 397, y: 508, w: 56, h: 10, angle: Math.PI / 2 },
			{ x: 422, y: 513, w: 62, h: 10, angle: Math.PI / 2 },
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
		orbSlots: std.orbSlots.map((o) => ({ ...o, x: scX(o.x), y: scY(o.y), radius: Math.round(o.radius * (sx + sy) / 2) })),
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
	standard: scaleSpec(STD, "standard", 620, 740),
	narrow: scaleSpec(STD, "narrow", 545, 800),
	wide: scaleSpec(STD, "wide", 680, 700),
	tall: scaleSpec(STD, "tall", 590, 860),
};
