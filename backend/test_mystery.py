"""Invariant tests for the procedural case generator (pure — no cognee, no net).

Run: .venv/bin/python -m pytest test_mystery.py -q
"""
import json

import mystery


def test_determinism():
    a = mystery.generate_case(1234)
    b = mystery.generate_case(1234)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_culprit_varies_across_seeds():
    culprits = {mystery.generate_case(s)["culpritId"] for s in range(60)}
    assert culprits == set(mystery.CREW_IDS), f"culprit pool degenerate: {culprits}"


def test_200_seeds_invariants():
    """generate_case asserts its own invariants — 200 seeds must all pass."""
    for seed in range(200):
        case = mystery.generate_case(seed)
        # Extra checks beyond the built-in assertions:
        # every slot has every crew member placed in a real room
        for slot in range(mystery.N_SLOTS):
            for npc in mystery.CREW_IDS:
                assert case["timeline"][slot][npc] in mystery.ROOMS
        # claims cover all slots for all crew
        for npc in mystery.CREW_IDS:
            assert set(case["claims"][npc]) == set(range(mystery.N_SLOTS))
        # innocents' claims are the truth
        for npc in mystery.CREW_IDS:
            if npc not in (case["culpritId"], case["herringId"]):
                for slot in range(mystery.N_SLOTS):
                    assert case["claims"][npc][slot] == case["timeline"][slot][npc]
        # the herring lies about exactly one slot
        h = case["herringId"]
        lies = [s for s in range(mystery.N_SLOTS)
                if case["claims"][h][s] != case["timeline"][s][h]]
        assert lies == [case["herring"]["slot"]]
        # exactly one corrupted door-log row, and it's the culprit's scene entry
        corrupted = [r for r in case["doorLog"] if r["corrupted"]]
        assert len(corrupted) == 1
        assert corrupted[0]["npc"] == case["culpritId"]
        # gates reference the culprit and produce non-empty keyword sets
        assert case["gates"]["confession"]["npc"] == case["culpritId"]
        assert all(g["keywords"] for g in case["gates"]["locked"])
        # gossip: the witness topic is carried by the witness
        topics = {t["id"]: t for t in case["gossipTopics"]}
        assert topics["topic_witness"]["knower"] == case["witnessId"]
        assert topics["topic_motive"]["knower"] != case["culpritId"]


def test_adjacency_symmetric():
    for room, neighbours in mystery.ADJACENCY.items():
        for n in neighbours:
            assert room in mystery.ADJACENCY[n], f"{room}->{n} not symmetric"


def test_case_is_json_serializable():
    case = mystery.generate_case(42)
    parsed = json.loads(json.dumps(case))
    assert parsed["runId"] == case["runId"]
