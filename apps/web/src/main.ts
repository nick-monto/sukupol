import "./styles.css";

import { bindInteractionHandlers, bindNpcSelection, syncBusyState } from "./controller";
import { renderApp } from "./render";
import type { AppState } from "./types";
import { createAppMarkup, getUiElements } from "./ui";

const apiBase = (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://127.0.0.1:8000";

const state: AppState = {
  bootstrapTitle: "Sukupol",
  runId: "",
  snapshot: null,
  selectedNpcId: "",
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

  bindNpcSelection(ui, (npcId) => {
    if (!npcId) {
      return;
    }

    state.selectedNpcId = npcId;
    render();
  });
}

function renderError(error: unknown): void {
  const message = error instanceof Error ? error.message : "Unknown error";
  ui.dialogueLog.textContent = message;
}
