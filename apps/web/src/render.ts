import { hideMap, renderMap } from "./viewport";
import type { AppState, CombatNegotiationEntry, CombatPartySlot, DialogueMessage, OverworldMap, Snapshot } from "./types";
import type { UiElements } from "./ui";

const transitionTimers = new WeakMap<HTMLElement, number>();

export function renderApp(
  ui: UiElements,
  state: AppState,
  onViewportTransitionComplete?: (token: number) => void,
): void {
  const snapshot = getPresentedSnapshot(state);
  ui.heroSummary.innerHTML = renderHeroSummary(snapshot);
  ui.expeditionSignal.textContent = renderExpeditionSignal(snapshot);
  applyPresentationState(ui, state, snapshot);

  if (!snapshot) {
    ui.locationName.textContent = "No run started";
    ui.locationMeta.textContent = "Awaiting expedition telemetry.";
    ui.locationDescription.textContent = "Bring up the backend and start a run to render the traversal map.";
    ui.viewport.textContent = "Stand up the backend and begin a run.";
    hideMap(ui.viewportPixiStage);
    ui.overworldMap.innerHTML = renderOverworldMap(null);
    ui.inventoryList.innerHTML = "<p class=\"small empty-copy\">No loadout recorded.</p>";
    ui.questList.innerHTML = renderQuestEmpty("No contracts recorded.");
    ui.npcList.innerHTML = "<p class=\"small empty-copy\">No contacts in range.</p>";
    ui.combatOverlay.hidden = true;
    ui.combatOverlay.innerHTML = "";
    ui.dialogueLog.innerHTML = renderUnifiedTranscript(null, state);
    ui.combatActions.innerHTML = "";
    ui.questChoicePanel.innerHTML = "";
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
    onTransitionComplete: state.presentationLock?.transition === "combat-exit"
      ? () => onViewportTransitionComplete?.(state.presentationLock?.token ?? 0)
      : undefined,
  });
  ui.overworldMap.innerHTML = renderOverworldMap(snapshot.overworld_map ?? null);
  ui.inventoryList.innerHTML = renderInventory(snapshot);
  ui.questList.innerHTML = renderQuestList(snapshot);
  ui.npcList.innerHTML = renderNpcList(snapshot, state.selectedNpcId);
  ui.questChoicePanel.innerHTML = renderQuestChoicePanel(snapshot, state.selectedNpcId);
  ui.combatOverlay.hidden = !snapshot.in_combat || !snapshot.combat_state;
  applyCombatOverlayUpdate(ui.combatOverlay, snapshot);
  ui.combatActions.innerHTML = snapshot.in_combat && snapshot.combat_state ? renderCombatActions(snapshot) : "";

  ui.dialogueLog.innerHTML = renderUnifiedTranscript(snapshot, state);

  ui.dialogueLog.scrollTop = ui.dialogueLog.scrollHeight;

  ui.outcomeLog.textContent = snapshot.outcome_summary
    ? renderOutcome(snapshot)
    : "No completed run yet.";
  ui.journalList.innerHTML = renderJournal(snapshot);
}

