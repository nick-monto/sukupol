import { api } from "../api";
import type { AppState, DialogueMessage, Snapshot } from "../types";
import type { ControllerOptions } from "./options";
import { syncBusyState, syncExplorationOverlays } from "./state";

export function canSendCombatParleyMessage(state: AppState): boolean {
  return state.snapshot?.in_combat === true && state.snapshot.combat_state?.negotiation?.active === true;
}

export function nextSequence(state: AppState): number {
  state.messageSequence += 1;
  return state.messageSequence;
}

export function appendThreadMessage(state: AppState, npcId: string, message: Omit<DialogueMessage, "id" | "sequence">): void {
  const thread = state.dialogueThreads[npcId] ?? [];
  const sequence = nextSequence(state);
  thread.push({ id: `msg-${sequence}`, sequence, ...message });
  state.dialogueThreads[npcId] = thread;
}

function lastNpcMessage(thread: DialogueMessage[]): DialogueMessage | undefined {
  const last = thread[thread.length - 1];
  return last?.speaker === "npc" ? last : undefined;
}

export function upsertStreamingNpcMessage(state: AppState, message: { npcId: string; npcName: string; source: string; text: string }): void {
  const thread = state.dialogueThreads[message.npcId] ?? [];
  const last = lastNpcMessage(thread);
  if (last?.streaming) { Object.assign(last, message); return; }
  const seq = nextSequence(state);
  thread.push({ id: `msg-${seq}`, sequence: seq, speaker: "npc", npcId: message.npcId, npcName: message.npcName, source: message.source, text: message.text, streaming: true });
  state.dialogueThreads[message.npcId] = thread;
}

export function finalizeNpcMessage(state: AppState, npcId: string, npcName: string, source: string, text: string): void {
  const thread = state.dialogueThreads[npcId] ?? [];
  const last = lastNpcMessage(thread);
  if (last?.streaming) { Object.assign(last, { text, npcName, source, streaming: false }); return; }
  appendThreadMessage(state, npcId, { speaker: "npc", npcId, npcName, source, text });
}

type StreamEvent =
  | { type: "start"; npc_id: string; npc_name: string; source: string }
  | { type: "chunk"; text: string }
  | { type: "snapshot"; snapshot: Snapshot }
  | { type: "error"; detail: string };

function handleStreamStart(event: { npc_id: string; npc_name: string; source: string }, state: AppState, render: () => void): void {
  state.streamingDialogue = { npc_id: event.npc_id, npc_name: event.npc_name, source: event.source, text: "" };
  upsertStreamingNpcMessage(state, { npcId: event.npc_id, npcName: event.npc_name, source: event.source, text: "" });
  render();
}

function handleStreamChunk(event: { text: string }, state: AppState, render: () => void): void {
  if (!state.streamingDialogue) return;
  const nextText = `${state.streamingDialogue.text}${event.text}`;
  state.streamingDialogue = { ...state.streamingDialogue, text: nextText };
  upsertStreamingNpcMessage(state, { npcId: state.streamingDialogue.npc_id, npcName: state.streamingDialogue.npc_name, source: state.streamingDialogue.source, text: nextText });
  render();
}

function processStreamEvent(event: StreamEvent, state: AppState, render: () => void): void {
  switch (event.type) {
    case "start": handleStreamStart(event, state, render); return;
    case "chunk": handleStreamChunk(event, state, render); return;
    case "error": throw new Error(event.detail);
    default: return;
  }
}

async function readNpcDialogueStream(response: Response, state: AppState, render: () => void): Promise<Snapshot> {
  if (!response.body) throw new Error("Dialogue stream did not return a readable body");
  const reader = response.body.getReader(), decoder = new TextDecoder();
  let buffer = "", finalSnapshot: Snapshot | null = null;
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    let nl = buffer.indexOf("\n");
    while (nl >= 0) {
      const rawLine = buffer.slice(0, nl).trim();
      buffer = buffer.slice(nl + 1);
      if (rawLine) { const ev = JSON.parse(rawLine) as StreamEvent; if (ev.type === "snapshot") finalSnapshot = ev.snapshot; else processStreamEvent(ev, state, render); }
      nl = buffer.indexOf("\n");
    }
    if (done) break;
  }
  if (!finalSnapshot) throw new Error("Dialogue stream ended without a final snapshot");
  return finalSnapshot;
}

export async function streamNpcDialogue(options: ControllerOptions, npcId: string, message: string): Promise<void> {
  const { apiBase, state, render } = options;
  const response = await fetch(`${apiBase}/api/npcs/${npcId}/talk/stream`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ run_id: state.runId, message }),
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed with ${response.status}`);
  }
  const finalSnapshot = await readNpcDialogueStream(response, state, render);
  state.snapshot = finalSnapshot;
  syncExplorationOverlays(state, finalSnapshot);
  if (finalSnapshot.dialogue) finalizeNpcMessage(state, finalSnapshot.dialogue.npc_id, finalSnapshot.dialogue.npc_name, finalSnapshot.dialogue.source, finalSnapshot.dialogue.text);
  state.streamingDialogue = null;
}

export async function leaveNpcConversation(options: ControllerOptions, npcId?: string): Promise<void> {
  const { state, ui, apiBase, render, renderError } = options;
  const targetNpcId = npcId ?? state.selectedNpcId;
  if (!state.runId || !targetNpcId || state.busy || state.snapshot?.run_result) {
    if (targetNpcId && state.selectedNpcId === targetNpcId) { state.selectedNpcId = ""; state.dialogueOpen = false; render(); }
    return;
  }
  state.busy = true; syncBusyState(ui, state);
  try {
    const snapshot = await api<Snapshot>(apiBase, `/api/npcs/${targetNpcId}/leave`, {
      method: "POST", body: JSON.stringify({ run_id: state.runId }),
    });
    syncExplorationOverlays(state, snapshot);
    state.snapshot = snapshot;
    if (state.selectedNpcId === targetNpcId) { state.selectedNpcId = ""; state.dialogueOpen = false; }
    render();
  } catch (error) { renderError(error); } finally { state.busy = false; syncBusyState(ui, state); }
}
