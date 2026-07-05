"""Core memory operations — cognee (local granular pipeline or Cognee Cloud).

Two ingest/recall paths, chosen at import time:

  * GRANULAR (default in local mode) — the full cognee knowledge-graph pipeline:
      write  = add(text, node_set=[...]) -> cognify(temporal_cognify, ontology)
      read   = search(query_type=<per-beat SearchType>, node_name=[...] filter)
    This is what unlocks node_set metadata, temporal reasoning, ontology
    grounding, richer graph SearchTypes, feedback-weighted ranking and graph
    visualisation.
  * WRAPPER (Cognee Cloud, or any env where the granular API is absent) —
      write = remember(text, node_set=[...]);  read = recall(...).
    node_set still rides along via remember()'s kwargs.

Run lifecycle (DEAD AIR): datasets are run-scoped (r<seed>_npc_<id>_mem, …).
A new run seeds 7 datasets and best-effort forgets the previous run's. NEVER
call cognee.prune here — the cloud tenant is shared with unrelated data;
forget(dataset=...) is the only deletion primitive we use.
"""
import asyncio
import os
import pathlib

import config  # noqa: F401  -- loads .env + sets cognee dirs on import
import cognee

# SearchType is a top-level export in real cognee; absent under the test stub.
try:
    from cognee import SearchType
except Exception:  # noqa: BLE001 -- stubbed cognee (tests / devserver)
    SearchType = None

_HERE = pathlib.Path(__file__).resolve().parent

# Shared lock: serialize cognee access. The local graph store (Kuzu) is
# single-writer with a known file-lock bug, so the API holds this around every
# cognee call.
LOCK = asyncio.Lock()

# --------------------------------------------------------------------------- #
# Capability flags (env-tunable so a quota-constrained demo can lighten the
# pipeline without code changes). GRANULAR requires the real granular API.
# --------------------------------------------------------------------------- #
def _flag(name: str, default: str = "1") -> bool:
    return os.environ.get(name, default) not in ("0", "false", "False", "")

_HAS_GRANULAR = all(hasattr(cognee, fn) for fn in ("add", "cognify", "search")) and SearchType is not None
GRANULAR = (not config.CLOUD_MODE) and _flag("NPCMEM_GRANULAR") and _HAS_GRANULAR
TEMPORAL = _flag("NPCMEM_TEMPORAL")           # temporal_cognify on the seed pass
ONTOLOGY = _flag("NPCMEM_ONTOLOGY")           # OWL grounding on the seed pass
MEMIFY = _flag("NPCMEM_MEMIFY")               # post-seed enrichment pass
FEEDBACK_INFLUENCE = float(os.environ.get("NPCMEM_FEEDBACK_INFLUENCE", "0.3"))
FEEDBACK_LEARN = _flag("NPCMEM_FEEDBACK_LEARN", "0")  # write feedback -> edge weights (LLM-heavy)
EXTRACTION_PROMPT = _flag("NPCMEM_EXTRACTION_PROMPT", "0")  # steer cognify extraction (test before enabling)

# Domain steer for cognify's entity/relation extraction — complements the OWL
# ontology. OFF by default (a bad prompt could weaken every seed); enable with
# NPCMEM_EXTRACTION_PROMPT=1 and confirm via verify_live.py.
_STATION_PROMPT = (
    "This is a crew of a space station. Extract entities and relations about: "
    "crew members, the rooms they were in and when, who saw whom, items left at "
    "scenes, sabotaged systems, motives, and rumours. Prefer the station's own "
    "people, rooms and systems; do not invent people or places."
)

# Per-conversation-beat SearchType — the whole point of the graph store is that
# different questions want different retrieval shapes.
def _search_type(beat: str):
    if SearchType is None:
        return None
    return {
        "whereabouts": getattr(SearchType, "TEMPORAL", SearchType.GRAPH_COMPLETION),
        "confront": getattr(SearchType, "GRAPH_COMPLETION_COT", SearchType.GRAPH_COMPLETION),
        "free_text": getattr(SearchType, "HYBRID_COMPLETION", SearchType.GRAPH_COMPLETION),
        "broad": SearchType.GRAPH_COMPLETION,
        "default": SearchType.GRAPH_COMPLETION,
    }.get(beat, SearchType.GRAPH_COMPLETION)

# NodeSet filtering only applies to the graph-completion family + TEMPORAL;
# it's silently ignored by CHUNKS/RAG/HYBRID, so only forward it for those.
_NODE_FILTERABLE = {"whereabouts", "confront", "broad", "default"}

