import type { Snapshot } from "../types";
import { escapeHtml, renderChatText, renderQuestEmpty } from "./dom";

export function renderQuestList(snapshot: Snapshot): string {
  if (snapshot.quests.length === 0) {
    return renderQuestEmpty("No contracts active. Ask nearby NPCs if they need work done.");
  }

  return snapshot.quests
    .map((quest) => {
      const statusLabel = quest.status === "offered"
        ? "Offer"
        : quest.status === "active"
          ? quest.can_turn_in ? "Ready to turn in" : "Active"
          : quest.status === "completed"
            ? "Completed"
            : "Declined";
      const progressText = quest.status === "offered"
        ? `Reward ${quest.reward_gold} gold`
        : `${quest.progress_value}/${quest.progress_target} recovered`;
      const meta = [quest.offered_by_npc_name, quest.target_biome_name, quest.target_floor_number ? `Floor ${quest.target_floor_number}` : ""]
        .filter(Boolean)
        .join(" / ");
      return `
        <article class="quest-card is-${quest.status}">
          <div class="quest-card-head">
            <div>
              <strong>${escapeHtml(quest.title)}</strong>
              <div class="small">${escapeHtml(meta)}</div>
            </div>
            <span class="quest-status quest-status-${quest.status}">${escapeHtml(statusLabel)}</span>
          </div>
          <p class="quest-summary">${renderChatText(quest.summary)}</p>
          <p class="quest-objective">${renderChatText(quest.objective_text)}</p>
          <div class="quest-foot">
            <span class="small">${escapeHtml(progressText)}</span>
            <span class="small">${escapeHtml(quest.hint)}</span>
          </div>
        </article>
      `;
    })
    .join("");
}

export function renderQuestChoicePanel(snapshot: Snapshot, selectedNpcId: string): string {
  if (!selectedNpcId || snapshot.in_combat || snapshot.run_result) {
    return "";
  }

  const offeredQuest = snapshot.quests.find((quest) => quest.status === "offered" && quest.offered_by_npc_id === selectedNpcId);
  if (!offeredQuest) {
    return "";
  }

  return `
    <div class="quest-choice-card">
      <div class="quest-choice-copy">
        <span class="quest-status quest-status-offered">Quest offer</span>
        <strong>${escapeHtml(offeredQuest.title)}</strong>
        <p>${renderChatText(offeredQuest.summary)}</p>
        <p class="quest-objective">${renderChatText(offeredQuest.objective_text)}</p>
      </div>
      <div class="quest-choice-actions">
        <button type="button" data-quest-action="accept" data-quest-id="${offeredQuest.id}">Accept</button>
        <button type="button" data-quest-action="decline" data-quest-id="${offeredQuest.id}">Decline</button>
      </div>
    </div>
  `;
}
