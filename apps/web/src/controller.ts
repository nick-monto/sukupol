import { api } from "./api";
import type { AppState, DialogueMessage, Snapshot, ViewportTransition } from "./types";
import type { UiElements } from "./ui";
import { isEditableTarget } from "./ui";
import { setupPinball } from "./pinballCombat";
import type { PinballTable } from "./pinballCombat";
import { generatePinballTable } from "./pinballTable";

type ControllerOptions = {
  apiBase: string;
  state: AppState;
  ui: UiElements;
  render: () => void;
  renderError: (error: unknown) => void;
};

const CHAT_DOCK_HEIGHT_KEY = "sukupol.chatDockHeight";
const CHAT_DOCK_DEFAULT_HEIGHT = 300;
const CHAT_DOCK_MIN_HEIGHT = 256;
const CHAT_DOCK_MAX_HEIGHT_RATIO = 0.75;
const COMBAT_EXIT_LOCK_MS = 320;

let activePinball: PinballTable | null = null;

function getEquippedWeaponType(snapshot: Snapshot | null): string | null {
  if (!snapshot?.equipped_weapon) return null;
  const item = snapshot.inventory.find((i) => i.item_id === snapshot.equipped_weapon);
  return item?.item_type ?? null;
}

function managePinballFn(options: ControllerOptions): void {
  const { state } = options;
  const inCombat = !!(state.snapshot?.in_combat && state.snapshot.combat_state && !state.presentationLock);

  if (inCombat && !activePinball) {
    const canvas = document.querySelector<HTMLCanvasElement>("#pinball-cabinet-canvas");
    if (!canvas) return;
    const descriptor = state.snapshot?.combat_state?.pinball_descriptor ?? null;
    const layout = generatePinballTable(descriptor ?? {
      biome_id: "ashen_fields",
      floor_seed: 0,
      enemy_id: "unknown",
      enemy_pinball: {},
    });
    activePinball = setupPinball(canvas, {
      layout,
      equippedWeaponType: getEquippedWeaponType(state.snapshot ?? null),
      onPinballStrike: (score: number) => {
        if (score > 0) void runCombatActionRequest(options, `pinball_strike:${score}`);
      },
      onBallDrain: () => { /* score already handled via onPinballStrike at drain */ },
    });
    return;
  }

  if (!inCombat && activePinball) {
    activePinball.teardown();
    activePinball = null;
    return;
  }

  if (inCombat && activePinball) {
    activePinball.setEquippedWeapon(getEquippedWeaponType(state.snapshot ?? null));
  }
}

