import { Body, Bodies, World } from "../lib/matter";
import { BALL_R as BALL_RADIUS } from "../pinball/geometry";
import type { PinballRuntime } from "./runtime";

// Ball launch ----------------------------------------------------------------

function buildBall(runtime: PinballRuntime): Matter.Body {
	return Bodies.circle(
		runtime.cabinet.launchX,
		runtime.cabinet.launchY,
		BALL_RADIUS,
		{
			label: "pinball",
			restitution: 0.48,
			frictionAir: runtime.physicsSettings.ballDrag,
			collisionFilter: {
				mask: 0xffffffff,
				category: 2,
				group: 0,
			},
		},
	);
}

function launchBall(runtime: PinballRuntime): void {
	if (runtime.inPlay) return;
	Body.translate(runtime.hatch, {
		x: 0,
		y: runtime.cabinet.hatchTranslateY,
	});
	runtime.hatchUp = false;
	const b = buildBall(runtime);
	World.add(runtime.world, b);
	Body.setVelocity(b, {
		x: 0,
		y: -(25 + (Math.random() * 4 - 2)),
	});
	runtime.ball = b;
	runtime.inPlay = true;
}



// ---------------------------------------------------------------------------
// Keyboard event handlers
// ---------------------------------------------------------------------------

function onKeyDown(e: KeyboardEvent, runtime: PinballRuntime): void {
	if (e.code === "ArrowLeft" && !runtime.leftFired) {
		runtime.leftFired = true;
	} else if (e.code === "ArrowRight" && !runtime.rightFired) {
		runtime.rightFired = true;
	} else if (e.code === "ArrowUp" || e.code === "Space") {
		e.preventDefault();
		launchBall(runtime);
	}
}

function onKeyUp(e: KeyboardEvent, runtime: PinballRuntime): void {
	if (e.code === "ArrowLeft") runtime.leftFired = false;
	if (e.code === "ArrowRight") runtime.rightFired = false;
}

// ---------------------------------------------------------------------------
// Public — attach listeners, return teardown
// ---------------------------------------------------------------------------

export function attachFlipperInput(runtime: PinballRuntime): () => void {
	const keydown = (e: KeyboardEvent) => onKeyDown(e, runtime);
	const keyup = (e: KeyboardEvent) => onKeyUp(e, runtime);
	document.addEventListener("keydown", keydown);
	document.addEventListener("keyup", keyup);
	return () => {
		document.removeEventListener("keydown", keydown);
		document.removeEventListener("keyup", keyup);
	};
}
