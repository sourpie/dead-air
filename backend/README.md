# Neighbourhood Echoes — Backend

FastAPI + Cognee backend for the memory-native NPC mystery. Two source-of-truth split:
deterministic **game state** (day, flags, relationships, notebook, memory ledger) in
`game_state.json`, and **NPC memory** in per-NPC Cognee datasets. The LLM only phrases
lines; authored story logic decides what is true and what branches.

Its foundation (Phase 1) proves that **NPC memory changes dialogue**: three NPCs, each
with their own Cognee memory dataset, answer the same question differently.

## Setup

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # then configure ONE mode (below)
```

### Two modes (set in `.env`)

- **Cognee Cloud (Option B, recommended)** — set `COGNEE_SERVICE_URL` + `COGNEE_API_KEY`.
  `memory.ensure_connected()` calls `cognee.serve()` once, so memory **and** dialogue
  generation route to your managed tenant and are billed to Cognee credits. **No
  separate LLM key needed.** Leave the Gemini block blank.
- **Local (default)** — leave the `COGNEE_*` vars unset and provide a Gemini
  `LLM_API_KEY`. cognee runs in-process against on-disk stores; the Gemini key powers
  both generation and embeddings.

Either way, dialogue is generated **through cognee recall** (not a direct provider
call), and falls back to authored lines if recall is unavailable.

## Run

```bash
# Seed memories (wipes any old state first)
.venv/bin/python ask.py --reset --seed

# Ask all three NPCs the same question
.venv/bin/python ask.py "Who broke into the shed?" --all

# Inspect what one NPC actually retrieved (proof of dataset isolation / debug)
.venv/bin/python ask.py "Who broke into the shed?" --npc maya --context
```

## API

```bash
.venv/bin/uvicorn api:app --port 8000        # add --reload while developing
```

**Game endpoints** (driven by the React client; all camelCase JSON):

| Method | Path | Purpose |
|---|---|---|
| GET  | `/game/state` | current day, flags, relationships, notebook, ledger |
| POST | `/game/start` | reset game state (`{"reseed":true}` also wipes+reseeds Cognee) |
| POST | `/npc/talk` | `{npcId}` → recalled+validated NPC line, emotion, gated choices |
| POST | `/game/choose` | `{npcId, choiceId}` → apply effects + Cognee memory write-back |
| POST | `/day/advance` | Day 1→2; spreads gossip into shared memory if the player betrayed Maya |
| POST | `/game/conclude` | end + compute the ending from final flags |
| GET  | `/debug/memories/{npcId}` | the NPC's memory ledger (the Memory Debugger feed) |
| GET  | `/locations` | the 3 locations + which NPC is there |

**Legacy debug endpoints** (Phase 1 — proof of dataset isolation): `GET /health`,
`GET /npcs`, `POST /dialogue/respond`, `POST /memory/recall`, `POST /admin/reset`.

```bash
curl -s -X POST localhost:8000/npc/talk -H 'Content-Type: application/json' \
  -d '{"npcId":"maya"}'
```

`/npc/talk` generates the NPC line **through cognee recall** (`only_context=False`,
persona+stance as the system prompt), so all inference goes through cognee (billed to
credits in cloud mode). The line is checked by `validators.py` (locked-fact guardrail
+ 30–45 word limit); **emotion is authored per node** (story.py), not produced by the
model. On any failure (recall error, no key/credits, leak) it serves the node's
authored fallback — story truth never depends on the model. All cognee access is
serialized behind a lock (Kuzu is single-writer). CORS allows the Vite dev server
on `:5173`.

## Success criterion

`--all` returns three meaningfully different, memory-grounded answers:
Maya protects Sam, Sam denies involvement, Jules repeats a rumour.

## Files

| File | Purpose |
|---|---|
| `config.py` | Loads `.env`, pins cognee's local data dirs |
| `npcs.py` | NPC sheets: persona + recall dataset scope (own + shared + `player_profile`) |
| `seeds.py` | The seed memories per dataset |
| `memory.py` | `reset()`, `seed_all()`, `recall_for_npc()`, `remember_event()`, `ensure_connected()` (cloud) |
| `story.py` | **Authored canon**: locations, dialogue nodes, choices+effects, endings, per-node emotion, fallbacks |
| `gamestate.py` | Deterministic state in `game_state.json`: flags, relationships, notebook, ledger |
| `validators.py` | `validate_text()` — locked-fact guardrail + word limit |
| `dialogue.py` | `generate_line()` — cognee recall generation → validated text → authored fallback |
| `devserver_stub.py` | run the API with cognee stubbed (no key) for fast UI testing |
| `test_flow.py` | automated 38-check integration test (no key) |
| `api.py` | FastAPI app (game + legacy debug endpoints) |
| `ask.py` | Phase-1 CLI entrypoint |

Local cognee stores (SQLite/LanceDB/Kuzu) live in `.cognee_system/` and
`.cognee_data/`; delete those for a hard memory reset. Game progress lives in
`game_state.json` (gitignored) — `POST /game/start` resets it.

## Gemini free-tier quota (LOCAL mode only)

> Not relevant in **Cognee Cloud** mode — inference is billed to Cognee credits there.

The Google AI Studio **free tier caps each model at ~20 generate-content requests
per day** (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`). cognee's
GRAPH_COMPLETION recall generates roughly one answer per retrieved source (~3 per
NPC), so a single `--all` run uses ~9 calls and you exhaust a model quickly.

Mitigations used here:
- **Seeding batches each dataset into one `remember()` call** (see `memory.py`) so
  the full seed is ~10 LLM calls, not ~70.
- **Rotate models** when one is exhausted — edit `LLM_MODEL` in `.env`. Verified
  working models on this key: `gemini-2.5-flash`, `gemini-2.5-flash-lite`,
  `gemini-flash-latest`, `gemini-3.1-flash-lite`. (`gemini-2.0-flash` is **not**
  free-tier enabled on this key — limit 0.)
- Quotas reset daily (Pacific midnight). **For real development, enable billing**
  on the Gemini project — this whole demo costs well under a cent on pay-as-you-go.

Verified config: LLM via Gemini (any model above), embeddings
`gemini/gemini-embedding-001` at **3072 dims** (`EMBEDDING_DIMENSIONS=3072` must
match the model's default output, or the vector store breaks).

## Confabulation guardrail

Lower-tier models embellish — e.g. Jules invented "Maya lost the key" and "Omar
accusing Sam," which are NOT in her datasets (design doc **Risk 1**). The game path
now mitigates this: `validators.py` enforces a **locked-fact guardrail** (a generated
line that leaks the lost-key secret before the story has revealed it is rejected) plus
the 30–45 word limit, and `dialogue.generate_line()` falls back to the authored line
on any rejection or quota failure. Story truth, flags, and relationships live in
`gamestate.py`, never in the model.