export function bindInteractionHandlers(options: ControllerOptions): { managePinball: () => void } {
  const { ui } = options;

  bindChatResize(ui);
  bindHudToggles(options);

  document.addEventListener("keydown", async (event) => {
    const { state } = options;
    if (isEditableTarget(event.target)) {
      return;
    }

    if (!state.runId || state.busy || isCombatPresentationActive(state)) {
      return;
    }

    const keymap: Record<string, string> = {
      w: "move_north",
      s: "move_south",
      a: "move_west",
      d: "move_east",
    };

    const action = keymap[event.key.toLowerCase()];
    if (!action) {
      return;
    }

    event.preventDefault();
    await runAction(options, action);
  });

  ui.playerMessage.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || event.shiftKey) {
      return;
    }

    event.preventDefault();
    ui.sendMessageButton.click();
  });

  ui.playerNameInput.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") {
      return;
    }

    event.preventDefault();
    ui.launchRunButton.click();
  });

  const startRun = async () => {
    const { state, apiBase, render, renderError } = options;
    if (state.busy) {
      return;
    }

    const playerName = ui.playerNameInput.value.trim() || "Wayfarer";
    ui.playerNameInput.value = playerName;

    state.busy = true;
    syncBusyState(ui, state);
    try {
      const snapshot = await api<Snapshot>(apiBase, "/api/runs", {
        method: "POST",
        body: JSON.stringify({ player_name: playerName }),
      });
      closeExplorationOverlays(state);
      state.runId = snapshot.run_id;
      state.snapshot = snapshot;
      state.selectedNpcId = "";
      state.dialogueThreads = {};
      state.viewportTransition = "none";
      state.presentationLock = null;
      render();
    } catch (error) {
      renderError(error);
    } finally {
      state.busy = false;
      syncBusyState(ui, state);
    }
  };

  ui.startRunButton.addEventListener("click", startRun);
  ui.launchRunButton.addEventListener("click", startRun);

  ui.extractRunButton.addEventListener("click", async () => {
    const { state, apiBase, render, renderError } = options;
    if (!state.runId || state.busy) {
      return;
    }

    state.busy = true;
    syncBusyState(ui, state);
    try {
      const snapshot = await api<Snapshot>(apiBase, `/api/runs/${state.runId}/extract`, {
        method: "POST",
      });
      syncExplorationOverlays(state, snapshot);
      setViewportTransitionState(state, state.snapshot, snapshot, false);
      state.snapshot = snapshot;
      render();
    } catch (error) {
      renderError(error);
    } finally {
      state.busy = false;
      syncBusyState(ui, state);
    }
  });

  ui.leaveConversationButton.addEventListener("click", async () => {
    await leaveNpcConversation(options);
  });

  ui.questChoicePanel.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }

    const button = target.closest<HTMLButtonElement>("button[data-quest-action][data-quest-id]");
    if (!button) {
      return;
    }

    const action = button.dataset.questAction;
    const questId = button.dataset.questId;
    if (!action || !questId) {
      return;
    }

    await runQuestDecision(options, questId, action);
  });

  document.querySelectorAll<HTMLButtonElement>("[data-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      const action = button.dataset.action;
      if (!action) {
        return;
      }
      await runAction(options, action);
    });
  });

  ui.sendMessageButton.addEventListener("click", async () => {
    const { state, render, renderError, apiBase } = options;
    if (!state.runId || state.busy || isCombatPresentationActive(state)) {
      return;
    }

    const message = ui.playerMessage.value.trim();
    if (!message) {
      ui.playerMessage.focus();
      return;
    }

    if (canSendCombatParleyMessage(state)) {
      try {
        ui.playerMessage.value = "";
        await runCombatActionRequest(options, "parley_message", message);
      } catch (error) {
        renderError(error);
      }
      return;
    }

    if (!state.selectedNpcId) {
      return;
    }

    state.busy = true;
    appendThreadMessage(state, state.selectedNpcId, {
      speaker: "player",
      text: message,
    });
    ui.playerMessage.value = "";
    syncBusyState(ui, state);
    render();
    try {
      await streamNpcDialogue(options, state.selectedNpcId, message);
      state.viewportTransition = "none";
      state.presentationLock = null;
      render();
    } catch (error) {
      state.streamingDialogue = null;
      renderError(error);
    } finally {
      state.busy = false;
      syncBusyState(ui, state);
    }
  });

  ui.combatActions.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }

    const button = target.closest<HTMLButtonElement>("button[data-combat-action]");
    if (!button) {
      return;
    }

    const action = button.dataset.combatAction;
    const { state } = options;
    if (!action || !state.runId || state.busy || button.disabled) {
      return;
    }
    await runCombatActionRequest(options, action);
  });

  return { managePinball: () => managePinballFn(options) };
}

function bindHudToggles(options: ControllerOptions): void {
  const { ui, state, render } = options;

  ui.journalToggleButton.addEventListener("click", () => {
    toggleExplorationOverlay(state, "journal");
    render();
  });

  ui.mapToggleButton.addEventListener("click", () => {
    toggleExplorationOverlay(state, "map");
    render();
  });

  ui.inventoryToggleButton.addEventListener("click", () => {
    toggleExplorationOverlay(state, "inventory");
    render();
  });

  ui.dialogueToggleButton.addEventListener("click", () => {
    toggleDialogueDrawer(state);
    render();
  });
}

