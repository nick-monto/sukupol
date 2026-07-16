import { api } from "../api";
import type { Snapshot } from "../types";
import type { UiElements } from "../ui";
import { isEditableTarget } from "../ui";
import type { ControllerOptions } from "./options";
import { CHAT_DOCK_HEIGHT_KEY, CHAT_DOCK_DEFAULT_HEIGHT, CHAT_DOCK_MIN_HEIGHT, CHAT_DOCK_MAX_HEIGHT_RATIO } from "./options";
import { runAction, runCombatActionRequest, runQuestDecision } from "./actions";
import { streamNpcDialogue, leaveNpcConversation, appendThreadMessage, canSendCombatParleyMessage } from "./dialogue";
import { syncBusyState, closeExplorationOverlays, syncExplorationOverlays, setViewportTransitionState, toggleExplorationOverlay, toggleDialogueDrawer, isCombatPresentationActive } from "./state";
import { managePinballFn } from "./pinball";

function applyChatDockHeight(element: HTMLElement, height: number): void {
  element.style.height = `${height}px`;
}

function clampChatDockHeight(height: number, vpHeight: number): number {
  return Math.min(Math.max(height, CHAT_DOCK_MIN_HEIGHT), Math.max(CHAT_DOCK_MIN_HEIGHT, vpHeight * CHAT_DOCK_MAX_HEIGHT_RATIO));
}

function restoreSavedChatHeight(ui: UiElements): void {
  const saved = window.localStorage.getItem(CHAT_DOCK_HEIGHT_KEY);
  const h = saved ? Number.parseFloat(saved) : NaN;
  applyChatDockHeight(ui.contextDrawer, Number.isFinite(h) ? h : CHAT_DOCK_DEFAULT_HEIGHT);
}

function initChatResizeDrag(ui: UiElements, event: PointerEvent): void {
  event.preventDefault();
  const vpRect = ui.viewportPanel.getBoundingClientRect();
  const pointerOffset = event.clientY - ui.contextDrawer.getBoundingClientRect().top;
  ui.chatResizeHandle.setPointerCapture(event.pointerId);
  ui.contextDrawer.classList.add("is-resizing");
  document.body.classList.add("is-chat-resizing");
  const onMove = (me: PointerEvent) => applyChatDockHeight(ui.contextDrawer, clampChatDockHeight(vpRect.bottom - (me.clientY - pointerOffset), vpRect.height));
  const stop = () => {
    ui.contextDrawer.classList.remove("is-resizing");
    document.body.classList.remove("is-chat-resizing");
    ui.chatResizeHandle.removeEventListener("pointermove", onMove);
    ui.chatResizeHandle.removeEventListener("pointerup", stop);
    ui.chatResizeHandle.removeEventListener("pointercancel", stop);
    window.localStorage.setItem(CHAT_DOCK_HEIGHT_KEY, String(ui.contextDrawer.getBoundingClientRect().height));
  };
  ui.chatResizeHandle.addEventListener("pointermove", onMove);
  ui.chatResizeHandle.addEventListener("pointerup", stop);
  ui.chatResizeHandle.addEventListener("pointercancel", stop);
}

function bindChatResize(ui: UiElements): void {
  restoreSavedChatHeight(ui);
  ui.chatResizeHandle.addEventListener("dblclick", () => { window.localStorage.removeItem(CHAT_DOCK_HEIGHT_KEY); applyChatDockHeight(ui.contextDrawer, CHAT_DOCK_DEFAULT_HEIGHT); });
  ui.chatResizeHandle.addEventListener("pointerdown", (event) => initChatResizeDrag(ui, event));
}

function bindHudToggles(options: ControllerOptions): void {
  const { ui, state, render } = options;
  ui.journalToggleButton.addEventListener("click", () => { toggleExplorationOverlay(state, "journal"); render(); });
  ui.mapToggleButton.addEventListener("click", () => { toggleExplorationOverlay(state, "map"); render(); });
  ui.inventoryToggleButton.addEventListener("click", () => { toggleExplorationOverlay(state, "inventory"); render(); });
  ui.dialogueToggleButton.addEventListener("click", () => { toggleDialogueDrawer(state); render(); });
}

async function handleKeydown(options: ControllerOptions, event: KeyboardEvent): Promise<void> {
  const { state } = options;
  if (isEditableTarget(event.target) || !state.runId || state.busy || isCombatPresentationActive(state)) return;
  const keymap: Record<string, string> = { w: "move_north", s: "move_south", a: "move_west", d: "move_east" };
  const action = keymap[event.key.toLowerCase()];
  if (!action) return;
  event.preventDefault();
  await runAction(options, action);
}

