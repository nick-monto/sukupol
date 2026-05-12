import "./styles.css";

import { bindInteractionHandlers, bindNpcSelection, leaveNpcConversation, syncBusyState } from "./controller";
import { renderApp } from "./render";
import type { AppState } from "./types";
import { createAppMarkup, getUiElements } from "./ui";

const apiBase = (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://127.0.0.1:8000";

const state: AppState = {
  bootstrapTitle: "Sukupol",
  runId: "",
  snapshot: null,
  selectedNpcId: "",
  dialogueThreads: {},
  streamingDialogue: null,
  viewportTransition: "none",
  busy: false,
};

const app = document.querySelector<HTMLDivElement>("#app");

if (!app) {
  throw new Error("App root not found");
}

app.innerHTML = createAppMarkup(state.bootstrapTitle);

const ui = getUiElements();

bindInteractionHandlers({
  apiBase,
  state,
  ui,
  render,
  renderError,
});

render();

function render(): void {
  renderApp(ui, state);
  state.viewportTransition = "none";
  syncBusyState(ui, state);

  bindNpcSelection(ui, async (npcId) => {
    if (!npcId) {
      return;
    }

    if (state.selectedNpcId && state.selectedNpcId !== npcId) {
      await leaveNpcConversation({
        apiBase,
        state,
        ui,
        render,
        renderError,
      }, state.selectedNpcId);
    }

    state.selectedNpcId = npcId;
    render();
  });
}

function renderError(error: unknown): void {
  const message = error instanceof Error ? error.message : "Unknown error";
  const threadId = state.selectedNpcId || state.streamingDialogue?.npc_id || state.snapshot?.dialogue?.npc_id || "__system__";
  const thread = state.dialogueThreads[threadId] ?? [];
  thread.push({
    id: `system-${Date.now()}-${thread.length}`,
    speaker: "system",
    text: message,
  });
  state.dialogueThreads[threadId] = thread;
  render();
}
