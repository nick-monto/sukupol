export function createAppMarkup(title: string): string {
  return `
    <div class="shell" id="shell" data-mode="idle">
      <section class="hero" id="hero-panel">
        <div class="hero-top">
          <div class="hero-copy">
            <p class="eyebrow">Expedition Console / server-authoritative prototype</p>
            <h1>${title}</h1>
            <p class="hero-lede">A ceremonial terminal for town walks, dungeon descents, and uncertain conversations.</p>
          </div>
          <div class="hero-actions">
            <button id="start-run">Begin expedition</button>
            <button id="extract-run">Return to town</button>
          </div>
        </div>

        <div class="hero-band">
          <p class="signal" id="expedition-signal">No active expedition. Establish a run to receive telemetry.</p>
          <div class="legend">
            <span><span class="hotkey">W</span> advance</span>
            <span><span class="hotkey">S</span> withdraw</span>
            <span><span class="hotkey">A</span> pivot left</span>
            <span><span class="hotkey">D</span> pivot right</span>
          </div>
        </div>

        <div class="hero-summary" id="hero-summary"></div>
      </section>

      <section class="grid grid-primary">
        <div class="panel viewport" id="viewport-panel">
          <div class="panel-header panel-header-inline">
            <div>
              <p class="eyebrow">World View</p>
              <h2 id="location-name">No run started</h2>
            </div>
            <p class="location-meta" id="location-meta">Awaiting expedition telemetry.</p>
          </div>
          <p id="location-description">Bring up the backend and start a run to render the first-person view.</p>
          <div class="display-frame">
            <pre id="viewport">Stand up the backend and begin a run.</pre>
          </div>
          <div class="hud">
            <div class="message-strip" id="message-strip">
              <span class="message-label" id="message-label">Field report</span>
              <p class="message" id="message-log">Awaiting input.</p>
            </div>
            <div class="controls">
              <button data-action="forward">Advance</button>
              <button data-action="backward">Withdraw</button>
              <button data-action="turn_left">Pivot left</button>
              <button data-action="turn_right">Pivot right</button>
            </div>
          </div>
        </div>

        <div class="panel map" id="map-panel">
          <div class="panel-header">
            <div>
              <p class="eyebrow">Cartography</p>
              <h2>Survey Slate</h2>
            </div>
            <p class="small panel-note">Persistent map telemetry for inspection during the prototype.</p>
          </div>
          <div class="display-frame compact-frame">
            <pre id="minimap">No map yet.</pre>
          </div>
          <div class="panel-subsection">
            <div class="panel-header panel-header-compact">
              <div>
                <p class="eyebrow">Stores</p>
                <h3>Loadout</h3>
              </div>
            </div>
            <div class="inventory-list" id="inventory-list"></div>
          </div>
          <div class="npc-list" id="npc-list"></div>
        </div>
      </section>

      <section class="grid grid-secondary">
        <div class="panel log" id="log-panel">
          <div class="panel-header">
            <div>
              <p class="eyebrow">Comms</p>
              <h2 id="log-title">Dialogue</h2>
            </div>
            <p class="small panel-note" id="log-help">Nearby NPCs can answer through the current fallback service. This panel will later stream local-model output via Agent Framework.</p>
          </div>
          <div class="display-frame compact-frame">
            <pre id="dialogue-log">No dialogue yet.</pre>
          </div>
        </div>

        <div class="panel action-panel" id="action-panel" data-mode="idle">
          <div class="panel-header">
            <div>
              <p class="eyebrow" id="dispatch-kicker">Dispatch</p>
              <h2 id="dispatch-title">Field Orders</h2>
            </div>
            <p class="small panel-note" id="dispatch-note">Compose a message when stationed near an NPC. Combat orders replace dialogue during encounters.</p>
          </div>
          <div class="dialogue-form" id="interaction-panel">
            <label for="player-message">Message</label>
            <textarea id="player-message" rows="6" placeholder="Ask about the dungeon, the town, or supplies."></textarea>
            <button id="send-message">Transmit to selected contact</button>
            <div class="combat-actions" id="combat-actions">
              <button data-combat-action="attack">Attack</button>
              <button data-combat-action="defend">Defend</button>
              <button data-combat-action="use_item:health_potion">Use potion</button>
              <button data-combat-action="flee">Flee</button>
            </div>
          </div>
        </div>
      </section>

      <section class="panel outcome-panel" id="outcome-panel" data-mode="idle">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Archive</p>
            <h2 id="outcome-title">Run Chronicle</h2>
          </div>
          <p class="small panel-note" id="outcome-note">End-of-run outcomes and long-view progression notes.</p>
        </div>
        <div class="display-frame compact-frame">
          <pre id="outcome-log">No completed run yet.</pre>
        </div>
      </section>
    </div>
  `;
}

