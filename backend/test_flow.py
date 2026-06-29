"""Automated integration test for the deterministic game flow (no key needed).

Stubs cognee (incl. recall generation), then drives the real FastAPI app via
TestClient to verify flags, relationship deltas, choice gating, the memory ledger,
day-advance gossip spread, both endings, the cognee-generation path, and the
generation->fallback guardrail.

    .venv/bin/python test_flow.py
"""
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

# ---- Stub cognee BEFORE importing config (config imports cognee at load) ----- #
_cognee = ModuleType("cognee")
_cognee.config = SimpleNamespace(
    system_root_directory=lambda *a, **k: None,
    data_root_directory=lambda *a, **k: None,
)
_cognee.prune = SimpleNamespace(prune_data=AsyncMock(), prune_system=AsyncMock())
_cognee.remember = AsyncMock(return_value=None)
_cognee.serve = AsyncMock(return_value=None)
# recall is the generation path now; default [] -> empty -> authored fallback.
_cognee.recall = AsyncMock(return_value=[])
sys.modules["cognee"] = _cognee

from fastapi.testclient import TestClient  # noqa: E402
import api  # noqa: E402

client = TestClient(api.app)
_failures = []


def set_recall(value):
    """Control what cognee.recall returns (a list of result objects or strings)."""
    _cognee.recall.return_value = value