function bindChatResize(ui: UiElements): void {
  const savedHeight = window.localStorage.getItem(CHAT_DOCK_HEIGHT_KEY);
  if (savedHeight) {
    const parsedHeight = Number.parseFloat(savedHeight);
    if (Number.isFinite(parsedHeight)) {
      applyChatDockHeight(ui.contextDrawer, parsedHeight);
    }
  } else {
    applyChatDockHeight(ui.contextDrawer, CHAT_DOCK_DEFAULT_HEIGHT);
  }

  ui.chatResizeHandle.addEventListener("dblclick", () => {
    window.localStorage.removeItem(CHAT_DOCK_HEIGHT_KEY);
    applyChatDockHeight(ui.contextDrawer, CHAT_DOCK_DEFAULT_HEIGHT);
  });

  ui.chatResizeHandle.addEventListener("pointerdown", (event) => {
    event.preventDefault();

    const viewportPanelRect = ui.viewportPanel.getBoundingClientRect();
    const dockRect = ui.contextDrawer.getBoundingClientRect();
    const pointerOffset = event.clientY - dockRect.top;

    ui.chatResizeHandle.setPointerCapture(event.pointerId);
    ui.contextDrawer.classList.add("is-resizing");
    document.body.classList.add("is-chat-resizing");

    const onPointerMove = (moveEvent: PointerEvent) => {
      const nextHeight = viewportPanelRect.bottom - (moveEvent.clientY - pointerOffset);
      const clampedHeight = clampChatDockHeight(nextHeight, viewportPanelRect.height);
      applyChatDockHeight(ui.contextDrawer, clampedHeight);
    };

    const stopResize = () => {
      ui.contextDrawer.classList.remove("is-resizing");
      document.body.classList.remove("is-chat-resizing");
      ui.chatResizeHandle.removeEventListener("pointermove", onPointerMove);
      ui.chatResizeHandle.removeEventListener("pointerup", stopResize);
      ui.chatResizeHandle.removeEventListener("pointercancel", stopResize);
      window.localStorage.setItem(CHAT_DOCK_HEIGHT_KEY, String(ui.contextDrawer.getBoundingClientRect().height));
    };

    ui.chatResizeHandle.addEventListener("pointermove", onPointerMove);
    ui.chatResizeHandle.addEventListener("pointerup", stopResize);
    ui.chatResizeHandle.addEventListener("pointercancel", stopResize);
  });
}

function clampChatDockHeight(height: number, viewportPanelHeight: number): number {
  const maxHeight = Math.max(CHAT_DOCK_MIN_HEIGHT, viewportPanelHeight * CHAT_DOCK_MAX_HEIGHT_RATIO);
  return Math.min(Math.max(height, CHAT_DOCK_MIN_HEIGHT), maxHeight);
}

function applyChatDockHeight(element: HTMLElement, height: number): void {
  element.style.height = `${height}px`;
}

async function streamNpcDialogue(options: ControllerOptions, npcId: string, message: string): Promise<void> {
  const { apiBase, state, render } = options;
  const response = await fetch(`${apiBase}/api/npcs/${npcId}/talk/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ run_id: state.runId, message }),
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed with ${response.status}`);
  }

  if (!response.body) {
    throw new Error("Dialogue stream did not return a readable body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalSnapshot: Snapshot | null = null;

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });

    let newlineIndex = buffer.indexOf("\n");
    while (newlineIndex >= 0) {
      const rawLine = buffer.slice(0, newlineIndex).trim();
      buffer = buffer.slice(newlineIndex + 1);
      if (rawLine) {
        const event = JSON.parse(rawLine) as
          | { type: "start"; npc_id: string; npc_name: string; source: string }
          | { type: "chunk"; text: string }
          | { type: "snapshot"; snapshot: Snapshot }
          | { type: "error"; detail: string };

        if (event.type === "start") {
          state.streamingDialogue = {
            npc_id: event.npc_id,
            npc_name: event.npc_name,
            source: event.source,
            text: "",
          };
          upsertStreamingNpcMessage(state, {
            npcId: event.npc_id,
            npcName: event.npc_name,
            source: event.source,
            text: "",
          });
          render();
        } else if (event.type === "chunk") {
          if (state.streamingDialogue) {
            const nextText = `${state.streamingDialogue.text}${event.text}`;
            state.streamingDialogue = {
              ...state.streamingDialogue,
              text: nextText,
            };
            upsertStreamingNpcMessage(state, {
              npcId: state.streamingDialogue.npc_id,
              npcName: state.streamingDialogue.npc_name,
              source: state.streamingDialogue.source,
              text: nextText,
            });
            render();
          }
        } else if (event.type === "snapshot") {
          finalSnapshot = event.snapshot;
        } else if (event.type === "error") {
          throw new Error(event.detail);
        }
      }
      newlineIndex = buffer.indexOf("\n");
    }

    if (done) {
      break;
    }
  }

  if (!finalSnapshot) {
    throw new Error("Dialogue stream ended without a final snapshot");
  }

  state.snapshot = finalSnapshot;
  syncExplorationOverlays(state, finalSnapshot);
  if (finalSnapshot.dialogue) {
    finalizeNpcMessage(
      state,
      finalSnapshot.dialogue.npc_id,
      finalSnapshot.dialogue.npc_name,
      finalSnapshot.dialogue.source,
      finalSnapshot.dialogue.text,
    );
  }
  state.streamingDialogue = null;
}

