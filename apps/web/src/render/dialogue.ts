import type { AppState, DialogueMessage, Snapshot } from "../types";
import { escapeHtml, renderChatEmpty, renderChatText } from "./dom";

export function renderChatMessage(message: DialogueMessage): string {
  const speakerLabel = message.speaker === "player"
    ? "You"
    : message.speaker === "ally"
      ? "Ally"
    : message.speaker === "system"
      ? "System"
      : message.npcName ?? "Contact";
  const sourceChip = message.speaker === "npc" && message.source && !message.streaming
    ? `<span class="chat-source">${escapeHtml(message.source)}</span>`
    : "";
  const text = message.text.trim();
  const content = message.streaming && !text
    ? '<div class="chat-loading" aria-label="Response in progress"><span></span><span></span><span></span></div>'
    : `<p>${renderChatText(text)}</p>`;

  return `
    <div class="chat-message is-${message.speaker}${message.streaming ? " is-streaming" : ""}">
      <div class="chat-bubble">
        <div class="chat-bubble-meta">
          <span class="chat-speaker">${escapeHtml(speakerLabel)}</span>
          ${sourceChip}
        </div>
        ${content}
      </div>
    </div>
  `;
}

function renderDialogueTranscript(snapshot: Snapshot, state: AppState): string {
  const thread = [...(state.dialogueThreads[state.selectedNpcId] ?? [])];
  if (thread.length === 0 && snapshot.dialogue?.npc_id === state.selectedNpcId) {
    thread.push({
      id: "snapshot-dialogue",
      sequence: -1,
      speaker: "npc",
      npcId: snapshot.dialogue.npc_id,
      npcName: snapshot.dialogue.npc_name,
      source: snapshot.dialogue.source,
      text: snapshot.dialogue.text,
    });
  }

  if (thread.length === 0) {
    return renderChatEmpty("No messages on this channel yet. Ask for a route, rumor, supply, or warning.");
  }

  return thread.map(renderChatMessage).join("");
}

function renderCombatDispatch(snapshot: Snapshot): string {
  const combatState = snapshot.combat_state;
  if (!combatState) {
    return renderChatEmpty("Combat telemetry unavailable.");
  }

  const entries: DialogueMessage[] = combatState.events.map((event, index) => ({
    id: event.id,
    sequence: index,
    speaker: event.actor === "player" ? "player" : event.actor === "enemy" ? "npc" : event.actor === "ally" ? "ally" : "system",
    npcName: combatState.enemy.name,
    text: event.text,
  }));

  if (entries.length === 0) {
    combatState.log.forEach((line, index) => {
      entries.push({
        id: `combat-log-${index}`,
        sequence: entries.length,
        speaker: index === 0 ? "npc" : "system",
        npcName: combatState.enemy.name,
        text: line,
      });
    });
  }

  return entries.map(renderChatMessage).join("");
}

function renderCombatCommunicationTranscript(combatState: NonNullable<Snapshot["combat_state"]>): string {
  const transcript = combatState.negotiation?.transcript ?? [];
  if (transcript.length === 0) {
    return renderChatEmpty("Communication line is open. Send the first message to begin talking to the enemy.");
  }

  const entries: DialogueMessage[] = transcript.map((entry, index) => ({
    id: `combat-negotiation-${index}`,
    sequence: index,
    speaker: entry.speaker === "enemy" ? "npc" : entry.speaker,
    npcName: combatState.enemy.name,
    text: entry.text,
  }));

  return entries.map(renderChatMessage).join("");
}

export function renderUnifiedTranscript(snapshot: Snapshot | null, state: AppState): string {
  if (snapshot?.in_combat && snapshot.combat_state) {
    if (snapshot.combat_state.negotiation?.active) {
      return renderCombatCommunicationTranscript(snapshot.combat_state);
    }
    return renderCombatDispatch(snapshot);
  }

  if (!state.selectedNpcId) {
    return renderChatEmpty(
      snapshot
        ? "No active conversation. Choose a nearby contact to start chatting."
        : "No active channel. Begin a run and choose a nearby contact.",
    );
  }

  return renderDialogueTranscript(snapshot!, state);
}
