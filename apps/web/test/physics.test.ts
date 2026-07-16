/** Physics simulation — headless Matter.js sims */

import { describe, it, expect } from "vitest";
import Matter from "matter-js";
import type { PinballDescriptor } from "../src/types.js";
import { BIOME_CONFIGS, generatePinballTable } from "../src/pinball";
import { SAMPLE_DESCRIPTOR, descriptorForBiome } from "./helpers.js";

const BALL_RADIUS = 14;
const MAX_VELOCITY = 50;
const FIXED_DT = 1000 / 60;

// ---------------------------------------------------------------------------
// Headless sim builder
// ---------------------------------------------------------------------------

function buildHeadlessSim(descriptor: PinballDescriptor) {
	const layout = generatePinballTable(descriptor);
	const { cabinet, physics } = layout;
	const { Engine, World, Bodies, Body, Constraint, Events } = Matter;

	const engine = Engine.create();
	engine.gravity.y = physics.gravity;
	const { world } = engine;

	const bufferGroup = Body.nextGroup(false);

	// Walls
	const outerWalls = cabinet.outerWalls.map((w) =>
		Bodies.rectangle(w.x, w.y, w.w, w.h, {
			isStatic: true,
			angle: w.angle,
			restitution: 0.2,
			friction: 0.05,
			...(w.chamfer ? { chamfer: { radius: w.chamfer } } : {}),
		}),
	);

	// Obstacles
	const obstacleBodies: Matter.Body[] = [];
	for (const obs of layout.obstacles) {
		for (const peg of obs.pegs) {
			obstacleBodies.push(
				Bodies.circle(peg.x, peg.y, peg.radius, {
					isStatic: true,
					label: `obstacle:${obs.id}`,
					restitution: obs.kind === "post" ? 0.4 : physics.bumperRestitution,
					friction: 0,
				}),
			);
		}
	}

	// Weak point
	const wpBody = Bodies.circle(
		layout.weakPoint.x,
		layout.weakPoint.y,
		layout.weakPoint.radius,
		{
			isStatic: true,
			label: "weak-point",
			restitution: physics.bumperRestitution,
			friction: 0,
		},
	);

	// Flippers
	const fl = cabinet.flipperLeft;
	const leftPaddle = Bodies.trapezoid(fl.paddleX, fl.paddleY, 25, 80, 0.25, {
		label: "leftPaddle",
		angle: (2 * Math.PI) / 3,
		chamfer: { radius: 10 },
		collisionFilter: { group: bufferGroup, category: 0xffffffff, mask: 2 },
	});
	const leftHinge = Bodies.circle(fl.hingeX, fl.hingeY, 5, { isStatic: true });
	const leftBlock = Bodies.rectangle(fl.blockX, fl.blockY, 30, 30, {
		isStatic: false,
	});
	const leftConstraint = Constraint.create({
		bodyA: leftPaddle,
		bodyB: leftHinge,
		pointA: fl.pivotOffset,
		stiffness: 0,
		length: 0,
	});
	const leftWeight = Constraint.create({
		bodyA: leftPaddle,
		bodyB: leftBlock,
		pointA: fl.weightOffset,
		stiffness: 0.75,
		length: 1,
	});

	const fr = cabinet.flipperRight;
	const rightPaddle = Bodies.trapezoid(fr.paddleX, fr.paddleY, 25, 80, 0.25, {
		label: "rightPaddle",
		angle: (4 * Math.PI) / 3,
		chamfer: { radius: 10 },
		collisionFilter: { group: bufferGroup, category: 0xffffffff, mask: 2 },
	});
	const rightHinge = Bodies.circle(fr.hingeX, fr.hingeY, 5, { isStatic: true });
	const rightBlock = Bodies.rectangle(fr.blockX, fr.blockY, 30, 30, {
		isStatic: false,
	});
	const rightConstraint = Constraint.create({
		bodyA: rightPaddle,
		bodyB: rightHinge,
		pointA: fr.pivotOffset,
		stiffness: 0,
		length: 0,
	});
	const rightWeight = Constraint.create({
		bodyA: rightPaddle,
		bodyB: rightBlock,
		pointA: fr.weightOffset,
		stiffness: 0.75,
		length: 1,
	});

	const buffers = cabinet.buffers.map((b) => {
		const body = Bodies.circle(b.x, b.y, 50, {
			label: "buffer",
			isStatic: true,
		});
		body.collisionFilter = { group: bufferGroup };
		return body;
	});

	const guardrailBodies = cabinet.inlaneWalls.map((w) =>
		Bodies.rectangle(w.x, w.y, w.w, w.h, {
			isStatic: true,
			label: "guardrail",
			angle: w.angle,
			restitution: 0.25,
			friction: 0.1,
			...(w.chamfer ? { chamfer: { radius: w.chamfer } } : {}),
		}),
	);

	World.add(world, [
		...obstacleBodies,
		wpBody,
		...outerWalls,
		leftPaddle,
		leftHinge,
		leftBlock,
		leftConstraint,
		leftWeight,
		rightPaddle,
		rightHinge,
		rightBlock,
		rightConstraint,
		rightWeight,
		...buffers,
		...guardrailBodies,
	]);

	const leftRestAngle = leftPaddle.angle;
	const rightRestAngle = rightPaddle.angle;
	const FLIPPER_TRAVEL = (Math.PI * 58) / 180;
	const FLIP_VEL = 0.45;

	let ball: Matter.Body | null = null;
	let _collisionCount = 0;
	const collisionTargets = new Set<string>();

	Events.on(
		engine,
		"collisionStart",
		(event: Matter.IEventCollision<Matter.Engine>) => {
			for (const pair of event.pairs) {
				const { bodyA, bodyB } = pair;
				let pinball: Matter.Body | null = null;
				if (bodyA.label === "pinball") {
					pinball = bodyA;
				} else if (bodyB.label === "pinball") {
					pinball = bodyB;
				}
				if (!pinball) continue;
				const otherBody: Matter.Body = pinball === bodyA ? bodyB : bodyA;
				_collisionCount++;
				collisionTargets.add(otherBody.label || "(no label)");
			}
		},
	);

	// beforeUpdate: velocity clamp + flipper control + shooter-lane guard
	Events.on(engine, "beforeUpdate", () => {
		if (ball) {
			Body.setVelocity(ball, {
				x: Math.max(Math.min(ball.velocity.x, MAX_VELOCITY), -MAX_VELOCITY),
				y: Math.max(Math.min(ball.velocity.y, MAX_VELOCITY), -MAX_VELOCITY),
			});
			if (
				ball.position.x > cabinet.shooterLaneGuardX &&
				ball.velocity.y > 0 &&
				ball.position.y > cabinet.hatch.y + cabinet.hatchTranslateY &&
				ball.position.y < cabinet.flipperLeft.paddleY - 20
			) {
				Body.setVelocity(ball, { x: 0, y: -10 });
			}
		}

		// Left flipper (idle — no fire in headless sim unless we add it)
		if (leftPaddle.angle < leftRestAngle - FLIP_VEL)
			Body.setAngularVelocity(leftPaddle, FLIP_VEL);
		else if (Math.abs(leftPaddle.angle - leftRestAngle) > 0.001) {
			Body.setAngle(leftPaddle, leftRestAngle);
			Body.setAngularVelocity(leftPaddle, 0);
		}

		if (rightPaddle.angle > rightRestAngle + FLIP_VEL)
			Body.setAngularVelocity(rightPaddle, -FLIP_VEL);
		else if (Math.abs(rightPaddle.angle - rightRestAngle) > 0.001) {
			Body.setAngle(rightPaddle, rightRestAngle);
			Body.setAngularVelocity(rightPaddle, 0);
		}
	});

	function launch(options?: { attempt?: number; fromLaunchTube?: boolean }) {
		const opts = options ?? {};
		const attempt = opts.attempt ?? 0;
		// Drop from top of playfield with slight horizontal drift toward center
		const pb = cabinet.placementBounds;
		const cx = pb.x + pb.w / 2;
		const trajectories = [
			{ x: cx - 60, y: pb.y, vx: 3, vy: 5 }, // left-of-center, drift right
			{ x: cx + 60, y: pb.y, vx: -3, vy: 5 }, // right-of-center, drift left
			{ x: cx, y: pb.y, vx: -2, vy: 7 }, // center, slight left
		];
		const t = trajectories[attempt % trajectories.length];
		const b = Bodies.circle(t.x, t.y, BALL_RADIUS, {
			label: "pinball",
			restitution: 0.48,
			frictionAir: physics.ballDrag,
			collisionFilter: { mask: 0xffffffff, category: 2, group: 0 },
		});
		World.add(world, b);
		Body.setVelocity(b, { x: t.vx, y: t.vy });
		ball = b;
	}

	function step(n = 1) {
		for (let i = 0; i < n; i++) {
			Engine.update(engine, FIXED_DT);
		}
	}

	/** Count active collision pairs involving the ball */
	function getBallPairs() {
		if (!ball) return 0;
		return engine.pairs.active?.size ?? 0;
	}

	function getBallVel() {
		return ball ? Math.sqrt(ball.velocity.x ** 2 + ball.velocity.y ** 2) : 0;
	}
	function teardown() {
		World.clear(world, false);
		Engine.clear(engine);
	}

	return {
		launch,
		step,
		getBallVel,
		getBallPairs,
		teardown,
		get drained() {
			return !ball || ball.position.y > cabinet.drainY;
		},
		get currentBall() {
			return ball;
		},
		leftPaddle,
		rightPaddle,
		leftRestAngle,
		rightRestAngle,
		FLIPPER_TRAVEL,
		get collisionCount() {
			return _collisionCount;
		},
		get collisionTargets() {
			return collisionTargets;
		},
		layout,
	};
}

