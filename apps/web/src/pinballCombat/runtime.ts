import type Matter from "matter-js";
import type { FlipperBodies } from "./physics";
import type {
	PinballTableLayout,
	ObstacleSpec,
	BumperShape,
} from "../pinball/types";

// ---------------------------------------------------------------------------
// Shared mutable state bag — replaces closure captures across split modules
// ---------------------------------------------------------------------------

export interface PinballRuntime {
	engine: Matter.Engine;
	world: Matter.World;
	cabinet: PinballTableLayout["cabinet"];
	theme: PinballTableLayout["theme"];
	obstacleSpecs: ObstacleSpec[];
	wpSpec: PinballTableLayout["weakPoint"];
	physicsSettings: PinballTableLayout["physics"];

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
	obstacleShapeMap: Map<string, BumperShape>;

	ball: Matter.Body | null;
	inPlay: boolean;
	leftFired: boolean;
	rightFired: boolean;
	pendingScore: number;
	equippedWeaponType: string | null;
	orbFlash: Map<string, number>;
	weakPointFlash: number;
	lastHitTime: Map<string, number>;
	hatchUp: boolean;

	canvas: HTMLCanvasElement;
	ctx: CanvasRenderingContext2D;

	rafId: number;
	lastTs: number;
	accumulator: number;

	onPinballStrike: (score: number) => void;
	onBallDrain: () => void;
}
