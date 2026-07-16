/** Scoring contract: weapon → orb → shape mapping invariants */

import { describe, it, expect } from "vitest";
import { generatePinballTable, BIOME_CONFIGS } from "../src/pinball";
import { initObstacleShapeMap } from "../src/pinballCombat/engine";
import {
  WEAPON_BUMPER_SHAPE,
  WEAPON_ORB,
  ORB_LABEL_ORDER,
} from "../src/pinballCombat/weapons";
import { SAMPLE_DESCRIPTOR, descriptorForBiome } from "./helpers";

describe("scoring contract", () => {
  // Shared layout for all weapon-agnostic tests (no enemy obstacles)
  const baseLayout = generatePinballTable(SAMPLE_DESCRIPTOR);

  // ── 1. initObstacleShapeMap returns exactly info.count entries ──────────
  for (const weapon of Object.keys(WEAPON_BUMPER_SHAPE)) {
    const info = WEAPON_BUMPER_SHAPE[weapon];
    it(`${weapon}: initObstacleShapeMap yields ${info.count} orb entries`, () => {
      const map = initObstacleShapeMap(baseLayout.obstacles, weapon);
      expect(map.size).toBe(info.count);
      for (const id of map.keys()) {
        const obs = baseLayout.obstacles.find((o) => o.id === id);
        expect(obs).toBeDefined();
        expect(obs!.weaponLabel).toBeDefined();
        expect(ORB_LABEL_ORDER).toContain(obs!.weaponLabel);
      }
    });
  }

  // ── 2. WEAPON_ORB symmetry ──────────────────────────────────────────────
  it("every WEAPON_ORB label is in ORB_LABEL_ORDER and emitted by the table", () => {
    for (const [weapon, orbLabel] of Object.entries(WEAPON_ORB)) {
      expect(ORB_LABEL_ORDER).toContain(orbLabel);
      const emitted = baseLayout.obstacles.some(
        (o) => o.weaponLabel === orbLabel,
      );
      expect(emitted).toBe(true);
    }
  });

  // ── 3. Enemy obstacles have scoreValue > 0 ──────────────────────────────
  it("every enemy obstacle has scoreValue > 0", () => {
    const layout = generatePinballTable({
      ...SAMPLE_DESCRIPTOR,
      enemy_pinball: {
        obstacles: [
          {
            id: "e1",
            label: "Lich",
            pegs: [{ angle: 0, distance: 0, radius: 14 }],
            scoreValue: 20,
          },
        ],
      },
    });
    for (const obs of layout.obstacles) {
      if (obs.kind === "enemy") {
        expect(obs.scoreValue).toBeGreaterThan(0);
      }
    }
  });

  // ── 4. Orb labels are unique ────────────────────────────────────────────
  it("at most one obstacle per orb label", () => {
    for (const label of ORB_LABEL_ORDER) {
      const matches = baseLayout.obstacles.filter(
        (o) => o.weaponLabel === label,
      );
      expect(matches.length).toBeLessThanOrEqual(1);
    }
  });

  // ── 5. Bonus bumpers carry no weaponLabel ───────────────────────────────
  it("bonus bumpers have no weaponLabel", () => {
    for (const obs of baseLayout.obstacles) {
      if (obs.id.startsWith("bumper-bonus-")) {
        expect(obs.weaponLabel).toBeUndefined();
      }
    }
  });

  // ── 6. Every biome produces exactly 3 orb-* bumpers ────────────────────
  // Orbs are canonical (always placed via cabinet.orbSlots with a safe-relocate
  // fallback spread), so every biome must emit all 3. Catches orb-loss regressions.
  for (const biomeId of Object.keys(BIOME_CONFIGS)) {
    it(`${biomeId}: layout has exactly 3 orb-* bumpers`, () => {
      const layout = generatePinballTable(descriptorForBiome(biomeId));
      const orbs = layout.obstacles.filter(
        (o) =>
          o.kind === "bumper" &&
          o.weaponLabel !== undefined &&
          ORB_LABEL_ORDER.includes(o.weaponLabel),
      );
      expect(orbs.length).toBe(3);
    });
  }
});
