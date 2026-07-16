import type { AppState, Snapshot } from "../types";
import type { UiElements } from "../ui";
import { hideMap, renderMap } from "../viewport";
import { applyCombatOverlayUpdate, renderCombatActions } from "./combat";
import { renderJournalEmpty, renderQuestEmpty } from "./dom";
import { renderJournal } from "./journal";
import { renderExpeditionSignal, renderHeroSummary, renderLocationMeta } from "./map";
import { renderNpcList } from "./npc";
import { renderOutcome } from "./outcome";
import { renderOverworldMap } from "./overworld";
import { applyPresentationState, getPresentedSnapshot } from "./presentation";
import { renderQuestChoicePanel, renderQuestList } from "./quest";
import { renderUnifiedTranscript } from "./dialogue";
import { renderInventory } from "./inventory";

export function renderApp(
  ui: UiElements,
  state: AppState,
  onViewportTransitionComplete?: (token: number) => void,
): void {
  const snapshot = getPresentedSnapshot(state);
  ui.heroSummary.innerHTML = renderHeroSummary(snapshot);
  ui.expeditionSignal.textContent = renderExpeditionSignal(snapshot);
  applyPresentationState(ui, state, snapshot);

  if (!snapshot) {
    ui.locationName.textContent = "No run started";
    ui.locationMeta.textContent = "Awaiting expedition telemetry.";
    ui.locationDescription.textContent = "Bring up the backend and start a run to render the traversal map.";
    ui.viewport.textContent = "Stand up the backend and begin a run.";
    hideMap(ui.viewportPixiStage);
    ui.overworldMap.innerHTML = renderOverworldMap(null);
    ui.inventoryList.innerHTML = "<p class=\"small empty-copy\">No loadout recorded.</p>";
    ui.questList.innerHTML = renderQuestEmpty("No contracts recorded.");
    ui.npcList.innerHTML = "<p class=\"small empty-copy\">No contacts in range.</p>";
    ui.combatOverlay.hidden = true;
    ui.combatOverlay.innerHTML = "";
    ui.dialogueLog.innerHTML = renderUnifiedTranscript(null, state);
    ui.combatActions.innerHTML = "";
    ui.questChoicePanel.innerHTML = "";
    ui.outcomeLog.textContent = "No completed run yet.";
    ui.journalList.innerHTML = renderJournalEmpty("Leave a conversation to record it here.");
    return;
  }

  ui.locationName.textContent = snapshot.location.name;
  ui.locationMeta.textContent = renderLocationMeta(snapshot);
  ui.locationDescription.textContent = snapshot.location.floor_number
    ? `${snapshot.location.description} Floor ${snapshot.location.floor_number}.`
    : snapshot.location.description;
  renderMap({
    stage: ui.viewportPixiStage,
    fallback: ui.viewport,
    lines: snapshot.map_view,
    metadata: snapshot.map_metadata ?? null,
    transition: state.viewportTransition,
    onTransitionComplete: state.presentationLock?.transition === "combat-exit"
      ? () => onViewportTransitionComplete?.(state.presentationLock?.token ?? 0)
      : undefined,
  });
  ui.overworldMap.innerHTML = renderOverworldMap(snapshot.overworld_map ?? null);
  ui.inventoryList.innerHTML = renderInventory(snapshot);
  ui.questList.innerHTML = renderQuestList(snapshot);
  ui.npcList.innerHTML = renderNpcList(snapshot, state.selectedNpcId);
  ui.questChoicePanel.innerHTML = renderQuestChoicePanel(snapshot, state.selectedNpcId);
  ui.combatOverlay.hidden = !snapshot.in_combat || !snapshot.combat_state;
  applyCombatOverlayUpdate(ui.combatOverlay, snapshot);
  ui.combatActions.innerHTML = snapshot.in_combat && snapshot.combat_state ? renderCombatActions(snapshot) : "";

  ui.dialogueLog.innerHTML = renderUnifiedTranscript(snapshot, state);

  ui.dialogueLog.scrollTop = ui.dialogueLog.scrollHeight;

  ui.outcomeLog.textContent = snapshot.outcome_summary
    ? renderOutcome(snapshot)
    : "No completed run yet.";
  ui.journalList.innerHTML = renderJournal(snapshot);
}
