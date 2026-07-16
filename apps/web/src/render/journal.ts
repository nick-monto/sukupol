import type { Snapshot } from "../types";
import { escapeHtml, renderChatText, renderJournalEmpty } from "./dom";

function formatJournalStamp(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Visit logged";
  }

  return parsed.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function renderJournal(snapshot: Snapshot): string {
  if (snapshot.journal.length === 0) {
    return renderJournalEmpty("Leave a conversation to record a summary for that visit.");
  }

  return snapshot.journal
    .map((group) => `
      <article class="journal-group">
        <div class="journal-group-head">
          <div>
            <strong>${escapeHtml(group.npc_name)}</strong>
            <div class="small">${group.entries.length} visit${group.entries.length === 1 ? "" : "s"}</div>
          </div>
        </div>
        <div class="journal-group-entries">
          ${group.entries.map((entry) => `
            <div class="journal-entry">
              <div class="journal-entry-meta">
                <span class="journal-entry-stamp">${escapeHtml(formatJournalStamp(entry.visit_ended_at))}</span>
                <span class="journal-entry-turns">${entry.turn_count} turn${entry.turn_count === 1 ? "" : "s"}</span>
              </div>
              <p>${renderChatText(entry.summary)}</p>
            </div>
          `).join("")}
        </div>
      </article>
    `)
    .join("");
}