def check(label, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        _failures.append(label)


def talk(npc):
    return client.post("/npc/talk", json={"npcId": npc}).json()


def choose(npc, choice):
    return client.post("/game/choose", json={"npcId": npc, "choiceId": choice}).json()


def reset():
    return client.post("/game/start", json={"reseed": False}).json()


def solve(theory):
    return client.post("/game/solve", json={"theoryId": theory}).json()


print("\n[1] Start / initial state")
st = reset()
check("day starts at 1", st["day"] == 1)
check("maya trust seeded 50", st["relationships"]["maya"]["trust"] == 50)
check("no flags set", not any(st["flags"].values()))
check("empty ledger + notebook + clues", st["ledger"] == [] and st["notebook"] == [] and st["cluesFound"] == [])

print("\n[1b] Catalog never leaks the solution")
cat = client.get("/game/catalog").json()
check("catalog has 5 clues + 4 theories", len(cat["clues"]) == 5 and len(cat["theories"]) == 4)
check("no theory is flagged correct", all("correct" not in t for t in cat["theories"]))

print("\n[2] Locked choices hidden before gate met")
ids = {c["id"] for c in talk("maya")["choices"]}
check("maya_start offers reassure+probe only", ids == {"maya_reassure", "maya_probe"})
jids = {c["id"] for c in talk("jules")["choices"]}
check("jules betrayal choice hidden (key not revealed)", "jules_tell_secret" not in jids)
check("jules keep-quiet hidden (no promise yet)", "jules_keep_quiet" not in jids)

print("\n[3] Build trust until Maya reveals the lost key (gated on trust>=65)")
choose("maya", "maya_reassure"); talk("maya")
choose("maya", "maya_support_sam")
t = talk("maya")
check("trust climbed to 70", t["relationship"]["trust"] == 70)
check("ask_key now available (gate met)", any(c["id"] == "maya_ask_key" for c in t["choices"]))
r = choose("maya", "maya_ask_key")
st = r["state"]
check("mayaRevealedLostKey flag set", st["flags"]["mayaRevealedLostKey"])
check("secret event written to ledger", any(e["type"] == "secret" for e in st["ledger"]))
check("notebook records the admission", any("lost it" in n for n in st["notebook"]))
check("clue 'maya_lost_key' collected", "maya_lost_key" in st["cluesFound"])
check("newClues surfaced for the toast", "maya_lost_key" in r["newClues"])
check("advanced to reveal node", r["nextNodeId"] == "maya_reveal_key")

print("\n[4] Promise (the secret-keeping setup)")
st = choose("maya", "maya_promise")["state"]
check("playerPromisedMaya set", st["flags"]["playerPromisedMaya"])
check("promise event targets player_profile",
      any(e["type"] == "promise" and "player_profile" in e["datasets"] for e in st["ledger"]))
check("maya trust >= 80 after promise", st["relationships"]["maya"]["trust"] >= 80)

print("\n[5] Betrayal: tell Jules (choice now unlocked)")
jids = {c["id"] for c in talk("jules")["choices"]}
check("jules_tell_secret now available", "jules_tell_secret" in jids)
check("jules_keep_quiet now available (promise made)", "jules_keep_quiet" in jids)
st = choose("jules", "jules_tell_secret")["state"]
check("playerToldJules set", st["flags"]["playerToldJules"])
check("gossip event under jules", any(e["type"] == "gossip" and e["ownerNpc"] == "jules" for e in st["ledger"]))

print("\n[6] Advance day -> gossip spreads to Maya")
before = len(st["ledger"])
st = client.post("/day/advance").json()
check("day == 2", st["day"] == 2)
check("two spread events added", len(st["ledger"]) == before + 2)
check("betrayal event reached maya", any(e["type"] == "betrayal" and e["ownerNpc"] == "maya" for e in st["ledger"]))
check("shared rumour event added", any(e["ownerNpc"] == "shared" for e in st["ledger"]))
check("maya convo branched to confront", st["convo"]["maya"] == "maya_d2_confront")

print("\n[7] Day-2 Maya confronts (authored fallback, recall empty)")
t = talk("maya")
check("source is fallback", t["source"] == "fallback")
check("confront line mentions trust", "trusted you" in t["npcLine"].lower())
check("emotion is authored (hurt)", t["emotion"] == "hurt")

print("\n[8] Memory debugger feed (dataset isolation)")
owners = {e["ownerNpc"] for e in client.get("/debug/memories/maya").json()["memories"]}
check("maya debug shows maya + shared events", owners <= {"maya", "shared"} and "maya" in owners)
dbg_j = client.get("/debug/memories/jules").json()
check("jules debug never shows maya's private secret",
      not any(e["type"] == "secret" and e["ownerNpc"] == "maya" for e in dbg_j["memories"]))

print("\n[9] Solve correctly but betrayed -> 'Sharp Eyes, Cold Heart'")
st = solve("accident")
res = st["result"]
check("marked solved", st["solved"] is True)
check("solvedCorrectly", res["solvedCorrectly"])
check("narrative is broken_trust", res["narrative"]["id"] == "broken_trust")
check("2 stars (correct but betrayed)", res["stars"] == 2)
check("rank is cold_detective", res["rank"]["title"] == "Sharp Eyes, Cold Heart")
check("wrong theory would be cold case", solve("sam_did_it")["result"]["rank"]["title"] == "Cold Case")

print("\n[10] cognee-generation path returns the generated line + authored emotion")
set_recall([SimpleNamespace(text="Oh, you must be the new neighbour. Welcome to Maple Street.")])
reset()
t = talk("maya")
check("source is cognee", t["source"] == "cognee")
check("line is the generated one", "new neighbour" in t["npcLine"])
check("emotion stays authored (anxious at maya_start)", t["emotion"] == "anxious")

print("\n[11] Locked-fact guardrail forces fallback on early key leak")
set_recall([SimpleNamespace(text="Honestly? I lost the shed key myself last week.")])
reset()
check("leak rejected -> fallback", talk("maya")["source"] == "fallback")

print("\n[12] Keep-secret branch -> peaceful_resolution")
set_recall([])  # back to authored fallback lines
reset()
choose("maya", "maya_reassure"); talk("maya")
choose("maya", "maya_support_sam"); talk("maya")
choose("maya", "maya_ask_key")
choose("maya", "maya_promise")
choose("sam", "sam_reassure"); talk("sam")
choose("sam", "sam_note_latch")
st = client.post("/day/advance").json()
check("day2 maya branches to trust (secret kept)", st["convo"]["maya"] == "maya_d2_trust")
check("warm clue line, not confront", "thank you" in talk("maya")["npcLine"].lower())
st = choose("maya", "maya_d2_take_clue")["state"]
check("4 clues collected (kept secret path)", len(st["cluesFound"]) == 4)
res = solve("accident")["result"]
check("narrative is peaceful_resolution", res["narrative"]["id"] == "peaceful_resolution")
check("3 stars + Hero rank", res["stars"] == 3 and res["rank"]["title"] == "Maple Street Hero")

print(f"\n{'=' * 50}")
if _failures:
    print(f"{len(_failures)} FAILURE(S): {_failures}")
    sys.exit(1)
print("ALL CHECKS PASSED")
