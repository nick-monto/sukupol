export function createAppMarkup(title: string): string {
  return `
    <div class="shell" id="shell" data-mode="idle">
      <section class="panel viewport viewport-root" id="viewport-panel">
        <div class="display-frame viewport-frame">
          <div class="viewport-stage">
            <div id="viewport-pixi-stage" class="viewport-pixi-stage" hidden aria-label="Traversal map"></div>
            <div id="combat-overlay" class="combat-overlay" hidden aria-live="polite"></div>
            <pre id="viewport" class="viewport-fallback">Stand up the backend and begin a run.</pre>
          </div>
        </div>

        <section class="viewport-overlay launch-panel-shell" id="launch-panel">
          <div class="panel launch-panel-card">
            <div class="launch-panel-copy">
              <p class="eyebrow">Expedition launch</p>
              <h1>${title}</h1>
              <p class="hero-lede" id="launch-message">Enter your name and begin a run from the center portal.</p>
            </div>
            <label class="launch-field" for="player-name-input">
              <span class="small">Wayfarer name</span>
              <input id="player-name-input" type="text" maxlength="32" value="Wayfarer" autocomplete="nickname" placeholder="Wayfarer" />
            </label>
            <div class="launch-actions">
              <button id="launch-run" type="button">Begin expedition</button>
            </div>
          </div>
        </section>

        <div class="viewport-overlay viewport-top-hud" id="top-hud">
          <button class="hud-toggle hud-toggle-corner" id="journal-toggle" type="button">Journal</button>
          <div class="area-banner" id="area-banner">
            <p class="eyebrow">Current area</p>
            <h2 id="location-name">No run started</h2>
          </div>
          <button class="hud-toggle hud-toggle-corner" id="map-toggle" type="button">Map</button>
        </div>

        <section class="panel viewport-overlay journal-overlay-card" id="journal-panel" hidden>
          <section class="hero hero-overlay" id="hero-panel">
            <div class="hero-top">
              <div class="hero-copy">
                <p class="eyebrow">Sukupol / expedition console</p>
                <h1>${title}</h1>
                <p class="hero-lede">Map-led traversal for movement, creature pressure, contact, and extraction.</p>
              </div>
              <div class="hero-actions">
                <button id="start-run">Begin expedition</button>
                <button id="extract-run">Return to town</button>
              </div>
            </div>

            <div class="hero-band">
              <p class="signal" id="expedition-signal">No active expedition. Establish a run to receive telemetry.</p>
              <div class="hero-summary" id="hero-summary"></div>
            </div>
          </section>

          <div class="journal-overlay-scroll">
            <section class="panel-subsection viewport-dock-card journal-visits-card">
              <div class="panel-header panel-header-compact">
                <div>
                  <p class="eyebrow">Journal</p>
                  <h3>NPC visits</h3>
                </div>
              </div>
              <div class="journal-list" id="journal-list"></div>
            </section>

            <section class="panel-subsection viewport-dock-card journal-quest-card">
              <div class="panel-header panel-header-compact">
                <div>
                  <p class="eyebrow">Contracts</p>
                  <h3>Active quests</h3>
                </div>
              </div>
              <div class="quest-list" id="quest-list"></div>
            </section>

            <section class="panel outcome-panel outcome-overlay journal-outcome-card" id="outcome-panel" data-mode="idle">
              <div class="panel-header">
                <div>
                  <p class="eyebrow">Archive</p>
                  <h2 id="outcome-title">Run Chronicle</h2>
                </div>
                <p class="small panel-note" id="outcome-note">Resolved runs and long-view progression.</p>
              </div>
              <div class="display-frame compact-frame">
                <pre id="outcome-log">No completed run yet.</pre>
              </div>
            </section>
          </div>
        </section>

        <section class="panel viewport-overlay map-overlay-card" id="map-panel" hidden>
          <div class="panel-header panel-header-inline">
            <div>
              <p class="eyebrow">Survey</p>
              <h3>Overworld map</h3>
            </div>
            <p class="location-meta" id="location-meta">Awaiting expedition telemetry.</p>
          </div>
          <p id="location-description">Begin a run to render the live route, nearby contacts, and encounter ground.</p>
          <div class="overworld-map" id="overworld-map"></div>
        </section>

        <section class="panel viewport-overlay inventory-overlay-card" id="inventory-panel" hidden>
          <div class="panel-header panel-header-inline">
            <div>
              <p class="eyebrow">Stores</p>
              <h3>Loadout</h3>
            </div>
          </div>
          <div class="inventory-list" id="inventory-list"></div>
        </section>

        <section class="viewport-chat context-drawer viewport-overlay viewport-chat-overlay" id="context-drawer" data-mode="idle">
          <button
            class="viewport-chat-resize-handle"
            id="viewport-chat-resize-handle"
            type="button"
            aria-label="Resize dialogue panel"
            title="Drag to resize dialogue panel"
          >
            <span class="viewport-chat-resize-grip" aria-hidden="true"></span>
          </button>
          <div class="viewport-chat-roster">
            <div class="npc-list" id="npc-list"></div>
          </div>
          <div class="viewport-chat-stage">
            <div class="chat-transcript" id="dialogue-log" role="log" aria-live="polite"></div>
          </div>
          <div class="action-panel viewport-chat-compose" id="action-panel" data-mode="idle">
            <div class="dialogue-form" id="interaction-panel">
              <div class="chat-composer-row">
                <textarea id="player-message" rows="3" placeholder="Ask for rumors, routes, supplies, or warnings."></textarea>
                <div class="chat-composer-actions">
                  <button id="send-message">Send</button>
                  <button id="leave-conversation" type="button">Leave</button>
                </div>
              </div>
              <div class="quest-choice-panel" id="quest-choice-panel"></div>
              <div class="combat-actions" id="combat-actions"></div>
            </div>
          </div>
        </section>

        <div class="viewport-overlay viewport-bottom-bar">
          <button class="hud-toggle hud-toggle-corner inventory-toggle" id="inventory-toggle" type="button">Inventory</button>
          <button class="hud-toggle hud-toggle-corner dialogue-toggle" id="dialogue-toggle" type="button">Converse</button>
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
  topHud: HTMLElement;
  areaBanner: HTMLElement;
  bottomHud: HTMLElement;
  launchPanel: HTMLElement;
  launchMessage: HTMLParagraphElement;
  playerNameInput: HTMLInputElement;
  launchRunButton: HTMLButtonElement;
  heroPanel: HTMLElement;
  viewportPanel: HTMLElement;
  journalPanel: HTMLElement;
  mapPanel: HTMLElement;
  inventoryPanel: HTMLElement;
  journalToggleButton: HTMLButtonElement;
  mapToggleButton: HTMLButtonElement;
  inventoryToggleButton: HTMLButtonElement;
  dialogueToggleButton: HTMLButtonElement;
  contextDrawer: HTMLElement;
  chatResizeHandle: HTMLButtonElement;
  actionPanel: HTMLElement;
  outcomePanel: HTMLElement;
  startRunButton: HTMLButtonElement;
  extractRunButton: HTMLButtonElement;
  expeditionSignal: HTMLParagraphElement;
  heroSummary: HTMLDivElement;
  viewport: HTMLPreElement;
  viewportPixiStage: HTMLDivElement;
  combatOverlay: HTMLDivElement;
  dialogueLog: HTMLDivElement;
  locationName: HTMLHeadingElement;
  locationMeta: HTMLParagraphElement;
  locationDescription: HTMLParagraphElement;
  npcList: HTMLDivElement;
  inventoryList: HTMLDivElement;
  overworldMap: HTMLDivElement;
  questList: HTMLDivElement;
  sendMessageButton: HTMLButtonElement;
  leaveConversationButton: HTMLButtonElement;
  playerMessage: HTMLTextAreaElement;
  questChoicePanel: HTMLDivElement;
  combatActions: HTMLDivElement;
  outcomeTitle: HTMLHeadingElement;
  outcomeNote: HTMLParagraphElement;
  outcomeLog: HTMLPreElement;
  journalList: HTMLDivElement;
};

export function getUiElements(): UiElements {
  return {
    shell: element<HTMLDivElement>("#shell"),
    topHud: element<HTMLElement>("#top-hud"),
    areaBanner: element<HTMLElement>("#area-banner"),
    bottomHud: element<HTMLElement>(".viewport-bottom-bar"),
    launchPanel: element<HTMLElement>("#launch-panel"),
    launchMessage: element<HTMLParagraphElement>("#launch-message"),
    playerNameInput: element<HTMLInputElement>("#player-name-input"),
    launchRunButton: element<HTMLButtonElement>("#launch-run"),
    heroPanel: element<HTMLElement>("#hero-panel"),
    viewportPanel: element<HTMLElement>("#viewport-panel"),
    journalPanel: element<HTMLElement>("#journal-panel"),
    mapPanel: element<HTMLElement>("#map-panel"),
    inventoryPanel: element<HTMLElement>("#inventory-panel"),
    journalToggleButton: element<HTMLButtonElement>("#journal-toggle"),
    mapToggleButton: element<HTMLButtonElement>("#map-toggle"),
    inventoryToggleButton: element<HTMLButtonElement>("#inventory-toggle"),
    dialogueToggleButton: element<HTMLButtonElement>("#dialogue-toggle"),
    contextDrawer: element<HTMLElement>("#context-drawer"),
    chatResizeHandle: element<HTMLButtonElement>("#viewport-chat-resize-handle"),
    actionPanel: element<HTMLElement>("#action-panel"),
    outcomePanel: element<HTMLElement>("#outcome-panel"),
    startRunButton: element<HTMLButtonElement>("#start-run"),
    extractRunButton: element<HTMLButtonElement>("#extract-run"),
    expeditionSignal: element<HTMLParagraphElement>("#expedition-signal"),
    heroSummary: element<HTMLDivElement>("#hero-summary"),
    viewport: element<HTMLPreElement>("#viewport"),
    viewportPixiStage: element<HTMLDivElement>("#viewport-pixi-stage"),
    combatOverlay: element<HTMLDivElement>("#combat-overlay"),
    dialogueLog: element<HTMLDivElement>("#dialogue-log"),
    locationName: element<HTMLHeadingElement>("#location-name"),
    locationMeta: element<HTMLParagraphElement>("#location-meta"),
    locationDescription: element<HTMLParagraphElement>("#location-description"),
    npcList: element<HTMLDivElement>("#npc-list"),
    inventoryList: element<HTMLDivElement>("#inventory-list"),
    overworldMap: element<HTMLDivElement>("#overworld-map"),
    questList: element<HTMLDivElement>("#quest-list"),
    sendMessageButton: element<HTMLButtonElement>("#send-message"),
    leaveConversationButton: element<HTMLButtonElement>("#leave-conversation"),
    playerMessage: element<HTMLTextAreaElement>("#player-message"),
    questChoicePanel: element<HTMLDivElement>("#quest-choice-panel"),
    combatActions: element<HTMLDivElement>("#combat-actions"),
    outcomeTitle: element<HTMLHeadingElement>("#outcome-title"),
    outcomeNote: element<HTMLParagraphElement>("#outcome-note"),
    outcomeLog: element<HTMLPreElement>("#outcome-log"),
    journalList: element<HTMLDivElement>("#journal-list"),
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