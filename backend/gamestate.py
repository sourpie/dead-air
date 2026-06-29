"""Deterministic game state — the single source of truth for story progress.

Everything here is plain data persisted to game_state.json: day, current location,
story flags, per-NPC relationship numbers (trust/suspicion), the case notebook, the
per-NPC conversation node, and the structured memory **ledger** (what was written to
which Cognee dataset — this is what the Memory Debugger reads, deterministically).

The LLM never touches any of this (plan §5 / §11). Cognee write-back happens as a
side effect of applying a choice's authored effects, via memory.remember_event.
"""
import json
import pathlib

import config  # noqa: F401  -- loads .env + sets cognee dirs on import
import memory
import story

_HERE = pathlib.Path(__file__).resolve().parent
_STATE_PATH = _HERE / "game_state.json"


def _initial_state() -> dict:
    return {
        "day": 1,
        "location": "bakery",
        "relationships": {
            "maya": {"trust": 50, "suspicion": 10},
            "sam": {"trust": 40, "suspicion": 20},
            "jules": {"trust": 45, "suspicion": 5},
        },
        "flags": {
            "mayaRevealedLostKey": False,
            "playerPromisedMaya": False,
            "playerToldJules": False,
            "samSharedAlibi": False,
            "mayaRevealedSamClue": False,
        },
        "notebook": [],
        "cluesFound": [],      # clue ids collected — the win goal (X/5)
        "ledger": [],          # structured memory events (plan §6) — for the debugger
        "convo": {             # current dialogue node per NPC (entry node for day 1)
            "maya": "maya_start",
            "sam": "sam_start",
            "jules": "jules_start",
        },
        "solved": None,        # bool once the player makes an accusation
        "result": None,        # scored outcome (see story.compute_result)
    }


# In-process cache; persisted to disk after every mutation.
_state: dict | None = None


def _load() -> dict:
    global _state
    if _state is not None:
        return _state
    if _STATE_PATH.exists():
        _state = json.loads(_STATE_PATH.read_text())
    else:
        _state = _initial_state()
        _save()
    return _state


def _save() -> None:
    _STATE_PATH.write_text(json.dumps(_state, indent=2))


def get_state() -> dict:
    return _load()


async def start(reseed: bool = False) -> dict:
    """Begin a fresh game. Optionally reset+reseed Cognee (heavy — LLM calls)."""
    global _state
    if reseed:
        async with memory.LOCK:
            await memory.reset()
        await memory.seed_all()
    _state = _initial_state()
    _save()
    return _state


# --------------------------------------------------------------------------- #
# Requirement gating + effect application
# --------------------------------------------------------------------------- #

def _meets(requires: dict | None, state: dict) -> bool:
    """Evaluate a choice's gate against the current state."""
    if not requires:
        return True
    for flag, expected in requires.get("flags", {}).items():
        if bool(state["flags"].get(flag)) != bool(expected):
            return False
    for key, threshold in requires.get("minRel", {}).items():
        npc, attr = key.split(".")
        if state["relationships"].get(npc, {}).get(attr, 0) < threshold:
            return False
    return True


def available_choices(node: dict, state: dict) -> list[dict]:
    """The subset of a node's choices whose gates are currently satisfied.

    Returned without the internal `effects`/`requires`/`next` keys — just what the
    frontend needs to render a button.
    """
    out = []
    for c in node.get("choices", []):
        if _meets(c.get("requires"), state):
            out.append({"id": c["id"], "text": c["text"]})
    return out


def _clamp(v: int) -> int:
    return max(0, min(100, v))


async def apply_choice(npc_id: str, choice_id: str) -> dict:
    """Apply an authored choice's effects: relationships, flags, notebook, and
    Cognee memory write-back. Advances the NPC's conversation node. Returns state.
    """
    state = _load()
    node = story.NODES[state["convo"][npc_id]]
    choice = next((c for c in node["choices"] if c["id"] == choice_id), None)
    if choice is None:
        raise KeyError(f"Unknown choice {choice_id} at node {state['convo'][npc_id]}")
    if not _meets(choice.get("requires"), state):
        raise PermissionError(f"Choice {choice_id} is not currently available")

    eff = choice.get("effects", {})

    # Relationship deltas — default to the NPC being talked to.
    rel = state["relationships"][npc_id]
    if "trust" in eff:
        rel["trust"] = _clamp(rel["trust"] + eff["trust"])
    if "suspicion" in eff:
        rel["suspicion"] = _clamp(rel["suspicion"] + eff["suspicion"])
    for other, deltas in eff.get("rel", {}).items():
        tgt = state["relationships"][other]
        for attr, d in deltas.items():
            tgt[attr] = _clamp(tgt[attr] + d)

    # Flags + notebook (dedupe notebook so repeated visits don't pile up).
    state["flags"].update(eff.get("flags", {}))
    for line in eff.get("notebook", []):
        if line not in state["notebook"]:
            state["notebook"].append(line)

    # Clues collected toward solving the case (the win goal).
    newly_found = [c for c in eff.get("clues", []) if c not in state["cluesFound"]]
    state["cluesFound"].extend(newly_found)

    # Memory write-back → Cognee datasets + the deterministic ledger.
    for event in eff.get("events", []):
        await _record_event(event)

    # Advance the conversation node.
    state["convo"][npc_id] = choice.get("next") or state["convo"][npc_id]
    _save()
    # return the just-found clue ids too, so the API can surface a "new clue!" toast
    return state, newly_found


async def _record_event(event: dict) -> None:
    """Append a structured event to the ledger and write its text into Cognee."""
    state = _load()
    stamped = dict(event)
    stamped["id"] = f"evt_{len(state['ledger']) + 1:03d}"
    stamped["writtenOk"] = await memory.remember_event(stamped)
    state["ledger"].append(stamped)
    _save()


async def advance_day() -> dict:
    """Day 1 → Day 2. Spread gossip if the player betrayed Maya, then re-point each
    NPC's conversation to its day-2 entry node (branched on flags).
    """
    state = _load()
    if state["day"] >= 2:
        return state
    state["day"] = 2

    # The "memory travelled through the neighbourhood" beat.
    if state["flags"].get("playerToldJules"):
        for event in story.day_advance_spread_events():
            await _record_event(event)

    # Reset conversations to the branched day-2 entry nodes.
    for npc_id in ("maya", "sam", "jules"):
        state["convo"][npc_id] = story.start_node(npc_id, state)
    _save()
    return state


def solve(theory_id: str) -> dict:
    """Make the accusation: score clues + correctness + trust into a result."""
    state = _load()
    result = story.compute_result(state, theory_id)
    state["solved"] = result["solvedCorrectly"]
    state["result"] = result
    _save()
    return state
