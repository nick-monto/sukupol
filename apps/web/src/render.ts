import { hideMap, renderMap } from "./viewport";
import type { AppState, DialogueMessage, Snapshot } from "./types";
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
    ui.locationDescription.textContent = "Bring up the backend and start a run to render the traversal map.";
    ui.viewport.textContent = "Stand up the backend and begin a run.";
    hideMap(ui.viewportPixiStage);
    ui.messageLabel.textContent = "Field report";
    ui.messageLog.textContent = "Awaiting input.";
    ui.inventoryList.innerHTML = "<p class=\"small empty-copy\">No loadout recorded.</p>";
    ui.npcList.innerHTML = "<p class=\"small empty-copy\">No contacts in range.</p>";
    ui.dialogueLog.innerHTML = renderChatEmpty("No active channel. Begin a run and choose a nearby contact.");
    ui.outcomeLog.textContent = "No completed run yet.";
    ui.journalList.innerHTML = renderJournalEmpty("Leave a conversation to record it here.");
    return;
  }

  ui.locationName.textContent = snapshot.location.name;
  ui.locationMeta.textContent = renderLocationMeta(snapshot);
  ui.locationDescription.textContent = snapshot.location.floor_number
    ? `${snapshot.location.description} Floor ${snapshot.location.floor_number}.`
    : snapshot.location.description;
  renderMap({
    stage: ui.viewportPixiStage,
    fallback: ui.viewport,
    lines: snapshot.map_view,
    metadata: snapshot.map_metadata ?? null,
    transition: state.viewportTransition,
  });
  ui.messageLabel.textContent = snapshot.in_combat ? "Combat report" : "Field report";
  ui.messageLog.textContent = snapshot.message;
  ui.inventoryList.innerHTML = renderInventory(snapshot);
  ui.npcList.innerHTML = renderNpcList(snapshot, state.selectedNpcId);

  if (snapshot.in_combat && snapshot.combat_state) {
    ui.logTitle.textContent = `Combat: ${snapshot.combat_state.enemy_name}`;
    ui.logHelp.textContent = `Round ${snapshot.combat_state.round}. Movement and dialogue are locked until combat resolves.`;
    ui.dialogueLog.innerHTML = renderCombatTranscript(snapshot);
  } else {
    ui.logTitle.textContent = "Dialogue";
    ui.logHelp.textContent = state.selectedNpcId
      ? "A contact is tuned in. Send a question or change recipients from the slate."
      : "No contact selected. Open the slate and choose a nearby voice.";
    ui.dialogueLog.innerHTML = renderDialogueTranscript(snapshot, state);
  }

  ui.dialogueLog.scrollTop = ui.dialogueLog.scrollHeight;

  ui.outcomeLog.textContent = snapshot.outcome_summary
    ? renderOutcome(snapshot)
    : "No completed run yet.";
  ui.journalList.innerHTML = renderJournal(snapshot);
}