# Cognee Cloud connection (cloud mode only).
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


# --------------------------------------------------------------------------- #
# Ontology grounding (built once, guarded — a broken/​missing rdflib just
# disables grounding rather than breaking seeding).
# --------------------------------------------------------------------------- #
_ONTO_CONFIG = None
_ONTO_TRIED = False


def _ontology_config():
    global _ONTO_CONFIG, _ONTO_TRIED
    if _ONTO_TRIED:
        return _ONTO_CONFIG
    _ONTO_TRIED = True
    if not ONTOLOGY:
        return None
    try:
        from cognee.modules.ontology.rdf_xml.RDFLibOntologyResolver import RDFLibOntologyResolver
        from cognee.modules.ontology.matching_strategies import FuzzyMatchingStrategy
        owl = _HERE / "station.owl"
        if not owl.exists():
            return None
        resolver = RDFLibOntologyResolver(ontology_file=str(owl), matching_strategy=FuzzyMatchingStrategy())
        _ONTO_CONFIG = {"ontology_config": {"ontology_resolver": resolver}}
    except Exception as e:  # noqa: BLE001
        print(f"    ! ontology disabled: {type(e).__name__}: {str(e)[:100]}")
        _ONTO_CONFIG = None
    return _ONTO_CONFIG


# --------------------------------------------------------------------------- #
# node_set derivation — the metadata axis the graph is tagged and filtered on.
# --------------------------------------------------------------------------- #
def node_set_for_dataset(name: str) -> list[str]:
    """Tags for a seed write, parsed from the run-scoped dataset name."""
    tags = ["kind:seed"]
    if "_npc_" in name and name.endswith("_mem"):
        npc = name.split("_npc_", 1)[1].rsplit("_mem", 1)[0]
        tags += [f"npc:{npc}", "scope:private", "shift:0"]
    elif name.endswith("_rumours"):
        tags += ["scope:rumours", "shift:0"]
    elif name.endswith("_player_profile"):
        tags += ["scope:player", "shift:0"]
    else:
        tags += ["scope:lore"]
    run = name.split("_", 1)[0]
    if run.startswith("r"):
        tags.append(f"run:{run}")
    return tags


def node_set_for_event(event: dict) -> list[str]:
    """Tags for a runtime memory event (gossip / claim / confrontation)."""
    tags = [f"type:{event.get('type', 'event')}", f"shift:{event.get('shift', 0)}"]
    if event.get("ownerNpc") and event["ownerNpc"] != "shared":
        tags.append(f"npc:{event['ownerNpc']}")
    if event.get("truthStatus"):
        tags.append(f"truth:{event['truthStatus']}")
    if event.get("privacy"):
        tags.append(f"privacy:{event['privacy']}")
    return tags


# --------------------------------------------------------------------------- #
# Result text extraction (handles wrapper recall dicts, granular SearchResult
# objects, and plain strings alike).
# --------------------------------------------------------------------------- #
# Field names carrying the answer/context across every result shape cognee
# returns: wrapper recall() -> ResponseQAEntry.answer / .content; granular
# search() -> SearchResult.search_result; plain strings pass through.
_TEXT_FIELDS = ("text", "answer", "result", "content", "search_result")


def as_text(r) -> str:
    if isinstance(r, str):
        return r
    if isinstance(r, list):
        return "\n".join(as_text(x) for x in r)
    if isinstance(r, dict):
        for k in _TEXT_FIELDS:
            if r.get(k):
                return as_text(r[k])
        return str(r)
    for attr in _TEXT_FIELDS:
        v = getattr(r, attr, None)
        if v:
            return v if isinstance(v, str) else as_text(v)
    return str(r)


def first_answer(results) -> str:
    """Pick one line out of a recall/search result."""
    if not results:
        return ""
    if isinstance(results, str):
        return results
    return as_text(results[0])


