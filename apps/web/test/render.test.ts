/** Minimal smoke test for renderApp — asserts DOM classes/content are set.
 *
 * Pixi.js requires WebGL (unavailable in jsdom), but the render map
 * loader catches Pixi failures gracefully, so renderApp does not throw.
 */

import { describe, it, expect } from "vitest";
import type { UiElements } from "../src/ui";
import type { AppState, Snapshot } from "../src/types";
import { renderApp } from "../src/render";

function createMockUi(): UiElements {
	return {
		shell: document.createElement("div"),
		topHud: document.createElement("div"),
		areaBanner: document.createElement("div"),
		bottomHud: document.createElement("div"),
		launchPanel: document.createElement("div"),
		launchMessage: document.createElement("p"),
		playerNameInput: document.createElement("input") as HTMLInputElement,
		launchRunButton: document.createElement("button") as HTMLButtonElement,
		heroPanel: document.createElement("div"),
		viewportPanel: document.createElement("div"),
		journalPanel: document.createElement("div"),
		mapPanel: document.createElement("div"),
		inventoryPanel: document.createElement("div"),
		journalToggleButton: document.createElement("button") as HTMLButtonElement,
		mapToggleButton: document.createElement("button") as HTMLButtonElement,
		inventoryToggleButton: document.createElement("button") as HTMLButtonElement,
		dialogueToggleButton: document.createElement("button") as HTMLButtonElement,
		contextDrawer: document.createElement("div"),
		chatResizeHandle: document.createElement("button") as HTMLButtonElement,
		actionPanel: document.createElement("div"),
		outcomePanel: document.createElement("div"),
		startRunButton: document.createElement("button") as HTMLButtonElement,
		extractRunButton: document.createElement("button") as HTMLButtonElement,
		expeditionSignal: document.createElement("p"),
		heroSummary: document.createElement("div"),
		viewport: document.createElement("pre"),
		viewportPixiStage: document.createElement("div"),
		combatOverlay: document.createElement("div"),
		dialogueLog: document.createElement("div"),
		locationName: document.createElement("h2"),
		locationMeta: document.createElement("p"),
		locationDescription: document.createElement("p"),
		npcList: document.createElement("div"),
		inventoryList: document.createElement("div"),
		overworldMap: document.createElement("div"),
		questList: document.createElement("div"),
		sendMessageButton: document.createElement("button") as HTMLButtonElement,
		leaveConversationButton: document.createElement("button") as HTMLButtonElement,
		playerMessage: document.createElement("textarea") as HTMLTextAreaElement,
		questChoicePanel: document.createElement("div"),
		combatActions: document.createElement("div"),
		outcomeTitle: document.createElement("h3"),
		outcomeNote: document.createElement("p"),
		outcomeLog: document.createElement("pre"),
		journalList: document.createElement("div"),
	};
}

const MINIMAL_SNAPSHOT: Snapshot = {
	run_id: "test-run-1",
	player_name: "Tester",
	location: {
		id: "town_square",
		name: "Town Square",
		description: "The central square of the settlement.",
		type: "town",
		encounter_enabled: false,
	},
	position: { x: 3, y: 5 },
	stats: { hp: 20, max_hp: 20, gold: 10 },
	facing: "N",
	message: "You stand in the town square.",
	map_view: [
		"#########",
		"#.......#",
		"#.#...#.#",
		"#.......#",
		"#........",
		"#.......#",
		"#.......#",
		"#.#...#.#",
		"#########",
	],
	map_metadata: null,
	dialogue: undefined,
	overworld_map: null,
	nearby_npcs: [
		{
			id: "marta-innkeeper",
			display_name: "Marta",
			ascii_art: ["@@"],
			role: "innkeeper",
			distance: 1,
		},
	],
	inventory: [],
	equipped_weapon: null,
	in_combat: false,
	combat_state: null,
	run_result: null,
	run_depth: 0,
	enemies_defeated: 0,
	outcome_summary: null,
	progression: null,
	journal: [],
	quests: [],
};

function minimalState(overrides?: Partial<AppState>): AppState {
	return {
		bootstrapTitle: "Sukupol",
		runId: "test-run-1",
		snapshot: MINIMAL_SNAPSHOT,
		journalOpen: false,
		mapOpen: false,
		inventoryOpen: false,
		dialogueOpen: false,
		selectedNpcId: "",
		dialogueThreads: {},
		streamingDialogue: null,
		messageSequence: 0,
		viewportTransition: "none",
		presentationLock: null,
		presentationToken: 0,
		busy: false,
		...overrides,
	};
}

describe("renderApp", () => {
	it("does not throw when called with a valid snapshot", () => {
		const ui = createMockUi();
		const state = minimalState();

		expect(() => renderApp(ui, state)).not.toThrow();
	});

	it("sets location name from snapshot", () => {
		const ui = createMockUi();
		const state = minimalState();

		renderApp(ui, state);
		expect(ui.locationName.textContent).toBe("Town Square");
	});

	it("sets expedition signal from snapshot", () => {
		const ui = createMockUi();
		const state = minimalState();

		renderApp(ui, state);
		expect(ui.expeditionSignal.textContent).toBeTruthy();
	});

	it("renders fallback map viewport for snapshot", () => {
		const ui = createMockUi();
		const state = minimalState();

		renderApp(ui, state);
		// The fallback <pre> should have the map text
		expect(ui.viewport.textContent).toContain("#########");
	});

	it("renders empty state when snapshot is null", () => {
		const ui = createMockUi();
		const state = minimalState({ snapshot: null });

		expect(() => renderApp(ui, state)).not.toThrow();
		expect(ui.locationName.textContent).toBe("No run started");
		expect(ui.viewport.textContent).toBe(
			"Stand up the backend and begin a run.",
		);
	});
});
