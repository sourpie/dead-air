"""Interview layer — synthesizes conversation beats from the generated case.

The old authored node tree is gone; instead, every player verb gets a
pseudo-node {stance, fallback, emotion} built at request time from case atoms,
so dialogue.generate_line keeps its exact contract (phrase the stance via
cognee recall; any failure serves the fallback).

Also owns the overhear exchange: the one-call prompt that writes both sides of
an NPC-to-NPC conversation, and the strict parser for its A:/B: format.
"""
import re

import content
from crew import CREW
from mystery import CREW_NAMES, FIRST_NAMES, ITEMS, ROOMS


# --------------------------------------------------------------------------- #
# Verb menu
# --------------------------------------------------------------------------- #

def available_verbs(state: dict, npc_id: str) -> list[dict]:
    """The verb buttons currently offered when talking to this NPC."""
    case = state["case"]
    verbs = [
        {"id": "ask_whereabouts", "verb": "ask_whereabouts", "arg": None,
         "label": content.VERB_LABELS["ask_whereabouts"]},
        {"id": "ask_sabotage", "verb": "ask_sabotage", "arg": None,
         "label": content.VERB_LABELS["ask_sabotage"]},
    ]
    for other in CREW:
        if other != npc_id:
            verbs.append({"id": f"ask_about:{other}", "verb": "ask_about", "arg": other,
                          "label": content.VERB_LABELS["ask_about"].format(
                              otherName=FIRST_NAMES[other])})
    if "scene_item" in state["cluesFound"] and f"{npc_id}:present_clue:scene_item" not in state["verbUses"]:
        verbs.append({"id": "present_clue:scene_item", "verb": "present_clue", "arg": "scene_item",
                      "label": content.VERB_LABELS["present_clue"].format(
                          clueTitle=case["clues"]["scene_item"]["title"])})
    for contra in case["contradictions"]:
        if contra["targetNpc"] != npc_id or contra["id"] in state["confronted"]:
            continue
        have_stmt = all(n in state["statements"] for n in contra["requiresStatements"])
        have_clues = all(c in state["cluesFound"] for c in contra["requiresClues"])
        if have_stmt and have_clues:
            verbs.append({"id": f"confront:{contra['id']}", "verb": "confront",
                          "arg": contra["id"], "label": f"Confront: {contra['label']}"})
    return verbs


# --------------------------------------------------------------------------- #
# Pseudo-node synthesis (called AFTER gamestate.apply_verb)
# --------------------------------------------------------------------------- #

def _pressure(state: dict, npc_id: str) -> int:
    case = state["case"]
    return sum(1 for cid in state["confronted"]
               for c in case["contradictions"]
               if c["id"] == cid and c["targetNpc"] == npc_id)


