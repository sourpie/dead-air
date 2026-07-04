"""Procedural mystery generator — the deterministic heart of DEAD AIR.

`generate_case(seed)` builds the complete ground truth for one run: who sabotaged
what, when, the full night timeline for all five crew, what everyone claims (the
culprit and one red-herring crew member lie), the evidence that exposes the lies,
and the per-run guardrail gates that stop the LLM leaking any of it early.

Everything is derived from `random.Random(seed)` — same seed, byte-identical case.
Pure stdlib; no cognee, no I/O. The case dict is persisted inside game_state.json
and NEVER sent raw to the client (gamestate.public_state strips the secrets).

Solvability is by construction, not by search: three independent evidence chains
are placed deliberately and asserted at the end —
  1. witness chain  — a crew member saw the culprit near the scene,
  2. physical chain — the culprit's departmental item left at the scene,
  3. alibi chain    — the culprit's cover story breaks against the door log.
"""
import random

CREW_IDS = ["oda", "vega", "lin", "rio", "nova"]

CREW_NAMES = {
    "oda": "Captain Oda",
    "vega": "Engineer Vega",
    "lin": "Medic Lin",
    "rio": "Comms Officer Rio",
    "nova": "Science Chief Nova",
}

FIRST_NAMES = {"oda": "Oda", "vega": "Vega", "lin": "Lin", "rio": "Rio", "nova": "Nova"}

# --------------------------------------------------------------------------- #
# Fixed scaffold: rooms, adjacency, night slots
# --------------------------------------------------------------------------- #

ROOMS = {
    "cafeteria": "Cafeteria",
    "medbay": "MedBay",
    "engine": "Engine Room",
    "storage": "Storage",
    "comms": "Comms",
    "quarters": "Quarters",
}

# Which rooms share a corridor segment — drives witness placement and the
# overhear "adjacent room" rule. Symmetric.
ADJACENCY = {
    "cafeteria": ["medbay", "quarters", "storage"],
    "medbay": ["cafeteria", "engine"],
    "engine": ["medbay", "storage"],
    "storage": ["cafeteria", "engine", "comms"],
    "comms": ["storage", "quarters"],
    "quarters": ["cafeteria", "comms"],
}

# The night is 6 slots. The sabotage lands in slots 1-3 (0-indexed) so there is
# always timeline before and after it for witnesses and door-log context.
SLOT_TIMES = ["22:00", "23:00", "00:00", "01:00", "02:00", "03:00"]
N_SLOTS = 6

# Sabotage-able systems, bound to the room where the damage is found.
SABOTAGE_TARGETS = [
    {"id": "coolant", "name": "coolant regulator", "room": "engine",
     "synonyms": ["coolant", "regulator", "reactor"]},
    {"id": "cryo", "name": "cryo-storage freezer", "room": "medbay",
     "synonyms": ["cryo", "freezer", "samples"]},
    {"id": "antenna", "name": "long-range antenna array", "room": "comms",
     "synonyms": ["antenna", "array", "uplink"]},
    {"id": "reclaimer", "name": "water reclaimer", "room": "storage",
     "synonyms": ["reclaimer", "water system", "filtration"]},
]

# Where each crew member is stationed during the day (shift posts).
POSTS = {
    "oda": "cafeteria",
    "vega": "engine",
    "lin": "medbay",
    "rio": "comms",
    "nova": "storage",
}

# Innocent night excursions (persona-flavored). Each: (room, first-person memory).
NIGHT_EXCURSIONS = {
    "oda": [("cafeteria", "I did a late round through the cafeteria like every night — old habit from the academy.")],
    "vega": [("engine", "I got up to check the pressure readouts. I always do when I can't sleep.")],
    "lin": [("cafeteria", "I couldn't sleep, so I made tea in the cafeteria and watched the stars for a while."),
            ("medbay", "I went back to medbay to finish labelling samples. Quiet hours are the only time it gets done.")],
    "rio": [("comms", "I was chasing a weird echo on the long-range band. Probably nothing, but it kept me up.")],
    "nova": [("storage", "I went to storage to re-check my sample crates. Nobody handles them as carefully as I do.")],
}

