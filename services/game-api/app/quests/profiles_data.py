"""Static profile data and constants for quest profiles."""

from .profiles import QuestProfile

QUEST_TRIGGER_TERMS = (
    "help",
    "job",
    "quest",
    "work",
    "errand",
    "task",
    "need",
    "missing",
    "find",
    "recover",
    "retrieve",
    "fetch",
    "looking for",
)

TITLE_TEMPLATES = (
    "Recover the {item_name}",
    "Bring Back the {item_name}",
    "Find {npc_name}'s {item_name}",
)

SUMMARY_TEMPLATES = (
    "{npc_name} asked you to recover the {item_name}, last seen in the {biome_name}, and return it intact.",
    "A missing keepsake lies somewhere in the {biome_name}. {npc_name} wants it brought back before the dungeon ruins it completely.",
    "{npc_name} believes the {item_name} was dragged into the {biome_name}. Recover it and bring it back in person.",
)

OFFER_TEMPLATES = (
    "If you're heading into the {biome_name}, acquire my lost {item_label} and bring it back to me.",
    "One thing more: my {item_label} vanished into the {biome_name}. Bring it back if you can.",
    "Do a piece of work for me. Recover my {item_label} from the {biome_name} and return it here.",
)

ACCEPT_TEMPLATES = (
    "Good. Recover the {item_name} from the {biome_name} and bring it straight back to me.",
    "Then we understand each other. Find the {item_name} in the {biome_name} and return with it.",
)

DECLINE_TEMPLATES = (
    "Leave it, then. I will find another way to bear the loss.",
    "Fair enough. Better a refusal than a promise made loosely.",
)

COMPLETE_TEMPLATES = (
    "You brought it back. I'll see this kept safe, and {reward_gold} gold is yours.",
    "That is the one. You have my thanks, and {reward_gold} gold for bringing it home.",
)

BIOME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "ancient_halls": (
        "ancient halls",
        "halls",
        "hall",
        "first descent",
        "approach",
        "shrine",
        "stone halls",
    ),
    "sunken_archive": (
        "sunken archive",
        "archive",
        "archives",
        "flooded archive",
        "whispering cave",
        "cave",
        "flooded stair",
        "drowned vault",
    ),
}

NPC_BIOME_PREFERENCES: dict[str, tuple[str, ...]] = {
    "marta-innkeeper": ("sunken_archive", "ancient_halls"),
    "ilya-lamplighter": ("ancient_halls", "sunken_archive"),
    "petra-scout": ("ancient_halls", "sunken_archive"),
    "sava-herbalist": ("sunken_archive", "ancient_halls"),
}


