import type { Snapshot } from "../types";
import { escapeHtml } from "./dom";

export function renderNpcList(snapshot: Snapshot, selectedNpcId: string): string {
  if (snapshot.nearby_npcs.length === 0) {
    return "<p class=\"small empty-copy\">No contacts in range.</p>";
  }

  return `
    <div class="npc-roster">
      ${snapshot.nearby_npcs
      .map((npc) => {
        const selected = npc.id === selectedNpcId;
        return `
          <button class="npc-tab${selected ? " is-selected" : ""}" data-npc-id="${npc.id}" ${selected ? "disabled" : ""}>
            <span class="npc-tab-name">${escapeHtml(npc.display_name)}</span>
            <span class="npc-tab-meta">${escapeHtml(npc.distance === 0 ? "In range" : "One step away")}</span>
          </button>
        `;
      })
      .join("")}
    </div>
  `;
}
