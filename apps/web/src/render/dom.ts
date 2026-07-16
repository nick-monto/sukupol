export function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

export function renderChatText(value: string): string {
  return escapeHtml(value).replaceAll("\n", "<br>");
}

export function statCards(entries: Array<[string, string]>): string {
  return entries
    .map(
      ([label, value]) => `
        <div class="stat-card">
          <span class="small">${label}</span>
          <strong>${value}</strong>
        </div>
      `,
    )
    .join("");
}

export function renderChatEmpty(copy: string): string {
  return `<div class="chat-empty">${escapeHtml(copy)}</div>`;
}

export function renderJournalEmpty(copy: string): string {
  return `<div class="chat-empty">${escapeHtml(copy)}</div>`;
}

export function renderQuestEmpty(copy: string): string {
  return `<div class="chat-empty">${escapeHtml(copy)}</div>`;
}
