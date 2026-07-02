export type MapTone = "wall" | "floor" | "decor" | "exit" | "player" | "npc";

export type MapCell = {
	x: number;
	y: number;
	glyph: string;
	tone: MapTone;
	variant?: string;
};

export type MapMetadata = {
	width: number;
	height: number;
	player_x?: number;
	player_y?: number;
	cells: MapCell[];
};

export type OverworldMapNode = {
	id: string;
	name: string;
	x: number;
	y: number;
	discovered: boolean;
};

export type OverworldMapConnection = {
	location_ids: [string, string];
	discovered: boolean;
};

export type OverworldMap = {
	current_location_id: string | null;
	nodes: OverworldMapNode[];
	connections: OverworldMapConnection[];
};

export type CombatPresentation = {
	mode: "ascii";
	ascii_art: string[];
};

export type CombatAction = {
	id: string;
	label: string;
	kind: "attack" | "defend" | "item" | "flee" | "parley";
	enabled: boolean;
	item_id?: string | null;
};

export type CombatEvent = {
	id: string;
	round: number;
	actor: "player" | "enemy" | "ally" | "system";
	text: string;
	emphasis:
		| "entry"
		| "impact"
		| "guard"
		| "item"
		| "system"
		| "warning"
		| "support"
		| "parley";
};

export type CombatNegotiationOption = {
	id: string;
	label: string;
	outcome: "recruit" | "tribute" | "retreat";
	enabled: boolean;
};

export type CombatNegotiationEntry = {
	speaker: "player" | "enemy" | "system";
	text: string;
};

export type CombatNegotiationState = {
	communication_mode: "speech" | "telepathy";
	temperament: "wary" | "resentful" | "irate";
	available: boolean;
	channel_ready?: boolean;
	locked: boolean;
	active: boolean;
	attempts: number;
	anger: number;
	anger_limit: number;
	leverage: number;
	difficulty: number;
	lock_reason: string;
	active_intent?: string | null;
	outcome?: string | null;
	options: CombatNegotiationOption[];
	transcript: CombatNegotiationEntry[];
};

export type CombatPartySlot = {
	slot_id: string;
	name: string;
	role: string;
	hp: number;
	max_hp: number;
	attack: number;
	defence: number;
	is_player: boolean;
	is_active: boolean;
	reserve: boolean;
};

export type CombatEnemy = {
	id: string;
	name: string;
	hp: number;
	max_hp: number;
	attack: number;
	defence: number;
	presentation: CombatPresentation;
};

// Peg-based pinball obstacle system
export type PegDef = {
	angle: number; // radians, 0 = right (east)
	distance: number; // px from obstacle center; 0 = centered
	radius: number; // collision radius of this peg
};

export type ObstacleTemplate = {
	id: string;
	label: string;
	pegs: PegDef[];
	effect?: string;
	effectValue?: number;
	scoreValue: number;
	detail?: string;
};

// Legacy type — kept for backward compat during migration
export type EnemyPinballObstacle = {
	kind: string;
	label: string;
	effect: string;
	value: number;
	detail: string;
};

export type PinballDescriptor = {
	biome_id: string;
	floor_seed: number;
	enemy_id: string;
	enemy_pinball: {
		// New peg-based format
		obstacles?: ObstacleTemplate[];
		// Legacy grid-based format — migrated at runtime
		unique_obstacles?: EnemyPinballObstacle[];
		accent?: string;
		damage_node_count?: number;
		converse_node_count?: number;
	};
};

export type CombatState = {
	mode?: "turn-based";
	status: "engaged";
	round: number;
	enemy: CombatEnemy;
	party: CombatPartySlot[];
	available_actions: CombatAction[];
	events: CombatEvent[];
	log: string[];
	negotiation?: CombatNegotiationState | null;
	pinball_descriptor?: PinballDescriptor | null;
};

export type ViewportTransition =
	| "none"
	| "combat-enter"
	| "combat-impact"
	| "combat-exit";

export type PresentationLock = {
	transition: "combat-exit";
	combatState: CombatState;
	token: number;
	startedAt: number;
};

export type Snapshot = {
	run_id: string;
	player_name: string;
	location: {
		id: string;
		name: string;
		description: string;
		floor_number?: number;
		biome_id?: string;
		type?: string;
		encounter_enabled?: boolean;
	};
	position: {
		x: number;
		y: number;
	};
	stats: {
		hp: number;
		max_hp: number;
		gold: number;
	};
	facing: string;
	message: string;
	map_view: string[];
	map_metadata?: MapMetadata | null;
	overworld_map?: OverworldMap | null;
	nearby_npcs: Array<{
		id: string;
		display_name: string;
		ascii_art: string[];
		role: string;
		distance: number;
	}>;
	inventory: Array<{
		item_id: string;
		quantity: number;
		equipped?: boolean;
		name: string;
		item_type: string;
		description: string;
	}>;
	equipped_weapon?: string | null;
	in_combat: boolean;
	combat_state?: CombatState | null;
	run_result?: string | null;
	run_depth: number;
	enemies_defeated: number;
	outcome_summary?: {
		result: string;
		depth_reached: number;
		enemies_defeated: number;
		gold_earned: number;
		items_found: Array<{
			item_id: string;
			quantity: number;
		}>;
	} | null;
	progression?: {
		total_runs: number;
		total_victories: number;
		deepest_depth: number;
		last_outcome: string;
	} | null;
	journal: Array<{
		npc_id: string;
		npc_name: string;
		entries: Array<{
			id: string;
			run_id: string;
			turn_count: number;
			visit_started_at: string;
			visit_ended_at: string;
			summary: string;
			created_at: string;
		}>;
	}>;
	quests: Array<{
		id: string;
		title: string;
		summary: string;
		objective_text: string;
		objective_kind: string;
		status: string;
		offered_by_npc_id: string;
		offered_by_npc_name: string;
		target_biome_id?: string | null;
		target_biome_name?: string | null;
		target_floor_number?: number | null;
		target_count: number;
		progress_value: number;
		progress_target: number;
		target_item_id: string;
		target_item_name: string;
		reward_gold: number;
		completion_summary?: string | null;
		can_turn_in: boolean;
		hint: string;
		offered_at?: string | null;
		accepted_at?: string | null;
		completed_at?: string | null;
		declined_at?: string | null;
		updated_at?: string | null;
	}>;
	dialogue?: {
		npc_id: string;
		npc_name: string;
		text: string;
		source: string;
	};
};

export type DialogueMessage = {
	id: string;
	sequence: number;
	speaker: "player" | "npc" | "ally" | "system";
	text: string;
	npcId?: string;
	npcName?: string;
	source?: string;
	streaming?: boolean;
};

export type AppState = {
	bootstrapTitle: string;
	runId: string;
	snapshot: Snapshot | null;
	journalOpen: boolean;
	mapOpen: boolean;
	inventoryOpen: boolean;
	dialogueOpen: boolean;
	selectedNpcId: string;
	dialogueThreads: Record<string, DialogueMessage[]>;
	streamingDialogue: {
		npc_id: string;
		npc_name: string;
		source: string;
		text: string;
	} | null;
	messageSequence: number;
	viewportTransition: ViewportTransition;
	presentationLock: PresentationLock | null;
	presentationToken: number;
	busy: boolean;
};