# --------------------------------------------------------------------------- #
# Write path
# --------------------------------------------------------------------------- #
async def _ingest(text: str, dataset: str, node_set: list[str], rich: bool,
                  importance: float = 0.5) -> None:
    """One write. GRANULAR builds the graph (add -> cognify); otherwise the
    wrapper remember() does add+cognify+improve internally. `rich` enables the
    heavier temporal + ontology + extraction-steer passes (seeding, not per-turn
    events). `importance` (0..1) feeds cognee's importance-aware ranking."""
    if GRANULAR:
        await cognee.add(text, dataset_name=dataset, node_set=node_set,
                         importance_weight=importance)
        kwargs = {"datasets": [dataset]}
        if rich and TEMPORAL:
            kwargs["temporal_cognify"] = True
        if rich:
            onto = _ontology_config()
            if onto:
                kwargs["config"] = onto
            if EXTRACTION_PROMPT:
                kwargs["custom_prompt"] = _STATION_PROMPT
        await cognee.cognify(**kwargs)
    else:
        await cognee.remember(text, dataset_name=dataset, self_improvement=False, node_set=node_set)


async def _ingest_with_retry(text, dataset, node_set, rich, importance=0.5, max_retries=5) -> bool:
    """Store one document, retrying with backoff on rate-limit / transient errors."""
    for attempt in range(max_retries):
        try:
            await _ingest(text, dataset, node_set, rich, importance)
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


async def _maybe_memify(dataset: str) -> None:
    """Post-seed enrichment: index triplet embeddings over the freshly built
    graph so graph-aware retrieval has denser signal. Best-effort — a memify
    failure never blocks a run (the graph is already usable)."""
    if not (GRANULAR and MEMIFY and hasattr(cognee, "memify")):
        return
    try:
        await cognee.memify(dataset=dataset)
    except Exception as e:  # noqa: BLE001
        print(f"    ~ memify({dataset}) skipped: {type(e).__name__}: {str(e)[:80]}")


async def seed_run(seeds: dict, pause: float = 2.0) -> bool:
    """Seed one run's datasets (7): one graph-building write each, then enrich."""
    ok = True
    async with LOCK:
        await ensure_connected()
        items = list(seeds.items())
        for idx, (dataset, lines) in enumerate(items, 1):
            blob = "\n".join(lines)
            ns = node_set_for_dataset(dataset)
            print(f"  [seed {idx}/{len(items)}] {dataset}: {len(lines)} memories, "
                  f"{len(blob)} chars, node_set={ns}")
            landed = await _ingest_with_retry(blob, dataset, ns, rich=True, importance=0.8)
            if landed:
                await _maybe_memify(dataset)
            ok = landed and ok
            await asyncio.sleep(pause)
    return ok


async def seed_lore(lines: list[str]) -> bool:
    """Seed the permanent shared lore dataset (one-time; ask.py --seed-lore)."""
    from crew import LORE_DATASET
    async with LOCK:
        await ensure_connected()
        return await _ingest_with_retry("\n".join(lines), LORE_DATASET,
                                        node_set_for_dataset(LORE_DATASET), rich=True)


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
    """Write a structured memory event's canonical text into each target dataset,
    tagged with the event's node_set (type/shift/npc/truth/privacy). Runtime
    events skip the temporal+ontology passes (rich=False) to stay cheap.

    Returns True only if every write landed — the caller records the event in
    the ledger either way, so the Memory Debugger stays correct even on failure.
    """
    text = event["canonicalText"]
    ns = node_set_for_event(event)
    importance = float(event.get("importance", 0.5))
    ok = True
    async with LOCK:
        await ensure_connected()
        for dataset in event.get("datasets", []):
            ok = await _ingest_with_retry(text, dataset, ns, rich=False, importance=importance) and ok
    return ok


# --------------------------------------------------------------------------- #
# Read path
# --------------------------------------------------------------------------- #
async def recall_scoped(
    datasets: list[str],
    query: str,
    system_prompt: str,
    context_only: bool = False,
    top_k: int = 8,
    beat: str = "default",
    node_name: list[str] | None = None,
    session_id: str | None = None,
):
    """Recall against an explicit dataset scope (leakage-free by construction),
    using the SearchType that fits this conversation beat.

    One quick retry on transient network failures (flaky DNS). Anything else —
    auth errors, missing datasets — re-raises immediately; the caller serves
    the fallback line.
    """
    await ensure_connected()
    qtype = _search_type(beat)
    filt = node_name if (node_name and beat in _NODE_FILTERABLE) else None
    for attempt in (1, 2):
        try:
            if GRANULAR:
                kwargs = dict(
                    query_text=query, query_type=qtype, datasets=datasets,
                    system_prompt=system_prompt, only_context=context_only, top_k=top_k,
                    feedback_influence=FEEDBACK_INFLUENCE,
                )
                if filt:
                    kwargs["node_name"] = filt
                    kwargs["node_name_filter_operator"] = "OR"
                if session_id:
                    kwargs["session_id"] = session_id
                return await cognee.search(**kwargs)
            # Wrapper path (cloud / stub): recall() also honours query_type,
            # session_id and feedback_influence.
            kwargs = dict(
                query_text=query, datasets=datasets, system_prompt=system_prompt,
                only_context=context_only, top_k=top_k,
                feedback_influence=FEEDBACK_INFLUENCE,
            )
            if qtype is not None:
                kwargs["query_type"] = qtype
            if session_id:
                kwargs["session_id"] = session_id
            return await cognee.recall(**kwargs)
        except Exception as e:  # noqa: BLE001
            transient = any(
                k in type(e).__name__ for k in ("Connector", "Connection", "Timeout", "DNS")
            )
            if attempt == 2 or not transient:
                raise
            await asyncio.sleep(2)


