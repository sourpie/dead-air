# DEAD AIR — Memory Architecture

> **The one-sentence thesis:** every crew member on station K‑7 recalls **only their own
> Cognee dataset** (plus a few shared ones), so the same question gets five different,
> memory-grounded answers — and when gossip travels the station, you can *watch a memory
> physically move from one crewmate's dataset into another's*.

This document is the complete map of how memory works in the project: the storage model,
the dataset topology, the event schema, every write path and read path, the freshness
strategy, and the safety guardrails that keep the mystery solvable and leak-free.

Built on **[Cognee](https://docs.cognee.ai)** `v1.2.2` — SQLite (relational) + LanceDB
(vector) + Kuzu (graph), or the managed **Cognee Cloud** tenant.

> 📊 **Presentation diagrams:** see **[DIAGRAMS.md](DIAGRAMS.md)** (Mermaid, GitHub-rendered,
> slide-ready). 🧩 **Cognee feature deep-dive** (every API → gameplay purpose):
> **[COGNEE_FEATURES.md](COGNEE_FEATURES.md)**.
>
> **Implemented graph-pipeline upgrades** (beyond the base engine below): the write path now
> uses `add()` + `cognify(temporal_cognify, ontology=station.owl)` + `memify()` with
> `node_set` metadata and `importance_weight`; recall routes a **per-beat SearchType**
> (`TEMPORAL` / `GRAPH_COMPLETION_COT` / `HYBRID_COMPLETION`) with `feedback_influence`; and
> `/debug/{graph,provenance,ask}` expose knowledge-graph viz, provenance, and a
> natural-language query console. Toggle passes via `NPCMEM_*` in `.env`.

---

## 0. The core idea (why this is a *memory* game, not a chatbot)

Cognee's `recall(query, datasets=[...])` is **leakage-free by construction**: an NPC can
retrieve *only* the datasets you name. We turn that one property into the whole game:

- Give each NPC its **own private dataset**. → They diverge, because they *know* different things.
- Add **shared datasets** (rumours, station lore). → They agree on common knowledge.
- **Write new memories at runtime** — gossip, player accusations, confrontations — into
  specific datasets. → Information *spreads*, and dialogue changes because the underlying
  memory changed, not because a flag flipped.

Everything below is the machinery that makes that safe, cheap, and observable.

---

## 1. Two sources of truth (the load-bearing split)

The single most important architectural decision: **truth and memory are separated.**

| | **Deterministic State** | **Memory (Cognee)** |
|---|---|---|
| Lives in | `game_state.json` | Cognee datasets (local or cloud) |
| Owns | who did it, timelines, clues found, relationships, the ledger | what each NPC can *recall* and *say* |
| Decided by | pure Python (`mystery.py`, `gamestate.py`) | seeded + written events, retrieved at recall time |
| The LLM's role | **none** — it never decides anything | phrases lines from retrieved memories only |

> The LLM **only supplies words**. Stances, emotions, clue grants, relationship deltas, and
> the solution are all deterministic. This is what makes the game shippable despite
> confabulation — a hallucinated line can never change game truth.

```
mystery.generate_case(seed)  ──►  ground truth (culprit, timeline, evidence, gates)
        │                                    │
        ├── runseeds.build_seeds() ──► Cognee datasets (per-NPC memories)   [MEMORY]
        └── stored in game_state.json ──► flags / clues / relationships / ledger  [TRUTH]
```

---

## 2. Dataset topology (the heart of the system)

### 2.1 Per-run, per-NPC scoping

Datasets are **run-scoped** so consecutive games never cross-contaminate. A run id is
derived from the seed: `run_id = f"r{seed % 2**32:08x}"` (e.g. `r1a2b3c4d`).

`crew.datasets_for(npc_id, run_id)` — **the recall scope for one NPC** — returns exactly:

```
┌─────────────────────────────────────────────────────────────┐
│  ONE NPC'S RECALL SCOPE                                       │
│                                                               │
│   {run_id}_npc_{npc_id}_mem   ← PRIVATE  (only this NPC)      │
│   {run_id}_rumours            ← SHARED   (whole crew)         │
│   {run_id}_player_profile     ← SHARED   (what you've said)   │
│   station_world_lore          ← PERMANENT (seeded once ever)  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 The full dataset map for one run

```
                        station_world_lore   (permanent, seeded once — ask.py --seed-lore)
                                 │  shared by everyone, every run
        ┌────────────┬──────────┴───────────┬────────────┬────────────┐
        │            │                       │            │            │
  ┌───────────┐┌───────────┐          ┌───────────┐┌───────────┐┌───────────┐
  │ oda_mem   ││ vega_mem  │   ...    │ lin_mem   ││ rio_mem   ││ nova_mem  │  ← 5 PRIVATE
  └─────┬─────┘└─────┬─────┘          └─────┬─────┘└─────┬─────┘└─────┬─────┘
        └────────────┴──────────┬───────────┴────────────┴───────────┘
                                │
              ┌─────────────────┴──────────────────┐
              │  {run_id}_rumours                   │  ← SHARED: case-critical gossip
              │  {run_id}_player_profile            │  ← SHARED: your accusations/claims
              └─────────────────────────────────────┘
```

- **7 run-scoped datasets** per game: 5 private (`_npc_*_mem`) + `_rumours` + `_player_profile`
  (see `crew.run_datasets`).
- **1 permanent dataset**: `station_world_lore`.

### 2.3 Lifecycle

`gamestate.start()` on every new game:
1. **Forget** the previous run's 7 datasets — `memory.forget_datasets()` (best-effort,
   background). *We never call `cognee.prune`* — the cloud tenant may hold unrelated data;
   per-dataset `forget()` is the only deletion primitive.
2. **Generate** a fresh case + shift schedule (deterministic from the seed).
3. **Seed** the 7 new datasets in the background (`memory.seed_run`).

The game is **playable before seeding finishes** — early recalls just serve authored
fallback lines. Orphaned datasets from a failed forget are harmless: run-scoped names
mean they can never appear in a future recall scope.

---

## 3. The three-tier memory content model

What actually goes *into* each dataset (`runseeds.build_seeds`):

| Tier | Dataset | Content | Changes per run? |
|---|---|---|---|
| **Persona** | `_npc_*_mem` | 3 fixed background lines that anchor voice (`BACKGROUND`) | No — persona is fixed |
| **Case facts** | `_npc_*_mem` | this NPC's true night, or (culprit) cover story + motive + guilt, or (herring) their innocent secret + cover | Yes — regenerated |
| **Shared** | `_rumours`, `_player_profile`, `station_world_lore` | station-wide talk, your statements, world lore | rumours/profile yes; lore never |

### 3.1 THE critical safety rule (in `runseeds.py`)

> The culprit's dataset gets their **cover story, motive, and diffuse guilt — but NEVER the
> sabotage act itself.**

Retrieval cannot leak what was never stored. This is the first line of defense against the
LLM confessing early; the validator gates (§6) are the backstop. Both fail only into safe
fallback lines.

### 3.2 Cost model

Each dataset is written with **one** `cognee.remember()` call (all its lines batched with
`\n`), so a full seed is **7 graph-extraction passes**, not ~70. `self_improvement=False`
skips the enrichment pass. This was a deliberate mitigation for LLM rate limits.

---

## 4. The Memory Event schema (structured, ledgered, observable)

Every runtime memory write is a **structured event** — not a raw string. It lands in the
deterministic `ledger` *immediately* and in Cognee *in the background*. The ledger is what
powers the **Memory Debugger** UI.

```jsonc
{
  "id":            "evt_007",              // sequential
  "type":          "npc_gossip",           // npc_gossip | claim | confrontation | clue
  "ownerNpc":      "rio",                  // whose memory this primarily is
  "canonicalText": "Rio and Lin talked …", // the EXACT text written to Cognee
  "source":        "npc_encounter",        // npc_encounter | direct_conversation | ...
  "shift":         1,                       // 0..3
  "importance":    0.7,                     // 0..1 (critical gossip 0.7, small talk 0.2)
  "privacy":       "shared",               // private | shared
  "truthStatus":   "secondhand",           // true | secondhand | unverified
  "relatedQuest":  "sabotage_k7",
  "datasets":      ["r…_npc_rio_mem",       // ← which Cognee datasets receive canonicalText
                    "r…_npc_lin_mem",
                    "r…_rumours"],
  "writtenOk":     null                     // null=writing · true=landed · false=failed
}
```

**Why ledger-first, Cognee-background** (`gamestate._record_event_bg`):
- The Memory Debugger stays correct even if a Cognee write fails (`writtenOk: false`).
- Cached dialogue contexts learn the new fact instantly via `note_memory_write` (§5.3) —
  no waiting on the slow graph pipeline.
- `datasets: []` means **ledger-only** (small talk) — never written to Cognee (cost control).

---

## 5. Write paths (how memory gets created at runtime)

There are **five** ways memory is created. All flow through `remember_event` → the target
datasets, except seeding which uses `seed_run`.

| # | Trigger | Function | Writes to | Notes |
|---|---|---|---|---|
| 1 | New game | `runseeds.build_seeds` → `memory.seed_run` | all 7 datasets | 1 `remember()` each, background |
| 2 | Shift ends | `gamestate._fire_shift_transfers` | both talkers' `_mem` (+`_rumours` if critical) | deterministic; fires whether or not you overheard |
| 3 | You type a claim | `gamestate.apply_free_text` | that NPC's `_mem` + `_player_profile` | ≥4 words; accusations bump suspicion |
| 4 | You confront an NPC | `gamestate.apply_verb("confront")` | that NPC's `_mem` | importance 0.85, `truthStatus: true` |
| 5 | Player gossip propagation | `_spawn_reactive_encounter` / `_attach_pending_gossip` | next talker's `_mem` (+`_rumours` via Rio) | NPC you confided in walks off to tell someone |

### 5.1 Gossip spread — the showcase mechanic

When a shift ends, `_fire_shift_transfers` writes each scheduled encounter's topic into
**both participants' private datasets**, and case-critical topics also into `_rumours`.
So a memory that started only in the witness's dataset can **physically appear** in another
crewmate's dataset — and now *they* can recall it when questioned. Information travels the
station on its own clock.

### 5.2 Persona-gated propagation (`content.GOSSIP_DISCRETION`)

Whether a crewmate passes on *what you told them* depends on character:

```
oda  → "never"        (by-the-book: "gossip is corrosion")
nova → "never"        (guarded: hoards information)
vega → "accusations"  (paranoid: only warns people about direct accusations)
lin  → "always"       (warm, can't help it)
rio  → "always"       (the rumour mill — AND Rio's retellings also hit _rumours,
                        so the WHOLE crew can then recall them)
```

This means **who you confide in matters**: whisper a suspicion to Rio and it reaches
everyone; tell Oda and it dies with them.

### 5.3 Freshness without re-retrieval (`dialogue.note_memory_write`)

Cognee retrieval is the latency bottleneck (~10 s). So we retrieve each NPC's context
**once** (broad query, cached, 600 s TTL) and then, when a new memory event is written, we
**append its `canonicalText` to the cached context** of every NPC whose scope includes an
affected dataset. Crewmates therefore "remember" what just happened *instantly*, with zero
extra Cognee calls. (The durable write still lands in Cognee in the background.)

---

## 6. Read paths (how memory becomes dialogue)

### 6.1 The single retrieval primitive

Everything reads through `memory.recall_scoped(datasets, query, system_prompt, context_only, top_k)`,
a thin wrapper over `cognee.recall(...)` with one transient-error retry. **It always passes
an explicit `datasets=[...]`** — the leakage-free scope from `datasets_for`.

### 6.2 Two generation backends (`LLM_BACKEND` in `.env`)

```
┌─ cognee (default) ────────────────────────────────────────────────┐
│  cognee.recall(only_context=False)                                 │
│  → ONE call does retrieval + generation server-side (Cognee Cloud) │
└────────────────────────────────────────────────────────────────────┘
┌─ bedrock (fast path) ─────────────────────────────────────────────┐
│  cognee.recall(only_context=True)   ← retrieval only, scope intact │
│  → GLM 5 on Amazon Bedrock writes the line from retrieved memories │
│  → ~2 s vs ~10 s; freshness via the context cache (§5.3)           │
└────────────────────────────────────────────────────────────────────┘
```

Either way, **memory always goes through Cognee** and the model only phrases the result.

### 6.3 The dialogue call chain

```
/npc/ask  ──► gamestate.apply_verb()      (deterministic: clues, trust, statements)
          ──► interview.synth_node()       (build {stance, fallback, emotion} from case)
          ──► dialogue.generate_line()
                 ├─ recall_scoped(datasets_for(npc), query, persona+stance)   [MEMORY]
                 ├─ validate_text()         (the guardrail — §7)              [SAFETY]
                 └─ on ANY failure → node["fallback"]  (authored template)   [SAFETY NET]
```

`/npc/say` (free text) and `/encounter/overhear` (NPC↔NPC exchange, generated *lazily* at
the moment you're in earshot) follow the same pattern.

---

## 7. Safety guardrails (keeping the mystery intact)

Three layers stop the LLM from spoiling the case, stacked so any single failure is harmless:

1. **Storage-level** — the culprit's dataset never contains the act (§3.1). *You can't leak
   what was never stored.*
2. **Validation-level** — `validators.validate_text()` checks every generated line against
   **per-run gates** emitted by `mystery.generate_case`:
   - **Confession gate:** the culprit may never use admission phrasing or place themselves
     at the scene at night.
   - **Locked-fact gates:** keyword co-occurrence sets that block a key fact (the witness
     sighting, the corrupted door log, the herring's secret, the motive) *until the player
     has actually found that clue*.
   - A 30–45 word pacing trim.
   - A rejection raises `ValueError` → the caller serves the authored fallback. Gates are
     deliberately coarse; a false positive only costs one fallback line.
3. **Redaction-level** — `gamestate.public_state()` is the boundary between server and
   client. It strips the culprit id, all lies, the full timeline, the gates, and unfired
   gossip topics before *anything* reaches the browser. The client literally never receives
   the solution.

---

## 8. Configuration & modes (`config.py`, `.env`)

`config.py` loads `.env` **before** importing Cognee (so provider env vars are visible to
LiteLLM) and pins the local store dirs.

| Mode | Set | Memory | Generation |
|---|---|---|---|
| **Cognee Cloud** | `COGNEE_SERVICE_URL` + `COGNEE_API_KEY` | managed tenant | Cognee (billed to credits — **no LLM key needed**) |
| **Local** | Gemini `LLM_API_KEY` + embeddings | in-process SQLite/LanceDB/Kuzu | Gemini via LiteLLM |
| **+ Bedrock words** | `LLM_BACKEND=bedrock` | Cognee (retrieval only) | GLM 5 on Bedrock (fast) |
| **No key** | — | stubbed | authored fallback lines only |

**Concurrency note:** Kuzu (the local graph store) is single-writer with a known file-lock
bug, so **all** Cognee access is serialized behind `memory.LOCK`.

---

## 9. The Memory Debugger (making memory visible)

The whole point is *observable* memory, so the frontend ships a debugger
(`MemoryDebugger.tsx`) that renders the ledger as **five columns, one per crewmate**. Each
memory card shows its `type`, `shift`, `importance`, `canonicalText`, and crucially the
`→ datasets` it was written to (or `ledger only`). A write in flight shows `writing…`; a
failed Cognee write shows `write failed (ledger kept)`.

This is the demo money-shot: gossip an accusation to Rio, advance the shift, and watch the
same memory appear in Rio's column, then the shared rumours, then in the datasets of whoever
Rio talks to next — the information visibly travels the station.

---

## 10. File-by-file (the memory subsystem)

| File | Role in the memory system |
|---|---|
| `config.py` | Loads `.env`, selects cloud/local, pins Cognee store dirs |
| `memory.py` | **The Cognee wrapper**: `seed_run`, `remember_event`, `recall_scoped`, `forget_datasets`, `ensure_connected`, `LOCK` |
| `crew.py` | Persona sheets + **`datasets_for` / `own_dataset` / `run_datasets`** (the scoping rules) |
| `mystery.py` | Deterministic case generator: ground truth, evidence chains, **per-run validator gates**, gossip topics |
| `runseeds.py` | Turns a case into first-person memories → `{dataset: [lines]}` (with the culprit safety rule) |
| `simulation.py` | 4-shift schedule; who's where and who talks to whom; guarantees critical gossip is reachable |
| `gamestate.py` | Deterministic state + **the ledger**; fires gossip transfers, records events, redacts (`public_state`) |
| `dialogue.py` | recall → validate → fallback; the **context cache + `note_memory_write` freshness** |
| `interview.py` | Synthesizes `{stance, fallback, emotion}` per verb; the overhear-exchange prompt/parser |
| `content.py` | Authored fallback banks, `GOSSIP_DISCRETION`, emotions, endings, scoring |
| `validators.py` | The guardrail: confession + locked-fact gates, word trim |
| `llm.py` | Bedrock GLM 5 fast-path generation (words only) |
| `api.py` | FastAPI surface; every response passes through the redaction boundary |
| `game-client/src/components/MemoryDebugger.tsx` | Renders the ledger — memory made visible |

---

## 11. One end-to-end trace

> *You tell Lin: "I think Rio has been lying about the antenna."*

```
1. POST /npc/say {npcId:"lin", text:"I think Rio has been lying…"}
2. gamestate.apply_free_text:
     • ≥4 words → record a "claim" event
         datasets = [r…_npc_lin_mem, r…_player_profile]   ← Lin now remembers you said this
     • Lin's discretion = "always" → spawn a reactive encounter:
         Lin walks off to tell a colleague; your quote rides along
3. ledger append (instant) + Cognee write (background) + cache append (note_memory_write)
4. dialogue.generate_free_reply:
     • recall_scoped(datasets_for("lin"), your text, Lin's persona)   [MEMORY]
     • Lin answers grounded in HER memories — including the new claim
     • validate_text → fallback if any gate trips                     [SAFETY]
5. Next shift: the reactive encounter fires → the claim lands in the
   colleague's _mem. If it reached Rio (or via Rio → _rumours), Rio can
   now recall it when you question them.
```

The dialogue changed because the **memory graph changed** — exactly the thing the project
set out to prove.
