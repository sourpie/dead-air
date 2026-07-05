# DEAD AIR

**A sabotage mystery where every character actually remembers — persistent, graph-native NPC memory powered by [Cognee](https://docs.cognee.ai).**

> Cognee AI-Memory Hackathon submission.

Station K-7 has been sabotaged. Five crew, one saboteur, and an investigator — you.
You question the crew, present clues, confront liars, and accuse before the shifts run
out. The twist: **the NPCs aren't reading from a script.** Every crew member has their
own Cognee memory, and their answers are generated from what *they* actually remember —
what they saw, what you told them, and what they overheard.

---

## Why this exists

Every LLM agent has the same failure: **amnesia.** The moment the context window ends,
it forgets who you are. Prompt-stuffing the whole world into every request doesn't scale.
The fix is real memory — a durable, queryable store the agent reads and writes over time.

DEAD AIR makes that tangible by building an entire game on top of Cognee's memory
lifecycle. Memory isn't a transcript we replay; it's a living knowledge graph that
different characters see different slices of.

---

## The core idea: leakage-free memory isolation

Each crew member gets a **private Cognee dataset**. Recall is scoped to that dataset plus
a few shared ones — so the same question yields **five different, memory-grounded answers.**

```
5 PRIVATE datasets            SHARED datasets
  oda_mem                       {run}_rumours        (gossip anyone can hear)
  vega_mem                      {run}_player_profile (what you've said)
  lin_mem                       station_world_lore   (permanent, seeded once)
  rio_mem      ── recall scope ─┘
  nova_mem
```

`recall(datasets=[...])` is **leakage-free by construction**: Rio can never see Oda's
private memories. That isolation is *why* the mystery works — the culprit can lie, and a
witness genuinely can't see everything. Seven run-scoped datasets per game, wiped and
reseeded each run.

## Two sources of truth

The LLM only ever supplies the **words**. What's *true* — the case, which clues drop, who
the culprit is — is deterministic Python. So a hallucination can colour how a character
talks, but can **never** change game truth or leak the mystery.

```
React client ──HTTP──▶ FastAPI ──▶ deterministic state (case · clues · relationships)   [TRUTH]
                            └──────▶ memory (Cognee: graph · vector · relational)         [WORDS]
```

## The showcase: watch a memory travel the station

Tell **Medic Lin** a suspicion about **Rio** — it's written straight into Lin's dataset.
A shift later, Lin gossips: the rumour is physically transferred into **Rio's** dataset.
You never spoke to Rio about it — but ask him now and he recalls the rumour that reached
him. The **Memory Debugger** shows information spreading dataset-to-dataset, live.

Gossip is a real graph write, not a script flag.

---

## How we use Cognee

The build touches the whole Cognee memory lifecycle — each wired to a concrete game
system, not bolted on:

| Cognee capability | In DEAD AIR |
|---|---|
| `add` + `cognify` graph pipeline | build a durable knowledge graph per crew member |
| `node_set` metadata | every memory tagged `npc:*`, `shift:*`, `type:claim/gossip`, `truth:*` |
| temporal graph (`temporal_cognify`) | events on a timeline → time-aware alibis |
| ontology grounding (`station.owl`) | entities validated against the station's people/rooms/systems |
| `memify` enrichment | denser graph signal for retrieval |
| per-beat `SearchType` | the right retrieval shape for each question (below) |
| `feedback_influence` + `improve` | solve the case → the graph learns which recalls were good |
| `visualize` | live knowledge-graph and provenance renders in the UI |

### Retrieval: the right graph search per question

Retrieval is routed by conversation beat:

- **whereabouts** → `SearchType.TEMPORAL` (time-aware over the night's timeline)
- **confrontation** → `GRAPH_COMPLETION_COT` (multi-hop chain-of-thought over the graph)
- **free text** → `HYBRID_COMPLETION` (BM25 + vectors + entity relationships)
- **default** → `GRAPH_COMPLETION`

Every generated line passes a **guardrail** (`validators.py`): on any locked-fact leak or
error we serve an authored fallback, and a redaction boundary keeps the culprit, the lies
and unfired gossip server-side. Story truth never depends on the model.

> Diagrams for all of the above live in [`DIAGRAMS.md`](DIAGRAMS.md).

---

## Tech stack

- **Memory:** Cognee (local graph pipeline — SQLite + LanceDB + Kuzu — **or** Cognee Cloud)
- **Backend:** Python 3.12 · FastAPI · async
- **Dialogue words:** Cognee recall-generation *or* a pluggable direct backend
  (local **Ollama** `llama3.1:8b`, or **GLM 5** on Amazon Bedrock) — Cognee always owns memory
- **Frontend:** React + Vite + TypeScript · Zustand · Tailwind · a hand-built top-down station map

---

## Quickstart

### 1. Backend (start this first)

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # then fill in a memory mode (see Configuration)
.venv/bin/uvicorn api:app --port 8000
```

Memory is **seeded automatically** in the background when a new game starts
(`POST /game/start`) — no manual seed step. Early lines fall back safely while seeding
finishes.

### 2. Game client

```bash
cd game-client
npm install
npm run dev                   # http://localhost:5173
```

Open the URL, hit **Start**, and play. (The backend must be running on `:8000`; with no
keys configured the game still runs on authored fallback lines.)

---

## Configuration

Copy `backend/.env.example` → `backend/.env` and pick **one memory mode**:

- **Cognee Cloud** — set `COGNEE_SERVICE_URL` + `COGNEE_API_KEY`. Memory and (optionally)
  generation route to your managed tenant; no separate LLM key needed.
- **Local** (default) — Cognee runs in-process against on-disk stores using a Gemini key
  (`LLM_API_KEY` / `EMBEDDING_API_KEY`) via LiteLLM.

**Generation backend** (optional — Cognee always owns memory; this only changes who writes
the *words*, for much lower latency):

```bash
# local, free, offline:  `ollama pull llama3.1:8b`
LLM_BACKEND=ollama
OLLAMA_MODEL=llama3.1:8b

# or GLM 5 on Amazon Bedrock:
# LLM_BACKEND=bedrock
# AWS_BEARER_TOKEN_BEDROCK=...
# BEDROCK_MODEL_ID=zai.glm-5
```

Cognee feature passes (graph pipeline, temporal, ontology, memify, feedback ranking) are
all on by default in local mode and individually toggleable — see the comments in
`.env.example` for quota-constrained runs.

### Performance note

In **Cognee Cloud** mode, memory calls run concurrently (a cognee round trip no longer
blocks LLM generation or a second retrieval), the per-NPC context is cached and
single-flighted, and approaching an eavesdrop pre-warms both speakers — so leaning in to
overhear is fast instead of paying a cold retrieval.

---

## Explore the memory (judge-facing)

Once a game is running:

- **Memory Debugger** (in-game) — five columns showing who knows what, `node_set` tags and
  write status; watch gossip spread in real time.
- **Ask the memory graph** — a natural-language console (NL → Cypher) over the whole station.
- `GET /debug/graph/{npc}` — Cognee's own knowledge-graph render of one crewmate's mind.
- `GET /debug/provenance` — where each memory came from.
- `GET /debug/datasets` — which Cognee capabilities are live this run.

Key HTTP surface: `POST /game/start` · `/npc/talk` · `/npc/ask` · `/npc/say` ·
`/encounter/overhear` · `/encounter/prewarm` · `/shift/advance` · `/world/examine` ·
`/game/accuse`.

---

## Repository layout

```
backend/                 Python memory engine + game API
  api.py                 FastAPI surface (game, dialogue, overhear, debug)
  memory.py              Cognee integration — writes, scoped recall, per-beat SearchType
  dialogue.py            recall → words → guardrail → validated line (or fallback)
  llm.py                 pluggable generation backends (ollama / bedrock)
  gamestate.py           deterministic truth: case, clues, relationships, ledger
  crew.py · mystery.py   crew personas + per-run dataset scoping + case generation
  validators.py          locked-fact guardrail + authored fallback
  station.owl            OWL ontology used to ground entity extraction
game-client/             React + Vite + TypeScript app
  src/components/map/     top-down station, crew simulation, eavesdropping
  src/components/         MemoryDebugger, dialogue, meeting/eject screens, ...
DIAGRAMS.md              architecture + memory-flow diagrams
COGNEE_FEATURES.md       how each Cognee feature maps to a game system
MEMORY_ARCHITECTURE.md   deeper design notes
```

---

## Credits

Built for the Cognee AI-Memory Hackathon. Memory by [Cognee](https://www.cognee.ai).
