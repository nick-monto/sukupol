import "./styles.css";

type Snapshot = {
  run_id: string;
  player_name: string;
  location: {
    id: string;
    name: string;
    description: string;
    floor_number?: number;
    biome_id?: string;
  };
  stats: {
    hp: number;
    max_hp: number;
    gold: number;
  };
  facing: string;
  message: string;
  first_person_view: string[];
  minimap: string[];
  nearby_npcs: Array<{
    id: string;
    display_name: string;
    role: string;
    distance: number;
  }>;
  inventory: Array<{
    item_id: string;
    quantity: number;
    equipped?: boolean;
  }>;
  equipped_weapon?: string | null;
  in_combat: boolean;
  combat_state?: {
    enemy_id: string;
    enemy_name: string;
    enemy_hp: number;
    enemy_max_hp: number;
    round: number;
    log: string[];
  } | null;
  run_result?: string | null;
  run_depth: number;
  enemies_defeated: number;
  outcome_summary?: {
    result: string;
    depth_reached: number;
    enemies_defeated: number;
    gold_earned: number;
    items_found: Array<{
      item_id: string;
      quantity: number;
    }>;
  } | null;
  progression?: {
    total_runs: number;
    total_victories: number;
    deepest_depth: number;
    last_outcome: string;
  } | null;
  dialogue?: {
    npc_id: string;
    npc_name: string;
    text: string;
    source: string;
  };
};

