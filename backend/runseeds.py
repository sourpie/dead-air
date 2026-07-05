"""Per-run memory seeds — turns a generated case into first-person memories.

`build_seeds(case)` returns {dataset_name: [memory strings]} for one run. Each
dataset is written with ONE cognee remember() call (memory.seed_run), so a full
run costs 7 graph-extraction passes.

THE critical safety rule lives here: the culprit's dataset gets their cover
story, their resentment and diffuse guilt — but NEVER the sabotage act itself.
Retrieval cannot leak what was never stored; the generated validator gates are
the backstop, and both fail only into fallback lines.
"""
from crew import CREW, LORE_DATASET, datasets_for, own_dataset  # noqa: F401
from mystery import CREW_IDS, CREW_NAMES, FIRST_NAMES, ROOMS, SLOT_TIMES

# Persona background lines, seeded into each crew member's own dataset every
# run (they anchor the voice; the case facts change around them).
BACKGROUND = {
    "oda": [
        "I am Captain Oda, commander of station K-7. Twenty-two years of service without a black mark.",
        "I run this station by the book because the book is what keeps people breathing in space.",
        "Gossip is corrosion. I shut it down wherever I find it.",
    ],
    "vega": [
        "I am Vega, station engineer. Every system on K-7 runs because I don't sleep enough.",
        "Whenever anything breaks, everyone looks at me first. I am sick of being the default suspect.",
        "I file fault reports nobody reads. I keep copies.",
    ],
    "lin": [
        "I am Lin, the station medic. I know everyone's blood type and most of their secrets.",
        "I barely sleep. At night I wander — tea in the cafeteria, stars through the viewport.",
        "The crew is my patient. All of it, together.",
    ],
    "rio": [
        "I am Rio, comms officer. Everything said on this station eventually crosses my board.",
        "A good story is worth two dull facts. I might polish; I never invent.",
        "I hear everything and forget nothing. Ask nicely.",
    ],
    "nova": [
        "I am Nova, science chief. My samples are worth more than this station's hull.",
        "Command passed me over for station lead. I remember exactly who voted how.",
        "I answer questions with questions. Habit worth keeping.",
    ],
}

# Permanent lore — seeded ONCE ever (ask.py --seed-lore), shared by all crew.
LORE_SEEDS = [
    "Station K-7 is a six-room orbital research station: Cafeteria, MedBay, Engine Room, Storage, Comms, and Crew Quarters, joined by a central corridor.",
    "K-7's crew of five: Captain Oda (command), Engineer Vega (systems), Medic Lin (medbay), Comms Officer Rio (communications), Science Chief Nova (research).",
    "Every door on K-7 logs entries and exits to the ops console in Comms.",
    "Resupply shuttles dock monthly. Between shuttles, the station is alone in the dark.",
]


def build_seeds(case: dict) -> dict:
    """{dataset: [lines]} for one run: 5 crew datasets + rumours + player_profile."""
    run_id = case["runId"]
    culprit = case["culpritId"]
    herring = case["herringId"]
    witness = case["witnessId"]
    sab = case["sabotage"]
    scene_name = ROOMS[sab["room"]].lower()

    # Absolute date anchor so temporal_cognify can place the night's events on a
    # real timeline (Event/Timestamp nodes) rather than bare times-of-day.
    incident_date = "2149-03-12"
    morning_after = (
        f"On the morning of {incident_date}, the {sab['name']} in the {scene_name} was "
        f"found deliberately sabotaged during the night of {incident_date}. An "
        f"investigator arrived on the shuttle. The whole crew is on edge."
    )

    seeds: dict[str, list[str]] = {}
    for npc in CREW_IDS:
        lines = list(BACKGROUND[npc])
        lines.append(morning_after)

        if npc == culprit:
            # Cover story + motive + diffuse guilt. NEVER the act itself.
            lines.append(f"If anyone asks about that night: {case['coverStory']}")
            lines.append(f"I keep turning it over in my head: {case['motive']}. Nobody sees it that way but me.")
            lines.append("I haven't slept properly since. Every alarm makes my chest tight.")
            lines.append("The investigator cannot be allowed to pull the thread. Stay calm. Stick to the story.")
        elif npc == herring:
            h = case["herring"]
            lines.append(f"That night around {SLOT_TIMES[h['slot']]} I was in the {ROOMS[h['room']].lower()}. {h['secret']}. Nobody can know.")
            lines.append(f"If anyone asks where I was: {h['claim']} If pressed, say I was {h['excuse']}.")
        else:
            # Innocents: their true night, plainly remembered.
            for slot in range(len(SLOT_TIMES)):
                room = case["timeline"][slot][npc]
                if room != "quarters":
                    text = _excursion_text(case, npc, slot, room)
                    lines.append(f"Around {SLOT_TIMES[slot]}: {text}")

        if npc == witness:
            lines.append(case["witness"]["reason"])
            lines.append(case["witness"]["sighting"] + " I have not decided who to tell.")

        seeds[own_dataset(npc, run_id)] = lines

    seeds[f"{run_id}_rumours"] = [
        f"There is talk on K-7 that the {sab['name']} did not fail on its own — someone with tools and access cut it.",
        "The crew has started watching each other in the corridors.",
    ]
    seeds[f"{run_id}_player_profile"] = [
        f"An investigator arrived on the morning shuttle to find out who sabotaged the {sab['name']}.",
    ]
    return seeds


def _excursion_text(case: dict, npc: str, slot: int, room: str) -> str:
    exc = case["excursions"].get(npc)
    if exc and exc["slot"] == slot:
        return exc["text"]
    if npc == case["witnessId"] and room == case["witness"]["room"]:
        return case["witness"]["reason"]
    return f"I stepped out to the {ROOMS[room].lower()} for a while. Quiet night, or so I thought."
