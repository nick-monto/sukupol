import type { Snapshot } from "../types";
import { statCards } from "./dom";

export function renderHeroSummary(snapshot: Snapshot | null): string {
  const entries: Array<[string, string]> = snapshot
    ? [
        ["Condition", `${snapshot.stats.hp}/${snapshot.stats.max_hp}`],
        ["Depth", String(snapshot.run_depth)],
        ["Trophies", String(snapshot.enemies_defeated)],
        ["Posture", snapshot.in_combat ? "Engaged" : "Surveying"],
      ]
    : [
        ["Condition", "Dormant"],
        ["Depth", "-"],
        ["Trophies", "0"],
        ["Posture", "Awaiting orders"],
      ];

  return statCards(entries);
}

export function renderExpeditionSignal(snapshot: Snapshot | null): string {
  if (!snapshot) {
    return "No active expedition. Establish a run to receive telemetry.";
  }

  if (snapshot.run_result) {
    return `Run archived: ${snapshot.run_result}. Review the chronicle before departing again.`;
  }

  if (snapshot.in_combat) {
    return "Combat lock engaged. Resolve the encounter before moving.";
  }

  const safety = snapshot.location.encounter_enabled ? "encounter watch active" : "town is holding";
  return `Position ${snapshot.position.x},${snapshot.position.y} with ${snapshot.nearby_npcs.length} contact${snapshot.nearby_npcs.length === 1 ? "" : "s"} nearby; ${safety}.`;
}

export function renderLocationMeta(snapshot: Snapshot): string {
  const floorText = snapshot.location.floor_number ? `Floor ${snapshot.location.floor_number}` : snapshot.location.type ?? "surface";
  const biomeText = snapshot.location.biome_id ? snapshot.location.biome_id.replaceAll("_", " ") : "settled ground";
  const safetyText = snapshot.location.encounter_enabled ? "encounter ground" : "safe ground";
  return `${floorText} / ${biomeText} / ${safetyText} / ${snapshot.enemies_defeated} foes broken`;
}
