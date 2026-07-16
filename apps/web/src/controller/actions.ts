import { api } from "../api";
import type { Snapshot } from "../types";
import type { AppState } from "../types";
import type { UiElements } from "../ui";
import type { ControllerOptions } from "./options";
import { syncBusyState, syncExplorationOverlays, setViewportTransitionState, applyCombatSnapshotUpdate } from "./state";
import { appendThreadMessage } from "./dialogue";

async function withBusy<T>(state: AppState, ui: UiElements, fn: () => Promise<T>): Promise<T> {
  state.busy = true;
  syncBusyState(ui, state);
  try { return await fn(); } finally { state.busy = false; syncBusyState(ui, state); }
}

export async function runCombatActionRequest(options: ControllerOptions, action: string, message?: string): Promise<void> {
  const { state, ui, apiBase, render, renderError } = options;
  if (!action || !state.runId || state.busy) return;
  try {
    const snapshot = await withBusy(state, ui, () => api<Snapshot>(apiBase, `/api/runs/${state.runId}/combat`, {
      method: "POST", body: JSON.stringify({ action, ...(message ? { message } : {}) }),
    }));
    if (!snapshot) return;
    applyCombatSnapshotUpdate(state, snapshot, true);
    render();
    if (action === "parley_open" && snapshot.combat_state?.negotiation?.active) ui.playerMessage.focus();
  } catch (error) { renderError(error); }
}

export async function runAction(options: ControllerOptions, action: string): Promise<void> {
  const { state, ui, apiBase, render, renderError } = options;
  if (!state.runId || state.busy) return;
  try {
    const previousSnapshot = state.snapshot;
    const snapshot = await withBusy(state, ui, () => api<Snapshot>(apiBase, `/api/runs/${state.runId}/actions`, {
      method: "POST", body: JSON.stringify({ action }),
    }));
    if (!snapshot) return;
    syncExplorationOverlays(state, snapshot);
    setViewportTransitionState(state, previousSnapshot, snapshot, false);
    state.snapshot = snapshot;
    if (state.selectedNpcId && !snapshot.nearby_npcs.some((npc) => npc.id === state.selectedNpcId)) {
      state.selectedNpcId = ""; state.dialogueOpen = false;
    }
    render();
  } catch (error) { renderError(error); }
}

export async function runQuestDecision(options: ControllerOptions, questId: string, action: string): Promise<void> {
  const { state, ui, apiBase, render, renderError } = options;
  if (!state.runId || state.busy) return;
  try {
    const snapshot = await withBusy(state, ui, () => api<Snapshot>(apiBase, `/api/quests/${questId}/${action}`, {
      method: "POST", body: JSON.stringify({ run_id: state.runId }),
    }));
    if (!snapshot) return;
    syncExplorationOverlays(state, snapshot);
    state.snapshot = snapshot;
    if (snapshot.dialogue) appendThreadMessage(state, snapshot.dialogue.npc_id, {
      speaker: "npc", npcId: snapshot.dialogue.npc_id, npcName: snapshot.dialogue.npc_name, source: snapshot.dialogue.source, text: snapshot.dialogue.text,
    });
    render();
  } catch (error) { renderError(error); }
}
