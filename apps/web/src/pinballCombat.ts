import Matter from "matter-js";

const { Engine, World, Bodies, Body, Constraint, Events, Composite } = Matter;

// ---------------------------------------------------------------------------
// Exact replica of fishshiz/pinball-wizard cabinet
// Canvas: 550 × 650  |  Gravity: 0.95
// ---------------------------------------------------------------------------
const W = 550;
const H = 650;

// Colors from the reference
const C = {
  bg:         "#212529",   // matches reference background
  walls:      "#C4CFD4",
  innerWalls: "#608CBB",
  orbs:       "#5C43B5",
  orbHit:     "#B09150",
  kickers:    "#A9D2F0",
  paddle:     "#f5a02e",
  ball:       "#dee2e6",
} as const;

// Weapon type → orb label
// orb-left=(146,200)  orb-center=(235,120)  orb-right=(323,200)
const WEAPON_ORB: Record<string, string> = {
  sword:  "orb-left",
  axe:    "orb-left",
  staff:  "orb-center",
  wand:   "orb-center",
  bow:    "orb-right",
  dagger: "orb-right",
};

const MAX_VELOCITY = 50;

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------
export interface PinballCombatOptions {
  onBumperHit: (bumperId: string, weaponMultiplier: number) => void;
  onBallDrain: () => void;
  equippedWeaponType?: string | null;
}

export interface PinballTable {
  teardown: () => void;
  setEquippedWeapon: (weaponType: string | null) => void;
}

