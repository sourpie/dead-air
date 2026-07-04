"""Integration test for DEAD AIR — deterministic flow with cognee stubbed.

Verifies the whole game works independently of LLM generation: case redaction,
verbs, statements, examine spots, contradictions, overhear gating + clue grants,
scoring, and the per-run validator gates.

Run: .venv/bin/python -m pytest test_flow.py -q
"""
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

# Force the cognee generation path: the developer's .env may enable the Bedrock
# backend, and tests must NEVER make live LLM calls.
os.environ["LLM_BACKEND"] = ""
os.environ.pop("AWS_BEARER_TOKEN_BEDROCK", None)

# --- Stub cognee BEFORE importing config (config imports cognee at load) ----- #
_c = ModuleType("cognee")
_c.config = SimpleNamespace(
    system_root_directory=lambda *a, **k: None,
    data_root_directory=lambda *a, **k: None,
)
_c.remember = AsyncMock(return_value=None)
_c.forget = AsyncMock(return_value=None)
_c.serve = AsyncMock(return_value=None)
_c.recall = AsyncMock(return_value=[])
sys.modules["cognee"] = _c

import json  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import api  # noqa: E402
import gamestate  # noqa: E402
import mystery  # noqa: E402
import validators  # noqa: E402

SEED = 1234
CASE = mystery.generate_case(SEED)  # ground truth, derived independently


@pytest.fixture()
def client(tmp_path):
    gamestate._STATE_PATH = tmp_path / "game_state.json"
    gamestate._state = None
    with TestClient(api.app) as c:
        r = c.post("/game/start", json={"seed": SEED, "reseed": False})
        assert r.status_code == 200
        yield c


def _talk(client, npc):
    r = client.post("/npc/talk", json={"npcId": npc})
    assert r.status_code == 200
    return r.json()


def _ask(client, npc, verb, arg=None):
    return client.post("/npc/ask", json={"npcId": npc, "verb": verb, "arg": arg})


# --------------------------------------------------------------------------- #

def test_public_state_never_leaks_the_case(client):
    state = client.get("/game/state").json()
    blob = json.dumps(state)
    assert "culpritId" not in blob
    assert "topicText" not in blob
    assert "gates" not in blob
    assert "coverStory" not in blob
    assert CASE["motive"] not in blob
    # but the playable surface is there
    assert state["shiftPlan"]["encounters"]
    assert len(state["clueCatalog"]) == 7
    assert state["maxShifts"] == 4


def test_talk_returns_greeting_and_verbs(client):
    t = _talk(client, "oda")
    assert t["source"] == "script" and t["npcLine"]
    verb_ids = {v["id"] for v in t["verbs"]}
    assert "ask_whereabouts" in verb_ids and "ask_sabotage" in verb_ids
    assert sum(1 for v in verb_ids if v.startswith("ask_about:")) == 4


def test_whereabouts_records_statements_and_liars_lie(client):
    culprit, herring = CASE["culpritId"], CASE["herringId"]
    r = _ask(client, culprit, "ask_whereabouts").json()
    assert culprit in r["newStatements"]
    assert r["source"] == "fallback"  # stub recall -> templated line
    state = client.get("/game/state").json()
    assert state["statements"][culprit] == CASE["coverStory"]
    _ask(client, herring, "ask_whereabouts")
    state = client.get("/game/state").json()
    assert state["statements"][herring] == CASE["herring"]["claim"]


def test_examine_grants_clues_once_and_masks_door_log(client):
    r = client.post("/world/examine", json={"spotId": "scene_sweep"}).json()
    assert "scene_item" in r["newClues"]
    r2 = client.post("/world/examine", json={"spotId": "scene_sweep"}).json()
    assert r2["newClues"] == []
    r3 = client.post("/world/examine", json={"spotId": "ops_console"}).json()
    assert "door_gap" in r3["newClues"]
    corrupted = [row for row in r3["doorLog"] if row["corrupted"]]
    assert len(corrupted) == 1 and corrupted[0]["room"] == "▒▒▒▒▒"
    assert client.post("/world/examine", json={"spotId": "nope"}).status_code == 404


