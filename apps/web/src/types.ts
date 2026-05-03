export type Snapshot = {
  run_id: string;
  player_name: string;
  location: {
    id: string;
    name: string;
    description: string;
    floor_number?: number;
    biome_id?: string;
  };
  stats: {
    hp: number;
    max_hp: number;
    gold: number;
  };
  facing: string;
  message: string;
  first_person_view: string[];
  minimap: string[];
  nearby_npcs: Array<{
    id: string;
    display_name: string;
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
  combat_state?: {
    enemy_id: string;
    enemy_name: string;
    enemy_hp: number;
    enemy_max_hp: number;
    round: number;
    log: string[];
  } | null;
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
  dialogue?: {
    npc_id: string;
    npc_name: string;
    text: string;
    source: string;
  };
};

export type AppState = {
  bootstrapTitle: string;
  runId: string;
  snapshot: Snapshot | null;
  selectedNpcId: string;
  busy: boolean;
};