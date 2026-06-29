"""Core memory operations — thin wrappers over cognee (local or Cognee Cloud)."""
import asyncio
import os

import config  # noqa: F401  -- loads .env + sets cognee dirs on import
import cognee

from npcs import NPCS
from seeds import SEEDS

# Shared lock: serialize cognee/Kuzu access. The local graph store is single-writer
# and has a known file-lock issue under concurrent access, so the API holds this
# around every cognee call.
LOCK = asyncio.Lock()

# Cloud mode (Option B): if COGNEE_SERVICE_URL + COGNEE_API_KEY are set, connect the
# SDK to the managed tenant once — then remember/recall route to the cloud and the
# inference runs on Cognee credits (no separate LLM provider key needed). If they're
# unset we stay in local mode using the LLM_API_KEY from .env.
_connected = False


async def ensure_connected():
    """Connect to Cognee Cloud once if configured; no-op in local mode."""
    global _connected
    if _connected:
        return
    url = os.environ.get("COGNEE_SERVICE_URL")
    key = os.environ.get("COGNEE_API_KEY")
    if url and key:
        await cognee.serve(url=url, api_key=key)
    _connected = True


def as_text(r):
    """Best-effort extraction of text from a cognee recall result."""
    return getattr(r, "text", None) or str(r)


def first_answer(results) -> str:
    """Pick one line out of a recall result (generation mode may return several)."""
    if not results:
        return ""
    if isinstance(results, str):
        return results
    return as_text(results[0])


async def reset():
    """Wipe all cognee state for a clean, repeatable run (no LLM calls)."""
    await ensure_connected()
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)


async def _remember_with_retry(text, dataset, max_retries=6):
    """Store one document, retrying with backoff on rate-limit (free-tier 429s)."""
    for attempt in range(max_retries):
        try:
            await cognee.remember(text, dataset_name=dataset, self_improvement=False)
            return True
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if attempt == max_retries - 1:
                print(f"    ! {dataset} FAILED: {type(e).__name__}: {msg[:140]}")
                return False
            wait = 15 * (attempt + 1)
            tag = "rate-limit" if ("429" in msg or "RESOURCE_EXHAUSTED" in msg) else type(e).__name__
            print(f"    ...retrying {dataset} in {wait}s ({tag})")
            await asyncio.sleep(wait)


async def seed_all(pause=3.0):
    """Seed memories, ONE document per dataset.

    We batch each dataset's memories into a single remember() call so cognee runs
    one graph-extraction pass per dataset instead of one per memory. That keeps us
    well under the Gemini free-tier daily request cap (20/model/day) while leaving
    per-NPC dataset isolation — and therefore the divergence proof — intact.
    """
    await ensure_connected()
    items = list(SEEDS.items())
    for idx, (dataset, memories) in enumerate(items, 1):
        blob = "\n".join(memories)
        print(f"  [{idx}/{len(items)}] {dataset}: {len(memories)} memories, {len(blob)} chars")
        await _remember_with_retry(blob, dataset)
        await asyncio.sleep(pause)


async def remember_event(event: dict) -> bool:
    """Write a structured memory event's canonical text into each target dataset.

    `event["datasets"]` lists where it goes (e.g. a promise → npc_maya_memory +
    player_profile; gossip → npc_jules_memory). Held under LOCK like every other
    cognee call (Kuzu is single-writer). Returns True only if every write landed —
    the caller still records the event in the ledger either way, so the Memory
    Debugger stays correct even when a write hits the free-tier quota.
    """
    text = event["canonicalText"]
    ok = True
    async with LOCK:
        await ensure_connected()
        for dataset in event.get("datasets", [f"npc_{event['ownerNpc']}_memory"]):
            ok = await _remember_with_retry(text, dataset) and ok
    return ok


async def recall_for_npc(
    npc_id: str, query: str, context_only: bool = False, system_prompt: str | None = None
):
    """Recall scoped to one NPC's datasets only (own + shared).

    context_only=True returns the raw retrieved memories (proof of scoping / debug).
    context_only=False returns an LLM answer in the NPC's voice — generation runs
    through cognee (so in cloud mode it's billed to Cognee credits, not a separate key).
    Pass system_prompt to override the NPC's default persona for a specific beat.
    """
    await ensure_connected()
    npc = NPCS[npc_id]
    return await cognee.recall(
        query_text=query,
        datasets=npc["datasets"],
        system_prompt=system_prompt or npc["persona"],
        only_context=context_only,
        top_k=8,
    )
