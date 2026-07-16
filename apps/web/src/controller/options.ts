import type { PinballTable } from "../pinballCombat";
import type { AppState } from "../types";
import type { UiElements } from "../ui";

export type ControllerOptions = {
  apiBase: string;
  state: AppState;
  ui: UiElements;
  render: () => void;
  renderError: (error: unknown) => void;
  pinballRegistry: PinballRegistry;
};

export interface PinballRegistry {
  get(): PinballTable | null;
  set(table: PinballTable | null): void;
  clear(): void;
}

export function createPinballRegistry(): PinballRegistry {
  let active: PinballTable | null = null;
  return {
    get: () => active,
    set: (table) => { active = table; },
    clear: () => {
      if (active) {
        active.teardown();
        active = null;
      }
    },
  };
}

export const CHAT_DOCK_HEIGHT_KEY = "sukupol.chatDockHeight";
export const CHAT_DOCK_DEFAULT_HEIGHT = 300;
export const CHAT_DOCK_MIN_HEIGHT = 256;
export const CHAT_DOCK_MAX_HEIGHT_RATIO = 0.75;
export const COMBAT_EXIT_LOCK_MS = 320;
