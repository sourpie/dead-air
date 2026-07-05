# DEAD AIR — Presentation Diagrams

Slide-ready diagrams of the memory system and its flows, in **Mermaid** (renders
live on GitHub). To use in a deck: open this file on GitHub and screenshot, or
paste any block into <https://mermaid.live> and **Export → PNG/SVG**. Slidev,
Marp and reveal.js render Mermaid natively.

Each diagram has a **slide title** and a **talking point** — use them as-is.

---

## 1 · The big idea — two sources of truth
**Slide:** "Memory changes the dialogue — not the game logic."

```mermaid
flowchart LR
  UI["React client<br/>map · dialogue · Memory Debugger"] -->|"HTTP JSON"| API["FastAPI · api.py"]
  API -->|"TRUTH: game logic"| GS["Deterministic state<br/>gamestate.py → game_state.json<br/>case · clues · relationships · ledger"]
  API -->|"WORDS: recall + phrasing"| MEM["Memory · memory.py"]
  MEM --> COG[("Cognee<br/>graph + vector + relational")]
  classDef truth fill:#14233f,stroke:#4c5876,color:#eaf,stroke-width:2px
  classDef mem fill:#2a1640,stroke:#8a5cff,color:#eaf,stroke-width:2px
  class GS truth
  class MEM,COG mem
```

**Talking point:** the LLM only *phrases* lines. What's true, which clues drop,
and who the culprit is are all deterministic — so a hallucination can never
change game truth or leak the mystery.

---

## 2 · Memory topology — leakage-free dataset scoping
**Slide:** "Each crewmate remembers only their own dataset → five different answers."

```mermaid
flowchart TB
  LORE["station_world_lore<br/>PERMANENT · seeded once"]
  RUM["{run}_rumours<br/>SHARED"]
  PROF["{run}_player_profile<br/>SHARED"]
  subgraph PRIV["5 PRIVATE datasets — one per crew member"]
    direction LR
    O["oda_mem"]
    V["vega_mem"]
    LN["lin_mem"]
    RI["rio_mem"]
    NV["nova_mem"]
  end
  RI -->|"recall scope · crew.datasets_for"| RUM
  RI --> PROF
  RI --> LORE
  classDef priv fill:#14233f,stroke:#36c5e0,color:#eaf
  classDef shared fill:#2a1640,stroke:#e85fc0,color:#eaf
  class O,V,LN,RI,NV priv
  class LORE,RUM,PROF shared
```

**Talking point:** `recall(datasets=[...])` is leakage-free by construction. Rio
sees only `rio_mem` + the shared datasets — never Oda's private memories. That
isolation is *why* the same question gets divergent answers. 7 run-scoped
datasets per game, wiped and reseeded each run.

---

## 3 · Write path — building the knowledge graph
**Slide:** "Every memory is tagged, timed, and ontology-grounded as it's stored."

```mermaid
flowchart LR
  T["memory text<br/>+ node_set + importance"] --> MODE{"mode"}
  MODE -->|"local (default)"| ADD["cognee.add()<br/>node_set · importance_weight"]
  ADD --> COG["cognee.cognify()<br/>temporal_cognify · ontology"]
  COG --> MEMIFY["cognee.memify()<br/>enrichment"]
  MODE -->|"Cognee Cloud"| REM["cognee.remember()<br/>node_set"]
  MEMIFY --> G[("knowledge graph<br/>entities · relations · timestamps")]
  REM --> G
  classDef step fill:#14233f,stroke:#8a5cff,color:#eaf
  class ADD,COG,MEMIFY,REM step
```

**Talking point:** seeds get the full pipeline (temporal + ontology + enrichment);
per-turn gossip uses a lighter `cognify` for speed/quota. `node_set` tags
(`npc:rio`, `shift:1`, `type:gossip`, `truth:secondhand`) make the store a real
hybrid graph-vector index.

---

## 4 · Read path — the right SearchType per question
**Slide:** "Different questions want different retrieval — routed to the right graph search."

```mermaid
flowchart TD
  Q["player question"] --> B{"conversation<br/>beat?"}
  B -->|"where were you?"| T["SearchType.TEMPORAL"]
  B -->|"confront w/ evidence"| C["GRAPH_COMPLETION_COT<br/>(multi-hop)"]
  B -->|"free text"| H["HYBRID_COMPLETION<br/>(BM25 + vector + graph)"]
  B -->|"default"| D["GRAPH_COMPLETION"]
  T --> S
  C --> S
  H --> S
  D --> S
  S["cognee.search()<br/>dataset scope · node_name filter<br/>feedback_influence · session_id"] --> VAL{"validate_text<br/>guardrail gates"}
  VAL -->|pass| OUT["NPC line"]
  VAL -->|"leak / error"| FB["authored fallback line"]
  classDef st fill:#14233f,stroke:#36c5e0,color:#eaf
  class T,C,H,D,S st
```