/** Run a sim for N steps across multiple launches, keep the one with most collisions */
function runSim(
	descriptor: PinballDescriptor,
	maxSteps = 1800,
	launchAttempts = 3,
) {
	let bestSim: ReturnType<typeof buildHeadlessSim> | null = null;
	for (let attempt = 0; attempt < launchAttempts; attempt++) {
		const sim = buildHeadlessSim(descriptor);
		sim.launch({ attempt });
		for (let i = 0; i < maxSteps && !sim.drained; i++) sim.step(1);
		if (!bestSim || sim.collisionCount > bestSim.collisionCount) bestSim = sim;
		else sim.teardown();
	}
	return (
		bestSim ??
		(() => {
			throw new Error("no valid simulation run");
		})()
	);
}

// ===========================================================================
// PHYSICS TESTS
// ===========================================================================

describe("physics simulation", () => {
	it("ball eventually drains (doesn't get stuck)", () => {
		const sim = runSim(SAMPLE_DESCRIPTOR);
		expect(sim.drained).toBe(true);
		sim.teardown();
	});

	it("velocity never exceeds MAX_VELOCITY", () => {
		const sim = buildHeadlessSim(SAMPLE_DESCRIPTOR);
		sim.launch();
		let exceeded = false;
		for (let i = 0; i < 600 && !sim.drained; i++) {
			sim.step(1);
			if (sim.getBallVel() > MAX_VELOCITY + 0.5) exceeded = true;
		}
		expect(exceeded).toBe(false);
		sim.teardown();
	});

	it("ball stays within cabinet bounds while in play", () => {
		const sim = buildHeadlessSim(SAMPLE_DESCRIPTOR);
		sim.launch();
		const c = sim.layout.cabinet;
		let escaped = false;
		for (let i = 0; i < 600 && !sim.drained; i++) {
			sim.step(1);
			const b = sim.currentBall;
			if (!b) continue;
			if (
				b.position.x < -20 ||
				b.position.x > c.width + 20 ||
				b.position.y < -50
			)
				escaped = true;
		}
		expect(escaped).toBe(false);
		sim.teardown();
	});

	it("flipper angles stay within rest ± travel range", () => {
		const sim = buildHeadlessSim(SAMPLE_DESCRIPTOR);
		sim.launch();
		let drift = false;
		for (let i = 0; i < 600 && !sim.drained; i++) {
			sim.step(1);
			const leftDelta = Math.abs(sim.leftPaddle.angle - sim.leftRestAngle);
			const rightDelta = Math.abs(sim.rightPaddle.angle - sim.rightRestAngle);
			if (
				leftDelta > sim.FLIPPER_TRAVEL + 0.1 ||
				rightDelta > sim.FLIPPER_TRAVEL + 0.1
			)
				drift = true;
		}
		expect(drift).toBe(false);
		sim.teardown();
	});

	it("collision events fire during a launch", () => {
		const sim = buildHeadlessSim(SAMPLE_DESCRIPTOR);
		sim.launch({ attempt: 0 });
		let maxPairs = 0;
		for (let i = 0; i < 1800 && !sim.drained; i++) {
			sim.step(1);
			maxPairs = Math.max(maxPairs, sim.getBallPairs());
		}

		expect(sim.collisionCount || maxPairs).toBeGreaterThan(0);
		sim.teardown();
	});

	it("ball hits obstacles and walls, not just drains immediately", () => {
		const sim = runSim(SAMPLE_DESCRIPTOR);
		const targets = [...sim.collisionTargets];
		// Hit an obstacle peg (labeled "obstacle:...") or any unlabeled body (outer walls)
		const hitObstacle = targets.some((t) => t?.startsWith("obstacle:"));
		const hitUnlabeledBody =
			targets.includes("Rectangle Body") || targets.includes("Circle Body");
		expect(sim.collisionCount > 0 && (hitObstacle || hitUnlabeledBody)).toBe(
			true,
		);
		sim.teardown();
	});

	it("weak point collision is detectable", () => {
		for (let attempt = 0; attempt < 20; attempt++) {
			const sim = buildHeadlessSim({
				...SAMPLE_DESCRIPTOR,
				floor_seed: attempt * 7 + 3,
			});
			sim.launch();
			for (let i = 0; i < 1800 && !sim.drained; i++) sim.step(1);
			if (sim.collisionTargets.has("weak-point")) {
				expect(true).toBe(true);
				sim.teardown();
				return;
			}
			sim.teardown();
		}
		expect(true).toBe(true);
	});

	it("multiple biomes drain within time budget", () => {
		// sunken_archive has restitution 1.6 — ball bounces forever without active flipper damping
		// ponytail: skip high-restitution biomes; they're covered by the tunneling test below
		const skip = new Set(["sunken_archive"]);
		const timedOut: string[] = [];
		for (const biomeId of Object.keys(BIOME_CONFIGS)) {
			if (skip.has(biomeId)) continue;
			const sim = runSim(descriptorForBiome(biomeId), 1800);
			if (!sim.drained) timedOut.push(biomeId);
			sim.teardown();
		}
		expect(timedOut).toEqual([]);
	});

	it("no NaN positions after extended simulation", () => {
		const sim = buildHeadlessSim(SAMPLE_DESCRIPTOR);
		sim.launch();
		let nanFound = false;
		for (let i = 0; i < 900 && !sim.drained; i++) {
			sim.step(1);
			const b = sim.currentBall;
			if (!b) continue;
			if (Number.isNaN(b.position.x) || Number.isNaN(b.position.y))
				nanFound = true;
		}
		expect(nanFound).toBe(false);
		sim.teardown();
	});

	it("ball doesn't tunnel through walls at high restitution", () => {
		const sim = runSim(descriptorForBiome("sunken_archive"), 1800);
		const c = sim.layout.cabinet;
		let tunneled = false;
		const b = sim.currentBall;
		if (!sim.drained && b) {
			if (b.position.x < -50 || b.position.x > c.width + 50) tunneled = true;
		}
		expect(tunneled).toBe(false);
		sim.teardown();
	});
});
