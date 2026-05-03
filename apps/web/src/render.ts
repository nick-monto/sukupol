import type { AppState, Snapshot } from "./types";
import type { UiElements } from "./ui";

const transitionTimers = new WeakMap<HTMLElement, number>();

export function renderApp(ui: UiElements, state: AppState): void {
  const snapshot = state.snapshot;
  ui.heroSummary.innerHTML = renderHeroSummary(snapshot);
  ui.expeditionSignal.textContent = renderExpeditionSignal(snapshot);
  applyPresentationState(ui, state);

  if (!snapshot) {
    ui.locationName.textContent = "No run started";
    ui.locationMeta.textContent = "Awaiting expedition telemetry.";
    ui.locationDescription.textContent = "Bring up the backend and start a run to render the first-person view.";
    ui.viewport.textContent = "Stand up the backend and begin a run.";
    ui.minimap.textContent = "No map yet.";
    ui.messageLabel.textContent = "Field report";
    ui.messageLog.textContent = "Awaiting input.";
    ui.inventoryList.innerHTML = "<p class=\"small empty-copy\">No loadout recorded.</p>";
    ui.npcList.innerHTML = "<p class=\"small empty-copy\">No contacts in range.</p>";
    ui.dialogueLog.textContent = "No dialogue yet.";
    ui.outcomeLog.textContent = "No completed run yet.";
    return;
  }

  ui.locationName.textContent = snapshot.location.name;
  ui.locationMeta.textContent = renderLocationMeta(snapshot);
  ui.locationDescription.textContent = snapshot.location.floor_number
    ? `${snapshot.location.description} Floor ${snapshot.location.floor_number}.`
    : snapshot.location.description;
  ui.viewport.textContent = snapshot.in_combat && snapshot.combat_state
    ? renderCombatViewport(snapshot)
    : snapshot.first_person_view.join("\n");
  ui.minimap.textContent = snapshot.minimap.join("\n");
  ui.messageLabel.textContent = snapshot.in_combat ? "Combat report" : "Field report";
  ui.messageLog.textContent = snapshot.message;
  ui.inventoryList.innerHTML = renderInventory(snapshot);
  ui.npcList.innerHTML = renderNpcList(snapshot, state.selectedNpcId);

  if (snapshot.in_combat && snapshot.combat_state) {
    ui.logTitle.textContent = `Combat: ${snapshot.combat_state.enemy_name}`;
    ui.logHelp.textContent = `Round ${snapshot.combat_state.round}. Movement and dialogue are disabled until combat resolves.`;
    ui.dialogueLog.textContent = snapshot.combat_state.log.join("\n\n");
  } else {
    ui.logTitle.textContent = "Dialogue";
    ui.logHelp.textContent = state.selectedNpcId
      ? "A contact is tuned in. Send a question or switch recipients from the survey slate."
      : "No contact selected. Choose a nearby voice from the survey slate to open dialogue.";
    ui.dialogueLog.textContent = snapshot.dialogue
      ? `${snapshot.dialogue.npc_name} [${snapshot.dialogue.source}]\n\n${snapshot.dialogue.text}`
      : "No dialogue yet.";
  }

  ui.outcomeLog.textContent = snapshot.outcome_summary
    ? renderOutcome(snapshot)
    : "No completed run yet.";
}

