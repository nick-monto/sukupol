export function createAppMarkup(title: string): string {
  return `
    <div class="shell" id="shell" data-mode="idle">
      <section class="hero" id="hero-panel">
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

      <section class="stage-shell">
        <div class="panel viewport" id="viewport-panel">
          <div class="panel-header panel-header-inline">
            <div>
              <p class="eyebrow">Traversal Map</p>
              <h2 id="location-name">No run started</h2>
            </div>
            <p class="location-meta" id="location-meta">Awaiting expedition telemetry.</p>
          </div>
          <p id="location-description">Begin a run to render the live route, nearby contacts, and encounter ground.</p>
          <div class="display-frame viewport-frame">
            <div class="viewport-stage">
              <div id="viewport-pixi-stage" class="viewport-pixi-stage" hidden aria-label="Traversal map"></div>
              <pre id="viewport" class="viewport-fallback">Stand up the backend and begin a run.</pre>
            </div>
          </div>
          <section class="viewport-chat context-drawer" id="context-drawer" data-mode="idle">
            <button
              class="viewport-chat-resize-handle"
              id="viewport-chat-resize-handle"
              type="button"
              aria-label="Resize dialogue panel"
              title="Drag to resize dialogue panel"
            >
              <span class="viewport-chat-resize-grip" aria-hidden="true"></span>
            </button>
            <div class="viewport-chat-head">
              <div class="viewport-chat-intro">
                <div>
                  <p class="eyebrow" id="dispatch-kicker">Dispatch</p>
                  <h3 id="dispatch-title">Field Orders</h3>
                </div>
                <p class="small panel-note" id="dispatch-note">Movement, contact, and combat orders converge here.</p>
              </div>
              <div class="viewport-chat-status log" id="log-panel" data-mode="idle">
                <span class="chat-channel-pill" id="log-title">Dialogue</span>
                <p class="small panel-note" id="log-help">Choose a nearby contact to open the channel.</p>
              </div>
            </div>
            <div class="chat-transcript" id="dialogue-log" role="log" aria-live="polite"></div>
            <div class="action-panel viewport-chat-compose" id="action-panel" data-mode="idle">
              <div class="dialogue-form" id="interaction-panel">
                <label for="player-message">Message</label>
                <div class="chat-composer-row">
                  <textarea id="player-message" rows="3" placeholder="Ask for rumors, routes, supplies, or warnings."></textarea>
                  <div class="chat-composer-actions">
                    <button id="send-message">Send</button>
                    <button id="leave-conversation" type="button">Leave</button>
                  </div>
                </div>
                <div class="combat-actions" id="combat-actions">
                  <button data-combat-action="attack">Attack</button>
                  <button data-combat-action="defend">Defend</button>
                  <button data-combat-action="use_item:health_potion">Use potion</button>
                  <button data-combat-action="flee">Flee</button>
                </div>
              </div>
            </div>
          </section>
          <div class="viewport-support">
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
          <div class="hud">
            <div class="message-strip" id="message-strip">
              <span class="message-label" id="message-label">Field report</span>
              <p class="message" id="message-log">Awaiting input.</p>
            </div>
            <div class="controls">
              <button data-action="move_north"><span class="hotkey">W</span> Move north</button>
              <button data-action="move_west"><span class="hotkey">A</span> Move west</button>
              <button data-action="move_south"><span class="hotkey">S</span> Move south</button>
              <button data-action="move_east"><span class="hotkey">D</span> Move east</button>
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
          <p class="small panel-note" id="outcome-note">Resolved runs and long-view progression.</p>
        </div>
        <div class="display-frame compact-frame">
          <pre id="outcome-log">No completed run yet.</pre>
        </div>
        <div class="panel-subsection">
          <div class="panel-header panel-header-compact">
            <div>
              <p class="eyebrow">Journal</p>
              <h3>NPC visits</h3>
            </div>
          </div>
          <div class="journal-list" id="journal-list"></div>
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
  contextDrawer: HTMLElement;
  chatResizeHandle: HTMLButtonElement;
  logPanel: HTMLElement;
  actionPanel: HTMLElement;
  outcomePanel: HTMLElement;
  startRunButton: HTMLButtonElement;
  extractRunButton: HTMLButtonElement;
  expeditionSignal: HTMLParagraphElement;
  heroSummary: HTMLDivElement;
  viewport: HTMLPreElement;
  viewportPixiStage: HTMLDivElement;
  dialogueLog: HTMLDivElement;
  logTitle: HTMLElement;
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
  leaveConversationButton: HTMLButtonElement;
  playerMessage: HTMLTextAreaElement;
  combatActions: HTMLDivElement;
  dispatchKicker: HTMLParagraphElement;
  dispatchTitle: HTMLHeadingElement;
  dispatchNote: HTMLParagraphElement;
  outcomeTitle: HTMLHeadingElement;
  outcomeNote: HTMLParagraphElement;
  outcomeLog: HTMLPreElement;
  journalList: HTMLDivElement;
};

export function getUiElements(): UiElements {
  return {
    shell: element<HTMLDivElement>("#shell"),
    heroPanel: element<HTMLElement>("#hero-panel"),
    viewportPanel: element<HTMLElement>("#viewport-panel"),
    contextDrawer: element<HTMLElement>("#context-drawer"),
    chatResizeHandle: element<HTMLButtonElement>("#viewport-chat-resize-handle"),
    logPanel: element<HTMLElement>("#log-panel"),
    actionPanel: element<HTMLElement>("#action-panel"),
    outcomePanel: element<HTMLElement>("#outcome-panel"),
    startRunButton: element<HTMLButtonElement>("#start-run"),
    extractRunButton: element<HTMLButtonElement>("#extract-run"),
    expeditionSignal: element<HTMLParagraphElement>("#expedition-signal"),
    heroSummary: element<HTMLDivElement>("#hero-summary"),
    viewport: element<HTMLPreElement>("#viewport"),
    viewportPixiStage: element<HTMLDivElement>("#viewport-pixi-stage"),
    dialogueLog: element<HTMLDivElement>("#dialogue-log"),
    logTitle: element<HTMLElement>("#log-title"),
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
    leaveConversationButton: element<HTMLButtonElement>("#leave-conversation"),
    playerMessage: element<HTMLTextAreaElement>("#player-message"),
    combatActions: element<HTMLDivElement>("#combat-actions"),
    dispatchKicker: element<HTMLParagraphElement>("#dispatch-kicker"),
    dispatchTitle: element<HTMLHeadingElement>("#dispatch-title"),
    dispatchNote: element<HTMLParagraphElement>("#dispatch-note"),
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