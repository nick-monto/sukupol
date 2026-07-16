import type { AppState, Snapshot, ViewportTransition } from "../types";
import type { UiElements } from "../ui";
import { COMBAT_EXIT_LOCK_MS } from "./options";

export function syncExplorationOverlays(state: AppState, snapshot: Snapshot): void {
  if (snapshot.in_combat || snapshot.run_result) closeExplorationOverlays(state);
}

export function closeExplorationOverlays(state: AppState): void {
  state.journalOpen = false; state.mapOpen = false; state.inventoryOpen = false; state.dialogueOpen = false;
}

export function toggleExplorationOverlay(state: AppState, overlay: "journal" | "map" | "inventory"): void {
  if (state.snapshot?.in_combat) return;
  const nextOpen = overlay === "journal" ? !state.journalOpen : overlay === "map" ? !state.mapOpen : !state.inventoryOpen;
  closeExplorationOverlays(state);
  if (!nextOpen) return;
  if (overlay === "journal") state.journalOpen = true;
  else if (overlay === "map") state.mapOpen = true;
  else state.inventoryOpen = true;
}

export function toggleDialogueDrawer(state: AppState): void {
  if (!state.runId || state.snapshot?.in_combat || state.snapshot?.run_result) return;
  state.dialogueOpen = !state.dialogueOpen;
  if (!state.dialogueOpen && state.selectedNpcId) state.selectedNpcId = "";
}

function deriveViewportTransition(previousSnapshot: Snapshot | null, nextSnapshot: Snapshot, isCombatAction: boolean): ViewportTransition {
  if (nextSnapshot.in_combat && !previousSnapshot?.in_combat) return "combat-enter";
  if (previousSnapshot?.in_combat && !nextSnapshot.in_combat) return "combat-exit";
  if (nextSnapshot.in_combat && isCombatAction) return "combat-impact";
  return "none";
}

export function setViewportTransitionState(state: AppState, previousSnapshot: Snapshot | null, nextSnapshot: Snapshot, isCombatAction: boolean): void {
  const transition = deriveViewportTransition(previousSnapshot, nextSnapshot, isCombatAction);
  state.viewportTransition = transition;
  if (transition === "combat-exit" && previousSnapshot?.combat_state) {
    state.presentationToken += 1;
    state.presentationLock = { transition, combatState: previousSnapshot.combat_state, token: state.presentationToken, startedAt: performance.now() };
    return;
  }
  state.presentationLock = null;
}

export function applyCombatSnapshotUpdate(state: AppState, snapshot: Snapshot, isCombatAction: boolean): void {
  const previousSnapshot = state.snapshot;
  syncExplorationOverlays(state, snapshot);
  setViewportTransitionState(state, previousSnapshot, snapshot, isCombatAction);
  state.snapshot = snapshot;
}

export function isCombatPresentationActive(state: AppState): boolean {
  if (state.snapshot?.in_combat === true) return true;
  if (!state.presentationLock || state.presentationLock.transition !== "combat-exit") return false;
  if ((performance.now() - state.presentationLock.startedAt) > COMBAT_EXIT_LOCK_MS) {
    state.presentationLock = null;
    if (state.viewportTransition === "combat-exit") state.viewportTransition = "none";
    return false;
  }
  return true;
}

function syncRunButtons(ui: UiElements, state: AppState, combatActive: boolean): void {
  ui.startRunButton.disabled = false;
  ui.launchRunButton.disabled = state.busy;
  ui.extractRunButton.disabled = !state.runId || combatActive
    || state.snapshot?.location.id !== "town_square" || !!state.snapshot?.run_result;
}

function syncMessageButtons(ui: UiElements, state: AppState, combatActive: boolean, parleyActive: boolean): void {
  ui.sendMessageButton.disabled = state.busy || !state.runId || combatActive
    || (!parleyActive && !state.selectedNpcId) || !!state.snapshot?.run_result;
  ui.leaveConversationButton.disabled = state.busy || !state.selectedNpcId || !state.runId
    || state.snapshot?.in_combat === true || combatActive || !!state.snapshot?.run_result;
  ui.playerMessage.disabled = state.busy || !state.runId
    || (state.snapshot?.in_combat === true && !parleyActive) || combatActive || !!state.snapshot?.run_result;
  ui.playerNameInput.disabled = state.busy;
}

function syncToggleButtons(ui: UiElements, state: AppState, combatActive: boolean): void {
  ui.journalToggleButton.disabled = combatActive;
  ui.mapToggleButton.disabled = combatActive || !state.snapshot || !!state.snapshot.run_result;
  ui.inventoryToggleButton.disabled = combatActive || !state.snapshot || !!state.snapshot.run_result;
  ui.dialogueToggleButton.disabled = combatActive || !state.runId || !!state.snapshot?.run_result;
}

function syncActionButtons(ui: UiElements, state: AppState, combatActive: boolean): void {
  document.querySelectorAll<HTMLButtonElement>("[data-action]").forEach((button) => {
    button.disabled = !state.runId || combatActive || !!state.snapshot?.run_result;
  });
  ui.combatActions.querySelectorAll<HTMLButtonElement>("button[data-combat-action]").forEach((button) => {
    const actionId = button.dataset.combatAction;
    const actionEnabled = actionId
      ? state.snapshot?.combat_state?.available_actions.find((a) => a.id === actionId)?.enabled ?? true : true;
    button.disabled = state.busy || !state.runId || state.snapshot?.in_combat !== true || !!state.snapshot?.run_result || !actionEnabled;
  });
  ui.questChoicePanel.querySelectorAll<HTMLButtonElement>("button[data-quest-action]").forEach((button) => {
    button.disabled = !state.runId || state.busy || combatActive || !!state.snapshot?.run_result;
  });
}

export function syncBusyState(ui: UiElements, state: AppState): void {
  const combatActive = isCombatPresentationActive(state);
  const parleyActive = state.snapshot?.in_combat === true && state.snapshot.combat_state?.negotiation?.active === true;
  syncRunButtons(ui, state, combatActive);
  syncMessageButtons(ui, state, combatActive, parleyActive);
  syncToggleButtons(ui, state, combatActive);
  syncActionButtons(ui, state, combatActive);
}