export function bindNpcSelection(ui: UiElements, onSelect: (npcId: string) => void): void {
  ui.npcList.querySelectorAll<HTMLButtonElement>("button[data-npc-id]").forEach((button) => {
    button.addEventListener("click", () => {
      void onSelect(button.dataset.npcId ?? "");
    });
  });
}

export async function leaveNpcConversation(options: ControllerOptions, npcId?: string): Promise<void> {
  const { state, ui, apiBase, render, renderError } = options;
  const targetNpcId = npcId ?? state.selectedNpcId;
  if (!state.runId || !targetNpcId || state.busy || state.snapshot?.run_result) {
    if (targetNpcId && state.selectedNpcId === targetNpcId) {
      state.selectedNpcId = "";
      state.dialogueOpen = false;
      render();
    }
    return;
  }

  state.busy = true;
  syncBusyState(ui, state);
  try {
    const snapshot = await api<Snapshot>(apiBase, `/api/npcs/${targetNpcId}/leave`, {
      method: "POST",
      body: JSON.stringify({ run_id: state.runId }),
    });
    syncExplorationOverlays(state, snapshot);
    state.snapshot = snapshot;
    if (state.selectedNpcId === targetNpcId) {
      state.selectedNpcId = "";
      state.dialogueOpen = false;
    }
    render();
  } catch (error) {
    renderError(error);
  } finally {
    state.busy = false;
    syncBusyState(ui, state);
  }
}

export function syncBusyState(ui: UiElements, state: AppState): void {
  const combatPresentationActive = isCombatPresentationActive(state);
  const combatParleyActive = canSendCombatParleyMessage(state);

  ui.startRunButton.disabled = false;
  ui.launchRunButton.disabled = state.busy;
  ui.extractRunButton.disabled = !state.runId
    || combatPresentationActive
    || state.snapshot?.location.id !== "town_square"
    || !!state.snapshot?.run_result;
  ui.sendMessageButton.disabled = state.busy
    || !state.runId
    || combatPresentationActive
    || (!combatParleyActive && !state.selectedNpcId)
    || !!state.snapshot?.run_result;
  ui.leaveConversationButton.disabled = state.busy
    || !state.selectedNpcId
    || !state.runId
    || state.snapshot?.in_combat === true
    || combatPresentationActive
    || !!state.snapshot?.run_result;
  ui.playerMessage.disabled = state.busy
    || !state.runId
    || (state.snapshot?.in_combat === true && !combatParleyActive)
    || combatPresentationActive
    || !!state.snapshot?.run_result;
  ui.playerNameInput.disabled = state.busy;
  ui.journalToggleButton.disabled = combatPresentationActive;
  ui.mapToggleButton.disabled = combatPresentationActive || !state.snapshot || !!state.snapshot.run_result;
  ui.inventoryToggleButton.disabled = combatPresentationActive || !state.snapshot || !!state.snapshot.run_result;
  ui.dialogueToggleButton.disabled = combatPresentationActive || !state.runId || !!state.snapshot?.run_result;

  document.querySelectorAll<HTMLButtonElement>("[data-action]").forEach((button) => {
    button.disabled = !state.runId || combatPresentationActive || !!state.snapshot?.run_result;
  });

  ui.combatActions.querySelectorAll<HTMLButtonElement>("button[data-combat-action]").forEach((button) => {
    const actionId = button.dataset.combatAction;
    const actionEnabled = actionId
      ? state.snapshot?.combat_state?.available_actions.find((action) => action.id === actionId)?.enabled ?? true
      : true;
    button.disabled = state.busy || !state.runId || state.snapshot?.in_combat !== true || !!state.snapshot?.run_result || !actionEnabled;
  });

  ui.questChoicePanel.querySelectorAll<HTMLButtonElement>("button[data-quest-action]").forEach((button) => {
    button.disabled = !state.runId || state.busy || combatPresentationActive || !!state.snapshot?.run_result;
  });
}

