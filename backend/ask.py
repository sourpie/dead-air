"""Phase 1 CLI — prove NPC memory changes dialogue.

Examples:
    python ask.py --reset --seed
    python ask.py "Who broke into the shed?" --all
    python ask.py "Who broke into the shed?" --npc maya --context
"""
import argparse
import asyncio

import memory
from npcs import NPCS


def _as_text(r):
    return getattr(r, "text", None) or str(r)


async def run(args):
    if args.reset:
        print("Resetting cognee state...")
        await memory.reset()

    if args.seed:
        print("Seeding NPC memories (LLM extraction per memory — please wait)...")
        await memory.seed_all()
        print("Seeding complete.\n")

    if args.question:
        if args.all:
            targets = list(NPCS)
        elif args.npc:
            targets = [args.npc]
        else:
            print("Provide --all or --npc <id> together with a question.")
            return

        for npc_id in targets:
            print("=" * 64)
            print(f"{NPCS[npc_id]['name']} ({npc_id})")
            print("=" * 64)
            results = await memory.recall_for_npc(
                npc_id, args.question, context_only=args.context
            )
            if args.context:
                for r in results:
                    print("  -", _as_text(r))
            else:
                for r in results:
                    print(_as_text(r))
            print()


def main():
    p = argparse.ArgumentParser(description="Neighbourhood Echoes - Phase 1 NPC memory CLI")
    p.add_argument("question", nargs="?", help="Question to ask the NPC(s)")
    p.add_argument("--reset", action="store_true", help="Wipe all cognee memory state")
    p.add_argument("--seed", action="store_true", help="Seed NPC memories")
    p.add_argument("--npc", choices=list(NPCS), help="Ask a single NPC by id")
    p.add_argument("--all", action="store_true", help="Ask every NPC")
    p.add_argument("--context", action="store_true",
                   help="Show raw retrieved memories instead of a generated answer")
    asyncio.run(run(p.parse_args()))


if __name__ == "__main__":
    main()