function applyPresentationState(ui: UiElements, state: AppState): void {
  const snapshot = state.snapshot;
  const shellMode = !snapshot ? "idle" : snapshot.run_result ? "archived" : snapshot.in_combat ? "combat" : "exploration";
  const contextMode = !snapshot
    ? "idle"
    : snapshot.run_result
      ? "archived"
      : snapshot.in_combat
        ? "combat"
        : state.selectedNpcId
          ? "dialogue"
          : "idle";
  const actionMode = !snapshot ? "idle" : snapshot.run_result ? "archived" : snapshot.in_combat ? "combat" : state.selectedNpcId ? "dialogue-ready" : "idle";

  setMode(ui.shell, shellMode);
  setMode(ui.contextDrawer, contextMode);
  setMode(ui.actionPanel, actionMode);
  setMode(ui.outcomePanel, snapshot?.run_result ? "archived" : "idle");
  setMode(ui.viewportPanel, snapshot?.in_combat ? "combat" : snapshot?.run_result ? "archived" : snapshot ? "exploration" : "idle");
  setMode(ui.logPanel, snapshot?.in_combat ? "combat" : state.selectedNpcId ? "tuned" : "idle");
  setMode(ui.messageStrip, snapshot?.in_combat ? "combat" : snapshot?.run_result ? "archived" : "exploration");
  ui.playerMessage.placeholder = getMessagePlaceholder(snapshot, state.selectedNpcId);

  if (!snapshot) {
    ui.dispatchKicker.textContent = "Dispatch";
    ui.dispatchTitle.textContent = "Field Orders";
    ui.dispatchNote.textContent = "Select a contact to transmit. Combat orders appear here during encounters.";
    ui.outcomeTitle.textContent = "Run Chronicle";
    ui.outcomeNote.textContent = "Resolved runs and the running journal of NPC visits.";
    return;
  }

  if (snapshot.run_result) {
    ui.dispatchKicker.textContent = "Stand Down";
    ui.dispatchTitle.textContent = "Expedition Closed";
    ui.dispatchNote.textContent = "This run is closed. Review the chronicle, then begin again from town.";
    ui.outcomeTitle.textContent = "Archived Chronicle";
    ui.outcomeNote.textContent = "Final record from the last completed expedition alongside your NPC journal.";
    return;
  }

  if (snapshot.in_combat) {
    const enemyName = snapshot.combat_state?.enemy_name ?? "enemy";
    ui.dispatchKicker.textContent = "Combat";
    ui.dispatchTitle.textContent = `Engage ${enemyName}`;
    ui.dispatchNote.textContent = "Dialogue is suspended. Commit to an action or break away if the route allows.";
    ui.outcomeTitle.textContent = "Run Chronicle";
    ui.outcomeNote.textContent = "Resolved runs and the running journal of NPC visits.";
    return;
  }

  if (state.selectedNpcId) {
    const npcName = snapshot.nearby_npcs.find((npc) => npc.id === state.selectedNpcId)?.display_name ?? "selected contact";
    ui.dispatchKicker.textContent = "Dialogue";
    ui.dispatchTitle.textContent = `Signal ${npcName}`;
    ui.dispatchNote.textContent = "A contact is tuned in. Ask for rumor, guidance, or supplies.";
  } else {
    ui.dispatchKicker.textContent = "Dispatch";
    ui.dispatchTitle.textContent = "Field Orders";
    ui.dispatchNote.textContent = "Move, survey the slate, or choose a nearby voice before transmitting.";
  }

  ui.outcomeTitle.textContent = "Run Chronicle";
  ui.outcomeNote.textContent = "Resolved runs and the running journal of NPC visits.";
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
    return "Ask for rumor, route, supplies, or warning.";
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
    return "Combat lock engaged. Resolve the encounter before moving.";
  }

  const safety = snapshot.location.encounter_enabled ? "encounter watch active" : "town is holding";
  return `Position ${snapshot.position.x},${snapshot.position.y} with ${snapshot.nearby_npcs.length} contact${snapshot.nearby_npcs.length === 1 ? "" : "s"} nearby; ${safety}.`;
}

