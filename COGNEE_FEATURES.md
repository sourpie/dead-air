# DEAD AIR × Cognee — Feature Deep-Dive (Hackathon Submission)

How DEAD AIR uses the **cognee 1.2.2** memory lifecycle — every API mapped to a
gameplay purpose. This is the "Best Use of Cognee" story: we don't treat cognee
as a vector store, we use its **graph pipeline, metadata, temporal graph,
ontology, enrichment, feedback, and visualization** as load-bearing game systems.

> Verified against the installed `cognee==1.2.2` source. Toggle any pass in
> `.env` (`NPCMEM_*`). Prove it live: `cd backend && .venv/bin/python verify_live.py`.

---

## The pipeline at a glance

```
SEED (per run, 7 datasets)                    RECALL (per conversation beat)
  add(text, node_set=[...])                     search(query_type=<beat>,
    → cognify(temporal_cognify=True,               node_name=[...] filter,
              config=<station.owl ontology>)        feedback_influence=0.3,
    → memify(dataset)   # enrichment              session_id=run_id)
                                                whereabouts → SearchType.TEMPORAL
WRITE-BACK (gossip / claims / confront)         confront    → GRAPH_COMPLETION_COT
  add(text, node_set=[type,shift,npc,truth])    free-text   → HYBRID_COMPLETION
    → cognify()                                 default     → GRAPH_COMPLETION

SOLVE → reward_session(): session feedback → improve() → edge weights
VISUALIZE → visualize_graph(dataset) → knowledge-graph HTML (the demo shot)
```

All of it stays **leakage-free**: each crew member recalls only their own
run-scoped dataset + shared rumours (`crew.datasets_for`).

---

## 1. Graph pipeline instead of blob storage — `add()` + `cognify()`
`memory._ingest` (local mode) builds a real knowledge graph: `cognee.add(text,
dataset_name, node_set=…)` then `cognee.cognify(...)`. The Cognee-Cloud
`remember()`/`recall()` wrapper remains the fallback (and still carries
`node_set`), chosen automatically by the `GRANULAR` flag. **Why it matters:**
entities and relations (crew ↔ rooms ↔ events) become queryable graph structure,
not opaque text.

## 2. Metadata — `node_set`
Every write is tagged. Seeds: `["npc:rio","scope:private","shift:0","run:…"]`.
Runtime events: `["type:npc_gossip","shift:1","npc:rio","truth:secondhand","privacy:shared"]`
(`memory.node_set_for_dataset` / `node_set_for_event`). Recall can then **filter
by node_set** via `search(node_name=[...])` for the graph-completion family. The
Memory Debugger renders these tags on every card, so you can *see* the metadata
axis. **Why it matters:** this is the hybrid graph-vector scoping cognee is built
around.

## 3. Temporal graph — `cognify(temporal_cognify=True)` + `SearchType.TEMPORAL`
The night is a 6-slot timeline; seeds carry an absolute date anchor
(`runseeds.py`). Cognify builds Event/Timestamp nodes, and the **"Where were you
that night?"** beat recalls with `SearchType.TEMPORAL` (`interview.synth_node`
→ `memory.recall_scoped`). **Why it matters:** alibi/whereabouts reasoning runs
through cognee's time-aware retrieval — a natural, novel fit.

## 4. Ontology grounding — `station.owl` + RDFLib resolver
`cognify(config={"ontology_config": {"ontology_resolver":
RDFLibOntologyResolver(ontology_file="station.owl", …)}})`. The OWL declares the
station world (8 classes: CrewMember/Room/System/Item/Event/Motive/Rumour/Station;
16 individuals). Cognee validates extracted entities against it and stamps
`ontology_valid` on grounded nodes. **Why it matters:** directly attacks the
design doc's *Risk 1* (confabulated crew/rooms/events) at the graph layer.

## 5. Per-beat retrieval — the right `SearchType` per question
`memory._search_type`: whereabouts→`TEMPORAL`, confront→`GRAPH_COMPLETION_COT`
(multi-hop chain-of-thought over the graph), free-text→`HYBRID_COMPLETION`
(BM25 + vector + entity edges), default→`GRAPH_COMPLETION`. **Why it matters:**
different questions want different retrieval shapes — using one everywhere wastes
the graph.

