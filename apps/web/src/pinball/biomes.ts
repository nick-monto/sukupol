// ---------------------------------------------------------------------------
// Biome types
// ---------------------------------------------------------------------------

export interface BiomePegConfig {
	/** Total peg budget per table — each placed peg costs from this pool */
	pegBudget: number;
	/** Cost per post obstacle (usually 1) */
	postCost: number;
	/** Cost per bumper obstacle (usually 2) */
	bumperCost: number;
	/** Cost multiplier per enemy obstacle peg (usually 1, distinct from postCost for clarity) */
	enemyPegCost: number;
	/** Number of bonus bumpers to place alongside weapon orbs */
	bonusBumpers: number;
}

export interface BiomePhysics {
	gravity: number;
	ballDrag: number;
	bumperRestitution: number;
}

export interface BiomeTheme {
	bg: string;
	walls: string;
	orbs: string;
	orbHit: string;
	paddle: string;
	ball: string;
	weakPoint: string;
	obstacle: string;
	obstacleStyle: "bones" | "moss" | "stone" | "archive" | "default";
}

export interface BiomeConfig {
	cabinetId: string;
	physics: BiomePhysics;
	theme: BiomeTheme;
	pegConfig: BiomePegConfig;
}

// ---------------------------------------------------------------------------
// Biome configs
// ---------------------------------------------------------------------------

export const BIOME_CONFIGS: Record<string, BiomeConfig> = {
	ashen_fields: {
		cabinetId: "standard",
		physics: { gravity: 0.95, ballDrag: 0.005, bumperRestitution: 1.5 },
		theme: {
			bg: "#212529",
			walls: "#C4CFD4",
			orbs: "#5C43B5",
			orbHit: "#B09150",
			paddle: "#f5a02e",
			ball: "#dee2e6",
			weakPoint: "#E8C547",
			obstacle: "#9B6B8A",
			obstacleStyle: "default",
		},
		pegConfig: {
			pegBudget: 24,
			postCost: 1,
			bumperCost: 2,
			enemyPegCost: 1,
			bonusBumpers: 3,
		},
	},
	whispering_caverns: {
		cabinetId: "narrow",
		physics: { gravity: 0.85, ballDrag: 0.008, bumperRestitution: 1.3 },
		theme: {
			bg: "#141C14",
			walls: "#4A6741",
			orbs: "#2E6B3A",
			orbHit: "#7DC980",
			paddle: "#5E8C5E",
			ball: "#C8DFC8",
			weakPoint: "#B0E84A",
			obstacle: "#6BAA55",
			obstacleStyle: "moss",
		},
		pegConfig: {
			pegBudget: 28,
			postCost: 1,
			bumperCost: 2,
			enemyPegCost: 1,
			bonusBumpers: 3,
		},
	},
	ancient_halls: {
		cabinetId: "wide",
		physics: { gravity: 0.9, ballDrag: 0.004, bumperRestitution: 1.4 },
		theme: {
			bg: "#1E1A14",
			walls: "#9E8B6E",
			orbs: "#7A5F3A",
			orbHit: "#D4A843",
			paddle: "#C4985A",
			ball: "#E8D5B0",
			weakPoint: "#F0C060",
			obstacle: "#A87B44",
			obstacleStyle: "stone",
		},
		pegConfig: {
			pegBudget: 26,
			postCost: 1,
			bumperCost: 2,
			enemyPegCost: 1,
			bonusBumpers: 3,
		},
	},
	sunken_archive: {
		cabinetId: "tall",
		physics: { gravity: 1.05, ballDrag: 0.012, bumperRestitution: 1.6 },
		theme: {
			bg: "#0A1520",
			walls: "#1E4060",
			orbs: "#1A4A6E",
			orbHit: "#4AB8D8",
			paddle: "#3A84A0",
			ball: "#A8D8E8",
			weakPoint: "#40E0C0",
			obstacle: "#2A7080",
			obstacleStyle: "archive",
		},
		pegConfig: {
			pegBudget: 30,
			postCost: 1,
			bumperCost: 2,
			enemyPegCost: 1,
			bonusBumpers: 3,
		},
	},
};

const DEFAULT_BIOME = BIOME_CONFIGS["ashen_fields"];
export { DEFAULT_BIOME };