export function element<T extends Element>(selector: string): T {
  const found = document.querySelector<T>(selector);
  if (!found) {
    throw new Error(`Missing element: ${selector}`);
  }
  return found;
}

export type UiElements = {
  shell: HTMLDivElement;
  heroPanel: HTMLElement;
  viewportPanel: HTMLElement;
  logPanel: HTMLElement;
  actionPanel: HTMLElement;
  outcomePanel: HTMLElement;
  startRunButton: HTMLButtonElement;
  extractRunButton: HTMLButtonElement;
  expeditionSignal: HTMLParagraphElement;
  heroSummary: HTMLDivElement;
  viewport: HTMLPreElement;
  minimap: HTMLPreElement;
  dialogueLog: HTMLPreElement;
  logTitle: HTMLHeadingElement;
  logHelp: HTMLParagraphElement;
  locationName: HTMLHeadingElement;
  locationMeta: HTMLParagraphElement;
  locationDescription: HTMLParagraphElement;
  messageStrip: HTMLDivElement;
  messageLabel: HTMLSpanElement;
  messageLog: HTMLParagraphElement;
  npcList: HTMLDivElement;
  inventoryList: HTMLDivElement;
  sendMessageButton: HTMLButtonElement;
  playerMessage: HTMLTextAreaElement;
  combatActions: HTMLDivElement;
  dispatchKicker: HTMLParagraphElement;
  dispatchTitle: HTMLHeadingElement;
  dispatchNote: HTMLParagraphElement;
  outcomeTitle: HTMLHeadingElement;
  outcomeNote: HTMLParagraphElement;
  outcomeLog: HTMLPreElement;
};

export function getUiElements(): UiElements {
  return {
    shell: element<HTMLDivElement>("#shell"),
    heroPanel: element<HTMLElement>("#hero-panel"),
    viewportPanel: element<HTMLElement>("#viewport-panel"),
    logPanel: element<HTMLElement>("#log-panel"),
    actionPanel: element<HTMLElement>("#action-panel"),
    outcomePanel: element<HTMLElement>("#outcome-panel"),
    startRunButton: element<HTMLButtonElement>("#start-run"),
    extractRunButton: element<HTMLButtonElement>("#extract-run"),
    expeditionSignal: element<HTMLParagraphElement>("#expedition-signal"),
    heroSummary: element<HTMLDivElement>("#hero-summary"),
    viewport: element<HTMLPreElement>("#viewport"),
    minimap: element<HTMLPreElement>("#minimap"),
    dialogueLog: element<HTMLPreElement>("#dialogue-log"),
    logTitle: element<HTMLHeadingElement>("#log-title"),
    logHelp: element<HTMLParagraphElement>("#log-help"),
    locationName: element<HTMLHeadingElement>("#location-name"),
    locationMeta: element<HTMLParagraphElement>("#location-meta"),
    locationDescription: element<HTMLParagraphElement>("#location-description"),
    messageStrip: element<HTMLDivElement>("#message-strip"),
    messageLabel: element<HTMLSpanElement>("#message-label"),
    messageLog: element<HTMLParagraphElement>("#message-log"),
    npcList: element<HTMLDivElement>("#npc-list"),
    inventoryList: element<HTMLDivElement>("#inventory-list"),
    sendMessageButton: element<HTMLButtonElement>("#send-message"),
    playerMessage: element<HTMLTextAreaElement>("#player-message"),
    combatActions: element<HTMLDivElement>("#combat-actions"),
    dispatchKicker: element<HTMLParagraphElement>("#dispatch-kicker"),
    dispatchTitle: element<HTMLHeadingElement>("#dispatch-title"),
    dispatchNote: element<HTMLParagraphElement>("#dispatch-note"),
    outcomeTitle: element<HTMLHeadingElement>("#outcome-title"),
    outcomeNote: element<HTMLParagraphElement>("#outcome-note"),
    outcomeLog: element<HTMLPreElement>("#outcome-log"),
  };
}

export function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false;
  }

  return target instanceof HTMLInputElement
    || target instanceof HTMLTextAreaElement
    || target instanceof HTMLSelectElement
    || target.isContentEditable;
}