const apiBase = (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://127.0.0.1:8000";

const state = {
  bootstrapTitle: "Sukupol",
  runId: "",
  snapshot: null as Snapshot | null,
  selectedNpcId: "",
  busy: false,
};

const app = document.querySelector<HTMLDivElement>("#app");

if (!app) {
  throw new Error("App root not found");
}

app.innerHTML = `
  <div class="shell">
    <section class="hero">
      <div class="hero-top">
        <div>
          <p class="small">Server-authoritative ASCII prototype</p>
          <h1>${state.bootstrapTitle}</h1>
          <p>Walk the town, descend the first halls, and test the dialogue seam before the broader procgen and rogue-lite systems land.</p>
        </div>
        <div class="hero-actions">
          <button id="start-run">Start new run</button>
          <button id="extract-run">Extract run</button>
        </div>
      </div>
      <p class="small">Controls: <span class="hotkey">W</span> forward, <span class="hotkey">S</span> backward, <span class="hotkey">A</span> turn left, <span class="hotkey">D</span> turn right.</p>
    </section>

    <section class="grid">
      <div class="panel viewport">
        <div class="status-row" id="status-row"></div>
        <h2 id="location-name">No run started</h2>
        <p id="location-description">Bring up the backend and start a run to render the first-person view.</p>
        <pre id="viewport">Stand up the backend and begin a run.</pre>
        <div class="hud">
          <p class="message" id="message-log">Awaiting input.</p>
          <div class="controls">
            <button data-action="forward">Forward</button>
            <button data-action="backward">Backward</button>
            <button data-action="turn_left">Turn left</button>
            <button data-action="turn_right">Turn right</button>
          </div>
        </div>
      </div>

      <div class="panel map">
        <h2>Situation</h2>
        <p class="small">The minimap stays visible during the prototype so movement and transitions are easy to inspect.</p>
        <pre id="minimap">No map yet.</pre>
        <div class="panel-subsection">
          <h3>Inventory</h3>
          <div class="inventory-list" id="inventory-list"></div>
        </div>
        <div class="npc-list" id="npc-list"></div>
      </div>
    </section>

    <section class="grid">
      <div class="panel log">
        <h2 id="log-title">Dialogue</h2>
        <p class="small" id="log-help">Nearby NPCs can answer through the current fallback service. This panel will later stream local-model output via Agent Framework.</p>
        <pre id="dialogue-log">No dialogue yet.</pre>
      </div>

      <div class="panel">
        <h2>Actions</h2>
        <div class="dialogue-form" id="interaction-panel">
          <label for="player-message">Message</label>
          <textarea id="player-message" rows="6" placeholder="Ask about the dungeon, the town, or supplies."></textarea>
          <button id="send-message">Send to selected NPC</button>
          <div class="combat-actions" id="combat-actions">
            <button data-combat-action="attack">Attack</button>
            <button data-combat-action="defend">Defend</button>
            <button data-combat-action="use_item:health_potion">Use potion</button>
            <button data-combat-action="flee">Flee</button>
          </div>
        </div>
      </div>
    </section>

    <section class="panel outcome-panel" id="outcome-panel">
      <h2>Run Outcome</h2>
      <pre id="outcome-log">No completed run yet.</pre>
    </section>
  </div>
`;

const startRunButton = element<HTMLButtonElement>("#start-run");
const extractRunButton = element<HTMLButtonElement>("#extract-run");
const viewport = element<HTMLPreElement>("#viewport");
const minimap = element<HTMLPreElement>("#minimap");
const dialogueLog = element<HTMLPreElement>("#dialogue-log");
const logTitle = element<HTMLHeadingElement>("#log-title");
const logHelp = element<HTMLParagraphElement>("#log-help");
const locationName = element<HTMLHeadingElement>("#location-name");
const locationDescription = element<HTMLParagraphElement>("#location-description");
const messageLog = element<HTMLParagraphElement>("#message-log");
const npcList = element<HTMLDivElement>("#npc-list");
const inventoryList = element<HTMLDivElement>("#inventory-list");
const sendMessageButton = element<HTMLButtonElement>("#send-message");
const playerMessage = element<HTMLTextAreaElement>("#player-message");
const statusRow = element<HTMLDivElement>("#status-row");
const combatActions = element<HTMLDivElement>("#combat-actions");
const outcomeLog = element<HTMLPreElement>("#outcome-log");

document.addEventListener("keydown", async (event) => {
  if (!state.runId || state.busy || state.snapshot?.in_combat) {
    return;
  }

  const keymap: Record<string, string> = {
    w: "forward",
    s: "backward",
    a: "turn_left",
    d: "turn_right",
  };

  const action = keymap[event.key.toLowerCase()];
  if (!action) {
    return;
  }

  event.preventDefault();
  await runAction(action);
});

startRunButton.addEventListener("click", async () => {
  state.busy = true;
  syncBusyState();
  try {
    const snapshot = await api<Snapshot>("/api/runs", {
      method: "POST",
      body: JSON.stringify({ player_name: "Wayfarer" }),
    });
    state.runId = snapshot.run_id;
    state.snapshot = snapshot;
    state.selectedNpcId = snapshot.nearby_npcs[0]?.id ?? "";
    render();
  } catch (error) {
    renderError(error);
  } finally {
    state.busy = false;
    syncBusyState();
  }
});

extractRunButton.addEventListener("click", async () => {
  if (!state.runId || state.busy) {
    return;
  }

  state.busy = true;
  syncBusyState();
  try {
    const snapshot = await api<Snapshot>(`/api/runs/${state.runId}/extract`, {
      method: "POST",
    });
    state.snapshot = snapshot;
    render();
  } catch (error) {
    renderError(error);
  } finally {
    state.busy = false;
    syncBusyState();
  }
});

document.querySelectorAll<HTMLButtonElement>("[data-action]").forEach((button) => {
  button.addEventListener("click", async () => {
    const action = button.dataset.action;
    if (!action) {
      return;
    }
    await runAction(action);
  });
});

sendMessageButton.addEventListener("click", async () => {
  if (!state.runId || !state.selectedNpcId || state.busy || state.snapshot?.in_combat) {
    return;
  }

  const message = playerMessage.value.trim();
  if (!message) {
    dialogueLog.textContent = "Type a message before sending it.";
    return;
  }

  state.busy = true;
  syncBusyState();
  try {
    const snapshot = await api<Snapshot>(`/api/npcs/${state.selectedNpcId}/talk`, {
      method: "POST",
      body: JSON.stringify({ run_id: state.runId, message }),
    });
    state.snapshot = snapshot;
    render();
  } catch (error) {
    renderError(error);
  } finally {
    state.busy = false;
    syncBusyState();
  }
});

combatActions.querySelectorAll<HTMLButtonElement>("button[data-combat-action]").forEach((button) => {
  button.addEventListener("click", async () => {
    const action = button.dataset.combatAction;
    if (!action || !state.runId) {
      return;
    }

    state.busy = true;
    syncBusyState();
    try {
      const snapshot = await api<Snapshot>(`/api/runs/${state.runId}/combat`, {
        method: "POST",
        body: JSON.stringify({ action }),
      });
      state.snapshot = snapshot;
      render();
    } catch (error) {
      renderError(error);
    } finally {
      state.busy = false;
      syncBusyState();
    }
  });
});

render();

async function runAction(action: string): Promise<void> {
  if (!state.runId) {
    return;
  }

  state.busy = true;
  syncBusyState();
  try {
    const snapshot = await api<Snapshot>(`/api/runs/${state.runId}/actions`, {
      method: "POST",
      body: JSON.stringify({ action }),
    });
    state.snapshot = snapshot;
    if (!snapshot.nearby_npcs.some((npc) => npc.id === state.selectedNpcId)) {
      state.selectedNpcId = snapshot.nearby_npcs[0]?.id ?? "";
    }
    render();
  } catch (error) {
    renderError(error);
  } finally {
    state.busy = false;
    syncBusyState();
  }
}

function render(): void {
  const snapshot = state.snapshot;
  if (!snapshot) {
    statusRow.innerHTML = statCards([
      ["Status", "No run"],
      ["Facing", "-"],
      ["Gold", "-"],
    ]);
    locationName.textContent = "No run started";
    locationDescription.textContent = "Bring up the backend and start a run to render the first-person view.";
    viewport.textContent = "Stand up the backend and begin a run.";
    minimap.textContent = "No map yet.";
    messageLog.textContent = "Awaiting input.";
    inventoryList.innerHTML = "<p class=\"small\">No inventory yet.</p>";
    npcList.innerHTML = "<p class=\"small\">No NPCs in range.</p>";
    dialogueLog.textContent = "No dialogue yet.";
    outcomeLog.textContent = "No completed run yet.";
    return;
  }

  statusRow.innerHTML = statCards([
    ["Health", `${snapshot.stats.hp}/${snapshot.stats.max_hp}`],
    ["Facing", snapshot.facing],
    ["Gold", String(snapshot.stats.gold)],
  ]);
  locationName.textContent = snapshot.location.name;
  locationDescription.textContent = snapshot.location.floor_number
    ? `${snapshot.location.description} Floor ${snapshot.location.floor_number}.`
    : snapshot.location.description;
  viewport.textContent = snapshot.in_combat && snapshot.combat_state
    ? renderCombatViewport(snapshot)
    : snapshot.first_person_view.join("\n");
  minimap.textContent = snapshot.minimap.join("\n");
  messageLog.textContent = snapshot.message;
  inventoryList.innerHTML = renderInventory(snapshot);
  npcList.innerHTML = renderNpcList(snapshot);
  if (snapshot.in_combat && snapshot.combat_state) {
    logTitle.textContent = `Combat: ${snapshot.combat_state.enemy_name}`;
    logHelp.textContent = `Round ${snapshot.combat_state.round}. Movement and dialogue are disabled until combat resolves.`;
    dialogueLog.textContent = snapshot.combat_state.log.join("\n\n");
  } else {
    logTitle.textContent = "Dialogue";
    logHelp.textContent = "Nearby NPCs can answer through the current fallback service. This panel will later stream local-model output via Agent Framework.";
    dialogueLog.textContent = snapshot.dialogue
      ? `${snapshot.dialogue.npc_name} [${snapshot.dialogue.source}]\n\n${snapshot.dialogue.text}`
      : "No dialogue yet.";
  }
  outcomeLog.textContent = snapshot.outcome_summary
    ? renderOutcome(snapshot)
    : "No completed run yet.";

  npcList.querySelectorAll<HTMLButtonElement>("button[data-npc-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedNpcId = button.dataset.npcId ?? "";
      render();
    });
  });
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
    return "<p class=\"small\">Inventory is empty.</p>";
  }

  return snapshot.inventory
    .map((item) => {
      const equipped = item.item_id === snapshot.equipped_weapon ? " equipped" : "";
      return `
        <div class="inventory-item">
          <strong>${item.item_id.replaceAll("_", " ")}</strong>
          <div class="small">Qty ${item.quantity}${equipped}</div>
        </div>
      `;
    })
    .join("");
}