function applyPresentationState(ui: UiElements, state: AppState, snapshot: Snapshot | null): void {
  const combatParleyActive = snapshot?.in_combat && snapshot.combat_state?.negotiation?.active;
  const combatVisible = snapshot?.in_combat === true;
  const archived = snapshot?.run_result != null;
  const launchVisible = !snapshot || archived;
  const dialogueVisible = !!snapshot && !combatVisible && !archived
    && (state.dialogueOpen || state.selectedNpcId !== "");
  const contextVisible = combatVisible || dialogueVisible;
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
  const actionMode = !snapshot
    ? "idle"
    : snapshot.run_result
      ? "archived"
      : snapshot.in_combat
        ? combatParleyActive ? "combat-parley" : "combat"
        : state.selectedNpcId
          ? "dialogue-ready"
          : "idle";

  setMode(ui.shell, shellMode);
  setMode(ui.contextDrawer, contextMode);
  setMode(ui.actionPanel, actionMode);
  setMode(ui.outcomePanel, snapshot?.run_result ? "archived" : "idle");
  setMode(ui.viewportPanel, snapshot?.in_combat ? "combat" : snapshot?.run_result ? "archived" : snapshot ? "exploration" : "idle");
  ui.launchPanel.hidden = combatVisible || !launchVisible;
  ui.topHud.hidden = combatVisible || launchVisible;
  ui.bottomHud.hidden = combatVisible || launchVisible;
  ui.contextDrawer.hidden = launchVisible || archived || !contextVisible;
  ui.journalPanel.hidden = launchVisible || combatVisible || !state.journalOpen;
  ui.mapPanel.hidden = launchVisible || combatVisible || !state.mapOpen || !snapshot || archived;
  ui.inventoryPanel.hidden = launchVisible || archived || !snapshot || (!combatVisible && !state.inventoryOpen);
  ui.shell.classList.toggle("is-journal-open", state.journalOpen && !combatVisible);
  ui.shell.classList.toggle("is-map-open", state.mapOpen && !combatVisible);
  ui.shell.classList.toggle("is-inventory-open", state.inventoryOpen && !combatVisible);
  ui.shell.classList.toggle("is-dialogue-open", state.dialogueOpen && !combatVisible);
  ui.journalToggleButton.setAttribute("aria-pressed", state.journalOpen ? "true" : "false");
  ui.mapToggleButton.setAttribute("aria-pressed", state.mapOpen ? "true" : "false");
  ui.inventoryToggleButton.setAttribute("aria-pressed", state.inventoryOpen ? "true" : "false");
  ui.dialogueToggleButton.setAttribute("aria-pressed", state.dialogueOpen ? "true" : "false");
  ui.playerMessage.placeholder = getMessagePlaceholder(snapshot, state.selectedNpcId);
  ui.sendMessageButton.textContent = combatParleyActive ? "Send" : "Send";

  if (!snapshot) {
    ui.launchMessage.textContent = "Enter your name and begin a run from the center portal.";
    ui.outcomeTitle.textContent = "Run Chronicle";
    ui.outcomeNote.textContent = "Resolved runs and the running journal of NPC visits.";
    return;
  }

  if (snapshot.run_result) {
    ui.launchMessage.textContent = "Your last expedition is archived. Enter a name to launch a new run.";
    ui.outcomeTitle.textContent = "Archived Chronicle";
    ui.outcomeNote.textContent = "Final record from the last completed expedition alongside your NPC journal.";
    return;
  }

  if (snapshot.in_combat) {
    ui.outcomeTitle.textContent = "Run Chronicle";
    ui.outcomeNote.textContent = "Resolved runs and the running journal of NPC visits.";
    return;
  }

  ui.outcomeTitle.textContent = "Run Chronicle";
  ui.outcomeNote.textContent = "Resolved runs and the running journal of NPC visits.";
}

function getPresentedSnapshot(state: AppState): Snapshot | null {
  const snapshot = state.snapshot;
  if (!snapshot || !state.presentationLock) {
    return snapshot;
  }

  return {
    ...snapshot,
    in_combat: true,
    combat_state: state.presentationLock.combatState,
  };
}

function setMode(element: HTMLElement, nextMode: string): void {
  const previousMode = element.dataset.mode;
  element.dataset.mode = nextMode;

  if (previousMode && previousMode !== nextMode && !shouldSuppressModeTransition(previousMode, nextMode)) {
    triggerModeTransition(element);
  }
}