QUEST_PROFILES: dict[str, tuple[QuestProfile, ...]] = {
    "marta-innkeeper": (
        QuestProfile(
            item_id="marta_ledger_satchel",
            target_biome_id="sunken_archive",
            target_floor_number=1,
            reward_gold=18,
            hint="Drowned scribes drag satchels toward the first flooded shelves.",
            offer_templates=(
                "If you're heading into the {biome_name}, acquire my lost {item_label} and bring it back to me.",
                "My {item_label} went missing in the {biome_name}. Bring it back before the damp ruins the whole account book.",
            ),
            complete_templates=(
                "You brought the {item_name} back dry enough to save. Take {reward_gold} gold for the trouble.",
                "Good. The house can keep its books another week. {reward_gold} gold, as promised.",
            ),
        ),
        QuestProfile(
            item_id="marta_cellar_key",
            target_biome_id="ancient_halls",
            target_floor_number=1,
            reward_gold=15,
            hint="Old bronze keys end up in rubble pockets where wardens used to stand watch.",
            offer_templates=(
                "There is another thing. My old cellar key vanished into the {biome_name}. Recover it if you pass that way.",
                "Bring me back my {item_label} from the {biome_name}. I'd rather not lose another storehouse to a bad latch.",
            ),
            complete_templates=(
                "That key still turns, by the look of it. Take {reward_gold} gold and my thanks.",
                "You saved me a locksmith and a great deal of cursing. {reward_gold} gold for you.",
            ),
        ),
    ),
    "ilya-lamplighter": (
        QuestProfile(
            item_id="ilya_lost_lamp",
            target_biome_id="ancient_halls",
            target_floor_number=1,
            reward_gold=16,
            hint="Bright things tend to end up near collapsed shrines on the first descent.",
            offer_templates=(
                "If you descend into the {biome_name}, acquire my lost {item_label} and bring it back lit or dark, I don't care which.",
                "My {item_label} is still somewhere in the {biome_name}. Find it and return it before the dark claims it entirely.",
            ),
            complete_templates=(
                "There it is. I know the weight of it even cold. {reward_gold} gold is yours.",
                "You carried a little light back with you. Take {reward_gold} gold for the effort.",
            ),
        ),
        QuestProfile(
            item_id="ilya_watch_oil",
            target_biome_id="sunken_archive",
            target_floor_number=1,
            reward_gold=17,
            hint="Oil flasks drift toward the archive shelves where the seep runs blackest.",
            offer_templates=(
                "A sealed flask of watch oil went missing in the {biome_name}. Bring the {item_label} back if you find it.",
                "Recover my {item_label} from the {biome_name}. Without it, half the square burns dirty by dusk.",
            ),
            complete_templates=(
                "Still sealed. Good. This will keep the square burning another few nights. {reward_gold} gold.",
                "That oil matters more than it looks. Take {reward_gold} gold and keep your own flame close.",
            ),
        ),
    ),
    "petra-scout": (
        QuestProfile(
            item_id="petra_scout_compass",
            target_biome_id="ancient_halls",
            target_floor_number=1,
            reward_gold=20,
            hint="Watch the first side chambers. Sentinels collect dropped field gear.",
            offer_templates=(
                "One of my route runs ended badly in the {biome_name}. Bring back my {item_label} if you see it.",
                "Find my {item_label} in the {biome_name} and bring it back. I trust the mark cuts on the casing more than memory.",
            ),
            complete_templates=(
                "Good. I can chart with this again. {reward_gold} gold for bringing it back.",
                "That compass still holds true. You've earned {reward_gold} gold.",
            ),
        ),
        QuestProfile(
            item_id="petra_route_case",
            target_biome_id="sunken_archive",
            target_floor_number=1,
            reward_gold=19,
            hint="Map cases snag under flooded desks and broken shelf braces.",
            offer_templates=(
                "My {item_label} slipped away in the {biome_name}. Recover it before the damp turns the route notes to pulp.",
                "If you push into the {biome_name}, keep an eye out for my {item_label} and bring it straight back.",
            ),
            complete_templates=(
                "The notes inside might still be readable. That's worth {reward_gold} gold to me.",
                "You saved the routes and a week's work with them. Take {reward_gold} gold.",
            ),
        ),
    ),
    "sava-herbalist": (
        QuestProfile(
            item_id="sava_spore_case",
            target_biome_id="sunken_archive",
            target_floor_number=1,
            reward_gold=22,
            hint="Specimen cases sink where the waterline meets broken reading desks.",
            offer_templates=(
                "Recover my {item_label} from the {biome_name}. I want those samples before the mold changes them.",
                "The {biome_name} took my {item_label}. Bring it back intact and I'll make it worth the trip.",
            ),
            complete_templates=(
                "Still sealed. Good. The samples may yet tell the truth. {reward_gold} gold for you.",
                "You kept the spores uncontaminated. That earns {reward_gold} gold and real gratitude.",
            ),
        ),
        QuestProfile(
            item_id="sava_amber_vial",
            target_biome_id="ancient_halls",
            target_floor_number=1,
            reward_gold=21,
            hint="Glass vials catch in cracked flagstones where shrine dust has settled thickest.",
            offer_templates=(
                "Bring back my {item_label} from the {biome_name}. The resin inside matters more than the glass.",
                "I lost an {item_label} in the {biome_name}. Recover it before the seal gives out.",
            ),
            complete_templates=(
                "Unbroken. Better than I expected. Take {reward_gold} gold for returning it.",
                "That vial could have shattered a dozen times over. {reward_gold} gold says I know the value of what you did.",
            ),
        ),
    ),
}
