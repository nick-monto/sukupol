declare module "*.css";

declare module "matter-attractors" {
	const plugin: unknown;
	export default plugin;
}

interface ImportMetaEnv {
	readonly VITE_API_BASE?: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