// ---------------------------------------------------------------------------
// setupPinball — exact fishshiz/pinball-wizard cabinet geometry
// ---------------------------------------------------------------------------
export function setupPinball(
  canvas: HTMLCanvasElement,
  opts: PinballCombatOptions,
): PinballTable {
  canvas.width  = W;
  canvas.height = H;

  const ctx = canvas.getContext("2d")!;

  // ── Engine ────────────────────────────────────────────────────────────────
  const engine = Engine.create();
  engine.gravity.y = 0.95;
  const { world } = engine;

  // Non-colliding group shared by paddles and buffer circles so they ignore
  // each other while the ball (category 2) still hits paddle surfaces.
  const bufferGroup = Body.nextGroup(false);

  // ── Orb scoring circles ────────────────────────────────────────────────
  const orbCenter = Bodies.circle(235, 120, 30, { label: "orb-center", isStatic: true, restitution: 1.5, friction: 0 });
  const orbLeft   = Bodies.circle(146, 200, 30, { label: "orb-left",   isStatic: true, restitution: 1.5, friction: 0 });
  const orbRight  = Bodies.circle(323, 200, 30, { label: "orb-right",  isStatic: true, restitution: 1.5, friction: 0 });
  const allOrbs = [orbCenter, orbLeft, orbRight];

  // ── Outer walls ────────────────────────────────────────────────────────
  const outerWalls = [
    Bodies.rectangle(  0, 325, 650,  20, { angle: Math.PI / 2,     isStatic: true }),
    Bodies.rectangle(550, 325, 650,  20, { angle: Math.PI / 2,     isStatic: true }),
    Bodies.rectangle(275,   0, 550,  20, {                          isStatic: true }),
    Bodies.rectangle(490, 455, 400,  20, { angle: Math.PI / 2,     isStatic: true, chamfer: { radius: 10 } }),
    Bodies.rectangle( 90, 560, 220,  20, { angle: Math.PI / 6,     isStatic: true, chamfer: { radius: 10 } }),
    Bodies.rectangle(400, 560, 220,  20, { angle: 5*Math.PI / 6,   isStatic: true, chamfer: { radius: 10 } }),
    Bodies.rectangle(100,   0, 350, 200, { angle: 5*Math.PI / 6,   isStatic: true, chamfer: { radius: 10 } }),
    Bodies.rectangle(420,   0, 400, 200, { angle: Math.PI / 6,     isStatic: true, chamfer: { radius: 10 } }),
  ];

  // ── Inner guide walls ──────────────────────────────────────────────────
  const innerWalls = [
    Bodies.rectangle( 60, 415, 120, 20, { angle: Math.PI / 2,     isStatic: true, chamfer: { radius: 10 } }),
    Bodies.rectangle(100, 490, 110, 20, { angle: Math.PI / 6,     isStatic: true, chamfer: { radius: 10 } }),
    Bodies.rectangle(430, 415, 120, 20, { angle: Math.PI / 2,     isStatic: true, chamfer: { radius: 10 } }),
    Bodies.rectangle(390, 490, 110, 20, { angle: 5*Math.PI / 6,   isStatic: true, chamfer: { radius: 10 } }),
  ];

  // ── Kicker bumpers + launchpads ────────────────────────────────────────
  const kickers = [
    Bodies.trapezoid(150, 400, 40, 100, 0.5, { label: "kicker",    isStatic: true, angle: 5.58505,  chamfer: { radius: 10 } }),
    Bodies.rectangle(155, 386,  5,  95,      { label: "launchpad", isStatic: true, angle: 5.47805,  chamfer: { radius:  2 } }),
    Bodies.trapezoid(340, 400, 40, 100, 0.5, { label: "kicker",    isStatic: true, angle: 0.698132, chamfer: { radius: 10 } }),
    Bodies.rectangle(335, 386,  5,  95,      { label: "launchpad", isStatic: true, angle: 0.810132, chamfer: { radius:  2 } }),
  ];

  // ── Thorns ────────────────────────────────────────────────────────────
  const thorns = [
    Bodies.trapezoid( 10, 280, 50, 50, 0.5, { isStatic: true, angle: Math.PI / 2,     chamfer: { radius: 10 } }),
    Bodies.trapezoid(475, 280, 50, 50, 0.5, { isStatic: true, angle: 3*Math.PI / 2,   chamfer: { radius: 10 } }),
  ];

  // ── Ball hatch (right-side chute separator) ────────────────────────────
  const hatch = Bodies.rectangle(490, 210, 130, 20, {
    label: "hatch", isStatic: true, angle: Math.PI / 2, chamfer: { radius: 10 },
  });
  let hatchUp = true;

  // ── Left flipper ──────────────────────────────────────────────────────
  const leftPaddle = Bodies.trapezoid(190, 540, 25, 80, 0.25, {
    label: "leftPaddle", angle: 2*Math.PI / 3, chamfer: { radius: 10 },
    collisionFilter: { group: bufferGroup, category: 0xFFFFFFFF, mask: 2 },
  });
  const leftHinge = Bodies.circle(172, 529, 5, { isStatic: true });
  const leftBlock = Bodies.rectangle(200, 550, 30, 30, { isStatic: false });
  const leftConstraint = Constraint.create({
    bodyA: leftPaddle, bodyB: leftHinge,
    pointA: { x: -18, y: -11 }, stiffness: 0, length: 0,
  });
  const leftWeight = Constraint.create({
    bodyA: leftPaddle, bodyB: leftBlock,
    pointA: { x: 13, y: 11 }, stiffness: 1, length: 1,
  });

  // ── Right flipper ─────────────────────────────────────────────────────
  const rightPaddle = Bodies.trapezoid(300, 540, 25, 80, 0.25, {
    label: "rightPaddle", angle: 4*Math.PI / 3, chamfer: { radius: 10 },
    collisionFilter: { group: bufferGroup, category: 0xFFFFFFFF, mask: 2 },
  });
  const rightHinge = Bodies.circle(318, 529, 5, { isStatic: true });
  const rightBlock = Bodies.rectangle(290, 550, 30, 30, { isStatic: false });
  const rightConstraint = Constraint.create({
    bodyA: rightPaddle, bodyB: rightHinge,
    pointA: { x: 18, y: -11 }, stiffness: 0, length: 0,
  });
  const rightWeight = Constraint.create({
    bodyA: rightPaddle, bodyB: rightBlock,
    pointA: { x: -13, y: 11 }, stiffness: 1, length: 1,
  });

  // ── Invisible buffer circles (bound paddle range) ──────────────────────
  const buffers = [
    Bodies.circle(190, 605, 50, { label: "buffer", isStatic: true }),
    Bodies.circle(190, 450, 50, { label: "buffer", isStatic: true }),
    Bodies.circle(300, 605, 50, { label: "buffer", isStatic: true }),
    Bodies.circle(300, 450, 50, { label: "buffer", isStatic: true }),
  ];
  for (const b of buffers) b.collisionFilter = { group: bufferGroup };

  // ── Add everything to world ────────────────────────────────────────────
  World.add(world, [
    ...allOrbs,
    ...outerWalls,
    ...innerWalls,
    ...kickers,
    ...thorns,
    hatch,
    leftPaddle, leftHinge, leftBlock, leftConstraint, leftWeight,
    rightPaddle, rightHinge, rightBlock, rightConstraint, rightWeight,
    ...buffers,
  ]);

  // ── Runtime state ──────────────────────────────────────────────────────
  let ball: Matter.Body | null = null;
  let inPlay     = false;
  let leftFired  = false;
  let rightFired = false;
  let equippedWeaponType: string | null = opts.equippedWeaponType ?? null;

  // ── Hatch helpers ──────────────────────────────────────────────────────
  function openHatch()  { Body.translate(hatch, { x: 0, y:  100 }); hatchUp = false; }
  function closeHatch() { Body.translate(hatch, { x: 0, y: -100 }); hatchUp = true;  }

  // ── Ball launch ────────────────────────────────────────────────────────
  function launchBall(): void {
    if (inPlay) return;
    openHatch();
    // Shoot from inside the right-side shooter lane (x 490–550, ball r=14)
    const b = Bodies.circle(510, 625, 14, {
      label: "pinball", restitution: 0.6, frictionAir: 0.005,
      collisionFilter: { mask: 0xFFFFFFFF, category: 2, group: 0 },
    });
    World.add(world, b);
    Body.setVelocity(b, { x: 0, y: -(25 + (Math.random() * 4 - 2)) });
    ball = b;
    inPlay = true;
  }

  // ── Orb flash state ────────────────────────────────────────────────────
  const orbFlash = new Map<string, number>(); // label → expiry timestamp (ms)

  // ── Collision events ───────────────────────────────────────────────────
  Events.on(engine, "collisionStart", (event: Matter.IEventCollision<Matter.Engine>) => {
    for (const pair of event.pairs) {
      const { bodyA, bodyB } = pair;
      if (bodyB.label !== "pinball") continue;
      if (bodyA.label === "reset") { launchBall(); continue; }
      if (!bodyA.label.startsWith("orb-")) continue;

      orbFlash.set(bodyA.label, performance.now() + 100);
      const activeOrb  = equippedWeaponType ? WEAPON_ORB[equippedWeaponType.toLowerCase()] : null;
      const multiplier = activeOrb === bodyA.label ? 2 : 1;
      opts.onBumperHit(bodyA.label, multiplier);
    }
  });

  // ── beforeUpdate: clamp velocity + shooter-lane guard ─────────────────
  Events.on(engine, "beforeUpdate", () => {
    if (!ball) return;
    Body.setVelocity(ball, {
      x: Math.max(Math.min(ball.velocity.x, MAX_VELOCITY), -MAX_VELOCITY),
      y: Math.max(Math.min(ball.velocity.y, MAX_VELOCITY), -MAX_VELOCITY),
    });
    // Prevent ball rolling back down the right-side shooter lane
    if (ball.position.x > 450 && ball.velocity.y > 0) {
      Body.setVelocity(ball, { x: 0, y: -10 });
    }
  });

  // ── afterUpdate: drain + hatch close ──────────────────────────────────
  Events.on(engine, "afterUpdate", () => {
    if (!ball || !inPlay) return;
    if (ball.position.y > H + 20) {
      Composite.remove(world, ball);
      ball   = null;
      inPlay = false;
      opts.onBallDrain();
      return;
    }
    if (ball.position.x < 490 && !hatchUp) closeHatch();
  });

  // ── Keyboard ──────────────────────────────────────────────────────────
  function onKeyDown(e: KeyboardEvent): void {
    if (e.code === "ArrowLeft" && !leftFired) {
      leftFired = true;
      Body.setAngularVelocity(leftPaddle, -1);
    } else if (e.code === "ArrowRight" && !rightFired) {
      rightFired = true;
      Body.setAngularVelocity(rightPaddle, 1);
    } else if (e.code === "ArrowUp" || e.code === "Space") {
      e.preventDefault();
      launchBall();
    }
  }

  function onKeyUp(e: KeyboardEvent): void {
    if (e.code === "ArrowLeft")  leftFired  = false;
    if (e.code === "ArrowRight") rightFired = false;
  }

  document.addEventListener("keydown", onKeyDown);
  document.addEventListener("keyup",   onKeyUp);

  // ── Canvas draw helpers ────────────────────────────────────────────────
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

  // ── Render loop ────────────────────────────────────────────────────────
  let rafId = 0;
  let lastTs = 0;

  function frame(ts: number): void {
    const dt = lastTs === 0 ? 16.67 : Math.min(ts - lastTs, 33);
    lastTs = ts;
    Engine.update(engine, dt);

    ctx.fillStyle = C.bg;
    ctx.fillRect(0, 0, W, H);

    for (const w of outerWalls)  drawPoly(w, C.walls);
    for (const w of innerWalls)  drawPoly(w, C.innerWalls);
    for (const k of kickers)     drawPoly(k, C.kickers);
    for (const t of thorns)      drawPoly(t, C.walls);
    if (hatchUp) drawPoly(hatch, C.walls);

    // Orbs
    const now = performance.now();
    const activeOrbLabel = equippedWeaponType
      ? WEAPON_ORB[equippedWeaponType.toLowerCase()] : null;
    for (const orb of allOrbs) {
      const flashing = now < (orbFlash.get(orb.label) ?? 0);
      const isActive = orb.label === activeOrbLabel;
      if (isActive && !flashing) {
        ctx.save();
        ctx.shadowColor = "rgba(214, 179, 116, 0.6)";
        ctx.shadowBlur  = 12;
        drawCirc(orb.position.x, orb.position.y, 30, "#7a5fd8", "rgba(255, 220, 140, 0.7)");
        ctx.restore();
      } else {
        drawCirc(orb.position.x, orb.position.y, 30, flashing ? C.orbHit : C.orbs);
      }
    }

    drawPoly(leftPaddle,  C.paddle);
    drawPoly(rightPaddle, C.paddle);

    // Hinge pins
    ctx.fillStyle = "rgba(255,255,255,0.5)";
    ctx.beginPath(); ctx.arc(172, 529, 4, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(318, 529, 4, 0, Math.PI * 2); ctx.fill();

    if (ball) drawCirc(ball.position.x, ball.position.y, 14, C.ball);

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