def test_present_item_traces_owner(client):
    client.post("/world/examine", json={"spotId": "scene_sweep"})
    innocent = next(n for n in mystery.CREW_IDS if n != CASE["culpritId"])
    r = _ask(client, innocent, "present_clue", "scene_item").json()
    assert "item_owner" in r["newClues"]
    # presenting to the culprit instead: suspicion, no clue
    r2 = _ask(client, CASE["culpritId"], "present_clue", "scene_item")
    assert r2.status_code == 200 and r2.json()["newClues"] == []


def test_confrontations_exonerate_and_fluster(client):
    culprit, herring = CASE["culpritId"], CASE["herringId"]
    # gather prerequisites
    _ask(client, culprit, "ask_whereabouts")
    _ask(client, herring, "ask_whereabouts")
    client.post("/world/examine", json={"spotId": "ops_console"})
    # confronting the wrong crewmate -> 409
    bad = _ask(client, CASE["witnessId"], "confront", "herring_vs_log")
    assert bad.status_code == 409
    # herring: exonerated
    r = _ask(client, herring, "confront", "herring_vs_log").json()
    assert "herring_truth" in r["newClues"]
    # culprit: flustered
    r2 = _ask(client, culprit, "confront", "culprit_vs_log").json()
    assert "alibi_broken" in r2["newClues"]
    state = client.get("/game/state").json()
    assert state["flustered"][culprit] == 1
    # confront verbs disappear once used
    verbs = {v["id"] for v in _talk(client, herring)["verbs"]}
    assert "confront:herring_vs_log" not in verbs


def test_overhear_gating_and_deterministic_clue_grant(client):
    sched = gamestate.get_state()["schedule"]
    target = next(e for e in sched["encounters"] if e["topicId"] == "topic_witness")
    # walk shifts forward until the witness encounter is live
    for _ in range(target["shift"]):
        client.post("/shift/advance", json={})
    # out of earshot -> 403
    far = next(r for r in mystery.ROOMS
               if r != target["room"] and r not in mystery.ADJACENCY[target["room"]])
    r = client.post("/encounter/overhear",
                    json={"encounterId": target["id"], "playerRoom": far})
    assert r.status_code == 403
    # in the room -> clue granted even though generation is stubbed
    r2 = client.post("/encounter/overhear",
                     json={"encounterId": target["id"], "playerRoom": target["room"]})
    body = r2.json()
    assert r2.status_code == 200
    assert "witness_sighting" in body["newClues"]
    assert body["source"] == "fallback" and len(body["lines"]) >= 2
    # replay is idempotent
    r3 = client.post("/encounter/overhear",
                     json={"encounterId": target["id"], "playerRoom": target["room"]})
    assert r3.json()["newClues"] == []


def test_shift_advance_fires_gossip_into_ledger(client):
    client.post("/shift/advance", json={})
    state = client.get("/game/state").json()
    assert state["shift"] == 1
    gossip = [e for e in state["ledger"] if e["type"] == "npc_gossip"]
    assert len(gossip) >= 2  # both shift-0 encounters recorded


def test_witness_shares_at_trust_threshold(client):
    w = CASE["witnessId"]
    # grind first-use trust: whereabouts+sabotage (+8), ask_about x4 (+8), present (+4)
    _ask(client, w, "ask_whereabouts")
    _ask(client, w, "ask_sabotage")
    for other in mystery.CREW_IDS:
        if other != w:
            _ask(client, w, "ask_about", other)
    client.post("/world/examine", json={"spotId": "scene_sweep"})
    _ask(client, w, "present_clue", "scene_item")
    state = client.get("/game/state").json()
    assert state["relationships"][w]["trust"] >= 65
    r = _ask(client, w, "ask_sabotage").json()
    assert "witness_sighting" in r["newClues"]


def test_accuse_scoring_both_ways(client):
    innocent = next(n for n in mystery.CREW_IDS if n != CASE["culpritId"])
    state = client.post("/game/accuse", json={"npcId": innocent}).json()
    assert state["result"]["wasSaboteur"] is False
    assert state["result"]["stars"] <= 1
    # fresh run, same seed: accuse correctly
    client.post("/game/start", json={"seed": SEED, "reseed": False})
    state2 = client.post("/game/accuse", json={"npcId": CASE["culpritId"]}).json()
    assert state2["result"]["wasSaboteur"] is True
    assert state2["result"]["stars"] >= 2
    assert CASE["motive"] in state2["result"]["narrative"]["body"]