## 6. Enrichment — `memify()`
After seeding a dataset, `memory._maybe_memify` runs `cognee.memify(dataset=…)`
to index triplet embeddings over the fresh graph (best-effort). **Why it matters:**
denser graph-aware retrieval signal without a full rebuild.

## 7. Feedback loop — `feedback_influence` + sessions + `improve()`
Recalls pass `feedback_influence=0.3` and a stable `session_id=run_id`, so
feedback-weighted ranking is active. On a **correct accusation**,
`gamestate.accuse` fires `memory.reward_session`: `session.add_feedback(...)` +
`improve(session_ids=…)` writes those scores into graph edge weights
(`feedback_weight`), which future recalls then favour. Gated behind
`NPCMEM_FEEDBACK_LEARN` because `improve()` is LLM-heavy. **Why it matters:**
memory that self-optimises from outcomes — the hackathon's core thesis.

## 8. Visualization — `visualize_graph()`
`GET /debug/graph/{npcId}` → `memory.visualize_dataset` → `cognee.visualize_graph`
renders that crewmate's memory as an interactive knowledge-graph HTML. The Memory
Debugger has a **"View Knowledge Graph"** button per crew. **Why it matters:** the
demo money-shot — judges *see* the graph, and watch it grow as gossip spreads.

## 9. Importance-weighted memory — `add(importance_weight=…)`
Every write carries an importance (seeds 0.8; runtime events forward their own
`importance` score — a confrontation is 0.85, small talk 0.2), so cognee ranks
weightier memories higher in recall (`memory._ingest`). **Why it matters:** the
game already scored memory importance; now the graph store uses it.

## 10. Memory provenance — `visualize_memory_provenance()`
`GET /debug/provenance` renders cognee's provenance graph: which dataset/pipeline
each memory came from — a second lens on top of the per-crew graph. Linked from
the debugger. **Why it matters:** shows the *lineage* of memory, not just its content.

## 11. Natural-language graph query — `SearchType.NATURAL_LANGUAGE`
`POST /debug/ask` (and the debugger's **"Ask the memory graph"** console) turns a
plain-English question into a Cypher query over the run's graph
(`memory.ask_graph`). **Why it matters:** an investigator tool that queries the
knowledge graph directly — a vivid demo of graph-native memory.

## 12. Extraction steering — `cognify(custom_prompt=…)` (opt-in)
A station-domain extraction prompt (`memory._STATION_PROMPT`) that complements the
ontology. Gated `NPCMEM_EXTRACTION_PROMPT` (default OFF — verify with
verify_live.py before enabling, since a bad prompt can weaken every seed).

---

## Safety contract (unchanged, still absolute)
Every generated line still passes the per-run guardrail (`validators.py`) and
falls back to an authored template on ANY failure; the culprit's dataset never
stores the act; `public_state()` redacts the solution. New cognee calls are all
wrapped so a cognee/LLM failure degrades to fallback lines — it can never break
the game or leak the mystery.

## Where each feature lives
| Feature | Code |
|---|---|
| GRANULAR pipeline, node_set, per-beat SearchType, temporal, ontology, memify, feedback, viz | `backend/memory.py` |
| Ontology | `backend/station.owl` |
| Beat tagging (whereabouts/confront) | `backend/interview.py` |
| Recall beat + session plumbing | `backend/dialogue.py` |
| Feedback reward on solve | `backend/gamestate.py` |
| Graph/provenance/NL-query endpoints + feature status | `backend/api.py` (`/debug/graph/{npc}`, `/debug/provenance`, `/debug/ask`, `/debug/datasets`) |
| Importance-weighted writes | `backend/memory.py` (`_ingest` importance_weight; events forward their score) |
| Feature toggles | `backend/.env.example` (`NPCMEM_*`) |
| Node-set chips + graph button + feature strip | `game-client/src/components/MemoryDebugger.tsx` |
| Live demo/verify | `backend/verify_live.py` |
