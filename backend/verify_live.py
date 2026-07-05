"""Live verification / demo driver for the cognee feature upgrades.

Run this on a machine with a working LLM key + quota (Gemini local mode, or set
COGNEE_* for Cloud). It exercises the REAL graph pipeline end to end — no game
UI needed — and is the fastest way to confirm the upgrades for the hackathon
demo/video.

    cd backend
    .venv/bin/python verify_live.py           # seed + divergent recall + graph
    .venv/bin/python verify_live.py --seed 7  # a specific case

What it proves, in order:
  1. Which cognee capabilities are live (GRANULAR/temporal/ontology/memify/feedback).
  2. node_set-tagged, ontology-grounded, temporal graph build (add -> cognify).
  3. Dataset isolation: the SAME question -> five DIFFERENT memory-grounded answers,
     using the TEMPORAL SearchType for a whereabouts question.
  4. cognee's knowledge-graph HTML render of one crewmate's memory (the demo shot).

Tip: cognee runs a 30s LLM reachability probe before pipelines; config.py sets
COGNEE_SKIP_CONNECTION_TEST=true so startup isn't stalled on a flaky link.
"""
import argparse
import asyncio
import pathlib

import config  # noqa: F401  -- loads .env + cognee dirs + skip-connection-test
import crew
import memory
import mystery
import runseeds
from crew import datasets_for


async def main(seed: int) -> None:
    case = mystery.generate_case(seed)
    run_id = case["runId"]
    sab = case["sabotage"]

    print("=" * 70)
    print(f"DEAD AIR live verify — run {run_id}, seed {seed}")
    print(f"  sabotage: {sab['name']} in {mystery.ROOMS[sab['room']]} at {sab['time']}")
    print(f"  cognee capabilities: GRANULAR={memory.GRANULAR} TEMPORAL={memory.TEMPORAL} "
          f"ONTOLOGY={memory.ONTOLOGY} MEMIFY={memory.MEMIFY} "
          f"feedback_influence={memory.FEEDBACK_INFLUENCE}")
    print("=" * 70)

    print("\n[1] Seeding 7 datasets (add + cognify: node_set + temporal + ontology + memify)…")
    ok = await memory.seed_run(runseeds.build_seeds(case))
    print(f"    seed complete (all writes landed: {ok})")

    q = (f"Where were you during the night the {sab['name']} was sabotaged, "
         f"and did you see anything?")
    print(f"\n[2] Same question to all five crew (TEMPORAL recall, own dataset only):")
    print(f'    "{q}"\n')
    for npc in mystery.CREW_IDS:
        try:
            res = await memory.recall_scoped(
                datasets_for(npc, run_id), q, crew.CREW[npc]["persona"],
                beat="whereabouts", session_id=run_id,
            )
            ans = memory.first_answer(res) or "(nothing recalled)"
        except Exception as e:  # noqa: BLE001
            ans = f"(recall failed: {type(e).__name__}: {str(e)[:80]})"
        tag = " <-- CULPRIT" if npc == case["culpritId"] else (
            " <-- witness" if npc == case["witnessId"] else "")
        print(f"  • {mystery.CREW_NAMES[npc]:<20}{tag}\n      {ans}\n")

    print("[3] Natural-language query over the memory graph (NL -> Cypher):")
    nlq = f"Which crew members were near the {mystery.ROOMS[sab['room']]} during the night?"
    print(f'    "{nlq}"')
    ans = await memory.ask_graph(crew.run_datasets(run_id), nlq)
    print(f"    → {ans or '(unavailable — needs GRANULAR + graph store)'}\n")

    print("[4] Rendering cognee graphs (knowledge graph + provenance)…")
    gdir = pathlib.Path(__file__).resolve().parent / ".graphs"
    gdir.mkdir(exist_ok=True)
    kg = await memory.visualize_dataset(crew.own_dataset(case["witnessId"], run_id),
                                        str(gdir / f"verify_{case['witnessId']}.html"))
    prov = await memory.visualize_provenance(str(gdir / "verify_provenance.html"))
    print(f"    knowledge graph: {kg or '(unavailable)'}")
    print(f"    provenance graph: {prov or '(unavailable)'}")
    print("\nDone. Open the HTML to see the memory graph; run the game for the full demo.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    asyncio.run(main(args.seed))
