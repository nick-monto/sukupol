import { describe, it, expect } from "vitest";
import { BIOME_CONFIGS } from "../src/pinball";
import { generatePinballTable } from "../src/pinball";
import { descriptorForBiome } from "./helpers";
import { ORB_LABEL_ORDER, WEAPON_BUMPER_SHAPE } from "../src/pinballCombat/weapons";

describe("debug", () => {
  it("find failing combos", () => {
    for (const biomeId of Object.keys(BIOME_CONFIGS)) {
      for (const weapon of Object.keys(WEAPON_BUMPER_SHAPE)) {
        const descriptor = {
          ...descriptorForBiome(biomeId),
          enemy_pinball: {
            obstacles: [{
              id: "e1", label: "Lich",
              pegs: [{ angle: 0, distance: 0, radius: 14 }],
              scoreValue: 20,
            }],
          },
        };
        const layout = generatePinballTable(descriptor);
        const orbs = layout.obstacles.filter(
          (o) => o.kind === "bumper" && o.weaponLabel && ORB_LABEL_ORDER.includes(o.weaponLabel),
        );
        if (orbs.length < 3) {
          console.log("FAIL biome:", biomeId, "weapon:", weapon, "orbs:", orbs.length,
            "obstacles total:", layout.obstacles.length,
            "obstacles:", JSON.stringify(layout.obstacles.map(o=>({id:o.id,kind:o.kind,wl:o.weaponLabel}))));
        }
      }
    }
  });
});
