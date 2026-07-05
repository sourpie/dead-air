"""Deterministic game state for DEAD AIR — the single source of truth.

Everything here is plain data persisted to game_state.json: the generated case
(ground truth — NEVER sent raw to the client), the precomputed shift schedule,
current shift, relationships, statements the player has collected, clues,
the memory ledger, and the accusation result.

The LLM never touches any of this. Cognee write-back happens as a side effect
of deterministic events (gossip transfers, player claims, confrontations) via
memory.remember_event — ledger immediately, cognee in the background.

public_state() is the redaction boundary: it strips the culprit, all lies,
timelines, gates and unfired gossip topics before anything reaches the client.
"""
import asyncio
import json
import pathlib
import random
import re

import config  # noqa: F401  -- loads .env + configures cognee on import
import content
import crew
import memory
import mystery
import simulation

_HERE = pathlib.Path(__file__).resolve().parent
_STATE_PATH = _HERE / "game_state.json"

TRUST_THRESHOLD_WITNESS = 65  # the witness shares their sighting at this trust

# First-use trust bonuses per verb — being consulted builds rapport, and the
# sum is tuned so the witness threshold (65 from a base of 50) is reachable
# through conversation alone (eavesdropping is the alternate route).
VERB_TRUST_BONUS = {"ask_whereabouts": 4, "ask_sabotage": 4, "ask_about": 2, "present_clue": 4}

# After the investigator says something substantial to a crewmate, that
# crewmate walks to a colleague to discuss it — at most this many times per
# shift (further statements spill into pendingGossip for the next shift).
REACTIVE_PER_SHIFT = 3


def _initial_state(seed: int) -> dict:
    case = mystery.generate_case(seed)
    schedule = simulation.build_schedule(case)
    return {
        "run": {
            "runId": case["runId"],
            "seed": seed,
            "datasets": crew.run_datasets(case["runId"]),
            "seeding": "pending",   # pending -> in_progress -> done | failed
        },
        "case": case,
        "schedule": schedule,
        "shift": 0,
        "maxShifts": simulation.N_SHIFTS,
        "playerRoom": "cafeteria",
        "relationships": {n: {"trust": 50, "suspicion": 10} for n in mystery.CREW_IDS},
        "flustered": {n: 0 for n in mystery.CREW_IDS},
        "statements": {},        # npcId -> claim text (from ask_whereabouts)
        "verbUses": [],          # "npc:verb[:arg]" keys already used (trust dedupe)
        "notebook": [],
        "cluesFound": [],
        "examined": [],
        "overheard": [],         # encounter ids the player eavesdropped
        "firedShifts": [],       # shifts whose gossip transfers have been written
        "pendingGossip": [],     # statements waiting for a next-shift meeting (budget spillover)
        "reactiveLeft": REACTIVE_PER_SHIFT,  # reactive-encounter budget this shift
        "confronted": [],        # contradiction ids already used
        "ledger": [],            # structured memory events (Memory Debugger feed)
        "solved": None,
        "result": None,
    }


# In-process cache; persisted to disk after every mutation.
_state: dict | None = None


def _load() -> dict:
    global _state
    if _state is not None:
        return _state
    if _STATE_PATH.exists():
        loaded = json.loads(_STATE_PATH.read_text())
        # JSON round-trip turns int dict keys into strings — restore them.
        if "case" in loaded:
            loaded["case"]["timeline"] = {int(k): v for k, v in loaded["case"]["timeline"].items()}
            loaded["case"]["claims"] = {n: {int(k): v for k, v in c.items()}
                                        for n, c in loaded["case"]["claims"].items()}
        _state = loaded
    else:
        _state = _initial_state(seed=random.SystemRandom().randrange(2**32))
        _save()
    return _state


def _save() -> None:
    _STATE_PATH.write_text(json.dumps(_state, indent=2))


def get_state() -> dict:
    return _load()


def _clamp(v: int) -> int:
    return max(0, min(100, v))


# --------------------------------------------------------------------------- #
# Run lifecycle
# --------------------------------------------------------------------------- #

