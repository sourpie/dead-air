"""Core memory operations — thin wrappers over cognee (local or Cognee Cloud).

Run lifecycle (DEAD AIR): datasets are run-scoped (r<seed>_npc_<id>_mem, …).
A new run seeds 7 datasets (one remember() each) and best-effort forgets the
previous run's. NEVER call cognee.prune here — the cloud tenant is shared with
unrelated data; forget(dataset=...) is the only deletion primitive we use.
"""
import asyncio

import config  # noqa: F401  -- loads .env + sets cognee dirs on import
import cognee

# Shared lock: serialize cognee access. The local graph store is single-writer
# and has a known file-lock issue under concurrent access, so the API holds this
# around every cognee call.
LOCK = asyncio.Lock()

# Cloud mode: if COGNEE_SERVICE_URL + COGNEE_API_KEY are set, connect the SDK to
# the managed tenant once — then all calls route to the cloud and inference is
# billed to Cognee credits (no separate LLM provider key needed).
_connected = False


async def ensure_connected():
    """Connect to Cognee Cloud once if configured; no-op in local mode."""
    global _connected
    if _connected:
        return
    import os
    url = os.environ.get("COGNEE_SERVICE_URL")
    key = os.environ.get("COGNEE_API_KEY")
    if url and key:
        await cognee.serve(url=url, api_key=key)
    _connected = True


def as_text(r):
    """Best-effort extraction of text from a cognee recall result.

    Local mode returns objects with a .text attribute; Cognee Cloud returns plain
    dicts like {'kind': 'graph_completion', 'text': ...} — handle both, falling
    back to str() only as a last resort.
    """
    if isinstance(r, dict):
        return r.get("text") or str(r)
    return getattr(r, "text", None) or str(r)


def first_answer(results) -> str:
    """Pick one line out of a recall result (generation mode may return several)."""
    if not results:
        return ""
    if isinstance(results, str):
        return results
    return as_text(results[0])


async def _remember_with_retry(text, dataset, max_retries=5):
    """Store one document, retrying with backoff on rate-limit / transient errors."""
    for attempt in range(max_retries):
        try:
            await cognee.remember(text, dataset_name=dataset, self_improvement=False)
            return True
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if attempt == max_retries - 1:
                print(f"    ! {dataset} FAILED: {type(e).__name__}: {msg[:140]}")
                return False
            wait = 10 * (attempt + 1)
            tag = "rate-limit" if ("429" in msg or "RESOURCE_EXHAUSTED" in msg) else type(e).__name__
            print(f"    ...retrying {dataset} in {wait}s ({tag})")
            await asyncio.sleep(wait)


async def seed_run(seeds: dict, pause: float = 2.0) -> bool:
    """Seed one run's datasets, ONE remember() per dataset (7 calls total)."""
    ok = True
    async with LOCK:
        await ensure_connected()
        items = list(seeds.items())
        for idx, (dataset, lines) in enumerate(items, 1):
            blob = "\n".join(lines)
            print(f"  [seed {idx}/{len(items)}] {dataset}: {len(lines)} memories, {len(blob)} chars")
            ok = await _remember_with_retry(blob, dataset) and ok
            await asyncio.sleep(pause)
    return ok


async def seed_lore(lines: list[str]) -> bool:
    """Seed the permanent shared lore dataset (one-time; ask.py --seed-lore)."""
    from crew import LORE_DATASET
    async with LOCK:
        await ensure_connected()
        return await _remember_with_retry("\n".join(lines), LORE_DATASET)


async def forget_datasets(names: list[str]) -> dict:
    """Best-effort per-dataset deletion of a finished run. A failure is harmless:
    run-scoped names mean orphaned data is never in any future recall scope."""
    results = {}
    async with LOCK:
        await ensure_connected()
        for name in names:
            try:
                await cognee.forget(dataset=name)
                results[name] = True
            except Exception as e:  # noqa: BLE001
                print(f"    ! forget({name}) failed: {type(e).__name__}: {str(e)[:100]}")
                results[name] = False
    return results


async def remember_event(event: dict) -> bool:
    """Write a structured memory event's canonical text into each target dataset.

    Returns True only if every write landed — the caller records the event in
    the ledger either way, so the Memory Debugger stays correct even when a
    write fails.
    """
    text = event["canonicalText"]
    ok = True
    async with LOCK:
        await ensure_connected()
        for dataset in event.get("datasets", []):
            ok = await _remember_with_retry(text, dataset) and ok
    return ok


async def recall_scoped(
    datasets: list[str],
    query: str,
    system_prompt: str,
    context_only: bool = False,
    top_k: int = 8,
):
    """Recall against an explicit dataset scope (leakage-free by construction).

    One quick retry on transient network failures (flaky VPN DNS makes the
    tenant hostname intermittently unresolvable). Anything else — auth errors,
    missing datasets — re-raises immediately; the caller serves the fallback.
    """
    await ensure_connected()
    for attempt in (1, 2):
        try:
            return await cognee.recall(
                query_text=query,
                datasets=datasets,
                system_prompt=system_prompt,
                only_context=context_only,
                top_k=top_k,
            )
        except Exception as e:  # noqa: BLE001
            transient = any(
                k in type(e).__name__ for k in ("Connector", "Connection", "Timeout", "DNS")
            )
            if attempt == 2 or not transient:
                raise
            await asyncio.sleep(2)
