import { Engine } from "../lib/matter";
import { renderScene } from "./draw";
import type { PinballRuntime } from "./runtime";

// ---------------------------------------------------------------------------
// Fixed-timestep render loop
// ---------------------------------------------------------------------------

const FIXED_DT = 1000 / 60; // ~16.67 ms

function physicsStep(runtime: PinballRuntime): void {
	runtime.accumulator += runtime.lastTs === 0
		? FIXED_DT
		: Math.min(performance.now() - runtime.lastTs, FIXED_DT * 5);
	while (runtime.accumulator >= FIXED_DT) {
		Engine.update(runtime.engine, FIXED_DT);
		runtime.accumulator -= FIXED_DT;
	}
}

function frame(ts: number, runtime: PinballRuntime): void {
	runtime.lastTs = ts;
	physicsStep(runtime);
	renderScene(runtime);
	runtime.rafId = requestAnimationFrame((t) => frame(t, runtime));
}

// ---------------------------------------------------------------------------
// Public — start the loop
// ---------------------------------------------------------------------------

export function startRenderLoop(runtime: PinballRuntime): void {
	runtime.rafId = requestAnimationFrame((ts: number) => {
		runtime.lastTs = ts;
		frame(ts, runtime);
	});
}
