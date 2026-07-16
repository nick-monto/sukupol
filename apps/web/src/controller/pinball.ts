import { generatePinballTable } from "../pinball";
import { setupPinball } from "../pinballCombat";
import type { Snapshot } from "../types";
import type { ControllerOptions, PinballRegistry } from "./options";
import { runCombatActionRequest } from "./actions";

export function getEquippedWeaponType(snapshot: Snapshot | null): string | null {
  if (!snapshot?.equipped_weapon) return null;
  const item = snapshot.inventory.find((i) => i.item_id === snapshot.equipped_weapon);
  return item?.item_type ?? null;
}

function startPinball(options: ControllerOptions, registry: PinballRegistry): void {
  const { state } = options;
  const canvas = document.querySelector<HTMLCanvasElement>("#pinball-cabinet-canvas");
  if (!canvas) return;
  const descriptor = state.snapshot?.combat_state?.pinball_descriptor ?? null;
  const layout = generatePinballTable(descriptor ?? {
    biome_id: "ashen_fields", floor_seed: 0, enemy_id: "unknown", enemy_pinball: {},
  });
  registry.set(setupPinball(canvas, {
    layout,
    equippedWeaponType: getEquippedWeaponType(state.snapshot ?? null),
    onPinballStrike: (score: number) => { if (score > 0) void runCombatActionRequest(options, `pinball_strike:${score}`); },
    onBallDrain: () => { /* score already handled via onPinballStrike at drain */ },
  }));
}

function stopPinball(registry: PinballRegistry): void {
  registry.clear();
}

function updatePinballWeapon(options: ControllerOptions, registry: PinballRegistry): void {
  const table = registry.get();
  if (table) table.setEquippedWeapon(getEquippedWeaponType(options.state.snapshot ?? null));
}

export function managePinballFn(options: ControllerOptions, registry: PinballRegistry): void {
  const { state } = options;
  const inCombat = !!(state.snapshot?.in_combat && state.snapshot.combat_state && !state.presentationLock);
  if (inCombat && !registry.get()) { startPinball(options, registry); return; }
  if (!inCombat && registry.get()) { stopPinball(registry); return; }
  if (inCombat && registry.get()) { updatePinballWeapon(options, registry); }
}
