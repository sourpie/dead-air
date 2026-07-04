"""Shift simulation for DEAD AIR — who is where, and who talks to whom.

The backend owns time as 4 discrete shifts. The whole day's schedule is
precomputed at run start from a seed-derived RNG and persisted in game state:
per-shift room positions for all five crew, plus 2 encounters per shift where a
pair meets and talks. Case-critical gossip (the witness sighting, the motive
rumour) is guaranteed to be carried by encounters in shifts 0-2, so eavesdropping
is a real alternate route to the evidence.

The client animates within a shift on its own clock using the `moves` we emit;
the backend never tracks wall-time. Information transfer (memory writes) fires
deterministically when a shift ends — whether or not the player overheard.
Verbatim dialogue is generated lazily, only on overhear (interview.py).
"""
import random

from mystery import ADJACENCY, CREW_IDS, POSTS

N_SHIFTS = 4
SHIFT_NAMES = ["MORNING SHIFT", "MIDDAY", "EVENING", "NIGHT WATCH"]
SHIFT_SECONDS = 360          # client animation window per shift
# Three staggered windows so the crew keeps talking throughout the shift
# instead of going silent after the first two minutes. An NPC may appear in
# multiple windows, never twice in the same one.
ENCOUNTER_WINDOWS = [(20, 70), (140, 190), (260, 310)]
WALK_LEAD = 8                # seconds before startSec the walkers set off

# Non-case small talk for encounters beyond the authored gossip topics.
# Ledger-only: never written to cognee (cost control), never grants clues.
SMALL_TALK = [
    "They traded complaints about the ration packs tasting like insulation foam.",
    "They argued about whose turn it is to recalibrate the gravity ring.",
    "They swapped theories about the strange noise the air ducts make at night.",
    "They reminisced about the last supply shuttle and the coffee it brought.",
]


def build_schedule(case: dict) -> dict:
    """Precompute positions, encounters and client move plans for all 4 shifts."""
    rng = random.Random(f"{case['seed']}:sched")

    # ---- positions: post by default, occasional wander ----------------------- #
    positions = []
    for shift in range(N_SHIFTS):
        rooms = {}
        for npc in CREW_IDS:
            if rng.random() < 0.3:
                rooms[npc] = rng.choice(ADJACENCY[POSTS[npc]])
            else:
                rooms[npc] = POSTS[npc]
        positions.append(rooms)

    # ---- encounters: 2 per shift, disjoint pairs ------------------------------ #
    # Critical topics are placed first, on shifts 0-2, with their knower present.
    critical = [t for t in case["gossipTopics"] if t["critical"]]
    flavor = [t for t in case["gossipTopics"] if not t["critical"]]
    rng.shuffle(flavor)
    flavor_pool = flavor + [{"id": f"small_talk_{i}", "knower": None, "clueId": None,
                             "critical": False, "text": txt}
                            for i, txt in enumerate(SMALL_TALK)]

    critical_shifts = rng.sample(range(3), len(critical))
    encounters = []
    # One encounter (one pair) per window slot; slots don't overlap in time,
    # so the same NPC may talk in several slots of one shift.
    filled = {}  # (shift, slot) -> pair

    for topic, shift in zip(critical, critical_shifts):
        knower = topic["knower"]
        partner = rng.choice([n for n in CREW_IDS if n != knower])
        pair = [knower, partner]
        filled[(shift, 0)] = pair
        encounters.append(_make_encounter(rng, case, shift, len(encounters), pair,
                                          positions[shift], topic, slot=0))

    fi = 0
    for shift in range(N_SHIFTS):
        for slot in range(len(ENCOUNTER_WINDOWS)):
            if (shift, slot) in filled:
                continue
            pair = rng.sample(CREW_IDS, 2)
            filled[(shift, slot)] = pair
            topic = flavor_pool[fi % len(flavor_pool)]
            fi += 1
            encounters.append(_make_encounter(rng, case, shift, len(encounters), pair,
                                              positions[shift], topic, slot=slot))

    encounters.sort(key=lambda e: (e["shift"], e["startSec"]))

    schedule = {
        "shiftNames": SHIFT_NAMES,
        "shiftSeconds": SHIFT_SECONDS,
        "positions": positions,
        "encounters": encounters,
    }
    _assert_schedule(case, schedule)
    return schedule


def _make_encounter(rng, case, shift, idx, pair, rooms, topic, slot):
    room = rooms[rng.choice(pair)]
    start, end = ENCOUNTER_WINDOWS[min(slot, len(ENCOUNTER_WINDOWS) - 1)]
    return {
        "id": f"enc_{shift}_{idx}",
        "shift": shift,
        "room": room,
        "npcs": list(pair),
        "startSec": start,
        "endSec": end,
        # secret half — stripped from the client payload by gamestate.public_state
        "topicId": topic["id"],
        "topicText": topic["text"],
        "clueId": topic.get("clueId"),
        "critical": topic.get("critical", False),
    }


def shift_plan(schedule: dict, shift: int) -> dict:
    """The client-facing plan for one shift: positions, walk moves, encounter
    windows. Topic/clue payloads are deliberately absent — overhearing is the
    only way to learn what was said."""
    positions = schedule["positions"][shift]
    encounters = [e for e in schedule["encounters"] if e["shift"] == shift]

    moves = []
    for e in encounters:
        for npc in e["npcs"]:
            if positions[npc] != e["room"]:
                moves.append({"npcId": npc, "atSec": max(0, e["startSec"] - WALK_LEAD),
                              "toRoom": e["room"]})
            moves.append({"npcId": npc, "atSec": e["endSec"], "toRoom": positions[npc]})
    moves.sort(key=lambda m: m["atSec"])

    return {
        "shift": shift,
        "shiftName": SHIFT_NAMES[shift],
        "shiftSeconds": SHIFT_SECONDS,
        "positions": positions,
        "moves": moves,
        "encounters": [
            {"id": e["id"], "room": e["room"], "npcs": e["npcs"],
             "startSec": e["startSec"], "endSec": e["endSec"]}
            for e in encounters
        ],
    }


def find_encounter(schedule: dict, encounter_id: str) -> dict | None:
    return next((e for e in schedule["encounters"] if e["id"] == encounter_id), None)


def in_earshot(player_room: str, encounter_room: str) -> bool:
    """Overhear rule: same room or an adjacent one."""
    return player_room == encounter_room or player_room in ADJACENCY.get(encounter_room, [])


def _assert_schedule(case: dict, schedule: dict) -> None:
    for shift in range(N_SHIFTS):
        rooms = schedule["positions"][shift]
        assert set(rooms) == set(CREW_IDS), "every crew member needs a room each shift"
        # windows within a shift must not overlap (an NPC can appear in several,
        # but only if the slots are sequential)
        in_shift = sorted((e for e in schedule["encounters"] if e["shift"] == shift),
                          key=lambda e: e["startSec"])
        for a, b in zip(in_shift, in_shift[1:]):
            assert a["endSec"] < b["startSec"], "encounter windows must not overlap"
    crit = [e for e in schedule["encounters"] if e["critical"]]
    assert len(crit) >= 2, "case-critical gossip must be schedulable"
    assert all(e["shift"] <= 2 for e in crit), "critical gossip must land before the last shift"
    topics = {t["id"]: t for t in case["gossipTopics"]}
    for e in crit:
        knower = topics[e["topicId"]]["knower"]
        assert knower in e["npcs"], "the knower must be present to share their gossip"