async def start(seed: int | None = None, reseed: bool = True) -> dict:
    """Begin a fresh run: forget the previous run's datasets (background, best
    effort), generate a new case + schedule, and kick off memory seeding in the
    background. The game is playable immediately — recall before seeding lands
    just serves fallback lines (the existing contract tolerates that)."""
    global _state
    old = _state if _state is not None else (_load() if _STATE_PATH.exists() else None)
    old_datasets = (old or {}).get("run", {}).get("datasets", [])

    if seed is None:
        seed = random.SystemRandom().randrange(2**32)
    _state = _initial_state(seed)
    _save()

    if reseed:
        loop = asyncio.get_running_loop()
        loop.create_task(_prepare_memory_bg(list(old_datasets)))
    else:
        _state["run"]["seeding"] = "skipped"
        _save()
    return _state


async def _prepare_memory_bg(old_datasets: list[str]) -> None:
    """Forget the previous run, then seed the new one. Failures are recorded,
    never raised — orphaned run-scoped datasets are unreachable by design."""
    state = _load()
    state["run"]["seeding"] = "in_progress"
    _save()
    try:
        if old_datasets:
            await memory.forget_datasets(old_datasets)
        import runseeds
        await memory.seed_run(runseeds.build_seeds(state["case"]))
        state["run"]["seeding"] = "done"
    except Exception as e:  # noqa: BLE001 -- playable without seeds (fallback lines)
        state["run"]["seeding"] = f"failed: {type(e).__name__}"
    _save()


# --------------------------------------------------------------------------- #
# Redaction — the only shape the client ever sees
# --------------------------------------------------------------------------- #

def public_state() -> dict:
    state = _load()
    case = state["case"]
    clue_catalog = []
    for cid, c in case["clues"].items():
        entry = {"id": cid, "title": c["title"], "icon": c["icon"], "hint": c["hint"]}
        if cid in state["cluesFound"]:
            entry["found"] = c["found"]
        clue_catalog.append(entry)

    return {
        "runId": state["run"]["runId"],
        "seeding": state["run"]["seeding"],
        "shift": state["shift"],
        "maxShifts": state["maxShifts"],
        "shiftName": simulation.SHIFT_NAMES[state["shift"]],
        "shiftPlan": simulation.shift_plan(state["schedule"], state["shift"]),
        "playerRoom": state["playerRoom"],
        "sabotage": {"name": case["sabotage"]["name"], "room": case["sabotage"]["room"],
                     "time": case["sabotage"]["time"]},
        "relationships": state["relationships"],
        "flustered": state["flustered"],
        "statements": state["statements"],
        "notebook": state["notebook"],
        "cluesFound": state["cluesFound"],
        "clueCatalog": clue_catalog,
        "examined": state["examined"],
        "overheard": state["overheard"],
        "ledger": state["ledger"],
        "solved": state["solved"],
        "result": state["result"],
    }


# --------------------------------------------------------------------------- #
# Memory event plumbing (ledger immediately, cognee in the background)
# --------------------------------------------------------------------------- #

async def _write_event_bg(stamped: dict) -> None:
    try:
        stamped["writtenOk"] = await memory.remember_event(stamped)
    except Exception as e:  # noqa: BLE001 -- background write; ledger already recorded
        stamped["writtenOk"] = False
        print(f"    ! remember_event({stamped.get('id')}) failed: {type(e).__name__}: {str(e)[:100]}")
    _save()


def _record_event_bg(event: dict) -> dict:
    """Append to the ledger now; write to cognee in the background. Cached
    dialogue contexts learn the new memory immediately (no re-retrieval)."""
    state = _load()
    stamped = dict(event)
    stamped["id"] = f"evt_{len(state['ledger']) + 1:03d}"
    stamped["writtenOk"] = None
    stamped["nodeSet"] = memory.node_set_for_event(stamped)  # the cognee tags written
    state["ledger"].append(stamped)
    _save()
    if stamped.get("datasets"):
        import dialogue
        dialogue.note_memory_write(stamped["datasets"], stamped["canonicalText"])
    asyncio.get_running_loop().create_task(_write_event_bg(stamped))
    return stamped


def _run_id() -> str:
    return _load()["run"]["runId"]