def test_free_text_writes_claim_to_ledger(client):
    r = client.post("/npc/say", json={"npcId": "lin", "text": "Tell me about the night of the sabotage."})
    assert r.status_code == 200 and r.json()["source"] == "fallback"
    state = client.get("/game/state").json()
    assert any(e["type"] == "claim" for e in state["ledger"])


def _dyn_encounters():
    return [e for e in gamestate.get_state()["schedule"]["encounters"]
            if e["id"].startswith("dyn_")]


def test_reactive_encounters_and_discretion(client):
    """Talking to a crewmate makes them seek out a colleague immediately; what
    they reveal there respects their discretion. The budget caps it per shift."""
    # captain: walks over, but never reveals what you said
    client.post("/npc/say", json={"npcId": "oda",
                                  "text": "Between us, I think Vega is lying about everything."})
    dyn = _dyn_encounters()
    assert len(dyn) == 1 and "oda" in dyn[0]["npcs"]
    assert "without revealing" in dyn[0]["topicText"]
    # Vega + idle mention: discusses being questioned, keeps the content
    client.post("/npc/say", json={"npcId": "vega",
                                  "text": "Rio seemed pretty calm this morning, don't you think?"})
    assert "without revealing" in _dyn_encounters()[1]["topicText"]
    # Vega + direct accusation: passes the quote on
    client.post("/npc/say", json={"npcId": "vega",
                                  "text": "I am sure it was Nova, they are guilty."})
    assert "they are guilty" in _dyn_encounters()[2]["topicText"]
    # budget (3/shift) exhausted: 4th statement queues for next shift instead
    client.post("/npc/say", json={"npcId": "lin",
                                  "text": "Honestly I do not trust Nova one bit."})
    assert len(_dyn_encounters()) == 3
    assert gamestate.get_state()["pendingGossip"]
    # new shift refills the budget
    client.post("/shift/advance", json={})
    assert gamestate.get_state()["reactiveLeft"] == gamestate.REACTIVE_PER_SHIFT


def test_player_statements_reach_memories(client):
    """The reactive discussion is written into BOTH participants' cognee
    datasets when the shift closes — so 'I suspect Rio' can reach Rio."""
    client.post("/npc/say", json={
        "npcId": "lin",
        "text": "Between us, I suspect Rio is hiding something about that night.",
    })
    dyn = _dyn_encounters()
    assert dyn and "I suspect Rio" in dyn[0]["topicText"]
    client.post("/shift/advance", json={})  # closes shift 0 -> transfers fire
    state = gamestate.get_state()
    spread = [e for e in state["ledger"]
              if e["type"] == "npc_gossip" and "investigator" in e["canonicalText"]]
    assert spread, "reactive discussion never fired as a transfer"
    assert spread[0]["datasets"], "spread gossip must reach cognee datasets"


def test_validator_gates_block_leaks(client):
    state = gamestate.get_state()
    culprit = CASE["culpritId"]
    scene_word = CASE["gates"]["confession"]["keywords"][-1]
    # confession phrasing from the culprit is rejected
    with pytest.raises(ValueError):
        validators.validate_text("Fine. It was me, I did it.", state, speaker=culprit)
    # self-placement at the scene at night is rejected
    with pytest.raises(ValueError):
        validators.validate_text(
            f"I passed the {scene_word} that night, briefly.", state, speaker=culprit)
    # locked fact (witness sighting keywords) blocked before the clue exists
    kw = next(g["keywords"] for g in CASE["gates"]["locked"]
              if g["clueId"] == "witness_sighting")
    leak = f"People say {kw[0]} was near the {kw[1]} after midnight."
    with pytest.raises(ValueError):
        validators.validate_text(leak, state, speaker=CASE["witnessId"])
    # ...and allowed after the clue is found
    state["cluesFound"].append("witness_sighting")
    assert validators.validate_text(leak, state, speaker=CASE["witnessId"])