function shouldSuppressModeTransition(previousMode: string, nextMode: string): boolean {
  return previousMode.includes("combat") || nextMode.includes("combat");
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
    if (snapshot.combat_state?.negotiation?.active) {
      return "Send terms, warning, apology, or threat. Shift+Enter for a line break.";
    }
    return "Combat is active. Use the combat orders or open communications first.";
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
            <strong>${escapeHtml(item.name)}</strong>
            <div class="small">${escapeHtml(item.item_type)} / Qty ${item.quantity}${equipped ? " / readied" : ""}</div>
          </div>
          <span class="inventory-mark">${equipped ? "Readied" : item.item_type === "quest" ? "Quest" : "Stored"}</span>
        </div>
      `;
    })
    .join("");
}

function renderOverworldMap(overworldMap: OverworldMap | null): string {
  if (!overworldMap || overworldMap.nodes.length === 0) {
    return "<div class=\"chat-empty\">No overworld telemetry available for this expedition.</div>";
  }

  const nodeById = new Map(overworldMap.nodes.map((node) => [node.id, node]));
  const xValues = overworldMap.nodes.map((node) => node.x);
  const yValues = overworldMap.nodes.map((node) => node.y);
  const minX = Math.min(...xValues);
  const maxX = Math.max(...xValues);
  const minY = Math.min(...yValues);
  const maxY = Math.max(...yValues);
  const horizontalStep = 120;
  const verticalStep = 92;
  const padding = 36;
  const width = ((maxX - minX) * horizontalStep) + (padding * 2) || 240;
  const height = ((maxY - minY) * verticalStep) + (padding * 2) || 168;

  const getPoint = (nodeId: string): { x: number; y: number } | null => {
    const node = nodeById.get(nodeId);
    if (!node) {
      return null;
    }
    return {
      x: padding + ((node.x - minX) * horizontalStep),
      y: padding + ((node.y - minY) * verticalStep),
    };
  };

  const connections = overworldMap.connections
    .map((connection) => {
      const from = getPoint(connection.location_ids[0]);
      const to = getPoint(connection.location_ids[1]);
      if (!from || !to) {
        return "";
      }
      return `<line class="overworld-map-link${connection.discovered ? " is-discovered" : ""}" x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}" />`;
    })
    .join("");

  const nodes = overworldMap.nodes
    .map((node) => {
      const point = getPoint(node.id);
      if (!point) {
        return "";
      }
      const isCurrent = overworldMap.current_location_id === node.id;
      const label = node.discovered ? escapeHtml(node.name) : "Uncharted";
      return `
        <g class="overworld-map-node${node.discovered ? " is-discovered" : ""}${isCurrent ? " is-current" : ""}" transform="translate(${point.x} ${point.y})">
          <circle class="overworld-map-node-ring" r="18"></circle>
          <circle class="overworld-map-node-core" r="9"></circle>
          <text class="overworld-map-node-label" x="0" y="34" text-anchor="middle">${label}</text>
        </g>
      `;
    })
    .join("");

  const status = overworldMap.current_location_id
    ? `Current route anchor: ${escapeHtml(nodeById.get(overworldMap.current_location_id)?.name ?? "Unknown")}.`
    : "Current location is below the surface; overworld telemetry remains cached.";

  return `
    <div class="overworld-map-card">
      <p class="small overworld-map-note">${status}</p>
      <svg class="overworld-map-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Overworld exploration map">
        <g class="overworld-map-links">${connections}</g>
        <g class="overworld-map-nodes">${nodes}</g>
      </svg>
    </div>
  `;
}