function applyPresentationState(ui: UiElements, state: AppState): void {
  const snapshot = state.snapshot;
  const mode = !snapshot ? "idle" : snapshot.run_result ? "archived" : snapshot.in_combat ? "combat" : state.selectedNpcId ? "dialogue-ready" : "exploration";

  setMode(ui.shell, mode);
  setMode(ui.actionPanel, mode);
  setMode(ui.outcomePanel, snapshot?.run_result ? "archived" : "idle");
  setMode(ui.viewportPanel, snapshot?.in_combat ? "combat" : mode);
  setMode(ui.logPanel, snapshot?.in_combat ? "combat" : state.selectedNpcId ? "tuned" : "idle");
  setMode(ui.messageStrip, snapshot?.in_combat ? "combat" : snapshot?.run_result ? "archived" : "exploration");
  ui.playerMessage.placeholder = getMessagePlaceholder(snapshot, state.selectedNpcId);

  if (!snapshot) {
    ui.dispatchKicker.textContent = "Dispatch";
    ui.dispatchTitle.textContent = "Field Orders";
    ui.dispatchNote.textContent = "Compose a message when stationed near an NPC. Combat orders replace dialogue during encounters.";
    ui.outcomeTitle.textContent = "Run Chronicle";
    ui.outcomeNote.textContent = "End-of-run outcomes and long-view progression notes.";
    return;
  }

  if (snapshot.run_result) {
    ui.dispatchKicker.textContent = "Stand Down";
    ui.dispatchTitle.textContent = "Expedition Closed";
    ui.dispatchNote.textContent = "This run has been archived. Review the chronicle, then begin a fresh expedition from town.";
    ui.outcomeTitle.textContent = "Archived Chronicle";
    ui.outcomeNote.textContent = "Final record recovered from the last completed expedition.";
    return;
  }

  if (snapshot.in_combat) {
    const enemyName = snapshot.combat_state?.enemy_name ?? "enemy";
    ui.dispatchKicker.textContent = "Combat";
    ui.dispatchTitle.textContent = `Engage ${enemyName}`;
    ui.dispatchNote.textContent = "Dialogue is suspended. Commit to an action, preserve your footing, or break away if the route allows.";
    ui.outcomeTitle.textContent = "Run Chronicle";
    ui.outcomeNote.textContent = "End-of-run outcomes and long-view progression notes.";
    return;
  }

  if (state.selectedNpcId) {
    const npcName = snapshot.nearby_npcs.find((npc) => npc.id === state.selectedNpcId)?.display_name ?? "selected contact";
    ui.dispatchKicker.textContent = "Dialogue";
    ui.dispatchTitle.textContent = `Signal ${npcName}`;
    ui.dispatchNote.textContent = "A contact is selected and listening. Ask for rumor, guidance, supplies, or a reading of the road ahead.";
  } else {
    ui.dispatchKicker.textContent = "Dispatch";
    ui.dispatchTitle.textContent = "Field Orders";
    ui.dispatchNote.textContent = "No contact is selected. Move, survey the slate, or choose a nearby voice before transmitting.";
  }

  ui.outcomeTitle.textContent = "Run Chronicle";
  ui.outcomeNote.textContent = "End-of-run outcomes and long-view progression notes.";
}

function setMode(element: HTMLElement, nextMode: string): void {
  const previousMode = element.dataset.mode;
  element.dataset.mode = nextMode;

  if (previousMode && previousMode !== nextMode) {
    triggerModeTransition(element);
  }
}

function triggerModeTransition(element: HTMLElement): void {
  const existingTimer = transitionTimers.get(element);
  if (existingTimer) {
    window.clearTimeout(existingTimer);
  }

  element.dataset.transition = "mode-change";
  const timer = window.setTimeout(() => {
    delete element.dataset.transition;
    transitionTimers.delete(element);
  }, 520);
  transitionTimers.set(element, timer);
}

function getMessagePlaceholder(snapshot: Snapshot | null, selectedNpcId: string): string {
  if (!snapshot) {
    return "Begin an expedition before sending orders.";
  }

  if (snapshot.run_result) {
    return "This expedition has been archived.";
  }

  if (snapshot.in_combat) {
    return "Combat is active. Use the combat orders instead.";
  }

  if (selectedNpcId) {
    return "Ask about the dungeon, the town, supplies, or what waits ahead.";
  }

  return "Choose a nearby contact before transmitting a message.";
}

