import type { Snapshot } from "../types";
import { escapeHtml } from "./dom";

export function renderInventory(snapshot: Snapshot): string {
  if (snapshot.inventory.length === 0) {
    return "<p class=\"small empty-copy\">No provisions carried.</p>";
  }

  return snapshot.inventory
    .map((item) => {
      const equipped = item.item_id === snapshot.equipped_weapon;
      return `
        <div class="inventory-item${equipped ? " is-equipped" : ""}">
          <div>
            <strong>${escapeHtml(item.name)}</strong>
            <div class="small">${escapeHtml(item.item_type)} / Qty ${item.quantity}${equipped ? " / readied" : ""}</div>
          </div>
          <span class="inventory-mark">${equipped ? "Readied" : item.item_type === "quest" ? "Quest" : "Stored"}</span>
        </div>
      `;
    })
    .join("");
}
