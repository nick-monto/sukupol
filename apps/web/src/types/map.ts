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

export type ViewportTransition =
	| "none"
	| "combat-enter"
	| "combat-impact"
	| "combat-exit";