# Motive templates per crew member ({target} slot filled at generation).
MOTIVES = {
    "oda": [
        "the upcoming inspection of the {target} would have exposed maintenance sign-offs Oda falsified",
        "a decommission order for K-7 was coming unless a serious incident proved the station still needs a crew",
    ],
    "vega": [
        "Vega was denied the chief-engineer promotion after flagging {target} faults that nobody fixed",
        "Vega wanted to prove the {target} would fail without proper funding — and picked the loud way",
    ],
    "lin": [
        "Lin has requested a medical transfer twice; a station failure forces an evacuation home",
        "a power interruption to the {target} would erase the records of a medication accounting gap Lin has been hiding",
    ],
    "rio": [
        "the {target}'s diagnostic logs would have revealed Rio's unauthorized side-channel transmissions",
        "Rio trades station telemetry off-books; the {target} upgrade would have encrypted everything",
    ],
    "nova": [
        "Nova was passed over as station lead; a crisis under Oda's watch changes the succession",
        "the {target} downtime conveniently destroys a rival lab's experiment data",
    ],
}

# Minor innocent secrets (the red herring). Each: (room, secret text, cover excuse).
HERRING_SECRETS = {
    "oda": [("medbay", "Oda slipped into medbay at night to read crew psych files the captain is not cleared to read",
             "reviewing crew wellbeing, off the record")],
    "vega": [("storage", "Vega keeps an unauthorized still hidden behind the storage crates and was tending it",
              "checking cargo restraints, nothing more")],
    "lin": [("medbay", "Lin has been quietly taking supplies from the med locker for a private stash",
             "double-checking inventory")],
    "rio": [("comms", "Rio made an unauthorized personal transmission home on the encrypted channel",
             "routine antenna calibration")],
    "nova": [("storage", "Nova was searching the cargo crates for a confiscated experiment",
              "auditing sample storage")],
}

# The culprit's departmental item, left at the scene (physical chain).
ITEMS = {
    "oda": "a command keycard lanyard",
    "vega": "an engraved torque wrench",
    "lin": "a medbay stylus, chewed at the cap",
    "rio": "a comms headset earpiece",
    "nova": "a sample-rack tag from the science lockers",
}

# Static clue catalog (ids stable across runs so the UI keeps its icons; hint
# text is filled per-run).
CLUE_DEFS = {
    "scene_item": {"title": "Item at the Scene", "icon": "🔧"},
    "item_owner": {"title": "Item Traced", "icon": "🏷"},
    "door_gap": {"title": "Corrupted Door Log", "icon": "🚪"},
    "witness_sighting": {"title": "Night Sighting", "icon": "👁"},
    "motive_hint": {"title": "A Grudge", "icon": "🗯"},
    "herring_truth": {"title": "Innocent Secret", "icon": "🕳"},
    "alibi_broken": {"title": "Broken Alibi", "icon": "⛓"},
}


# --------------------------------------------------------------------------- #
# Generation
# --------------------------------------------------------------------------- #