**Talking point:** a whereabouts question runs time-aware retrieval; a
confrontation runs multi-hop chain-of-thought over the graph. Any failure or
locked-fact leak falls back to an authored line — story truth never depends on
the model.

---

## 5 · The showcase — a memory travels the station
**Slide:** "Gossip is a real graph write — watch a rumour reach someone you never told."

```mermaid
sequenceDiagram
  actor P as Investigator
  participant Lin
  participant SH as Shift engine
  participant Rio
  P->>Lin: "I think Rio was near the engine room"
  Note over Lin: event written to lin_mem + player_profile<br/>node_set: type:claim, npc:lin
  Lin->>SH: walks off to gossip (reactive encounter)
  Note over SH: shift ends → transfer written to<br/>BOTH datasets (+ rumours if critical)
  SH->>Rio: the memory lands in rio_mem
  P->>Rio: "Where were you that night?"
  Rio-->>P: recalls the rumour that reached them
```

**Talking point:** you never spoke to Rio about this — but because Lin (a gossip)
passed it on, the memory physically moved into Rio's dataset and now colours what
Rio recalls. The Memory Debugger shows it happen live.

---

## 6 · One conversation turn — end to end
**Slide:** "Deterministic effects first, then memory-grounded words."

```mermaid
sequenceDiagram
  participant UI as React
  participant API as FastAPI
  participant GS as gamestate
  participant IV as interview
  participant DG as dialogue
  participant MEM as memory → Cognee
  participant VAL as validators
  UI->>API: POST /npc/ask {npc, verb}
  API->>GS: apply_verb — clues, trust, contradictions (deterministic)
  API->>IV: synth_node → {stance, beat, fallback}
  API->>DG: generate_line
  DG->>MEM: recall_scoped(beat SearchType, session_id)
  MEM-->>DG: grounded memories
  DG->>VAL: validate line
  VAL-->>API: validated line OR authored fallback
  API-->>UI: npcLine + redacted state
```

**Talking point:** clue grants and relationship changes happen in Python before
the model is ever called. The model's only job is phrasing — behind a validator
and a fallback.

---

## 7 · Self-improving memory — the feedback loop
**Slide:** "Solve the case → the memory graph learns which recalls were good."

```mermaid
flowchart LR
  R["recall()<br/>session_id · feedback_influence 0.3"] --> SOLVE{"case solved<br/>correctly?"}
  SOLVE -->|yes| RW["reward_session()"]
  RW --> FB["session.add_feedback(score=5)"]
  FB --> IMP["cognee.improve(session_ids)"]
  IMP --> W["graph edge feedback_weight ↑"]
  W -->|"biases ranking"| R
  classDef st fill:#14233f,stroke:#e0b036,color:#eaf
  class R,RW,FB,IMP,W st
```

**Talking point:** feedback scores flow into graph edge weights, which
`feedback_influence` then uses to rank future recall — memory that optimises
from outcomes. (Gated behind `NPCMEM_FEEDBACK_LEARN` because `improve()` is
LLM-heavy.)

---

## 8 · How we use Cognee → judging criteria
**Slide:** "Every Cognee lifecycle API, mapped to a game system."

```mermaid
flowchart LR
  subgraph BU["Best Use of Cognee"]
    A1["add + cognify graph pipeline"]
    A2["node_set metadata"]
    A3["temporal graph"]
    A4["ontology grounding"]
    A5["memify enrichment"]
    A6["NL-query console"]
  end
  subgraph TE["Technical Excellence"]
    B1["per-beat SearchType"]
    B2["importance_weight"]
    B3["leakage-free scoping"]
    B4["fallback + redaction contract"]
  end
  subgraph CR["Creativity"]
    C1["gossip spreads through the graph"]
    C2["time-aware alibis"]
    C3["feedback self-improvement"]
  end
  subgraph PR["Presentation"]
    D1["knowledge-graph viz"]
    D2["provenance graph"]
    D3["Memory Debugger"]
  end
```

**Talking point:** the build touches the whole Cognee memory lifecycle —
`add · cognify · memify · search · improve · visualize` — each wired to a concrete
gameplay purpose, not bolted on.

---

### Rendering notes
- **GitHub:** renders all of these inline — just open the file.
- **Slides:** paste a block into <https://mermaid.live>, tweak the theme if you
  like, then Export PNG/SVG. The `classDef` colours match a dark deck; delete the
  `classDef`/`class` lines for a plain black-on-white version.
- **Live in a deck:** Slidev / Marp / reveal.js (with the mermaid plugin) render
  these directly from the fenced mermaid code blocks.
