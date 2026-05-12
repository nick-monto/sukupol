export type MapTone = "wall" | "floor" | "decor" | "exit" | "player" | "npc";

export type MapCell = {
  x: number;
  y: number;
  glyph: string;
  tone: MapTone;
};

export type MapMetadata = {
  width: number;
  height: number;
  player_x?: number;
  player_y?: number;
  cells: MapCell[];
};

export type CombatState = {
  enemy_id: string;
  enemy_name: string;
  enemy_ascii_art?: string[];
  enemy_hp: number;
  enemy_max_hp: number;
  round: number;
  log: string[];
};

export type ViewportTransition =
  | "none"
  | "combat-enter"
  | "combat-impact"
  | "combat-exit";

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
  dialogue?: {
    npc_id: string;
    npc_name: string;
    text: string;
    source: string;
  };
};

export type DialogueMessage = {
  id: string;
  speaker: "player" | "npc" | "system";
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
  selectedNpcId: string;
  dialogueThreads: Record<string, DialogueMessage[]>;
  streamingDialogue: {
    npc_id: string;
    npc_name: string;
    source: string;
    text: string;
  } | null;
  viewportTransition: ViewportTransition;
  busy: boolean;
};