function canSendCombatParleyMessage(state: AppState): boolean {
  return state.snapshot?.in_combat === true && state.snapshot.combat_state?.negotiation?.active === true;
}

function applyCombatSnapshotUpdate(state: AppState, snapshot: Snapshot, isCombatAction: boolean): void {
  const previousSnapshot = state.snapshot;
  syncExplorationOverlays(state, snapshot);
  setViewportTransitionState(state, previousSnapshot, snapshot, isCombatAction);
  state.snapshot = snapshot;
}

async function runCombatActionRequest(options: ControllerOptions, action: string, message?: string): Promise<void> {
  const { state, ui, apiBase, render, renderError } = options;
  if (!action || !state.runId || state.busy) {
    return;
  }

  state.busy = true;
  syncBusyState(ui, state);
  try {
    const snapshot = await api<Snapshot>(apiBase, `/api/runs/${state.runId}/combat`, {
      method: "POST",
      body: JSON.stringify({ action, ...(message ? { message } : {}) }),
    });

    applyCombatSnapshotUpdate(state, snapshot, true);
    render();
    if (action === "parley_open" && snapshot.combat_state?.negotiation?.active) {
      ui.playerMessage.focus();
    }
  } catch (error) {
    renderError(error);
  } finally {
    state.busy = false;
    syncBusyState(ui, state);
  }
}

async function runAction(options: ControllerOptions, action: string): Promise<void> {
  const { state, ui, apiBase, render, renderError } = options;
  if (!state.runId || state.busy) {
    return;
  }

  state.busy = true;
  syncBusyState(ui, state);
  try {
    const previousSnapshot = state.snapshot;
    const snapshot = await api<Snapshot>(apiBase, `/api/runs/${state.runId}/actions`, {
      method: "POST",
      body: JSON.stringify({ action }),
    });
    syncExplorationOverlays(state, snapshot);
    setViewportTransitionState(state, previousSnapshot, snapshot, false);
    state.snapshot = snapshot;
    if (state.selectedNpcId && !snapshot.nearby_npcs.some((npc) => npc.id === state.selectedNpcId)) {
      state.selectedNpcId = "";
      state.dialogueOpen = false;
    }
    render();
  } catch (error) {
    renderError(error);
  } finally {
    state.busy = false;
    syncBusyState(ui, state);
  }
}

function deriveViewportTransition(
  previousSnapshot: Snapshot | null,
  nextSnapshot: Snapshot,
  isCombatAction: boolean,
): ViewportTransition {
  if (nextSnapshot.in_combat && !previousSnapshot?.in_combat) {
    return "combat-enter";
  }

  if (previousSnapshot?.in_combat && !nextSnapshot.in_combat) {
    return "combat-exit";
  }

  if (nextSnapshot.in_combat && isCombatAction) {
    return "combat-impact";
  }

  return "none";
}

function setViewportTransitionState(
  state: AppState,
  previousSnapshot: Snapshot | null,
  nextSnapshot: Snapshot,
  isCombatAction: boolean,
): void {
  const transition = deriveViewportTransition(previousSnapshot, nextSnapshot, isCombatAction);
  state.viewportTransition = transition;

  if (transition === "combat-exit" && previousSnapshot?.combat_state) {
    state.presentationToken += 1;
    state.presentationLock = {
      transition,
      combatState: previousSnapshot.combat_state,
      token: state.presentationToken,
      startedAt: performance.now(),
    };
    return;
  }

  state.presentationLock = null;
}

function isCombatPresentationActive(state: AppState): boolean {
  if (state.snapshot?.in_combat === true) {
    return true;
  }

  if (!state.presentationLock || state.presentationLock.transition !== "combat-exit") {
    return false;
  }

  if ((performance.now() - state.presentationLock.startedAt) > COMBAT_EXIT_LOCK_MS) {
    state.presentationLock = null;
    if (state.viewportTransition === "combat-exit") {
      state.viewportTransition = "none";
    }
    return false;
  }

  return true;
}