function renderLocationMeta(snapshot: Snapshot): string {
  const floorText = snapshot.location.floor_number ? `Floor ${snapshot.location.floor_number}` : snapshot.location.type ?? "surface";
  const biomeText = snapshot.location.biome_id ? snapshot.location.biome_id.replaceAll("_", " ") : "settled ground";
  const safetyText = snapshot.location.encounter_enabled ? "encounter ground" : "safe ground";
  return `${floorText} / ${biomeText} / ${safetyText} / ${snapshot.enemies_defeated} foes broken`;
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
        const asciiArt = npc.ascii_art.length > 0
          ? `<pre class="entity-ascii" aria-hidden="true">${escapeHtml(npc.ascii_art.join("\n"))}</pre>`
          : "";
        return `
          <div class="npc-item${selected ? " is-selected" : ""}">
            ${asciiArt}
            <div class="npc-item-copy">
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

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderDialogueTranscript(snapshot: Snapshot, state: AppState): string {
  if (!state.selectedNpcId) {
    return renderChatEmpty("Select a nearby contact to open a channel.");
  }

  const thread = [...(state.dialogueThreads[state.selectedNpcId] ?? [])];
  if (thread.length === 0 && snapshot.dialogue?.npc_id === state.selectedNpcId) {
    thread.push({
      id: "snapshot-dialogue",
      speaker: "npc",
      npcId: snapshot.dialogue.npc_id,
      npcName: snapshot.dialogue.npc_name,
      source: snapshot.dialogue.source,
      text: snapshot.dialogue.text,
    });
  }

  if (thread.length === 0) {
    return renderChatEmpty("No messages on this channel yet. Ask for a route, rumor, supply, or warning.");
  }

  return thread.map(renderChatMessage).join("");
}

function renderCombatTranscript(snapshot: Snapshot): string {
  const combatState = snapshot.combat_state;
  if (!combatState) {
    return renderChatEmpty("Combat telemetry unavailable.");
  }

  const entries: DialogueMessage[] = [];
  if ((combatState.enemy_ascii_art ?? []).length > 0) {
    entries.push({
      id: "combat-enemy-art",
      speaker: "npc",
      npcName: combatState.enemy_name,
      text: combatState.enemy_ascii_art?.join("\n") ?? "",
    });
  }

  combatState.log.forEach((line, index) => {
    entries.push({
      id: `combat-log-${index}`,
      speaker: index === 0 ? "npc" : "system",
      npcName: combatState.enemy_name,
      text: line,
    });
  });

  return entries.map(renderChatMessage).join("");
}

function renderChatEmpty(copy: string): string {
  return `<div class="chat-empty">${escapeHtml(copy)}</div>`;
}

function renderJournal(snapshot: Snapshot): string {
  if (snapshot.journal.length === 0) {
    return renderJournalEmpty("Leave a conversation to record a summary for that visit.");
  }

  return snapshot.journal
    .map((group) => `
      <article class="journal-group">
        <div class="journal-group-head">
          <div>
            <strong>${escapeHtml(group.npc_name)}</strong>
            <div class="small">${group.entries.length} visit${group.entries.length === 1 ? "" : "s"}</div>
          </div>
        </div>
        <div class="journal-group-entries">
          ${group.entries.map((entry) => `
            <div class="journal-entry">
              <div class="journal-entry-meta">
                <span class="journal-entry-stamp">${escapeHtml(formatJournalStamp(entry.visit_ended_at))}</span>
                <span class="journal-entry-turns">${entry.turn_count} turn${entry.turn_count === 1 ? "" : "s"}</span>
              </div>
              <p>${renderChatText(entry.summary)}</p>
            </div>
          `).join("")}
        </div>
      </article>
    `)
    .join("");
}

function renderJournalEmpty(copy: string): string {
  return `<div class="chat-empty">${escapeHtml(copy)}</div>`;
}

function formatJournalStamp(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Visit logged";
  }

  return parsed.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function renderChatMessage(message: DialogueMessage): string {
  const speakerLabel = message.speaker === "player"
    ? "You"
    : message.speaker === "system"
      ? "System"
      : message.npcName ?? "Contact";
  const sourceChip = message.speaker === "npc" && message.source
    ? `<span class="chat-source">${escapeHtml(message.source)}</span>`
    : "";
  const text = message.text.trim() || (message.streaming ? "..." : "");

  return `
    <div class="chat-message is-${message.speaker}">
      <div class="chat-bubble">
        <div class="chat-bubble-meta">
          <span class="chat-speaker">${escapeHtml(speakerLabel)}</span>
          ${sourceChip}
        </div>
        <p>${renderChatText(text)}</p>
      </div>
    </div>
  `;
}

function renderChatText(value: string): string {
  return escapeHtml(value).replaceAll("\n", "<br>");
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