def synth_node(state: dict, npc_id: str, verb: str, arg: str | None) -> dict:
    """Build the {stance, fallback, emotion} beat for one verb."""
    case = state["case"]
    is_culprit = npc_id == case["culpritId"]
    is_herring = npc_id == case["herringId"]
    is_witness = npc_id == case["witnessId"]
    sab = case["sabotage"]
    scene = ROOMS[sab["room"]].lower()
    pressure = _pressure(state, npc_id)

    slots = {
        "claimText": state["statements"].get(npc_id, ""),
        "targetName": sab["name"],
        "sceneRoom": scene,
        "otherFirst": FIRST_NAMES.get(arg, "") if arg in CREW_NAMES else "",
        "itemText": ITEMS[case["culpritId"]],
    }

    if verb == "ask_whereabouts":
        stance = (f"The investigator asked where you were during the night of the sabotage. "
                  f'Your account, delivered naturally in your own words: "{slots["claimText"]}"')
        if is_culprit:
            stance += " Do not waver from this story. Volunteer nothing extra."
        elif is_herring:
            stance += " You are hiding something small and personal — keep the details vague."

    elif verb == "ask_sabotage":
        stance = (f"The investigator asked what you know about the sabotage of the "
                  f"{sab['name']} in the {scene}.")
        if is_witness:
            if "witness_sighting" in state["cluesFound"]:
                stance += (f" You have decided to trust them. Tell them plainly: "
                           f"{case['witness']['sighting']}")
            else:
                stance += (" You saw something that night but you are NOT ready to share it. "
                           "Deflect without lying outright — hint that nights here are restless.")
        elif is_culprit:
            stance += (" Speculate blandly about wear and tear or outside causes. "
                       "Steer attention anywhere but yourself.")
        else:
            stance += " Share what you genuinely remember; speculate only in character."

    elif verb == "ask_about":
        other = FIRST_NAMES[arg]
        stance = (f"The investigator asked for your honest read on {other}. Ground it ONLY "
                  f"in what you actually remember; do not invent incidents.")
        if is_witness and arg == case["culpritId"] and "witness_sighting" in state["cluesFound"]:
            stance += f" You may mention what you saw that night: {case['witness']['sighting']}"
        if is_culprit and arg != npc_id:
            stance += " Quietly encourage suspicion of them without being obvious."

    elif verb == "present_clue":
        item = slots["itemText"]
        if is_culprit:
            stance = (f"The investigator shows you {item}, found at the sabotage scene. It is "
                      f"YOURS. Deny ownership calmly — suggest anyone could have taken it "
                      f"from your locker. Do not confess to anything.")
        else:
            stance = (f"The investigator shows you {item}, found at the sabotage scene. You "
                      f"recognize it as {CREW_NAMES[case['culpritId']]}'s. Say so honestly, "
                      f"with appropriate reluctance about accusing a crewmate.")

    elif verb == "confront":
        contra = next(c for c in case["contradictions"] if c["id"] == arg)
        if contra["isCulpritContradiction"]:
            stance = (f"The investigator confronted you with evidence: {contra['label']} "
                      f"You are cornered but you DO NOT confess. Get defensive, question the "
                      f"evidence, offer an alternate explanation, show a crack of fear.")
        else:
            h = case["herring"]
            stance = (f"The investigator confronted you with evidence: {contra['label']} "
                      f"Your cover is blown. Admit the embarrassing truth — {h['secret']} — "
                      f"and insist, truthfully, that it has nothing to do with the sabotage.")
    else:
        raise KeyError(f"Unknown verb {verb}")

    verb_kind = verb
    fallback = content.FALLBACK_LINES[npc_id][verb_kind].format(**slots)
    # Beat -> SearchType (memory.recall_scoped): whereabouts wants time-aware
    # retrieval, a confrontation wants multi-hop chain-of-thought over the graph.
    beat = {"ask_whereabouts": "whereabouts", "confront": "confront"}.get(verb, "default")
    return {
        "stance": stance,
        "fallback": fallback,
        "emotion": content.emotion_for(npc_id, verb_kind, pressure),
        "beat": beat,
    }


# --------------------------------------------------------------------------- #
# Overhear exchange — one generation call writes both sides
# --------------------------------------------------------------------------- #

def exchange_prompt(encounter: dict) -> str:
    a, b = encounter["npcs"]
    return (
        "You are writing a short conversation between two space-station crewmates, "
        "overheard by someone nearby. The speakers:\n"
        f"- {FIRST_NAMES[a]}: {CREW[a]['personaShort']}\n"
        f"- {FIRST_NAMES[b]}: {CREW[b]['personaShort']}\n"
        f"The substance that passes between them (you must convey this, in their voices): "
        f"{encounter['topicText']}\n"
        f"Write EXACTLY 4 lines of dialogue, alternating speakers, in this format:\n"
        f"{FIRST_NAMES[a]}: <line>\n{FIRST_NAMES[b]}: <line>\n"
        f"{FIRST_NAMES[a]}: <line>\n{FIRST_NAMES[b]}: <line>\n"
        "Each line under 20 words, natural and in-character. No narration, no extra text."
    )


_LINE_RE = re.compile(r"^\s*([A-Za-z]+)\s*:\s*(.+?)\s*$")


def parse_exchange(raw: str, npcs: list[str]) -> list[dict]:
    """Parse 'Name: line' rows into [{speaker, text}]. Raises on a bad format."""
    by_first = {FIRST_NAMES[n].lower(): n for n in npcs}
    lines = []
    for row in (raw or "").splitlines():
        m = _LINE_RE.match(row)
        if not m:
            continue
        speaker = by_first.get(m.group(1).strip().lower())
        if speaker:
            lines.append({"speaker": speaker, "text": m.group(2)})
    if len(lines) < 2:
        raise ValueError(f"unparseable exchange ({len(lines)} valid lines)")
    return lines[:6]
