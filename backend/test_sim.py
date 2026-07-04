"""Invariant tests for the shift simulation (pure — no cognee, no net).

Run: .venv/bin/python -m pytest test_sim.py -q
"""
import json

import mystery
import simulation


def _sched(seed):
    return simulation.build_schedule(mystery.generate_case(seed))


def test_determinism():
    assert json.dumps(_sched(7), sort_keys=True) == json.dumps(_sched(7), sort_keys=True)


def test_100_seeds_schedule_invariants():
    """build_schedule asserts its own invariants — 100 seeds must all pass."""
    for seed in range(100):
        case = mystery.generate_case(seed)
        sched = simulation.build_schedule(case)
        # every encounter window is generous (>= 40s) and inside the shift
        for e in sched["encounters"]:
            assert e["endSec"] - e["startSec"] >= 40
            assert 0 <= e["startSec"] < e["endSec"] <= simulation.SHIFT_SECONDS
        # the witness's sighting is reachable via eavesdrop
        crit_topics = {e["topicId"] for e in sched["encounters"] if e["critical"]}
        assert "topic_witness" in crit_topics


def test_shift_plan_redacts_topics():
    sched = _sched(3)
    for shift in range(simulation.N_SHIFTS):
        plan = simulation.shift_plan(sched, shift)
        blob = json.dumps(plan)
        assert "topicText" not in blob and "clueId" not in blob and "topicId" not in blob
        # moves reference real encounters and rooms
        for m in plan["moves"]:
            assert m["npcId"] in mystery.CREW_IDS
            assert m["toRoom"] in mystery.ROOMS


def test_earshot_rule():
    assert simulation.in_earshot("engine", "engine")
    assert simulation.in_earshot("medbay", "engine")     # adjacent
    assert not simulation.in_earshot("quarters", "engine")