async function handleStartRun(options: ControllerOptions): Promise<void> {
  const { state, ui, apiBase, render, renderError } = options;
  if (state.busy) return;
  const playerName = ui.playerNameInput.value.trim() || "Wayfarer";
  ui.playerNameInput.value = playerName;
  state.busy = true; syncBusyState(ui, state);
  try {
    const snapshot = await api<Snapshot>(apiBase, "/api/runs", { method: "POST", body: JSON.stringify({ player_name: playerName }) });
    closeExplorationOverlays(state);
    state.runId = snapshot.run_id; state.snapshot = snapshot;
    state.selectedNpcId = ""; state.dialogueThreads = {}; state.viewportTransition = "none"; state.presentationLock = null;
    render();
  } catch (error) { renderError(error); } finally { state.busy = false; syncBusyState(ui, state); }
}

async function handleExtractRun(options: ControllerOptions): Promise<void> {
  const { state, ui, apiBase, render, renderError } = options;
  if (!state.runId || state.busy) return;
  state.busy = true; syncBusyState(ui, state);
  try {
    const snapshot = await api<Snapshot>(apiBase, `/api/runs/${state.runId}/extract`, { method: "POST" });
    syncExplorationOverlays(state, snapshot);
    setViewportTransitionState(state, state.snapshot, snapshot, false);
    state.snapshot = snapshot; render();
  } catch (error) { renderError(error); } finally { state.busy = false; syncBusyState(ui, state); }
}

async function handleSendMessage(options: ControllerOptions): Promise<void> {
  const { state, ui, render, renderError } = options;
  if (!state.runId || state.busy || isCombatPresentationActive(state)) return;
  const message = ui.playerMessage.value.trim();
  if (!message) { ui.playerMessage.focus(); return; }
  if (canSendCombatParleyMessage(state)) {
    try { ui.playerMessage.value = ""; await runCombatActionRequest(options, "parley_message", message); } catch (error) { renderError(error); }
    return;
  }
  if (!state.selectedNpcId) return;
  state.busy = true;
  appendThreadMessage(state, state.selectedNpcId, { speaker: "player", text: message });
  ui.playerMessage.value = ""; syncBusyState(ui, state); render();
  try {
    await streamNpcDialogue(options, state.selectedNpcId, message);
    state.viewportTransition = "none"; state.presentationLock = null; render();
  } catch (error) { state.streamingDialogue = null; renderError(error); }
  finally { state.busy = false; syncBusyState(ui, state); }
}

function handleCombatActions(options: ControllerOptions, event: MouseEvent): void {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  const button = target.closest<HTMLButtonElement>("button[data-combat-action]");
  if (!button) return;
  const action = button.dataset.combatAction;
  const { state } = options;
  if (!action || !state.runId || state.busy || button.disabled) return;
  void runCombatActionRequest(options, action);
}

export function bindNpcSelection(ui: UiElements, onSelect: (npcId: string) => void): void {
  ui.npcList.querySelectorAll<HTMLButtonElement>("button[data-npc-id]").forEach((button) => {
    button.addEventListener("click", () => { void onSelect(button.dataset.npcId ?? ""); });
  });
}

function setupQuestChoicePanel(options: ControllerOptions): void {
  options.ui.questChoicePanel.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const button = target.closest<HTMLButtonElement>("button[data-quest-action][data-quest-id]");
    if (!button) return;
    const action = button.dataset.questAction, questId = button.dataset.questId;
    if (!action || !questId) return;
    await runQuestDecision(options, questId, action);
  });
}

function setupDataActionButtons(options: ControllerOptions): void {
  document.querySelectorAll<HTMLButtonElement>("[data-action]").forEach((button) => {
    button.addEventListener("click", async () => { const a = button.dataset.action; if (a) await runAction(options, a); });
  });
}

export function bindInteractionHandlers(options: ControllerOptions): { managePinball: () => void } {
  const { ui } = options;
  bindChatResize(ui);
  bindHudToggles(options);
  document.addEventListener("keydown", (e) => { void handleKeydown(options, e); });
  ui.playerMessage.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ui.sendMessageButton.click(); } });
  ui.playerNameInput.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); ui.launchRunButton.click(); } });
  ui.startRunButton.addEventListener("click", () => { void handleStartRun(options); });
  ui.launchRunButton.addEventListener("click", () => { void handleStartRun(options); });
  ui.extractRunButton.addEventListener("click", () => { void handleExtractRun(options); });
  ui.leaveConversationButton.addEventListener("click", () => { void leaveNpcConversation(options); });
  setupQuestChoicePanel(options);
  setupDataActionButtons(options);
  ui.sendMessageButton.addEventListener("click", () => { void handleSendMessage(options); });
  ui.combatActions.addEventListener("click", (e) => { handleCombatActions(options, e); });
  return { managePinball: () => managePinballFn(options, options.pinballRegistry) };
}
