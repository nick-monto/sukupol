import { Body, World, Engine } from "../lib/matter";
import type {
	PinballTableLayout,
	ObstacleSpec,
	BumperShape,
} from "../pinball/types";
import { buildEngineWorld, initObstacleShapeMap } from "./engine";
import { attachCollisionHandlers } from "./collisions";
import { startRenderLoop } from "./loop";
import { attachFlipperInput } from "./flippers";
import type { PinballRuntime } from "./runtime";

// ---------------------------------------------------------------------------
// Public API types
// ---------------------------------------------------------------------------

export interface PinballCombatOptions {
	layout: PinballTableLayout;
	onPinballStrike: (score: number) => void;
	onBallDrain: () => void;
	equippedWeaponType?: string | null;
}

export interface PinballTable {
	teardown: () => void;
	setEquippedWeapon: (weaponType: string | null) => void;
}

// ---------------------------------------------------------------------------
// setupPinball — builds the cabinet entirely from the provided layout
// ---------------------------------------------------------------------------

export function setupPinball(
	canvas: HTMLCanvasElement,
	opts: PinballCombatOptions,
): PinballTable {
	const { layout } = opts;
	const ctx = canvas.getContext("2d")!;
	canvas.width = layout.cabinet.width;
	canvas.height = layout.cabinet.height;

	const bufferGroup = Body.nextGroup(false);

	const obstacleShapeMap = initObstacleShapeMap(
		layout.obstacles,
		opts.equippedWeaponType ?? null,
	);

	const ew = buildEngineWorld(layout, obstacleShapeMap, bufferGroup);

	const runtime: PinballRuntime = {
		engine: ew.engine,
		world: ew.world,
		cabinet: layout.cabinet,
		theme: layout.theme,
		obstacleSpecs: layout.obstacles,
		wpSpec: layout.weakPoint,
		physicsSettings: layout.physics,

		outerWalls: ew.outerWalls,
		guardrailBodies: ew.guardrailBodies,
		buffers: ew.buffers,
		hatch: ew.hatch,
		weakPointBody: ew.weakPointBody,
		left: ew.left,
		right: ew.right,

		pegBodyMap: ew.pegBodyMap,
		parentPegBodies: ew.parentPegBodies,
		obstacleSpecMap: ew.obstacleSpecMap,
		obstacleShapeMap,

		ball: null,
		inPlay: false,
		leftFired: false,
		rightFired: false,
		pendingScore: 0,
		equippedWeaponType: opts.equippedWeaponType ?? null,
		orbFlash: new Map(),
		weakPointFlash: 0,
		lastHitTime: new Map(),
		hatchUp: true,

		canvas,
		ctx,

		rafId: 0,
		lastTs: 0,
		accumulator: 0,

		onPinballStrike: opts.onPinballStrike,
		onBallDrain: opts.onBallDrain,
	};

	attachCollisionHandlers(runtime);
	const cleanupInput = attachFlipperInput(runtime);
	startRenderLoop(runtime);

	return {
		teardown() {
			cancelAnimationFrame(runtime.rafId);
			cleanupInput();
			runtime.orbFlash.clear();
			World.clear(runtime.world, false);
			Engine.clear(runtime.engine);
		},
		setEquippedWeapon(type: string | null) {
			runtime.equippedWeaponType = type;
		},
	};
}
