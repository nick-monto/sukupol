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
  messageSequence: 0,
  viewportTransition: "none",
  presentationLock: null,
  presentationToken: 0,
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
  renderApp(ui, state, handleViewportTransitionComplete);
  if (state.viewportTransition !== "combat-exit") {
    state.viewportTransition = "none";
  }
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

function handleViewportTransitionComplete(token: number): void {
  if (state.presentationLock?.token !== token) {
    return;
  }

  state.presentationLock = null;
  state.viewportTransition = "none";
  render();
}

function renderError(error: unknown): void {
  const message = error instanceof Error ? error.message : "Unknown error";
  console.error(message, error);
  render();
}
