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
          <div class="stage-layout">
            <div class="stage-main">
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
                  <div id="combat-overlay" class="combat-overlay" hidden aria-live="polite"></div>
                  <pre id="viewport" class="viewport-fallback">Stand up the backend and begin a run.</pre>
                </div>
              </div>
              <div class="controls viewport-controls">
                <button data-action="move_north"><span class="hotkey">W</span> Move north</button>
                <button data-action="move_west"><span class="hotkey">A</span> Move west</button>
                <button data-action="move_south"><span class="hotkey">S</span> Move south</button>
                <button data-action="move_east"><span class="hotkey">D</span> Move east</button>
              </div>
              <div class="support-stack">
                <div class="panel-subsection">
                  <div class="panel-header panel-header-compact">
                    <div>
                      <p class="eyebrow">Survey</p>
                      <h3>Overworld map</h3>
                    </div>
                  </div>
                  <div class="overworld-map" id="overworld-map"></div>
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
                <div class="panel-subsection">
                  <div class="panel-header panel-header-compact">
                    <div>
                      <p class="eyebrow">Contracts</p>
                      <h3>Active quests</h3>
                    </div>
                  </div>
                  <div class="quest-list" id="quest-list"></div>
                </div>
              </div>
            </div>
            <aside class="stage-comms">
              <div class="panel-subsection stage-contacts-panel">
                <div>
                  <p class="eyebrow">Contacts</p>
                  <h3>Nearby voices</h3>
                </div>
                <div class="npc-list" id="npc-list"></div>
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
                    <p class="small panel-note" id="log-help">Status reports and conversations flow through the same channel.</p>
                  </div>
                </div>
                <div class="chat-transcript" id="dialogue-log" role="log" aria-live="polite"></div>
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
            </aside>
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
  combatOverlay: HTMLDivElement;
  dialogueLog: HTMLDivElement;
  logTitle: HTMLElement;
  logHelp: HTMLParagraphElement;
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
    combatOverlay: element<HTMLDivElement>("#combat-overlay"),
    dialogueLog: element<HTMLDivElement>("#dialogue-log"),
    logTitle: element<HTMLElement>("#log-title"),
    logHelp: element<HTMLParagraphElement>("#log-help"),
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