def generate_case(seed: int) -> dict:
    """Build the full ground truth + evidence graph for one run."""
    rng = random.Random(seed)
    run_id = f"r{seed % 2**32:08x}"

    culprit = rng.choice(CREW_IDS)
    target = rng.choice(SABOTAGE_TARGETS)
    scene = target["room"]
    s_slot = rng.choice([1, 2, 3])  # 23:00 / 00:00 / 01:00

    motive = rng.choice(MOTIVES[culprit]).format(target=target["name"])

    herring = rng.choice([n for n in CREW_IDS if n != culprit])
    h_room, h_secret, h_excuse = rng.choice(HERRING_SECRETS[herring])
    h_slot = rng.choice([s for s in range(1, N_SLOTS - 1) if s != s_slot])

    witness = rng.choice([n for n in CREW_IDS if n not in (culprit, herring)])
    w_room = rng.choice(ADJACENCY[scene])

    # ---- ground-truth timeline: room per (slot, npc); quarters is baseline --- #
    timeline = {slot: {npc: "quarters" for npc in CREW_IDS} for slot in range(N_SLOTS)}
    timeline[s_slot][culprit] = scene
    timeline[h_slot][herring] = h_room
    timeline[s_slot][witness] = w_room

    # Innocent bystanders get at most one flavor excursion in a slot where
    # nothing case-critical happens, so the door log stays legible.
    excursions = {}  # npc -> (slot, room, memory text)
    for npc in CREW_IDS:
        if npc in (culprit, herring, witness):
            continue
        if rng.random() < 0.6:
            room, text = rng.choice(NIGHT_EXCURSIONS[npc])
            free = [s for s in range(1, N_SLOTS - 1)
                    if s not in (s_slot, h_slot) and timeline[s][npc] == "quarters"]
            if free:
                slot = rng.choice(free)
                timeline[slot][npc] = room
                excursions[npc] = (slot, room, text)

    # The witness's excursion memory (why they were up) + the sighting itself.
    w_reason_room, w_reason = next(
        ((r, t) for r, t in NIGHT_EXCURSIONS[witness] if r == w_room),
        (w_room, f"I was in the {ROOMS[w_room].lower()} late — couldn't settle that night."),
    )
    sighting = (
        f"Around {SLOT_TIMES[s_slot]} I saw {FIRST_NAMES[culprit]} in the corridor, "
        f"moving toward the {ROOMS[scene].lower()}. They didn't see me."
    )

    # ---- claims: what everyone SAYS they did (culprit + herring lie) --------- #
    claims = {}
    for npc in CREW_IDS:
        true_rooms = {slot: timeline[slot][npc] for slot in range(N_SLOTS)}
        if npc == culprit:
            claimed = {slot: "quarters" for slot in range(N_SLOTS)}
        elif npc == herring:
            claimed = dict(true_rooms)
            claimed[h_slot] = "quarters"
        else:
            claimed = true_rooms
        claims[npc] = claimed

    cover_story = (
        f"I turned in early and was in my quarters all night. "
        f"I didn't hear anything until the alarm."
    )
    herring_claim = f"I was in my quarters — maybe I got up once for water, nothing more."

    # ---- door log: entry/exit events derived from the timeline -------------- #
    # One row per room transition. The culprit's ENTRY to the scene is corrupted
    # (the gap is itself a clue); their quarters EXIT survives. Everyone else's
    # rows are intact — including the herring's, which is what exposes them.
    door_log = []
    for npc in CREW_IDS:
        prev = "quarters"
        for slot in range(N_SLOTS):
            room = timeline[slot][npc]
            if room != prev:
                door_log.append({"slot": slot, "time": SLOT_TIMES[slot], "npc": npc,
                                 "kind": "left", "room": prev, "corrupted": False})
                corrupted = npc == culprit and room == scene and slot == s_slot
                door_log.append({"slot": slot, "time": SLOT_TIMES[slot], "npc": npc,
                                 "kind": "entered", "room": room, "corrupted": corrupted})
            prev = room
        if prev != "quarters":
            door_log.append({"slot": N_SLOTS - 1, "time": SLOT_TIMES[N_SLOTS - 1], "npc": npc,
                             "kind": "left", "room": prev, "corrupted": False})
    door_log.sort(key=lambda r: (r["slot"], r["npc"], r["kind"] == "entered"))

    # ---- clues (per-run hint text over the static catalog) ------------------ #
    clues = {
        "scene_item": {
            **CLUE_DEFS["scene_item"], "id": "scene_item",
            "hint": f"Something was dropped near the {target['name']}.",
            "found": f"Wedged behind the {target['name']}: {ITEMS[culprit]}.",
        },
        "item_owner": {
            **CLUE_DEFS["item_owner"], "id": "item_owner",
            "hint": "Someone will recognize the item from the scene.",
            "found": f"The item from the scene belongs to {CREW_NAMES[culprit]}.",
        },
        "door_gap": {
            **CLUE_DEFS["door_gap"], "id": "door_gap",
            "hint": "The station logs every door. Check the ops console.",
            "found": (f"The {SLOT_TIMES[s_slot]} entry log for the {ROOMS[scene].lower()} is corrupted — "
                      f"deliberately wiped. One quarters exit at the same hour survived."),
        },
        "witness_sighting": {
            **CLUE_DEFS["witness_sighting"], "id": "witness_sighting",
            "hint": "Somebody was awake that night. Somebody always is.",
            "found": f"{CREW_NAMES[witness]} saw {FIRST_NAMES[culprit]} heading toward the {ROOMS[scene].lower()} around {SLOT_TIMES[s_slot]}.",
        },
        "motive_hint": {
            **CLUE_DEFS["motive_hint"], "id": "motive_hint",
            "hint": "Who gains if the station breaks?",
            "found": f"Word among the crew: {motive}.",
        },
        "herring_truth": {
            **CLUE_DEFS["herring_truth"], "id": "herring_truth",
            "hint": "Not every lie hides a saboteur.",
            "found": f"{CREW_NAMES[herring]}'s lie explained: {h_secret}.",
        },
        "alibi_broken": {
            **CLUE_DEFS["alibi_broken"], "id": "alibi_broken",
            "hint": "Catch a story that doesn't survive the evidence.",
            "found": f"{CREW_NAMES[culprit]}'s quarters-all-night story doesn't hold.",
        },
    }

    # ---- examine spots (backend truth; the map places them visually) -------- #
    examine_spots = {
        "sabotage_panel": {
            "id": "sabotage_panel", "room": scene,
            "title": f"Sabotaged {target['name']}",
            "text": (f"The {target['name']} didn't fail — it was helped. Clean cuts, "
                     f"no scorching. Someone knew exactly where to reach."),
            "clueId": None,
            "notebook": [f"The {target['name']} was deliberately sabotaged ({ROOMS[scene]})."],
        },
        "scene_sweep": {
            "id": "scene_sweep", "room": scene,
            "title": "Search the scene",
            "text": f"Wedged behind the housing, missed in the panic: {ITEMS[culprit]}.",
            "clueId": "scene_item",
            "notebook": [f"Found at the scene: {ITEMS[culprit]}."],
        },
        "ops_console": {
            "id": "ops_console", "room": "comms",
            "title": "Ops console — door log",
            "text": ("The overnight door log loads… mostly. One entry is a smear of "
                     "corrupted blocks. Logs don't corrupt themselves."),
            "clueId": "door_gap",
            "notebook": ["The door log has been tampered with — one entry wiped."],
        },
        "med_scanner": {
            "id": "med_scanner", "room": "medbay",
            "title": "Diagnostics scanner",
            "text": "The scanner hums. Nothing case-related, but the sample tray has been reorganized recently.",
            "clueId": None, "notebook": [],
        },
        "cargo_manifest": {
            "id": "cargo_manifest", "room": "storage",
            "title": "Cargo manifest",
            "text": "Crates accounted for. A few have been shifted from their marked outlines.",
            "clueId": None, "notebook": [],
        },
        "emergency_button": {
            "id": "emergency_button", "room": "cafeteria",
            "title": "Emergency button",
            "text": "Big. Red. Once you press it, everyone stands trial. Not yet.",
            "clueId": None, "notebook": [],
        },
    }

    # ---- contradictions: precomputed confrontation logic --------------------- #
    # requires: statements (from ask_whereabouts) + clues already found.
    contradictions = [
        {
            "id": "herring_vs_log",
            "targetNpc": herring,
            "requiresStatements": [herring],
            "requiresClues": ["door_gap"],
            "isCulpritContradiction": False,
            "grantsClue": "herring_truth",
            "label": f"The door log shows {FIRST_NAMES[herring]} entered the {ROOMS[h_room].lower()} at {SLOT_TIMES[h_slot]} — not quarters.",
            "resolutionText": (f"{h_secret}. That is what {FIRST_NAMES[herring]} was hiding — "
                               f"nothing to do with the {target['name']}."),
        },
        {
            "id": "culprit_vs_log",
            "targetNpc": culprit,
            "requiresStatements": [culprit],
            "requiresClues": ["door_gap"],
            "isCulpritContradiction": True,
            "grantsClue": "alibi_broken",
            "label": f"The log shows {FIRST_NAMES[culprit]} LEFT quarters at {SLOT_TIMES[s_slot]} — while claiming to be asleep.",
            "resolutionText": f"{FIRST_NAMES[culprit]}'s story cracks. No admission — but the alibi is gone.",
        },
        {
            "id": "culprit_vs_witness",
            "targetNpc": culprit,
            "requiresStatements": [culprit],
            "requiresClues": ["witness_sighting"],
            "isCulpritContradiction": True,
            "grantsClue": "alibi_broken",
            "label": f"{CREW_NAMES[witness]} saw {FIRST_NAMES[culprit]} near the {ROOMS[scene].lower()} that night.",
            "resolutionText": f"Caught between a witness and a story. {FIRST_NAMES[culprit]} has no answer that fits both.",
        },
    ]

    # ---- per-run guardrail gates (consumed by validators.py) ----------------- #
    # A generated line is rejected when ALL keywords in a set appear before the
    # gating clue is found (or, for the confession gate, ever). False positives
    # only cost us a fallback line — safe by contract.
    gates = {
        "confession": {
            "npc": culprit,
            "keywords": [target["synonyms"][0], ROOMS[scene].lower().split()[0]],
        },
        "locked": [
            {"clueId": "witness_sighting",
             "keywords": [FIRST_NAMES[culprit].lower(), ROOMS[scene].lower().split()[0]],
             "speakerNot": culprit},
            {"clueId": "door_gap", "keywords": ["log", "corrupt"]},
            {"clueId": "herring_truth",
             "keywords": _secret_keywords(h_secret)},
            {"clueId": "motive_hint",
             "keywords": _motive_keywords(motive)},
        ],
    }

    # ---- gossip topics for NPC-to-NPC encounters (simulation draws these) ---- #
    # A "knower" mentions something to a partner. Case-critical topics carry a
    # clueId (granted on overhear) and are written into cognee; flavor topics
    # are ledger-only.
    motive_knower = rng.choice([n for n in CREW_IDS if n not in (culprit, witness)])
    gossip_topics = [
        {"id": "topic_witness", "knower": witness, "clueId": "witness_sighting", "critical": True,
         "text": (f"{CREW_NAMES[witness]} confided that they saw {FIRST_NAMES[culprit]} heading "
                  f"toward the {ROOMS[scene].lower()} around {SLOT_TIMES[s_slot]}.")},
        {"id": "topic_motive", "knower": motive_knower, "clueId": "motive_hint", "critical": True,
         "text": f"{CREW_NAMES[motive_knower]} mentioned a rumour: {motive}."},
        {"id": "topic_herring", "knower": rng.choice([n for n in CREW_IDS if n not in (herring, culprit)]),
         "clueId": None, "critical": False,
         "text": f"Someone noticed {FIRST_NAMES[herring]} acting cagey about where they were that night."},
        {"id": "topic_repairs", "knower": "vega", "clueId": None, "critical": False,
         "text": f"Vega complained that the {target['name']} repairs will take days without spare parts."},
        {"id": "topic_morale", "knower": "lin", "clueId": None, "critical": False,
         "text": "Lin worried aloud that the crew has stopped eating together since the incident."},
        {"id": "topic_command", "knower": "rio", "clueId": None, "critical": False,
         "text": "Rio joked that command will blame whoever files the report last."},
    ]

    case = {
        "seed": seed,
        "runId": run_id,
        "culpritId": culprit,
        "witnessId": witness,
        "herringId": herring,
        "sabotage": {"targetId": target["id"], "name": target["name"], "room": scene,
                     "slot": s_slot, "time": SLOT_TIMES[s_slot], "synonyms": target["synonyms"]},
        "motive": motive,
        "herring": {"npc": herring, "room": h_room, "slot": h_slot, "secret": h_secret,
                    "excuse": h_excuse, "claim": herring_claim},
        "witness": {"npc": witness, "room": w_room, "reason": w_reason, "sighting": sighting},
        "coverStory": cover_story,
        "timeline": timeline,
        "claims": claims,
        "excursions": {npc: {"slot": s, "room": r, "text": t} for npc, (s, r, t) in excursions.items()},
        "doorLog": door_log,
        "clues": clues,
        "examineSpots": examine_spots,
        "contradictions": contradictions,
        "gates": gates,
        "gossipTopics": gossip_topics,
    }
    _assert_solvable(case)
    return case


