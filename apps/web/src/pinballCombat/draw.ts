import type Matter from "matter-js";
import type { ObstacleSpec, BumperShape } from "../pinball/types";
import { WEAPON_ORB } from "./weapons";
import { BALL_R as BALL_RADIUS } from "../pinball/geometry";
import type { PinballRuntime } from "./runtime";

// Low-level canvas primitives -----------------------------------------------

export function drawPoly(
	body: Matter.Body,
	fill: string,
	ctx: CanvasRenderingContext2D,
): void {
	const v = body.vertices;
	if (!v.length) return;
	ctx.beginPath();
	ctx.moveTo(v[0].x, v[0].y);
	for (let i = 1; i < v.length; i++) ctx.lineTo(v[i].x, v[i].y);
	ctx.closePath();
	ctx.fillStyle = fill;
	ctx.fill();
}

export function strokePoly(
	body: Matter.Body,
	color: string,
	ctx: CanvasRenderingContext2D,
): void {
	ctx.strokeStyle = color;
	ctx.lineWidth = 2;
	const v = body.vertices;
	ctx.beginPath();
	ctx.moveTo(v[0].x, v[0].y);
	for (let j = 1; j < v.length; j++) ctx.lineTo(v[j].x, v[j].y);
	ctx.closePath();
	ctx.stroke();
}

export function drawCirc(
	x: number,
	y: number,
	r: number,
	fill: string,
	strokeCol: string | undefined,
	ctx: CanvasRenderingContext2D,
): void {
	ctx.beginPath();
	ctx.arc(x, y, r, 0, Math.PI * 2);
	ctx.fillStyle = fill;
	ctx.fill();
	if (strokeCol) {
		ctx.strokeStyle = strokeCol;
		ctx.lineWidth = 2;
		ctx.stroke();
	}
}

// Obstacle drawing (internal helpers) ---------------------------------------

function drawPost(
	peg: { x: number; y: number; radius: number },
	walls: string,
	ctx: CanvasRenderingContext2D,
): void {
	ctx.save();
	ctx.globalAlpha = 0.55;
	drawCirc(peg.x, peg.y, peg.radius, walls, undefined, ctx);
	ctx.restore();
}

function getBumperFill(
	obs: ObstacleSpec,
	weaponOrbLabel: string | null,
	flashing: boolean,
	theme: PinballRuntime["theme"],
): { fill: string; stroke: string | undefined; isActive: boolean } {
	const isActive = obs.weaponLabel === weaponOrbLabel;
	let fill: string;
	if (flashing) {
		fill = theme.orbHit;
	} else if (isActive) {
		fill = "#7a5fd8";
	} else {
		fill = theme.orbs;
	}
	const stroke =
		isActive && !flashing ? "rgba(255, 220, 140, 0.7)" : undefined;
	return { fill, stroke, isActive };
}

function drawBumperShape(
	x: number,
	y: number,
	body: Matter.Body,
	shape: string,
	fill: string,
	stroke: string | undefined,
	radius: number,
	ctx: CanvasRenderingContext2D,
): void {
	if (shape === "circle") {
		drawCirc(x, y, radius, fill, stroke, ctx);
	} else {
		drawPoly(body, fill, ctx);
		if (stroke) strokePoly(body, stroke, ctx);
	}
}

function drawBumper(
	obs: ObstacleSpec,
	peg: { x: number; y: number; radius: number },
	body: Matter.Body,
	flashing: boolean,
	weaponOrbLabel: string | null,
	shapeMap: Map<string, BumperShape>,
	theme: PinballRuntime["theme"],
	ctx: CanvasRenderingContext2D,
): void {
	const { fill, stroke, isActive } = getBumperFill(
		obs, weaponOrbLabel, flashing, theme,
	);
	const shape = shapeMap.get(obs.id) ?? "circle";
	if (isActive && !flashing) {
		ctx.save();
		ctx.shadowColor = "rgba(214, 179, 116, 0.6)";
		ctx.shadowBlur = 12;
	}
	drawBumperShape(
		body.position.x, body.position.y, body,
		shape, fill, stroke, peg.radius, ctx,
	);
	if (isActive && !flashing) ctx.restore();
}

function drawEnemyObstacle(
	body: Matter.Body,
	peg: { x: number; y: number; radius: number },
	flashing: boolean,
	theme: PinballRuntime["theme"],
	ctx: CanvasRenderingContext2D,
): void {
	ctx.save();
	ctx.translate(body.position.x, body.position.y);
	ctx.rotate(Math.PI / 4);
	const r = peg.radius;
	ctx.fillStyle = flashing ? theme.orbHit : theme.obstacle;
	if (theme.obstacleStyle !== "default") {
		ctx.shadowColor = theme.obstacle;
		ctx.shadowBlur = 8;
	}
	ctx.fillRect(-r * 0.7, -r * 0.7, r * 1.4, r * 1.4);
	ctx.restore();
}