# --------------------------------------------------------------------------- #
# Clue + notebook helpers
# --------------------------------------------------------------------------- #

def _grant_clue(state: dict, clue_id: str | None) -> list[str]:
    if not clue_id or clue_id in state["cluesFound"]:
        return []
    state["cluesFound"].append(clue_id)
    found = state["case"]["clues"][clue_id]["found"]
    if found not in state["notebook"]:
        state["notebook"].append(found)
    return [clue_id]


# --------------------------------------------------------------------------- #
# Player verbs (the deterministic half of every conversation beat)
# --------------------------------------------------------------------------- #

def apply_verb(npc_id: str, verb: str, arg: str | None = None) -> dict:
    """Apply a verb's deterministic effects. Returns {newClues, newStatements,
    contradiction, presentReaction} for the API layer; the LLM line is generated
    separately by interview/dialogue and never decides any of this."""
    state = _load()
    case = state["case"]
    rel = state["relationships"][npc_id]
    new_clues: list[str] = []
    new_statements: list[str] = []
    contradiction = None

    use_key = f"{npc_id}:{verb}" + (f":{arg}" if arg else "")
    first_use = use_key not in state["verbUses"]
    if first_use:
        state["verbUses"].append(use_key)
        rel["trust"] = _clamp(rel["trust"] + VERB_TRUST_BONUS.get(verb, 0))

    if verb == "ask_whereabouts":
        if npc_id not in state["statements"]:
            state["statements"][npc_id] = _claim_text(case, npc_id)
            new_statements.append(npc_id)

    elif verb in ("ask_sabotage", "ask_about"):
        # The witness shares their sighting once trust is earned — asking them
        # about the sabotage, or about the culprit specifically.
        is_witness = npc_id == case["witnessId"]
        about_culprit = verb == "ask_sabotage" or arg == case["culpritId"]
        if is_witness and about_culprit and rel["trust"] >= TRUST_THRESHOLD_WITNESS:
            new_clues += _grant_clue(state, "witness_sighting")

    elif verb == "present_clue":
        if arg not in state["cluesFound"]:
            raise PermissionError(f"You don't hold clue {arg}")
        if arg == "scene_item":
            if npc_id == case["culpritId"]:
                rel["suspicion"] = _clamp(rel["suspicion"] + 6)
            else:
                new_clues += _grant_clue(state, "item_owner")

    elif verb == "confront":
        contra = next((c for c in case["contradictions"] if c["id"] == arg), None)
        if contra is None:
            raise KeyError(f"Unknown contradiction {arg}")
        if contra["targetNpc"] != npc_id:
            raise PermissionError("Wrong crewmate for this contradiction")
        if arg in state["confronted"]:
            raise PermissionError("Already confronted")
        missing_stmt = [n for n in contra["requiresStatements"] if n not in state["statements"]]
        missing_clue = [c for c in contra["requiresClues"] if c not in state["cluesFound"]]
        if missing_stmt or missing_clue:
            raise PermissionError("You don't have the evidence for that yet")
        state["confronted"].append(arg)
        contradiction = contra
        new_clues += _grant_clue(state, contra["grantsClue"])
        rel["trust"] = _clamp(rel["trust"] - 5)
        rel["suspicion"] = _clamp(rel["suspicion"] + 8)
        if contra["isCulpritContradiction"]:
            state["flustered"][npc_id] += 1
        _record_event_bg({
            "type": "confrontation", "ownerNpc": npc_id,
            "canonicalText": (f"The investigator confronted {mystery.CREW_NAMES[npc_id]}: "
                              f"{contra['label']}"),
            "source": "direct_conversation", "shift": state["shift"], "importance": 0.85,
            "privacy": "private", "truthStatus": "true", "relatedQuest": "sabotage_k7",
            "datasets": [crew.own_dataset(npc_id, _run_id())],
        })

    else:
        raise KeyError(f"Unknown verb {verb}")

    _save()
    return {"state": state, "newClues": new_clues, "newStatements": new_statements,
            "contradiction": contradiction}