function renderHeroSummary(snapshot: Snapshot | null): string {
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

function renderExpeditionSignal(snapshot: Snapshot | null): string {
  if (!snapshot) {
    return "No active expedition. Establish a run to receive telemetry.";
  }

  if (snapshot.run_result) {
    return `Run archived: ${snapshot.run_result}. Review the chronicle before departing again.`;
  }

  if (snapshot.in_combat) {
    return "Combat lock engaged. Field movement suspended until the encounter resolves.";
  }

  return `Expedition active. Facing ${snapshot.facing.toLowerCase()} with ${snapshot.nearby_npcs.length} contact${snapshot.nearby_npcs.length === 1 ? "" : "s"} nearby.`;
}

function renderLocationMeta(snapshot: Snapshot): string {
  const floorText = snapshot.location.floor_number ? `Floor ${snapshot.location.floor_number}` : "Town approach";
  const biomeText = snapshot.location.biome_id ? snapshot.location.biome_id.replaceAll("_", " ") : "settled ground";
  return `${floorText} / ${biomeText} / ${snapshot.enemies_defeated} foes broken`;
}

function renderCombatViewport(snapshot: Snapshot): string {
  const combatState = snapshot.combat_state;
  if (!combatState) {
    return snapshot.first_person_view.join("\n");
  }

  return [
    `Enemy: ${combatState.enemy_name}`,
    `Enemy HP: ${combatState.enemy_hp}/${combatState.enemy_max_hp}`,
    `Your HP: ${snapshot.stats.hp}/${snapshot.stats.max_hp}`,
    `Round: ${combatState.round}`,
    "",
    ...combatState.log.slice(-4),
  ].join("\n");
}

function renderInventory(snapshot: Snapshot): string {
  if (snapshot.inventory.length === 0) {
    return "<p class=\"small empty-copy\">No provisions carried.</p>";
  }

  return snapshot.inventory
    .map((item) => {
      const equipped = item.item_id === snapshot.equipped_weapon;
      return `
        <div class="inventory-item${equipped ? " is-equipped" : ""}">
          <div>
            <strong>${item.item_id.replaceAll("_", " ")}</strong>
            <div class="small">Qty ${item.quantity}${equipped ? " / readied" : ""}</div>
          </div>
          <span class="inventory-mark">${equipped ? "Readied" : "Stored"}</span>
        </div>
      `;
    })
    .join("");
}

function renderNpcList(snapshot: Snapshot, selectedNpcId: string): string {
  if (snapshot.nearby_npcs.length === 0) {
    return "<p class=\"small empty-copy\">No contacts in range.</p>";
  }

  return `
    <div class="panel-header panel-header-compact">
      <div>
        <p class="eyebrow">Contacts</p>
        <h3>Nearby voices</h3>
      </div>
    </div>
    ${snapshot.nearby_npcs
      .map((npc) => {
        const selected = npc.id === selectedNpcId;
        return `
          <div class="npc-item${selected ? " is-selected" : ""}">
            <div>
              <strong>${npc.display_name}</strong>
              <div class="small">${npc.role} / ${npc.distance === 0 ? "within speaking distance" : "one step away"}</div>
            </div>
            <button data-npc-id="${npc.id}" ${selected ? "disabled" : ""}>
              ${selected ? "Listening" : "Tune in"}
            </button>
          </div>
        `;
      })
      .join("")}
  `;
}

function renderOutcome(snapshot: Snapshot): string {
  const outcome = snapshot.outcome_summary;
  const progression = snapshot.progression;
  if (!outcome) {
    return "No completed run yet.";
  }

  const lines = [
    `Result: ${outcome.result}`,
    `Depth reached: ${outcome.depth_reached}`,
    `Enemies defeated: ${outcome.enemies_defeated}`,
    `Gold earned: ${outcome.gold_earned}`,
  ];
  if (outcome.items_found.length > 0) {
    lines.push(`Recovered: ${outcome.items_found.map((item) => `${item.item_id} x${item.quantity}`).join(", ")}`);
  }
  if (progression) {
    lines.push("");
    lines.push(`Total runs: ${progression.total_runs}`);
    lines.push(`Victories: ${progression.total_victories}`);
    lines.push(`Deepest depth: ${progression.deepest_depth}`);
  }
  return lines.join("\n");
}

function statCards(entries: Array<[string, string]>): string {
  return entries
    .map(
      ([label, value]) => `
        <div class="stat-card">
          <span class="small">${label}</span>
          <strong>${value}</strong>
        </div>
      `,
    )
    .join("");
}