# --------------------------------------------------------------------------- #
# Feedback / self-improvement
# --------------------------------------------------------------------------- #
async def reward_session(session_id: str, datasets: list[str],
                         score: int = 5, text: str = "correct deduction") -> bool:
    """Self-improving memory: on a solved case, mark the run's Q&A session as
    good and run improve() so those feedback scores flow into graph edge weights
    (feedback_weight), which FEEDBACK_INFLUENCE then uses to rank future recall.
    LLM-heavy → gated behind NPCMEM_FEEDBACK_LEARN. Best-effort, never raises."""
    if not (GRANULAR and FEEDBACK_LEARN and hasattr(cognee, "session") and hasattr(cognee, "improve")):
        return False
    async with LOCK:
        await ensure_connected()
        try:
            entries = await cognee.session.get_session(session_id=session_id, last_n=5)
            for e in entries or []:
                qa = getattr(e, "qa_id", None) or (e.get("qa_id") if isinstance(e, dict) else None)
                if qa:
                    await cognee.session.add_feedback(session_id=session_id, qa_id=qa,
                                                      feedback_text=text, feedback_score=score)
            for ds in datasets:
                await cognee.improve(dataset=ds, session_ids=[session_id])
            return True
        except Exception as e:  # noqa: BLE001
            print(f"    ~ reward_session skipped: {type(e).__name__}: {str(e)[:80]}")
            return False


# --------------------------------------------------------------------------- #
# Visualisation + graph query — the demo money-shot: cognee's own knowledge-graph
# render of a crewmate's memory, the provenance graph, and a natural-language
# query console. All read-only; failures never touch game state.
# --------------------------------------------------------------------------- #
async def visualize_dataset(dataset: str, out_path: str) -> str | None:
    if not hasattr(cognee, "visualize_graph"):
        return None
    async with LOCK:
        await ensure_connected()
        try:
            return await cognee.visualize_graph(destination_file_path=out_path, dataset=dataset)
        except Exception as e:  # noqa: BLE001
            print(f"    ! visualize_graph({dataset}) failed: {type(e).__name__}: {str(e)[:100]}")
            return None


async def visualize_provenance(out_path: str) -> str | None:
    """Render cognee's memory-provenance graph — where each memory came from
    (which dataset/pipeline). A complementary view to the per-crew memory graph."""
    if not hasattr(cognee, "visualize_memory_provenance"):
        return None
    async with LOCK:
        await ensure_connected()
        try:
            return await cognee.visualize_memory_provenance(destination_file_path=out_path)
        except Exception as e:  # noqa: BLE001
            print(f"    ! visualize_memory_provenance failed: {type(e).__name__}: {str(e)[:100]}")
            return None


async def ask_graph(datasets: list[str], query: str, top_k: int = 8) -> str | None:
    """Investigator console: ask the station's memory graph in plain English —
    cognee converts it to a Cypher query (SearchType.NATURAL_LANGUAGE) and runs
    it over the graph store. GRANULAR-only (needs the local graph DB); guarded."""
    if not (GRANULAR and SearchType is not None and hasattr(SearchType, "NATURAL_LANGUAGE")):
        return None
    async with LOCK:
        await ensure_connected()
        try:
            res = await cognee.search(
                query_text=query, query_type=SearchType.NATURAL_LANGUAGE,
                datasets=datasets, top_k=top_k,
            )
            return first_answer(res)
        except Exception as e:  # noqa: BLE001
            print(f"    ! ask_graph failed: {type(e).__name__}: {str(e)[:100]}")
            return None