def _claim_text(case: dict, npc_id: str) -> str:
    """The NPC's official whereabouts statement (lies included, verbatim)."""
    if npc_id == case["culpritId"]:
        return case["coverStory"]
    if npc_id == case["herringId"]:
        return case["herring"]["claim"]
    claims = case["claims"][npc_id]
    away = {slot: room for slot, room in claims.items() if room != "quarters"}
    if not away:
        return "I was in my quarters all night. Slept straight through until the alarm."
    slot, room = next(iter(sorted(away.items())))
    return (f"I was in my quarters most of the night — I did go to the "
            f"{mystery.ROOMS[room].lower()} around {mystery.SLOT_TIMES[slot]}.")


# --------------------------------------------------------------------------- #
# Shifts, encounters, overhearing
# --------------------------------------------------------------------------- #

def _fire_shift_transfers(state: dict, shift: int) -> list[str]:
    """Write the shift's gossip into both participants' memories (and rumours
    if case-critical). Deterministic, independent of whether anyone overheard.
    Small-talk encounters stay ledger-only (cost control)."""
    if shift in state["firedShifts"]:
        return []
    state["firedShifts"].append(shift)
    fired = []
    run_id = _run_id()
    for e in state["schedule"]["encounters"]:
        if e["shift"] != shift:
            continue
        a, b = e["npcs"]
        datasets = []
        if not e["topicId"].startswith("small_talk"):
            datasets = [crew.own_dataset(a, run_id), crew.own_dataset(b, run_id)]
            if e["critical"]:
                datasets.append(f"{run_id}_rumours")
        stamped = _record_event_bg({
            "type": "npc_gossip", "ownerNpc": a,
            "canonicalText": (f"{mystery.CREW_NAMES[a]} and {mystery.CREW_NAMES[b]} talked in the "
                              f"{mystery.ROOMS[e['room']].lower()}. {e['topicText']}"),
            "source": "npc_encounter", "shift": shift, "importance": 0.7 if e["critical"] else 0.3,
            "privacy": "shared", "truthStatus": "secondhand", "relatedQuest": "sabotage_k7",
            "datasets": datasets,
        }) if datasets else _record_ledger_only(state, e, shift)
        fired.append(stamped["id"])
    return fired


def _record_ledger_only(state: dict, e: dict, shift: int) -> dict:
    stamped = {
        "type": "npc_gossip", "ownerNpc": e["npcs"][0],
        "canonicalText": (f"{mystery.CREW_NAMES[e['npcs'][0]]} and {mystery.CREW_NAMES[e['npcs'][1]]} "
                          f"chatted in the {mystery.ROOMS[e['room']].lower()}. {e['topicText']}"),
        "source": "npc_encounter", "shift": shift, "importance": 0.2,
        "privacy": "shared", "truthStatus": "secondhand", "relatedQuest": "sabotage_k7",
        "datasets": [], "id": f"evt_{len(state['ledger']) + 1:03d}", "writtenOk": True,
    }
    stamped["nodeSet"] = memory.node_set_for_event(stamped)
    state["ledger"].append(stamped)
    return stamped


def _attach_pending_gossip(state: dict, shift: int) -> None:
    """Fold notable player statements into the new shift's encounters.

    If the crewmate you confided in meets someone this shift, they pass it on:
    the encounter's topic text gains the quote (so overheard lines include it)
    and the transfer write carries it into both participants' memories. This is
    how 'I suspect Rio' told to Lin can reach Rio's ears."""
    pending = state.get("pendingGossip", [])
    if not pending:
        return
    remaining = []
    for item in pending:
        target = next(
            (e for e in state["schedule"]["encounters"]
             if e["shift"] == shift and item["from"] in e["npcs"]),
            None,
        )
        if target is None:
            remaining.append(item)  # teller has no meeting this shift — keep waiting
            continue
        teller = mystery.CREW_NAMES[item["from"]]
        target["topicText"] += (
            f' {teller} also passed on, in confidence, what the investigator told '
            f'them privately: "{item["text"]}"'
        )
        if target["topicId"].startswith("small_talk"):
            # promote: player gossip must reach cognee, not stay ledger-only
            target["topicId"] = f"player_gossip_{item['from']}"
        if item["from"] == "rio":
            # the rumour mill: Rio's retellings also hit the shared rumours
            # dataset, so the WHOLE crew can recall them
            target["critical"] = True
    state["pendingGossip"] = remaining


