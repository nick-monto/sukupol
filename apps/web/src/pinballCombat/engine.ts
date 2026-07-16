import Matter, { Body, Bodies, Engine, World } from "../lib/matter";
import type {
	PinballTableLayout,
	ObstacleSpec,
	BumperShape,
} from "../pinball/types";
import { createFlipperBodies } from "./physics";
import type { FlipperBodies } from "./physics";
import { WEAPON_BUMPER_SHAPE, ORB_LABEL_ORDER } from "./weapons";

// ---------------------------------------------------------------------------
// EngineWorld — collection of every body and map the runtime needs
// ---------------------------------------------------------------------------

export interface EngineWorld {
	engine: Matter.Engine;
	world: Matter.World;
	outerWalls: Matter.Body[];
	guardrailBodies: Matter.Body[];
	buffers: Matter.Body[];
	hatch: Matter.Body;
	weakPointBody: Matter.Body;
	left: FlipperBodies;
	right: FlipperBodies;
	pegBodyMap: Map<string, Matter.Body>;
	parentPegBodies: Map<string, Matter.Body[]>;
	obstacleSpecMap: Map<string, ObstacleSpec>;
}

// ---------------------------------------------------------------------------
// Obstacle shape map — computed once from equipped weapon at setup
// ---------------------------------------------------------------------------

export function initObstacleShapeMap(
	obstacleSpecs: ObstacleSpec[],
	weaponType: string | null,
): Map<string, BumperShape> {
	const t = weaponType ?? "";
	const info = t ? WEAPON_BUMPER_SHAPE[t.toLowerCase()] : null;
	const map = new Map<string, BumperShape>();
	if (!info) return map;
	for (let i = 0; i < info.count; i++) {
		const obs = obstacleSpecs.find(
			(o) => o.weaponLabel === ORB_LABEL_ORDER[i],
		);
		if (obs) map.set(obs.id, info.shape);
	}
	return map;
}

// ---------------------------------------------------------------------------
// Single peg body
// ---------------------------------------------------------------------------

function createPegBody(
	obs: ObstacleSpec,
	peg: { id: string; x: number; y: number; radius: number },
	shapeMap: Map<string, BumperShape>,
	restitution: number,
): Matter.Body {
	const opts = {
		label: `obstacle:${obs.id}`,
		isStatic: true,
		restitution: obs.kind === "post" ? 0.4 : restitution,
		friction: 0,
	};
	const shape = shapeMap.get(obs.id) ?? "circle";
	let sides: number;
	if (shape === "triangle") sides = 3;
	else if (shape === "square") sides = 4;
	else if (shape === "pentagon") sides = 5;
	else sides = 0;
	return sides > 0
		? Bodies.polygon(peg.x, peg.y, sides, peg.radius, opts)
		: Bodies.circle(peg.x, peg.y, peg.radius, opts);
}

// ---------------------------------------------------------------------------
// All obstacle bodies
// ---------------------------------------------------------------------------

function buildAllObstacles(
	specs: ObstacleSpec[],
	shapeMap: Map<string, BumperShape>,
	restitution: number,
): {
	pegBodyMap: Map<string, Matter.Body>;
	parentPegBodies: Map<string, Matter.Body[]>;
	obstacleSpecMap: Map<string, ObstacleSpec>;
	allBodies: Matter.Body[];
} {
	const obstacleSpecMap = new Map(specs.map((o) => [o.id, o]));
	const pegBodyMap = new Map<string, Matter.Body>();
	const parentPegBodies = new Map<string, Matter.Body[]>();
	const allBodies: Matter.Body[] = [];
	for (const obs of specs) {
		const bodies: Matter.Body[] = [];
		for (const peg of obs.pegs) {
			const b = createPegBody(obs, peg, shapeMap, restitution);
			pegBodyMap.set(peg.id, b);
			bodies.push(b);
			allBodies.push(b);
		}
		parentPegBodies.set(obs.id, bodies);
	}
	return { pegBodyMap, parentPegBodies, obstacleSpecMap, allBodies };
}

// ---------------------------------------------------------------------------
// Individual boundary helpers
// ---------------------------------------------------------------------------

