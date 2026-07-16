// Barrel: public re-export surface of the pinball package.
export { CABINET_SPECS } from "./cabinet";
export type {
	CabinetWallDef,
	CabinetFlipperDef,
	CabinetSpec,
} from "./cabinet";

export { BIOME_CONFIGS } from "./biomes";
export type {
	BiomePegConfig,
	BiomePhysics,
	BiomeTheme,
	BiomeConfig,
} from "./biomes";

export { generatePinballTable } from "./table";
export type {
	BumperShape,
	PlacedPeg,
	ObstacleSpec,
	WeakPointSpec,
	PinballTableLayout,
} from "./types";
