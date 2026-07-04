"""DEAD AIR maintenance CLI.

Examples:
    python ask.py --seed-lore              # one-time: seed station_world_lore
    python ask.py --probe oda "Where were you last night?"
"""
import argparse
import asyncio

import gamestate
import memory
from crew import CREW, datasets_for
from runseeds import LORE_SEEDS


async def run(args):
    if args.seed_lore:
        print("Seeding permanent station lore (one remember call)...")
        ok = await memory.seed_lore(LORE_SEEDS)
        print("done" if ok else "FAILED")

    if args.probe:
        npc_id, question = args.probe
        state = gamestate.get_state()
        run_id = state["run"]["runId"]
        results = await memory.recall_scoped(
            datasets_for(npc_id, run_id), question,
            CREW[npc_id]["persona"], context_only=args.context,
        )
        if isinstance(results, list):
            for r in results:
                print("  -", memory.as_text(r))
        else:
            print(results)


def main():
    p = argparse.ArgumentParser(description="DEAD AIR - maintenance CLI")
    p.add_argument("--seed-lore", action="store_true",
                   help="Seed the permanent station_world_lore dataset (once)")
    p.add_argument("--probe", nargs=2, metavar=("NPC", "QUESTION"),
                   help="Ask one crew member a question against the current run")
    p.add_argument("--context", action="store_true",
                   help="Show raw retrieved memories instead of a generated answer")
    asyncio.run(run(p.parse_args()))


if __name__ == "__main__":
    main()
