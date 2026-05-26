import Matter from "matter-js";
import type { PinballTableLayout, ObstacleSpec, BumperShape } from "./pinballTable";

const { Engine, World, Bodies, Body, Constraint, Events, Composite } = Matter;

// Weapon type → orb obstacle id (for 2× score bonus when weapon matches orb)
const WEAPON_ORB: Record<string, string> = {
  sword:  "orb-left",
  axe:    "orb-left",
  staff:  "orb-center",
  wand:   "orb-center",
  bow:    "orb-right",
  dagger: "orb-right",
};

// Weapon type → bumper shape + how many orbs (by ORB_LABEL_ORDER index) are reshaped
const WEAPON_BUMPER_SHAPE: Record<string, { shape: BumperShape; count: number }> = {
  sword:  { shape: "triangle", count: 2 },
  axe:    { shape: "square",   count: 3 },
  staff:  { shape: "pentagon", count: 1 },
  wand:   { shape: "pentagon", count: 2 },
  bow:    { shape: "triangle", count: 1 },
  dagger: { shape: "square",   count: 2 },
};
const ORB_LABEL_ORDER = ["orb-center", "orb-left", "orb-right"];

const MAX_VELOCITY = 50;
const BALL_RADIUS  = 14;

// ---------------------------------------------------------------------------
// Public API
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
  const { cabinet, physics, theme, obstacles: obstacleSpecs, weakPoint: wpSpec } = layout;
  const { width: W, height: H } = cabinet;

  canvas.width  = W;
  canvas.height = H;

  const ctx = canvas.getContext("2d")!;

  // ── Engine ────────────────────────────────────────────────────────────────
  const engine = Engine.create();
  engine.gravity.y = physics.gravity;
  const { world } = engine;

  // Non-colliding group shared by paddles and buffer circles so they ignore
  // each other while the ball (category 2) still hits paddle surfaces.
  const bufferGroup = Body.nextGroup(false);

  // ── Weapon-driven bumper shape map (computed once at setup) ──────────────
  const _initWeapon = opts.equippedWeaponType?.toLowerCase() ?? null;
  const _shapeInfo  = _initWeapon ? WEAPON_BUMPER_SHAPE[_initWeapon] : null;
  const obstacleShapeMap = new Map<string, BumperShape>();
  if (_shapeInfo) {
    for (let i = 0; i < _shapeInfo.count; i++) {
      const obs = obstacleSpecs.find(o => o.weaponLabel === ORB_LABEL_ORDER[i]);
      if (obs) obstacleShapeMap.set(obs.id, _shapeInfo.shape);
    }
  }

  // ── Fast obstacle lookup (id → spec + body) ────────────────────────────
  const obstacleSpecMap = new Map<string, ObstacleSpec>(obstacleSpecs.map(o => [o.id, o]));
  const obstacleBodyMap = new Map<string, Matter.Body>();

  const allObstacleBodies: Matter.Body[] = obstacleSpecs.map(obs => {
    const bodyOpts = {
      label: `obstacle:${obs.id}`,
      isStatic: true,
      restitution: obs.kind === "post" ? 0.4 : physics.bumperRestitution,
      friction: 0,
    };
    const shape = obstacleShapeMap.get(obs.id) ?? "circle";
    const sides = shape === "triangle" ? 3 : shape === "square" ? 4 : shape === "pentagon" ? 5 : 0;
    const b = sides > 0
      ? Bodies.polygon(obs.x, obs.y, sides, obs.radius, bodyOpts)
      : Bodies.circle(obs.x, obs.y, obs.radius, bodyOpts);
    obstacleBodyMap.set(obs.id, b);
    return b;
  });

  // ── Weak-point body ────────────────────────────────────────────────────
  const weakPointBody = Bodies.circle(wpSpec.x, wpSpec.y, wpSpec.radius, {
    label: "weak-point",
    isStatic: true,
    restitution: physics.bumperRestitution,
    friction: 0,
  });

  // ── Outer walls ────────────────────────────────────────────────────────
  const outerWalls = cabinet.outerWalls.map(w =>
    Bodies.rectangle(w.x, w.y, w.w, w.h, {
      isStatic: true, angle: w.angle, restitution: 0.2, friction: 0.05,
      ...(w.chamfer ? { chamfer: { radius: w.chamfer } } : {}),
    }),
  );

  // ── Hatch ─────────────────────────────────────────────────────────────
  const hatch = Bodies.rectangle(cabinet.hatch.x, cabinet.hatch.y, 130, 20, {
    label: "hatch", isStatic: true, angle: Math.PI / 2, chamfer: { radius: 10 },
  });
  let hatchUp = true;

  // ── Left flipper ──────────────────────────────────────────────────────
  const fl = cabinet.flipperLeft;
  const leftPaddle = Bodies.trapezoid(fl.paddleX, fl.paddleY, 25, 80, 0.25, {
    label: "leftPaddle", angle: 2 * Math.PI / 3, chamfer: { radius: 10 },
    collisionFilter: { group: bufferGroup, category: 0xFFFFFFFF, mask: 2 },
  });
  const leftHinge = Bodies.circle(fl.hingeX, fl.hingeY, 5, { isStatic: true });
  const leftBlock = Bodies.rectangle(fl.blockX, fl.blockY, 30, 30, { isStatic: false });
  const leftConstraint = Constraint.create({
    bodyA: leftPaddle, bodyB: leftHinge,
    pointA: fl.pivotOffset, stiffness: 0, length: 0,
  });
  const leftWeight = Constraint.create({
    bodyA: leftPaddle, bodyB: leftBlock,
    pointA: fl.weightOffset, stiffness: 0.75, length: 1,
  });

  // ── Right flipper ─────────────────────────────────────────────────────
  const fr = cabinet.flipperRight;
  const rightPaddle = Bodies.trapezoid(fr.paddleX, fr.paddleY, 25, 80, 0.25, {
    label: "rightPaddle", angle: 4 * Math.PI / 3, chamfer: { radius: 10 },
    collisionFilter: { group: bufferGroup, category: 0xFFFFFFFF, mask: 2 },
  });
  const rightHinge = Bodies.circle(fr.hingeX, fr.hingeY, 5, { isStatic: true });
  const rightBlock = Bodies.rectangle(fr.blockX, fr.blockY, 30, 30, { isStatic: false });
  const rightConstraint = Constraint.create({
    bodyA: rightPaddle, bodyB: rightHinge,
    pointA: fr.pivotOffset, stiffness: 0, length: 0,
  });
  const rightWeight = Constraint.create({
    bodyA: rightPaddle, bodyB: rightBlock,
    pointA: fr.weightOffset, stiffness: 0.75, length: 1,
  });

  // Rest angles captured at creation; used to enforce travel limits
  const leftRestAngle  = leftPaddle.angle;
  const rightRestAngle = rightPaddle.angle;
  // 58° swing — places the rest position at ~117° from the downward vertical,
  // matching the 115-120° / 55-60° spec
  const FLIPPER_TRAVEL = Math.PI * 58 / 180;

  // ── Buffer circles ─────────────────────────────────────────────────────
  const buffers = cabinet.buffers.map(b => {
    const body = Bodies.circle(b.x, b.y, 50, { label: "buffer", isStatic: true });
    body.collisionFilter = { group: bufferGroup };
    return body;
  });

  // ── Inlane guide walls — short wall segments flanking each flipper hinge ──
  const guardrailBodies = cabinet.inlaneWalls.map(w =>
    Bodies.rectangle(w.x, w.y, w.w, w.h, {
      label: "guardrail", isStatic: true, angle: w.angle,
      restitution: 0.25, friction: 0.1,
      ...(w.chamfer ? { chamfer: { radius: w.chamfer } } : {}),
    }),
  );

  // ── Add everything to world ────────────────────────────────────────────
  World.add(world, [
    ...allObstacleBodies,
    weakPointBody,
    ...outerWalls,
    hatch,
    leftPaddle,  leftHinge,  leftBlock,  leftConstraint,  leftWeight,
    rightPaddle, rightHinge, rightBlock, rightConstraint, rightWeight,
    ...buffers,
    ...guardrailBodies,
  ]);

  // ── Runtime state ──────────────────────────────────────────────────────
  let ball: Matter.Body | null = null;
  let inPlay        = false;
  let leftFired     = false;
  let rightFired    = false;
  let pendingScore  = 0;
  let equippedWeaponType: string | null = opts.equippedWeaponType ?? null;

  // Flash state: obstacle id → expiry ms; weak-point expiry
  const orbFlash       = new Map<string, number>();
  let   weakPointFlash = 0;

  // ── Hatch helpers ──────────────────────────────────────────────────────
  function openHatch()  { Body.translate(hatch, { x: 0, y:  cabinet.hatchTranslateY }); hatchUp = false; }
  function closeHatch() { Body.translate(hatch, { x: 0, y: -cabinet.hatchTranslateY }); hatchUp = true;  }

  // ── Ball launch ────────────────────────────────────────────────────────
  function launchBall(): void {
    if (inPlay) return;
    openHatch();
    const b = Bodies.circle(cabinet.launchX, cabinet.launchY, BALL_RADIUS, {
      label: "pinball", restitution: 0.48, frictionAir: physics.ballDrag,
      collisionFilter: { mask: 0xFFFFFFFF, category: 2, group: 0 },
    });
    World.add(world, b);
    Body.setVelocity(b, { x: 0, y: -(25 + (Math.random() * 4 - 2)) });
    ball  = b;
    inPlay = true;
  }

  // ── Collision events ───────────────────────────────────────────────────
  Events.on(engine, "collisionStart", (event: Matter.IEventCollision<Matter.Engine>) => {
    for (const pair of event.pairs) {
      const { bodyA, bodyB } = pair;
      if (bodyB.label !== "pinball") continue;

      if (bodyA.label === "weak-point") {
        // Convert full accumulated score to a damage strike
        weakPointFlash = performance.now() + 350;
        const score = pendingScore;
        pendingScore  = 0;
        if (score > 0) opts.onPinballStrike(score);
        continue;
      }

      if (bodyA.label.startsWith("obstacle:")) {
        const obsId = bodyA.label.slice(9);
        const obs   = obstacleSpecMap.get(obsId);
        if (!obs) continue;
        const weaponOrbLabel = equippedWeaponType
          ? WEAPON_ORB[equippedWeaponType.toLowerCase()] : null;
        const bonus = (obs.weaponLabel && weaponOrbLabel === obs.weaponLabel) ? 2 : 1;
        pendingScore += obs.scoreValue * bonus;
        // Posts score silently; bumpers and enemy obstacles flash
        if (obs.kind !== "post") orbFlash.set(obsId, performance.now() + 100);
      }
    }
  });

  // ── beforeUpdate: velocity clamp + shooter-lane guard + flipper control ───
  Events.on(engine, "beforeUpdate", () => {
    // Ball velocity clamp + shooter-lane guard
    if (ball) {
      Body.setVelocity(ball, {
        x: Math.max(Math.min(ball.velocity.x, MAX_VELOCITY), -MAX_VELOCITY),
        y: Math.max(Math.min(ball.velocity.y, MAX_VELOCITY), -MAX_VELOCITY),
      });
      // Guard only triggers when the ball is below the hatch opening (inside the
      // shooter lane return zone). Without the Y floor the guard fires anywhere
      // on the right side of the table, creating ghost bounces off the upper walls.
      if (
        ball.position.x > cabinet.shooterLaneGuardX &&
        ball.velocity.y > 0 &&
        ball.position.y > cabinet.hatch.y + cabinet.hatchTranslateY
      ) {
        Body.setVelocity(ball, { x: 0, y: -10 });
      }
    }
    // Flipper control: rate-limited drive with symmetric active return.
    // FLIP_VEL raised to 0.45 rad/step → 58° travel in ~2 steps (~33ms at 60fps).
    // Both fire and release are actively driven so return is as snappy as activation.
    // Dual hard clamps (engaged side + rest ceiling) prevent over-rotation in either
    // direction regardless of sub-step timing, fixing the occasional full-rotation bug.
    const FLIP_VEL = 0.45; // rad/step
    if (leftFired) {
      const leftTarget = leftRestAngle - FLIPPER_TRAVEL;
      if (leftPaddle.angle > leftTarget + FLIP_VEL) {
        Body.setAngularVelocity(leftPaddle, -FLIP_VEL);
      } else {
        Body.setAngle(leftPaddle, leftTarget);
        Body.setAngularVelocity(leftPaddle, 0);
      }
      // Hard stop: clamp any overshoot past the engaged angle
      if (leftPaddle.angle < leftTarget) {
        Body.setAngle(leftPaddle, leftTarget);
        Body.setAngularVelocity(leftPaddle, 0);
      }
    } else {
      // Active return toward rest — symmetric with fire, no spring-dependency
      if (leftPaddle.angle < leftRestAngle - FLIP_VEL) {
        Body.setAngularVelocity(leftPaddle, FLIP_VEL);
      } else {
        Body.setAngle(leftPaddle, leftRestAngle);
        Body.setAngularVelocity(leftPaddle, 0);
      }
    }
    if (rightFired) {
      const rightTarget = rightRestAngle + FLIPPER_TRAVEL;
      if (rightPaddle.angle < rightTarget - FLIP_VEL) {
        Body.setAngularVelocity(rightPaddle, FLIP_VEL);
      } else {
        Body.setAngle(rightPaddle, rightTarget);
        Body.setAngularVelocity(rightPaddle, 0);
      }
      // Hard stop: clamp any overshoot past the engaged angle
      if (rightPaddle.angle > rightTarget) {
        Body.setAngle(rightPaddle, rightTarget);
        Body.setAngularVelocity(rightPaddle, 0);
      }
    } else {
      // Active return toward rest — symmetric with fire, no spring-dependency
      if (rightPaddle.angle > rightRestAngle + FLIP_VEL) {
        Body.setAngularVelocity(rightPaddle, -FLIP_VEL);
      } else {
        Body.setAngle(rightPaddle, rightRestAngle);
        Body.setAngularVelocity(rightPaddle, 0);
      }
    }
  });

  // ── afterUpdate: drain + hatch close ──────────────────────────────────
  Events.on(engine, "afterUpdate", () => {
    if (!ball || !inPlay) return;
    if (ball.position.y > cabinet.drainY) {
      // Drain: deal half score, retain the other half
      const drainStrike = Math.floor(pendingScore / 2);
      pendingScore = Math.ceil(pendingScore / 2);
      if (drainStrike > 0) opts.onPinballStrike(drainStrike);
      Composite.remove(world, ball);
      ball   = null;
      inPlay = false;
      opts.onBallDrain();
      return;
    }
    if (ball.position.x < cabinet.hatch.x && !hatchUp) closeHatch();
  });

  // ── Keyboard ──────────────────────────────────────────────────────────
  function onKeyDown(e: KeyboardEvent): void {
    if (e.code === "ArrowLeft"  && !leftFired)  leftFired  = true;
    else if (e.code === "ArrowRight" && !rightFired) rightFired = true;
    else if (e.code === "ArrowUp" || e.code === "Space") { e.preventDefault(); launchBall(); }
  }

  function onKeyUp(e: KeyboardEvent): void {
    if (e.code === "ArrowLeft")  leftFired  = false;
    if (e.code === "ArrowRight") rightFired = false;
  }

  document.addEventListener("keydown", onKeyDown);
  document.addEventListener("keyup",   onKeyUp);

  // ── Draw helpers ───────────────────────────────────────────────────────
  function drawPoly(body: Matter.Body, fill: string): void {
    const v = body.vertices;
    if (!v.length) return;
    ctx.beginPath();
    ctx.moveTo(v[0].x, v[0].y);
    for (let i = 1; i < v.length; i++) ctx.lineTo(v[i].x, v[i].y);
    ctx.closePath();
    ctx.fillStyle = fill;
    ctx.fill();
  }

  function drawCirc(x: number, y: number, r: number, fill: string, strokeCol?: string): void {
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = fill;
    ctx.fill();
    if (strokeCol) { ctx.strokeStyle = strokeCol; ctx.lineWidth = 2; ctx.stroke(); }
  }

  function drawObstacle(obs: ObstacleSpec, body: Matter.Body, flashing: boolean): void {
    const { x, y } = body.position;
    const r = obs.radius;
    const weaponOrbLabel = equippedWeaponType
      ? WEAPON_ORB[equippedWeaponType.toLowerCase()] : null;

    if (obs.kind === "post") {
      ctx.save();
      ctx.globalAlpha = 0.55;
      drawCirc(x, y, r, theme.walls);
      ctx.restore();
    } else if (obs.kind === "bumper") {
      const isActive = obs.weaponLabel === weaponOrbLabel;
      const shape    = obstacleShapeMap.get(obs.id) ?? "circle";
      const fill     = flashing ? theme.orbHit : (isActive ? "#7a5fd8" : theme.orbs);
      const stroke   = isActive && !flashing ? "rgba(255, 220, 140, 0.7)" : undefined;

      if (isActive && !flashing) {
        ctx.save();
        ctx.shadowColor = "rgba(214, 179, 116, 0.6)";
        ctx.shadowBlur  = 12;
      }

      if (shape === "circle") {
        drawCirc(x, y, r, fill, stroke);
      } else {
        // Polygon — use the physics body vertices so shape matches collision hull
        drawPoly(body, fill);
        if (stroke) {
          ctx.strokeStyle = stroke;
          ctx.lineWidth   = 2;
          const v = body.vertices;
          ctx.beginPath();
          ctx.moveTo(v[0].x, v[0].y);
          for (let i = 1; i < v.length; i++) ctx.lineTo(v[i].x, v[i].y);
          ctx.closePath();
          ctx.stroke();
        }
      }

      if (isActive && !flashing) ctx.restore();
    } else {
      // Enemy-specific obstacle: rotated square (diamond style)
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(Math.PI / 4);
      ctx.fillStyle = flashing ? theme.orbHit : theme.obstacle;
      if (theme.obstacleStyle !== "default") {
        ctx.shadowColor = theme.obstacle;
        ctx.shadowBlur  = 8;
      }
      ctx.fillRect(-r * 0.7, -r * 0.7, r * 1.4, r * 1.4);
      ctx.restore();
    }
  }

  // ── Render loop ────────────────────────────────────────────────────────
  const FIXED_DT  = 1000 / 60;  // ~16.67 ms
  let   rafId     = 0;
  let   lastTs    = 0;
  let   accumulator = 0;

  function frame(ts: number): void {
    const elapsed = lastTs === 0 ? FIXED_DT : Math.min(ts - lastTs, FIXED_DT * 5);
    lastTs = ts;
    // Fixed-timestep sub-stepping: prevents jitter from variable frame times
    accumulator += elapsed;
    while (accumulator >= FIXED_DT) {
      Engine.update(engine, FIXED_DT);
      accumulator -= FIXED_DT;
    }

    ctx.fillStyle = theme.bg;
    ctx.fillRect(0, 0, W, H);

    for (const w of outerWalls) drawPoly(w, theme.walls);
    if (hatchUp) drawPoly(hatch, theme.walls);

    // Inlane guide walls
    ctx.save();
    ctx.globalAlpha = 0.55;
    for (const w of cabinet.inlaneWalls) drawPoly(w, theme.walls);
    ctx.restore();

    // Obstacles (orbs + enemy-specific)
    const now = performance.now();
    for (const obs of obstacleSpecs) {
      const body     = obstacleBodyMap.get(obs.id);
      if (!body) continue;
      const flashing = now < (orbFlash.get(obs.id) ?? 0);
      drawObstacle(obs, body, flashing);
    }

    // Weak-point — pulsing ring
    {
      const pulse     = Math.sin(now / 250) * 0.25 + 0.75;
      const wpFlash   = now < weakPointFlash;
      ctx.save();
      ctx.shadowColor = theme.weakPoint;
      ctx.shadowBlur  = wpFlash ? 28 : 10 * pulse;
      drawCirc(wpSpec.x, wpSpec.y, wpSpec.radius, wpFlash ? "#ffffff" : theme.weakPoint);
      ctx.strokeStyle  = wpFlash ? "#ffffff" : theme.weakPoint;
      ctx.lineWidth    = 2;
      ctx.globalAlpha  = pulse;
      ctx.beginPath();
      ctx.arc(wpSpec.x, wpSpec.y, wpSpec.radius + 6, 0, Math.PI * 2);
      ctx.stroke();
      ctx.restore();
    }

    drawPoly(leftPaddle,  theme.paddle);
    drawPoly(rightPaddle, theme.paddle);

    // Hinge pins
    ctx.fillStyle = "rgba(255,255,255,0.5)";
    ctx.beginPath(); ctx.arc(fl.hingeX, fl.hingeY, 4, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(fr.hingeX, fr.hingeY, 4, 0, Math.PI * 2); ctx.fill();

    if (ball) drawCirc(ball.position.x, ball.position.y, BALL_RADIUS, theme.ball);

    // Pending score indicator
    if (pendingScore > 0) {
      ctx.save();
      ctx.font        = "bold 13px monospace";
      ctx.fillStyle   = theme.weakPoint;
      ctx.shadowColor = theme.weakPoint;
      ctx.shadowBlur  = 6;
      ctx.fillText(`▶ ${pendingScore}`, 10, H - 56);
      ctx.restore();
    }

    rafId = requestAnimationFrame(frame);
  }

  rafId = requestAnimationFrame((ts) => { lastTs = ts; frame(ts); });

  // ── Public interface ───────────────────────────────────────────────────
  return {
    teardown() {
      cancelAnimationFrame(rafId);
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("keyup",   onKeyUp);
      orbFlash.clear();
      World.clear(world, false);
      Engine.clear(engine);
    },
    setEquippedWeapon(type: string | null) {
      equippedWeaponType = type;
    },
  };
}

