/** Minimal Matter.js sanity check — do collision events fire in Vitest? */

import { describe, it, expect } from "vitest";
import Matter from "matter-js";

describe("matter-js sanity", () => {
	it("collisionStart fires for ball hitting ground", () => {
		const { Engine, World, Bodies, Body, Events } = Matter;
		const engine = Engine.create();
		engine.gravity.y = 1;
		const { world } = engine;

		let collided = false;

		// Ground
		const ground = Bodies.rectangle(400, 600, 800, 60, { isStatic: true });
		// Ball dropped above ground
		const ball = Bodies.circle(400, 100, 20, { label: "pinball" });

		Events.on(engine, "collisionStart", (event) => {
			console.log("pairs:", event.pairs.length);
			for (const pair of event.pairs) {
				console.log("  collision:", pair.bodyA.label || "static", pair.bodyB.label || "static");
			}
			collided = true;
		});

		World.add(world, [ground, ball]);

		// Run for enough steps that the ball should hit the ground
		for (let i = 0; i < 300; i++) Engine.update(engine, 1000 / 60);

		expect(collided).toBe(true);
		Engine.clear(engine);
		World.clear(world, false);
	});

	it("collisionStart fires with constraints and bufferGroup present", () => {
		const { Engine, World, Bodies, Body, Constraint, Events } = Matter;
		const engine = Engine.create();
		engine.gravity.y = 1;
		const { world } = engine;

		let collided = false;

		// Buffer group (like flippers)
		const bufferGroup = Body.nextGroup(false);

		// Static obstacle
		const peg = Bodies.circle(300, 400, 26, {
			isStatic: true, label: "obstacle:test",
			restitution: 1.5, friction: 0,
		});

		// Flipper-like trapezoid with constraint
		const paddle = Bodies.trapezoid(200, 550, 25, 80, 0.25, {
			label: "leftPaddle", angle: (2 * Math.PI) / 3, chamfer: { radius: 10 },
			collisionFilter: { group: bufferGroup, category: 0xffffffff, mask: 2 },
		});
		const hinge = Bodies.circle(182, 539, 5, { isStatic: true });
		const block = Bodies.rectangle(210, 560, 30, 30, { isStatic: false });
		const pivotConstraint = Constraint.create({ bodyA: paddle, bodyB: hinge, pointA: { x: -18, y: -11 }, stiffness: 0, length: 0 });
		const weightConstraint = Constraint.create({ bodyA: paddle, bodyB: block, pointA: { x: 13, y: 11 }, stiffness: 0.75, length: 1 });

		// Ball with category 2 (like pinball)
		const ball = Bodies.circle(300, 100, 14, {
			label: "pinball", restitution: 0.48, frictionAir: 0.005,
			collisionFilter: { mask: 0xffffffff, category: 2, group: 0 },
		});

		Events.on(engine, "collisionStart", (event) => {
			for (const pair of event.pairs) {
				console.log("  collision:", pair.bodyA.label || "static", pair.bodyB.label || "static");
			}
			collided = true;
		});

		World.add(world, [peg, paddle, hinge, block, pivotConstraint, weightConstraint, ball]);

		// beforeUpdate handler (like velocity clamp + flipper control)
		Events.on(engine, "beforeUpdate", () => {
			if (ball.position.y < 1000) {
				Body.setVelocity(ball, {
					x: Math.max(Math.min(ball.velocity.x, 50), -50),
					y: Math.max(Math.min(ball.velocity.y, 50), -50),
				});
			}
		});

		for (let i = 0; i < 600; i++) Engine.update(engine, 1000 / 60);

		console.log("ball pos:", ball.position.x.toFixed(1), ball.position.y.toFixed(1));
		expect(collided).toBe(true);
		Engine.clear(engine);
		World.clear(world, false);
	});
});