def _secret_keywords(secret: str) -> list[str]:
    """Two distinctive lowercase keywords from a secret line, for a locked gate."""
    stop = {"the", "a", "an", "and", "was", "were", "for", "from", "into", "that",
            "his", "her", "their", "has", "have", "been", "not", "with", "off"}
    words = [w.strip(".,").lower() for w in secret.split()]
    picked = [w for w in words if len(w) > 4 and w not in stop][:2]
    return picked or ["secret", "hiding"]


def _motive_keywords(motive: str) -> list[str]:
    return _secret_keywords(motive)


def _assert_solvable(case: dict) -> None:
    """Solvability invariants — cheap, run on every generation."""
    c, h, w = case["culpritId"], case["herringId"], case["witnessId"]
    s = case["sabotage"]
    assert c != h and w not in (c, h), "roles must be distinct"
    # 1. witness chain: W adjacent to the scene during the sabotage slot.
    assert case["timeline"][s["slot"]][w] in ADJACENCY[s["room"]], "witness misplaced"
    # 2. physical chain: scene sweep grants the item, item traces to the culprit.
    assert case["examineSpots"]["scene_sweep"]["clueId"] == "scene_item"
    assert FIRST_NAMES[c].split()[0] in case["clues"]["item_owner"]["found"]
    # 3. alibi chain: culprit claims quarters but truly left; the departure row
    #    survives while the scene entry is corrupted.
    assert case["claims"][c][s["slot"]] == "quarters"
    assert case["timeline"][s["slot"]][c] == s["room"]
    rows_c = [r for r in case["doorLog"] if r["npc"] == c and r["slot"] == s["slot"]]
    assert any(r["kind"] == "left" and not r["corrupted"] for r in rows_c), "quarters exit must survive"
    assert any(r["kind"] == "entered" and r["corrupted"] for r in rows_c), "scene entry must be corrupted"
    # The herring's lying slot IS in the intact log (that's what exposes them).
    rows_h = [r for r in case["doorLog"] if r["npc"] == h and r["slot"] == case["herring"]["slot"]]
    assert any(r["kind"] == "entered" and not r["corrupted"] for r in rows_h), "herring entry must survive"
    # No innocent placed at the scene during the sabotage slot.
    for npc in CREW_IDS:
        if npc != c:
            assert case["timeline"][s["slot"]][npc] != s["room"], "innocent at the scene"
    # Contradictions reference real clues + statements.
    clue_ids = set(case["clues"])
    for contra in case["contradictions"]:
        assert set(contra["requiresClues"]) <= clue_ids
        assert contra["grantsClue"] in clue_ids
    # Case-critical gossip topics exist for the eavesdrop route.
    assert sum(1 for t in case["gossipTopics"] if t["critical"]) >= 2