function nextSequence(state: AppState): number {
  state.messageSequence += 1;
  return state.messageSequence;
}

function appendThreadMessage(state: AppState, npcId: string, message: Omit<DialogueMessage, "id" | "sequence">): void {
  const thread = state.dialogueThreads[npcId] ?? [];
  const sequence = nextSequence(state);
  thread.push({
    id: `msg-${sequence}`,
    sequence,
    ...message,
  });
  state.dialogueThreads[npcId] = thread;
}

function upsertStreamingNpcMessage(
  state: AppState,
  message: { npcId: string; npcName: string; source: string; text: string },
): void {
  const thread = state.dialogueThreads[message.npcId] ?? [];
  const last = thread[thread.length - 1];
  if (last?.speaker === "npc" && last.streaming) {
    last.text = message.text;
    last.npcName = message.npcName;
    last.source = message.source;
    return;
  }

  const sequence = nextSequence(state);
  thread.push({
    id: `msg-${sequence}`,
    sequence,
    speaker: "npc",
    npcId: message.npcId,
    npcName: message.npcName,
    source: message.source,
    text: message.text,
    streaming: true,
  });
  state.dialogueThreads[message.npcId] = thread;
}

function finalizeNpcMessage(
  state: AppState,
  npcId: string,
  npcName: string,
  source: string,
  text: string,
): void {
  const thread = state.dialogueThreads[npcId] ?? [];
  const last = thread[thread.length - 1];
  if (last?.speaker === "npc" && last.streaming) {
    last.text = text;
    last.npcName = npcName;
    last.source = source;
    last.streaming = false;
    return;
  }

  appendThreadMessage(state, npcId, {
    speaker: "npc",
    npcId,
    npcName,
    source,
    text,
  });
}

async function runQuestDecision(options: ControllerOptions, questId: string, action: string): Promise<void> {
  const { state, ui, apiBase, render, renderError } = options;
  if (!state.runId || state.busy) {
    return;
  }

  state.busy = true;
  syncBusyState(ui, state);
  try {
    const snapshot = await api<Snapshot>(apiBase, `/api/quests/${questId}/${action}`, {
      method: "POST",
      body: JSON.stringify({ run_id: state.runId }),
    });
    syncExplorationOverlays(state, snapshot);
    state.snapshot = snapshot;
    if (snapshot.dialogue) {
      appendThreadMessage(state, snapshot.dialogue.npc_id, {
        speaker: "npc",
        npcId: snapshot.dialogue.npc_id,
        npcName: snapshot.dialogue.npc_name,
        source: snapshot.dialogue.source,
        text: snapshot.dialogue.text,
      });
    }
    render();
  } catch (error) {
    renderError(error);
  } finally {
    state.busy = false;
    syncBusyState(ui, state);
  }
}

function toggleExplorationOverlay(state: AppState, overlay: "journal" | "map" | "inventory"): void {
  if (state.snapshot?.in_combat) {
    return;
  }

  const nextOpen = overlay === "journal"
    ? !state.journalOpen
    : overlay === "map"
      ? !state.mapOpen
      : !state.inventoryOpen;

  closeExplorationOverlays(state);

  if (!nextOpen) {
    return;
  }

  if (overlay === "journal") {
    state.journalOpen = true;
  } else if (overlay === "map") {
    state.mapOpen = true;
  } else {
    state.inventoryOpen = true;
  }
}

function closeExplorationOverlays(state: AppState): void {
  state.journalOpen = false;
  state.mapOpen = false;
  state.inventoryOpen = false;
  state.dialogueOpen = false;
}

function syncExplorationOverlays(state: AppState, snapshot: Snapshot): void {
  if (snapshot.in_combat || snapshot.run_result) {
    closeExplorationOverlays(state);
  }
}

function toggleDialogueDrawer(state: AppState): void {
  if (!state.runId || state.snapshot?.in_combat || state.snapshot?.run_result) {
    return;
  }

  state.dialogueOpen = !state.dialogueOpen;
  if (!state.dialogueOpen && state.selectedNpcId) {
    state.selectedNpcId = "";
  }
}