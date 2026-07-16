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

export type PinballDescriptor = {
	biome_id: string;
	floor_seed: number;
	enemy_id: string;
	enemy_pinball: {
		obstacles?: ObstacleTemplate[];
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

export type PresentationLock = {
	transition: "combat-exit";
	combatState: CombatState;
	token: number;
	startedAt: number;
};
