import Matter, { Body, Bodies, Constraint } from "../lib/matter";
import type { CabinetFlipperDef } from "../pinball";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const MAX_VELOCITY = 50;
export const OBSTACLE_HIT_COOLDOWN = 80; // ms — prevent multi-peg double-scoring

const FLIPPER_TRAVEL = (Math.PI * 58) / 180; // 58° swing
const FLIP_VEL = 0.45; // rad/step

// ---------------------------------------------------------------------------
// Flipper body/constraint creation
// ---------------------------------------------------------------------------

export interface FlipperBodies {
	paddle: Matter.Body;
	hinge: Matter.Body;
	block: Matter.Body;
	constraint: Matter.Constraint;
	weight: Matter.Constraint;
	restAngle: number;
}

export function createFlipperBodies(
	def: CabinetFlipperDef,
	label: string,
	bufferGroup: number,
	isLeft: boolean,
): FlipperBodies {
	const paddle = Bodies.trapezoid(
		def.paddleX,
		def.paddleY,
		25,
		80,
		0.25,
		{
			label,
			angle: isLeft ? (2 * Math.PI) / 3 : (4 * Math.PI) / 3,
			chamfer: { radius: 10 },
			collisionFilter: {
				group: bufferGroup,
				category: 0xffffffff,
				mask: 2,
			},
		},
	);
	const hinge = Bodies.circle(def.hingeX, def.hingeY, 5, { isStatic: true });
	const block = Bodies.rectangle(def.blockX, def.blockY, 30, 30, {
		isStatic: false,
	});
	const constraint = Constraint.create({
		bodyA: paddle,
		bodyB: hinge,
		pointA: def.pivotOffset,
		stiffness: 0,
		length: 0,
	});
	const weight = Constraint.create({
		bodyA: paddle,
		bodyB: block,
		pointA: def.weightOffset,
		stiffness: 0.75,
		length: 1,
	});
	return {
		paddle,
		hinge,
		block,
		constraint,
		weight,
		restAngle: paddle.angle,
	};
}

// ---------------------------------------------------------------------------
// Flipper control — rate-limited drive with symmetric active return
// ---------------------------------------------------------------------------

export function applyFlipperControl(
	paddle: Matter.Body,
	fired: boolean,
	restAngle: number,
	isLeft: boolean,
): void {
	if (fired) {
		const target = isLeft
			? restAngle - FLIPPER_TRAVEL
			: restAngle + FLIPPER_TRAVEL;
		if (isLeft
			? paddle.angle > target + FLIP_VEL
			: paddle.angle < target - FLIP_VEL
		) {
			Body.setAngularVelocity(paddle, isLeft ? -FLIP_VEL : FLIP_VEL);
		} else {
			Body.setAngle(paddle, target);
			Body.setAngularVelocity(paddle, 0);
		}
		// Hard stop: clamp any overshoot past the engaged angle
		if (isLeft ? paddle.angle < target : paddle.angle > target) {
			Body.setAngle(paddle, target);
			Body.setAngularVelocity(paddle, 0);
		}
	} else {
		// Active return toward rest — symmetric with fire, no spring-dependency
		if (isLeft
			? paddle.angle < restAngle - FLIP_VEL
			: paddle.angle > restAngle + FLIP_VEL
		) {
			Body.setAngularVelocity(paddle, isLeft ? FLIP_VEL : -FLIP_VEL);
		} else {
			Body.setAngle(paddle, restAngle);
			Body.setAngularVelocity(paddle, 0);
		}
	}
}