def advance_shift(player_room: str | None = None) -> dict:
    """Close the current shift (fire its gossip transfers) and open the next."""
    state = _load()
    if player_room in mystery.ROOMS:
        state["playerRoom"] = player_room
    fired = _fire_shift_transfers(state, state["shift"])
    if state["shift"] < state["maxShifts"] - 1:
        state["shift"] += 1
        state["reactiveLeft"] = REACTIVE_PER_SHIFT
        _attach_pending_gossip(state, state["shift"])
    _save()
    return {"state": state, "firedTransfers": fired}


def apply_overhear(encounter_id: str, player_room: str) -> dict:
    """Validate and apply an eavesdrop: mark overheard, grant the topic clue.
    The clue grant is deterministic — line generation (interview.py) is flavor."""
    state = _load()
    e = simulation.find_encounter(state["schedule"], encounter_id)
    if e is None:
        raise KeyError(f"Unknown encounter {encounter_id}")
    if e["shift"] != state["shift"]:
        raise PermissionError("That conversation isn't happening right now")
    if player_room in mystery.ROOMS:
        state["playerRoom"] = player_room
    if not simulation.in_earshot(state["playerRoom"], e["room"]):
        raise PermissionError("Too far away to overhear")
    new_clues = []
    if encounter_id not in state["overheard"]:
        state["overheard"].append(encounter_id)
        new_clues = _grant_clue(state, e.get("clueId"))
        note = f"Overheard ({mystery.ROOMS[e['room']]}): {e['topicText']}"
        if note not in state["notebook"]:
            state["notebook"].append(note)
    _save()
    return {"state": state, "encounter": e, "newClues": new_clues}


# --------------------------------------------------------------------------- #
# World examination
# --------------------------------------------------------------------------- #

def examine(spot_id: str) -> tuple[dict, list[str], dict]:
    state = _load()
    spot = state["case"]["examineSpots"].get(spot_id)
    if spot is None:
        raise KeyError(spot_id)
    new_clues: list[str] = []
    if spot_id not in state["examined"]:
        state["examined"].append(spot_id)
        new_clues = _grant_clue(state, spot.get("clueId"))
        for line in spot.get("notebook", []):
            if line not in state["notebook"]:
                state["notebook"].append(line)
        _save()
    result = {"title": spot["title"], "text": spot["text"]}
    if spot_id == "ops_console":
        result["doorLog"] = _public_door_log(state)
    return state, new_clues, result


def _public_door_log(state: dict) -> list[dict]:
    """Door log as the console shows it: corrupted rows are masked."""
    rows = []
    for r in state["case"]["doorLog"]:
        rows.append({
            "time": r["time"], "npc": mystery.CREW_NAMES[r["npc"]], "kind": r["kind"],
            "room": "▒▒▒▒▒" if r["corrupted"] else mystery.ROOMS[r["room"]],
            "corrupted": r["corrupted"],
        })
    return rows


# --------------------------------------------------------------------------- #
# Free-text player input (unchanged mechanism, run-scoped datasets)
# --------------------------------------------------------------------------- #

_ACCUSATION = re.compile(
    r"\b(you did it|it was you|you broke|you sabotaged|you cut|liar|lying|lied|guilty|saboteur)\b",
    re.I,
)
_MIN_REMEMBER_WORDS = 4


def _is_juicy(npc_id: str, text: str) -> bool:
    """Accusations, and anything naming another crew member, are gossip fuel."""
    if _ACCUSATION.search(text):
        return True
    lower = text.lower()
    return any(mystery.FIRST_NAMES[n].lower() in lower
               for n in mystery.CREW_IDS if n != npc_id)


def _will_spread(npc_id: str, text: str) -> bool:
    """Persona-dependent discretion: does this crewmate pass the statement on?"""
    mode = content.GOSSIP_DISCRETION[npc_id]
    if mode == "never":
        return False
    if mode == "accusations":
        return bool(_ACCUSATION.search(text))
    return _is_juicy(npc_id, text)  # "always"


