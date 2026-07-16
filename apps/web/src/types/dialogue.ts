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