function drawObstacle(
	obs: ObstacleSpec,
	pegs: { id: string; x: number; y: number; radius: number }[],
	bodies: Matter.Body[],
	flashing: boolean,
	runtime: PinballRuntime,
): void {
	const weaponOrbLabel = runtime.equippedWeaponType
		? WEAPON_ORB[runtime.equippedWeaponType.toLowerCase()]
		: null;
	for (let i = 0; i < pegs.length; i++) {
		const peg = pegs[i];
		const body = bodies[i];
		if (!body) continue;
		if (obs.kind === "post") {
			drawPost(peg, runtime.theme.walls, runtime.ctx);
		} else if (obs.kind === "bumper") {
			drawBumper(
				obs, peg, body, flashing, weaponOrbLabel,
				runtime.obstacleShapeMap, runtime.theme, runtime.ctx,
			);
		} else {
			drawEnemyObstacle(body, peg, flashing, runtime.theme, runtime.ctx);
		}
	}
}

// Scene-level render helpers -------------------------------------------------

function renderWalls(runtime: PinballRuntime): void {
	const { ctx, theme } = runtime;
	for (const w of runtime.outerWalls) drawPoly(w, theme.walls, ctx);
	if (runtime.hatchUp) drawPoly(runtime.hatch, theme.walls, ctx);
	ctx.save();
	ctx.globalAlpha = 0.55;
	for (const w of runtime.guardrailBodies) drawPoly(w, theme.walls, ctx);
	ctx.restore();
}

function renderAllObstacles(runtime: PinballRuntime): void {
	const now = performance.now();
	for (const obs of runtime.obstacleSpecs) {
		const bodies = runtime.parentPegBodies.get(obs.id);
		if (!bodies || !bodies.length) continue;
		const flashing = now < (runtime.orbFlash.get(obs.id) ?? 0);
		drawObstacle(obs, obs.pegs, bodies, flashing, runtime);
	}
}

function renderWeakPoint(runtime: PinballRuntime): void {
	const { ctx, theme, wpSpec } = runtime;
	const now = performance.now();
	const pulse = Math.sin(now / 250) * 0.25 + 0.75;
	const wpFlash = now < runtime.weakPointFlash;
	ctx.save();
	ctx.shadowColor = theme.weakPoint;
	ctx.shadowBlur = wpFlash ? 28 : 10 * pulse;
	drawCirc(
		wpSpec.x, wpSpec.y, wpSpec.radius,
		wpFlash ? "#ffffff" : theme.weakPoint, undefined, ctx,
	);
	ctx.strokeStyle = wpFlash ? "#ffffff" : theme.weakPoint;
	ctx.lineWidth = 2;
	ctx.globalAlpha = pulse;
	ctx.beginPath();
	ctx.arc(wpSpec.x, wpSpec.y, wpSpec.radius + 6, 0, Math.PI * 2);
	ctx.stroke();
	ctx.restore();
}

function renderHingePins(runtime: PinballRuntime): void {
	const { ctx, cabinet } = runtime;
	ctx.fillStyle = "rgba(255,255,255,0.5)";
	ctx.beginPath();
	ctx.arc(cabinet.flipperLeft.hingeX, cabinet.flipperLeft.hingeY, 4, 0, Math.PI * 2);
	ctx.fill();
	ctx.beginPath();
	ctx.arc(cabinet.flipperRight.hingeX, cabinet.flipperRight.hingeY, 4, 0, Math.PI * 2);
	ctx.fill();
}

function renderScoreIndicator(runtime: PinballRuntime): void {
	const { ctx, theme, cabinet, pendingScore } = runtime;
	if (pendingScore <= 0) return;
	ctx.save();
	ctx.font = "bold 13px monospace";
	ctx.fillStyle = theme.weakPoint;
	ctx.shadowColor = theme.weakPoint;
	ctx.shadowBlur = 6;
	ctx.fillText(`▶ ${pendingScore}`, 10, cabinet.height - 56);
	ctx.restore();
}

// Public — render the full scene for the current frame -----------------------

export function renderScene(runtime: PinballRuntime): void {
	const { ctx, theme, cabinet } = runtime;
	ctx.fillStyle = theme.bg;
	ctx.fillRect(0, 0, cabinet.width, cabinet.height);
	renderWalls(runtime);
	renderAllObstacles(runtime);
	renderWeakPoint(runtime);
	drawPoly(runtime.left.paddle, theme.paddle, ctx);
	drawPoly(runtime.right.paddle, theme.paddle, ctx);
	renderHingePins(runtime);
	if (runtime.ball) {
		drawCirc(
			runtime.ball.position.x, runtime.ball.position.y,
			BALL_RADIUS, theme.ball, undefined, ctx,
		);
	}
	renderScoreIndicator(runtime);
}
