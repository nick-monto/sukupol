import { Body, Events, Composite } from "../lib/matter";
import type Matter from "matter-js";
import { WEAPON_ORB } from "./weapons";
import { MAX_VELOCITY, OBSTACLE_HIT_COOLDOWN, applyFlipperControl } from "./physics";
import type { PinballRuntime } from "./runtime";

// ---------------------------------------------------------------------------
// collisionStart — identify pinball collisions
// ---------------------------------------------------------------------------

/** Extract the pinball body from a collision pair, if present. */
function findPinballPair(
	pair: { bodyA: Matter.Body; bodyB: Matter.Body },
): { pinball: Matter.Body; other: Matter.Body } | null {
	const { bodyA, bodyB } = pair;
	let pinball: Matter.Body | null = null;
	if (bodyA.label === "pinball") pinball = bodyA;
	else if (bodyB.label === "pinball") pinball = bodyB;
	if (!pinball) return null;
	return { pinball, other: pinball === bodyA ? bodyB : bodyA };
}

function handleWeakPointCollision(
	runtime: PinballRuntime,
	score: number,
): void {
	runtime.weakPointFlash = performance.now() + 350;
	runtime.pendingScore = 0;
	if (score > 0) runtime.onPinballStrike(score);
}

function handleObstacleCollision(
	runtime: PinballRuntime,
	obsId: string,
): void {
	const obs = runtime.obstacleSpecMap.get(obsId);
	if (!obs) return;

	const now = performance.now();
	const lastHit = runtime.lastHitTime.get(obsId) ?? 0;
	if (now - lastHit < OBSTACLE_HIT_COOLDOWN) return;
	runtime.lastHitTime.set(obsId, now);

	const weaponOrbLabel = runtime.equippedWeaponType
		? WEAPON_ORB[runtime.equippedWeaponType.toLowerCase()]
		: null;
	const bonus =
		obs.weaponLabel && weaponOrbLabel === obs.weaponLabel ? 2 : 1;
	runtime.pendingScore += obs.scoreValue * bonus;

	if (obs.kind !== "post")
		runtime.orbFlash.set(obsId, performance.now() + 100);
}

function onCollisionStart(
	event: Matter.IEventCollision<Matter.Engine>,
	runtime: PinballRuntime,
): void {
	for (const pair of event.pairs) {
		const found = findPinballPair(pair);
		if (!found) continue;
		const { other } = found;

		if (other.label === "weak-point") {
			handleWeakPointCollision(runtime, runtime.pendingScore);
		} else if (other.label.startsWith("obstacle:")) {
			handleObstacleCollision(runtime, other.label.slice(9));
		}
	}
}

// ---------------------------------------------------------------------------
// beforeUpdate — velocity clamp + shooter-lane guard + flipper control
// ---------------------------------------------------------------------------

function clampVelocity(ball: Matter.Body, maxVel: number): void {
	Body.setVelocity(ball, {
		x: Math.max(Math.min(ball.velocity.x, maxVel), -maxVel),
		y: Math.max(Math.min(ball.velocity.y, maxVel), -maxVel),
	});
}

function applyShooterGuard(
	ball: Matter.Body,
	runtime: PinballRuntime,
): void {
	const { cabinet } = runtime;
	if (
		ball.position.x > cabinet.shooterLaneGuardX &&
		ball.velocity.y > 0 &&
		ball.position.y > cabinet.hatch.y + cabinet.hatchTranslateY &&
		ball.position.y < cabinet.flipperLeft.paddleY - 20
	) {
		Body.setVelocity(ball, { x: 0, y: -10 });
	}
}

function updateFlippers(runtime: PinballRuntime): void {
	applyFlipperControl(
		runtime.left.paddle,
		runtime.leftFired,
		runtime.left.restAngle,
		true,
	);
	applyFlipperControl(
		runtime.right.paddle,
		runtime.rightFired,
		runtime.right.restAngle,
		false,
	);
}

function onBeforeUpdate(runtime: PinballRuntime): void {
	if (!runtime.ball) {
		updateFlippers(runtime);
		return;
	}
	clampVelocity(runtime.ball, MAX_VELOCITY);
	applyShooterGuard(runtime.ball, runtime);
	updateFlippers(runtime);
}

// ---------------------------------------------------------------------------
// afterUpdate — drain detection + hatch close
// ---------------------------------------------------------------------------

function handleDrain(runtime: PinballRuntime): void {
	const drainStrike = Math.floor(runtime.pendingScore / 2);
	runtime.pendingScore = Math.ceil(runtime.pendingScore / 2);
	if (drainStrike > 0) runtime.onPinballStrike(drainStrike);
	Composite.remove(runtime.world, runtime.ball!);
	runtime.ball = null;
	runtime.inPlay = false;
	runtime.onBallDrain();
}

function onAfterUpdate(runtime: PinballRuntime): void {
	if (!runtime.ball || !runtime.inPlay) return;
	if (runtime.ball.position.y > runtime.cabinet.drainY) {
		handleDrain(runtime);
		return;
	}
	if (
		runtime.ball.position.x < runtime.cabinet.hatch.x &&
		!runtime.hatchUp
	) {
		Body.translate(runtime.hatch, {
			x: 0,
			y: -runtime.cabinet.hatchTranslateY,
		});
		runtime.hatchUp = true;
	}
}

// ---------------------------------------------------------------------------
// Public — attach all handlers to the engine
// ---------------------------------------------------------------------------

export function attachCollisionHandlers(runtime: PinballRuntime): void {
	Events.on(runtime.engine, "collisionStart", (event: Matter.IEventCollision<Matter.Engine>) =>
		onCollisionStart(event, runtime),
	);
	Events.on(runtime.engine, "beforeUpdate", () =>
		onBeforeUpdate(runtime),
	);
	Events.on(runtime.engine, "afterUpdate", () =>
		onAfterUpdate(runtime),
	);
}