function createOuterWalls(
	cabinet: PinballTableLayout["cabinet"],
): Matter.Body[] {
	return cabinet.outerWalls.map(
		(w: {
			x: number;
			y: number;
			w: number;
			h: number;
			angle: number;
			chamfer?: number;
		}) =>
			Bodies.rectangle(w.x, w.y, w.w, w.h, {
				isStatic: true,
				angle: w.angle,
				restitution: 0.2,
				friction: 0.05,
				...(w.chamfer ? { chamfer: { radius: w.chamfer } } : {}),
			}),
	);
}

function createHatch(
	cabinet: PinballTableLayout["cabinet"],
): Matter.Body {
	return Bodies.rectangle(
		cabinet.hatch.x,
		cabinet.hatch.y,
		130,
		20,
		{
			label: "hatch",
			isStatic: true,
			angle: Math.PI / 2,
			chamfer: { radius: 10 },
		},
	);
}

function createGuardrails(
	cabinet: PinballTableLayout["cabinet"],
): Matter.Body[] {
	return cabinet.inlaneWalls.map(
		(w: {
			x: number;
			y: number;
			w: number;
			h: number;
			angle: number;
			chamfer?: number;
		}) =>
			Bodies.rectangle(w.x, w.y, w.w, w.h, {
				label: "guardrail",
				isStatic: true,
				angle: w.angle,
				restitution: 0.25,
				friction: 0.1,
				...(w.chamfer ? { chamfer: { radius: w.chamfer } } : {}),
			}),
	);
}

function createWeakPoint(
	wp: PinballTableLayout["weakPoint"],
	restitution: number,
): Matter.Body {
	return Bodies.circle(wp.x, wp.y, wp.radius, {
		label: "weak-point",
		isStatic: true,
		restitution,
		friction: 0,
	});
}

function createBuffers(
	cabinet: PinballTableLayout["cabinet"],
	group: number,
): Matter.Body[] {
	return cabinet.buffers.map((b: { x: number; y: number }) => {
		const body = Bodies.circle(b.x, b.y, 50, {
			label: "buffer",
			isStatic: true,
		});
		body.collisionFilter = { group };
		return body;
	});
}

// ---------------------------------------------------------------------------
// Public factory — build everything and add to world
// ---------------------------------------------------------------------------

export function buildEngineWorld(
	layout: PinballTableLayout,
	obstacleShapeMap: Map<string, BumperShape>,
	bufferGroup: number,
): EngineWorld {
	const engine = Engine.create();
	engine.gravity.y = layout.physics.gravity;
	const { world } = engine;

	const { pegBodyMap, parentPegBodies, obstacleSpecMap, allBodies } =
		buildAllObstacles(
			layout.obstacles,
			obstacleShapeMap,
			layout.physics.bumperRestitution,
		);
	const weakPointBody = createWeakPoint(
		layout.weakPoint,
		layout.physics.bumperRestitution,
	);
	const outerWalls = createOuterWalls(layout.cabinet);
	const guardrailBodies = createGuardrails(layout.cabinet);
	const buffers = createBuffers(layout.cabinet, bufferGroup);
	const hatch = createHatch(layout.cabinet);
	const left = createFlipperBodies(
		layout.cabinet.flipperLeft,
		"leftPaddle",
		bufferGroup,
		true,
	);
	const right = createFlipperBodies(
		layout.cabinet.flipperRight,
		"rightPaddle",
		bufferGroup,
		false,
	);

	World.add(world, [
		...allBodies,
		weakPointBody,
		...outerWalls,
		hatch,
		left.paddle,
		left.hinge,
		left.block,
		left.constraint,
		left.weight,
		right.paddle,
		right.hinge,
		right.block,
		right.constraint,
		right.weight,
		...buffers,
		...guardrailBodies,
	]);

	return {
		engine,
		world,
		outerWalls,
		guardrailBodies,
		buffers,
		hatch,
		weakPointBody,
		left,
		right,
		pegBodyMap,
		parentPegBodies,
		obstacleSpecMap,
	};
}