function renderNpcList(snapshot: Snapshot): string {
  if (snapshot.nearby_npcs.length === 0) {
    return "<p class=\"small\">No NPCs in range.</p>";
  }

  return `
    <h3>Nearby NPCs</h3>
    ${snapshot.nearby_npcs
      .map((npc) => {
        const selected = npc.id === state.selectedNpcId;
        return `
          <div class="npc-item">
            <div>
              <strong>${npc.display_name}</strong>
              <div class="small">${npc.role} · ${npc.distance === 0 ? "beside you" : "one step away"}</div>
            </div>
            <button data-npc-id="${npc.id}" ${selected ? "disabled" : ""}>
              ${selected ? "Selected" : "Select"}
            </button>
          </div>
        `;
      })
      .join("")}
  `;
}

function renderError(error: unknown): void {
  const message = error instanceof Error ? error.message : "Unknown error";
  dialogueLog.textContent = message;
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
    lines.push(`Items: ${outcome.items_found.map((item) => `${item.item_id} x${item.quantity}`).join(", ")}`);
  }
  if (progression) {
    lines.push("");
    lines.push(`Total runs: ${progression.total_runs}`);
    lines.push(`Victories: ${progression.total_victories}`);
    lines.push(`Deepest depth: ${progression.deepest_depth}`);
  }
  return lines.join("\n");
}

function syncBusyState(): void {
  const disabled = state.busy;
  startRunButton.disabled = disabled;
  extractRunButton.disabled = disabled || !state.runId || state.snapshot?.in_combat === true || state.snapshot?.location.id !== "town_square" || !!state.snapshot?.run_result;
  sendMessageButton.disabled = disabled || !state.selectedNpcId || !state.runId || state.snapshot?.in_combat === true || !!state.snapshot?.run_result;
  document.querySelectorAll<HTMLButtonElement>("[data-action]").forEach((button) => {
    button.disabled = disabled || !state.runId || state.snapshot?.in_combat === true || !!state.snapshot?.run_result;
  });
  combatActions.querySelectorAll<HTMLButtonElement>("button[data-combat-action]").forEach((button) => {
    button.disabled = disabled || !state.runId || state.snapshot?.in_combat !== true || !!state.snapshot?.run_result;
  });
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

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    headers: {
      "Content-Type": "application/json",
    },
    ...init,
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed with ${response.status}`);
  }

  return (await response.json()) as T;
}

function element<T extends Element>(selector: string): T {
  const found = document.querySelector<T>(selector);
  if (!found) {
    throw new Error(`Missing element: ${selector}`);
  }
  return found;
}
