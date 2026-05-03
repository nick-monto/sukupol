import { api } from "./api";
import type { AppState, Snapshot } from "./types";
import type { UiElements } from "./ui";
import { isEditableTarget } from "./ui";

type ControllerOptions = {
  apiBase: string;
  state: AppState;
  ui: UiElements;
  render: () => void;
  renderError: (error: unknown) => void;
};

export function bindInteractionHandlers(options: ControllerOptions): void {
  const { ui } = options;

  document.addEventListener("keydown", async (event) => {
    const { state } = options;
    if (!state.runId || state.busy || state.snapshot?.in_combat || isEditableTarget(event.target)) {
      return;
    }

    const keymap: Record<string, string> = {
      w: "forward",
      s: "backward",
      a: "turn_left",
      d: "turn_right",
    };

    const action = keymap[event.key.toLowerCase()];
    if (!action) {
      return;
    }

    event.preventDefault();
    await runAction(options, action);
  });

  ui.startRunButton.addEventListener("click", async () => {
    const { state, apiBase, render, renderError } = options;

    state.busy = true;
    syncBusyState(ui, state);
    try {
      const snapshot = await api<Snapshot>(apiBase, "/api/runs", {
        method: "POST",
        body: JSON.stringify({ player_name: "Wayfarer" }),
      });
      state.runId = snapshot.run_id;
      state.snapshot = snapshot;
      state.selectedNpcId = snapshot.nearby_npcs[0]?.id ?? "";
      render();
    } catch (error) {
      renderError(error);
    } finally {
      state.busy = false;
      syncBusyState(ui, state);
    }
  });

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
      state.snapshot = snapshot;
      render();
    } catch (error) {
      renderError(error);
    } finally {
      state.busy = false;
      syncBusyState(ui, state);
    }
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
    const { state, apiBase, render, renderError } = options;
    if (!state.runId || !state.selectedNpcId || state.busy || state.snapshot?.in_combat) {
      return;
    }

    const message = ui.playerMessage.value.trim();
    if (!message) {
      ui.dialogueLog.textContent = "Type a message before sending it.";
      return;
    }

    state.busy = true;
    syncBusyState(ui, state);
    try {
      const snapshot = await api<Snapshot>(apiBase, `/api/npcs/${state.selectedNpcId}/talk`, {
        method: "POST",
        body: JSON.stringify({ run_id: state.runId, message }),
      });
      state.snapshot = snapshot;
      render();
    } catch (error) {
      renderError(error);
    } finally {
      state.busy = false;
      syncBusyState(ui, state);
    }
  });

  ui.combatActions.querySelectorAll<HTMLButtonElement>("button[data-combat-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      const action = button.dataset.combatAction;
      const { state, apiBase, render, renderError } = options;
      if (!action || !state.runId) {
        return;
      }

      state.busy = true;
      syncBusyState(ui, state);
      try {
        const snapshot = await api<Snapshot>(apiBase, `/api/runs/${state.runId}/combat`, {
          method: "POST",
          body: JSON.stringify({ action }),
        });
        state.snapshot = snapshot;
        render();
      } catch (error) {
        renderError(error);
      } finally {
        state.busy = false;
        syncBusyState(ui, state);
      }
    });
  });
}

export function bindNpcSelection(ui: UiElements, onSelect: (npcId: string) => void): void {
  ui.npcList.querySelectorAll<HTMLButtonElement>("button[data-npc-id]").forEach((button) => {
    button.addEventListener("click", () => {
      onSelect(button.dataset.npcId ?? "");
    });
  });
}

export function syncBusyState(ui: UiElements, state: AppState): void {
  const disabled = state.busy;
  ui.startRunButton.disabled = disabled;
  ui.extractRunButton.disabled = disabled
    || !state.runId
    || state.snapshot?.in_combat === true
    || state.snapshot?.location.id !== "town_square"
    || !!state.snapshot?.run_result;
  ui.sendMessageButton.disabled = disabled
    || !state.selectedNpcId
    || !state.runId
    || state.snapshot?.in_combat === true
    || !!state.snapshot?.run_result;
  ui.playerMessage.disabled = disabled
    || !state.runId
    || state.snapshot?.in_combat === true
    || !!state.snapshot?.run_result;

  document.querySelectorAll<HTMLButtonElement>("[data-action]").forEach((button) => {
    button.disabled = disabled || !state.runId || state.snapshot?.in_combat === true || !!state.snapshot?.run_result;
  });

  ui.combatActions.querySelectorAll<HTMLButtonElement>("button[data-combat-action]").forEach((button) => {
    button.disabled = disabled || !state.runId || state.snapshot?.in_combat !== true || !!state.snapshot?.run_result;
  });
}

async function runAction(options: ControllerOptions, action: string): Promise<void> {
  const { state, ui, apiBase, render, renderError } = options;
  if (!state.runId) {
    return;
  }

  state.busy = true;
  syncBusyState(ui, state);
  try {
    const snapshot = await api<Snapshot>(apiBase, `/api/runs/${state.runId}/actions`, {
      method: "POST",
      body: JSON.stringify({ action }),
    });
    state.snapshot = snapshot;
    if (!snapshot.nearby_npcs.some((npc) => npc.id === state.selectedNpcId)) {
      state.selectedNpcId = snapshot.nearby_npcs[0]?.id ?? "";
    }
    render();
  } catch (error) {
    renderError(error);
  } finally {
    state.busy = false;
    syncBusyState(ui, state);
  }
}