function renderQuestList(snapshot: Snapshot): string {
  if (snapshot.quests.length === 0) {
    return renderQuestEmpty("No contracts active. Ask nearby NPCs if they need work done.");
  }

  return snapshot.quests
    .map((quest) => {
      const statusLabel = quest.status === "offered"
        ? "Offer"
        : quest.status === "active"
          ? quest.can_turn_in ? "Ready to turn in" : "Active"
          : quest.status === "completed"
            ? "Completed"
            : "Declined";
      const progressText = quest.status === "offered"
        ? `Reward ${quest.reward_gold} gold`
        : `${quest.progress_value}/${quest.progress_target} recovered`;
      const meta = [quest.offered_by_npc_name, quest.target_biome_name, quest.target_floor_number ? `Floor ${quest.target_floor_number}` : ""]
        .filter(Boolean)
        .join(" / ");
      return `
        <article class="quest-card is-${quest.status}">
          <div class="quest-card-head">
            <div>
              <strong>${escapeHtml(quest.title)}</strong>
              <div class="small">${escapeHtml(meta)}</div>
            </div>
            <span class="quest-status quest-status-${quest.status}">${escapeHtml(statusLabel)}</span>
          </div>
          <p class="quest-summary">${renderChatText(quest.summary)}</p>
          <p class="quest-objective">${renderChatText(quest.objective_text)}</p>
          <div class="quest-foot">
            <span class="small">${escapeHtml(progressText)}</span>
            <span class="small">${escapeHtml(quest.hint)}</span>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderQuestChoicePanel(snapshot: Snapshot, selectedNpcId: string): string {
  if (!selectedNpcId || snapshot.in_combat || snapshot.run_result) {
    return "";
  }

  const offeredQuest = snapshot.quests.find((quest) => quest.status === "offered" && quest.offered_by_npc_id === selectedNpcId);
  if (!offeredQuest) {
    return "";
  }

  return `
    <div class="quest-choice-card">
      <div class="quest-choice-copy">
        <span class="quest-status quest-status-offered">Quest offer</span>
        <strong>${escapeHtml(offeredQuest.title)}</strong>
        <p>${renderChatText(offeredQuest.summary)}</p>
        <p class="quest-objective">${renderChatText(offeredQuest.objective_text)}</p>
      </div>
      <div class="quest-choice-actions">
        <button type="button" data-quest-action="accept" data-quest-id="${offeredQuest.id}">Accept</button>
        <button type="button" data-quest-action="decline" data-quest-id="${offeredQuest.id}">Decline</button>
      </div>
    </div>
  `;
}

function renderNpcList(snapshot: Snapshot, selectedNpcId: string): string {
  if (snapshot.nearby_npcs.length === 0) {
    return "<p class=\"small empty-copy\">No contacts in range.</p>";
  }

  return `
    <div class="npc-roster">
      ${snapshot.nearby_npcs
      .map((npc) => {
        const selected = npc.id === selectedNpcId;
        return `
          <button class="npc-tab${selected ? " is-selected" : ""}" data-npc-id="${npc.id}" ${selected ? "disabled" : ""}>
            <span class="npc-tab-name">${escapeHtml(npc.display_name)}</span>
            <span class="npc-tab-meta">${escapeHtml(npc.distance === 0 ? "In range" : "One step away")}</span>
          </button>
        `;
      })
      .join("")}
    </div>
  `;
}

function renderUnifiedTranscript(snapshot: Snapshot | null, state: AppState): string {
  if (snapshot?.in_combat && snapshot.combat_state) {
    if (snapshot.combat_state.negotiation?.active) {
      return renderCombatCommunicationTranscript(snapshot.combat_state);
    }
    return renderCombatDispatch(snapshot);
  }

  if (!state.selectedNpcId) {
    return renderChatEmpty(
      snapshot
        ? "No active conversation. Choose a nearby contact to start chatting."
        : "No active channel. Begin a run and choose a nearby contact.",
    );
  }

  return renderDialogueTranscript(snapshot!, state);
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderDialogueTranscript(snapshot: Snapshot, state: AppState): string {
  const thread = [...(state.dialogueThreads[state.selectedNpcId] ?? [])];
  if (thread.length === 0 && snapshot.dialogue?.npc_id === state.selectedNpcId) {
    thread.push({
      id: "snapshot-dialogue",
      sequence: -1,
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

function renderCombatDispatch(snapshot: Snapshot): string {
  const combatState = snapshot.combat_state;
  if (!combatState) {
    return renderChatEmpty("Combat telemetry unavailable.");
  }

  const entries: DialogueMessage[] = combatState.events.map((event, index) => ({
    id: event.id,
    sequence: index,
    speaker: event.actor === "player" ? "player" : event.actor === "enemy" ? "npc" : event.actor === "ally" ? "ally" : "system",
    npcName: combatState.enemy.name,
    text: event.text,
  }));

  if (entries.length === 0) {
    combatState.log.forEach((line, index) => {
      entries.push({
        id: `combat-log-${index}`,
        sequence: entries.length,
        speaker: index === 0 ? "npc" : "system",
        npcName: combatState.enemy.name,
        text: line,
      });
    });
  }

  return entries.map(renderChatMessage).join("");
}

function renderCombatCommunicationTranscript(combatState: NonNullable<Snapshot["combat_state"]>): string {
  const transcript = combatState.negotiation?.transcript ?? [];
  if (transcript.length === 0) {
    return renderChatEmpty("Communication line is open. Send the first message to begin talking to the enemy.");
  }

  const entries: DialogueMessage[] = transcript.map((entry, index) => ({
    id: `combat-negotiation-${index}`,
    sequence: index,
    speaker: entry.speaker === "enemy" ? "npc" : entry.speaker,
    npcName: combatState.enemy.name,
    text: entry.text,
  }));

  return entries.map(renderChatMessage).join("");
}

// ---------------------------------------------------------------------------
// Combat overlay — smart update (preserves pinball canvas on re-renders)
// ---------------------------------------------------------------------------

export function applyCombatOverlayUpdate(el: HTMLDivElement, snapshot: Snapshot): void {
  const inCombat = !!(snapshot.in_combat && snapshot.combat_state);

  if (!inCombat) {
    el.innerHTML = "";
    return;
  }

  // If the canvas already exists, only refresh the mutable sidecard + strip.
  // This keeps the live pinball simulation in place across snapshot updates.
  const existingCanvas = el.querySelector<HTMLCanvasElement>("#pinball-cabinet-canvas");
  if (existingCanvas) {
    const sidecard = el.querySelector<HTMLElement>("#combat-sidecard");
    if (sidecard) sidecard.innerHTML = renderCombatSidecardContent(snapshot);
    const strip = el.querySelector<HTMLElement>("#combat-inventory-strip");
    if (strip) strip.innerHTML = renderCombatInventoryStripContent(snapshot);
    return;
  }

  // First paint: full layout
  el.innerHTML = renderCombatOverlay(snapshot);
}

function renderCombatOverlay(snapshot: Snapshot): string {
  const combatState = snapshot.combat_state;
  if (!combatState) return "";

  return `
    <div class="combat-overlay-shell">
      <div class="combat-overlay-stage">
        <div class="combat-pinball-cabinet">
          <canvas id="pinball-cabinet-canvas" aria-label="Pinball combat cabinet"></canvas>
        </div>
        <div class="combat-cabinet-sidecard" id="combat-sidecard">
          ${renderCombatSidecardContent(snapshot)}
        </div>
      </div>
      <div class="combat-inventory-strip" id="combat-inventory-strip">
        ${renderCombatInventoryStripContent(snapshot)}
      </div>
    </div>
  `;
}

function renderCombatSidecardContent(snapshot: Snapshot): string {
  const combatState = snapshot.combat_state;
  if (!combatState) return "";

  const asciiArt = combatState.enemy.presentation.ascii_art;
  const enemyArt = asciiArt.length > 0
    ? `<pre class="combat-overlay-art" aria-hidden="true">${escapeHtml(asciiArt.join("\n"))}</pre>`
    : `<div class="combat-overlay-sigil" aria-hidden="true">${escapeHtml(combatState.enemy.name.slice(0, 1).toUpperCase())}</div>`;

  const player = combatState.party.find((s) => s.is_player);
  const playerHp    = player ? player.hp    : 0;
  const playerMaxHp = player ? player.max_hp : 0;
  const playerHpPct = playerMaxHp > 0 ? Math.max(0, Math.min(100, (playerHp / playerMaxHp) * 100)) : 0;
  const enemyHpPct  = combatState.enemy.max_hp > 0
    ? Math.max(0, Math.min(100, (combatState.enemy.hp / combatState.enemy.max_hp) * 100))
    : 0;

  const log = renderCombatSidecardLog(snapshot);
  const negotiation = combatState.negotiation ? renderNegotiationCard(combatState) : "";

  return `
    <div class="combat-cabinet-sidecard-head">
      <h3>${escapeHtml(combatState.enemy.name)}</h3>
      <span class="combat-stat-pill">Round ${combatState.round}</span>
    </div>
    <div class="combat-cabinet-monster-panel">
      ${enemyArt}
    </div>
    <div class="combat-cabinet-hp-grid">
      <div class="combat-cabinet-hp-card is-enemy">
        <span class="combat-enemy-label">Monster</span>
        <strong>${combatState.enemy.hp}<span class="combat-hp-sep">/</span>${combatState.enemy.max_hp}</strong>
        <div class="combat-hp-bar"><div class="combat-hp-bar-fill is-enemy" style="width:${enemyHpPct}%"></div></div>
      </div>
      <div class="combat-cabinet-hp-card is-player">
        <span class="combat-enemy-label">You</span>
        <strong>${playerHp}<span class="combat-hp-sep">/</span>${playerMaxHp}</strong>
        <div class="combat-hp-bar"><div class="combat-hp-bar-fill is-player" style="width:${playerHpPct}%"></div></div>
      </div>
    </div>
    ${negotiation}
    <div class="combat-sidecard-log">
      ${log}
    </div>
  `;
}

function renderCombatSidecardLog(snapshot: Snapshot): string {
  const combatState = snapshot.combat_state;
  if (!combatState) return "";

  const events = combatState.events;
  if (events.length === 0) {
    return `<p class="small combat-log-empty">Combat started. Launch the ball to attack.</p>`;
  }

  return events
    .slice(-10)
    .map((event) => {
      const cls = `combat-log-entry is-${event.actor} is-${event.emphasis}`;
      return `<div class="${cls}">${renderChatText(event.text)}</div>`;
    })
    .join("");
}

function renderCombatInventoryStripContent(snapshot: Snapshot): string {
  const weapons = snapshot.inventory.filter((item) =>
    item.item_type === "weapon" || item.item_type === "armor" || item.equipped,
  );

  if (weapons.length === 0) {
    return `<span class="combat-inventory-empty small">No items equipped.</span>`;
  }

  return weapons
    .map((item) => {
      const isEquipped = item.equipped || item.item_id === snapshot.equipped_weapon;
      return `
        <div class="combat-inventory-item${isEquipped ? " is-equipped" : ""}"
             title="${escapeHtml(item.description)}">
          <span class="combat-inventory-item-name">${escapeHtml(item.name)}</span>
          <span class="combat-inventory-item-type">${escapeHtml(item.item_type)}</span>
          ${isEquipped ? '<span class="combat-inventory-item-badge">equipped</span>' : ""}
        </div>
      `;
    })
    .join("");
}

function renderNegotiationCard(combatState: Snapshot["combat_state"]): string {
  if (!combatState?.negotiation) {
    return "";
  }

  const negotiation = combatState.negotiation;
  const options = negotiation.options.length > 0
    ? negotiation.options.map((option) => `<span class="negotiation-option-pill">${escapeHtml(option.label)}</span>`).join("")
    : '<span class="negotiation-option-pill is-muted">No terms</span>';
  const transcript = negotiation.transcript.length > 0
    ? negotiation.transcript.map(renderNegotiationEntry).join("")
    : '<p class="small negotiation-empty">No terms have been offered yet.</p>';
  const status = negotiation.locked
    ? negotiation.lock_reason || "This mind is closed to reason."
    : negotiation.active
      ? "Communication is active. Press for a term or end the channel before the creature does."
      : negotiation.available
        ? `This foe can answer by ${escapeHtml(negotiation.communication_mode)}.`
        : negotiation.lock_reason || "No opening for reason.";

  return `
    <aside class="negotiation-card${negotiation.locked ? " is-locked" : negotiation.active ? " is-active" : ""}">
      <div class="negotiation-card-head">
        <div>
          <span class="combat-enemy-label">Communications</span>
          <strong>${escapeHtml(negotiation.communication_mode)}</strong>
        </div>
        <div class="negotiation-readout">
          <span class="combat-stat-pill">${escapeHtml(negotiation.temperament)}</span>
          <span class="combat-stat-pill">Leverage ${negotiation.leverage >= 0 ? `+${negotiation.leverage}` : negotiation.leverage}</span>
          <span class="combat-stat-pill${negotiation.anger > 0 ? " is-danger" : ""}">Anger ${negotiation.anger}/${negotiation.anger_limit}</span>
        </div>
      </div>
      <p class="small negotiation-copy">${status}</p>
      ${negotiation.active_intent ? `<p class="small negotiation-copy">Current line: ${escapeHtml(negotiation.active_intent)}</p>` : ""}
      <div class="negotiation-options">${options}</div>
      <div class="negotiation-transcript">${transcript}</div>
    </aside>
  `;
}

function renderNegotiationEntry(entry: CombatNegotiationEntry): string {
  const speaker = entry.speaker === "player"
    ? "You"
    : entry.speaker === "enemy"
      ? "Foe"
      : "System";

  return `
    <div class="negotiation-entry is-${entry.speaker}">
      <span class="negotiation-speaker">${escapeHtml(speaker)}</span>
      <span>${renderChatText(entry.text)}</span>
    </div>
  `;
}

function renderCombatPartyCard(slot: CombatPartySlot): string {
  const hpMax = slot.reserve ? 1 : Math.max(slot.max_hp, 1);
  const hpValue = slot.reserve ? 0 : slot.hp;
  const meterWidth = Math.max(0, Math.min(100, (hpValue / hpMax) * 100));
  const hpText = slot.reserve ? "Reserve" : `${slot.hp}/${slot.max_hp} HP`;
  return `
    <article class="combat-party-card${slot.is_player ? " is-player" : ""}${slot.reserve ? " is-reserve" : ""}">
      <div class="combat-party-card-head">
        <div>
          <span class="combat-enemy-label">${escapeHtml(slot.role)}</span>
          <strong>${escapeHtml(slot.name)}</strong>
        </div>
        <span class="combat-party-stat">ATK ${slot.attack}</span>
      </div>
      <div class="combat-party-meter">
        <div class="combat-party-meter-bar"><span style="width:${meterWidth}%"></span></div>
        <div class="combat-party-meter-copy">
          <span>${escapeHtml(hpText)}</span>
          <span>DEF ${slot.defence}</span>
        </div>
      </div>
    </article>
  `;
}

function renderCombatActions(snapshot: Snapshot): string {
  const combatState = snapshot.combat_state;
  if (!combatState) {
    return "";
  }

  return combatState.available_actions
    .map((action) => {
      const label = action.id === "parley_open"
        ? "Communicate"
        : action.id === "parley_end"
          ? "End communication"
          : action.label;

      return `
      <button
        type="button"
        class="combat-action-button combat-action-${action.kind}"
        data-combat-action="${escapeHtml(action.id)}"
        ${action.enabled ? "" : "disabled"}
      >
        ${escapeHtml(label)}
      </button>
    `;
    })
    .join("");
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

function renderQuestEmpty(copy: string): string {
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
    : message.speaker === "ally"
      ? "Ally"
    : message.speaker === "system"
      ? "System"
      : message.npcName ?? "Contact";
  const sourceChip = message.speaker === "npc" && message.source && !message.streaming
    ? `<span class="chat-source">${escapeHtml(message.source)}</span>`
    : "";
  const text = message.text.trim();
  const content = message.streaming && !text
    ? '<div class="chat-loading" aria-label="Response in progress"><span></span><span></span><span></span></div>'
    : `<p>${renderChatText(text)}</p>`;

  return `
    <div class="chat-message is-${message.speaker}${message.streaming ? " is-streaming" : ""}">
      <div class="chat-bubble">
        <div class="chat-bubble-meta">
          <span class="chat-speaker">${escapeHtml(speakerLabel)}</span>
          ${sourceChip}
        </div>
        ${content}
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