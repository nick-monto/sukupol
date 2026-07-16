import type { CombatNegotiationEntry, CombatPartySlot, Snapshot } from "../types";
import { escapeHtml, renderChatText } from "./dom";

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

export function renderCombatPartyCard(slot: CombatPartySlot): string {
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

export function renderCombatActions(snapshot: Snapshot): string {
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