def _spawn_reactive_encounter(state: dict, npc_id: str, text: str) -> dict | None:
    """The crewmate you just talked to walks over to a colleague to discuss it.

    Spawned immediately into the CURRENT shift's schedule so the client can
    show them walking off and the player can follow and eavesdrop. What gets
    discussed respects discretion: gossips quote you verbatim; the discreet
    only compare notes about being questioned. The overheard lines are
    generated at listen time, so they always carry the full up-to-the-moment
    context of what the investigator has said."""
    if state.get("reactiveLeft", 0) <= 0:
        return None
    state["reactiveLeft"] -= 1
    shift = state["shift"]
    n = sum(1 for e in state["schedule"]["encounters"] if e["id"].startswith("dyn_"))
    rng = random.Random(f"{state['run']['seed']}:react:{n}")
    partner = rng.choice([c for c in mystery.CREW_IDS if c != npc_id])
    room = state["schedule"]["positions"][shift][partner]

    teller = mystery.CREW_NAMES[npc_id]
    quoted = _will_spread(npc_id, text)
    if quoted:
        topic = (f'{teller} sought out {mystery.CREW_NAMES[partner]} to pass on what the '
                 f'investigator had just told them: "{text[:180]}"')
    else:
        topic = (f"{teller} sought out {mystery.CREW_NAMES[partner]} to compare notes about "
                 f"being questioned by the investigator — without revealing what was said.")

    encounter = {
        "id": f"dyn_{shift}_{n}",
        "shift": shift,
        "room": room,
        "npcs": [npc_id, partner],
        # server-side the window is the whole remaining shift; the client
        # re-times it locally from the moment it learns about it
        "startSec": 0,
        "endSec": simulation.SHIFT_SECONDS,
        "topicId": f"player_reaction_{npc_id}",   # non-small_talk => written to memories
        "topicText": topic,
        "clueId": None,
        "critical": npc_id == "rio" and quoted,   # the rumour mill reaches everyone
    }
    state["schedule"]["encounters"].append(encounter)
    return encounter


async def apply_free_text(npc_id: str, text: str) -> dict:
    state = _load()
    if _ACCUSATION.search(text):
        rel = state["relationships"][npc_id]
        rel["suspicion"] = _clamp(rel["suspicion"] + 4)
        rel["trust"] = _clamp(rel["trust"] - 2)
    if len(text.split()) >= _MIN_REMEMBER_WORDS:
        spawned = _spawn_reactive_encounter(state, npc_id, text)
        if spawned is None and _will_spread(npc_id, text):
            # budget exhausted — the statement still travels, next shift
            state.setdefault("pendingGossip", []).append({
                "from": npc_id, "text": text[:180], "shift": state["shift"],
            })
    if len(text.split()) >= _MIN_REMEMBER_WORDS:
        _record_event_bg({
            "type": "claim", "ownerNpc": npc_id,
            "canonicalText": (f'During shift {state["shift"] + 1}, the investigator said to '
                              f'{mystery.CREW_NAMES[npc_id]}: "{text}"'),
            "source": "direct_conversation", "shift": state["shift"], "importance": 0.5,
            "privacy": "private", "truthStatus": "unverified", "relatedQuest": "sabotage_k7",
            "datasets": [crew.own_dataset(npc_id, _run_id()), f"{_run_id()}_player_profile"],
        })
    _save()
    return state


# --------------------------------------------------------------------------- #
# The accusation
# --------------------------------------------------------------------------- #

def accuse(npc_id: str) -> dict:
    state = _load()
    if npc_id not in mystery.CREW_IDS:
        raise KeyError(npc_id)
    result = content.compute_result(state, npc_id)
    state["solved"] = result["solvedCorrectly"]
    state["result"] = result
    _save()
    if result["solvedCorrectly"]:
        # Self-improving memory: reward this run's recall session so its graph
        # edges gain feedback weight (best-effort, gated, background).
        try:
            asyncio.get_running_loop().create_task(
                memory.reward_session(_run_id(), state["run"]["datasets"]))
        except RuntimeError:
            pass
    return state
