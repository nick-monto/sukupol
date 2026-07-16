import type { AppState, Snapshot } from "../types";
import type { UiElements } from "../ui";

const transitionTimers = new WeakMap<HTMLElement, number>();

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

function setMode(element: HTMLElement, nextMode: string): void {
  const previousMode = element.dataset.mode;
  element.dataset.mode = nextMode;

  if (previousMode && previousMode !== nextMode && !shouldSuppressModeTransition(previousMode, nextMode)) {
    triggerModeTransition(element);
  }
}

export function getPresentedSnapshot(state: AppState): Snapshot | null {
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

export function applyPresentationState(ui: UiElements, state: AppState, snapshot: Snapshot | null): void {
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
