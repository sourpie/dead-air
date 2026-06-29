# Neighbourhood Echoes — Game Client

React + Vite + TypeScript browser game for the Cognee-powered NPC-memory mystery.
A clickable detective board: map → conversations with choices → case notebook →
**Memory Debugger** that shows which NPC remembers which fact.

> This replaced the earlier Godot prototype. The pivot rationale and full design are
> in the repo root `README.md` and the hackathon plan.

## Stack

- **React 19 + Vite 8 + TypeScript**
- **Tailwind CSS v4** (via `@tailwindcss/vite`) — theme tokens live in `src/index.css`
- **Zustand** for state (`src/state/gameStore.ts`)
- No game engine, no router — three screens switch on a `screen` field in the store.

## Run

```bash
npm install
npm run dev          # http://localhost:5173
```

The backend must be running on `http://127.0.0.1:8000` (see `../backend/README.md`).
Override the API base with `VITE_API_URL` if needed:

```bash
VITE_API_URL=http://127.0.0.1:8000 npm run dev
```

`npm run build` runs `tsc -b && vite build` (type-check + production bundle).

## Layout

```
src/
  api/client.ts        typed fetch wrapper, one fn per backend endpoint
  state/gameStore.ts   Zustand store; caches /game/state, drives all calls
  types.ts             TS types mirroring the backend JSON
  data/                display-only NPC + location metadata (canon is backend)
  components/          MapView, LocationCard, NPCPanel, DialogueBox, ChoiceButton,
                       RelationshipMeter, CaseNotebook, MemoryDebugger, HowItWorks
  pages/               StartPage, GamePage, EndingPage
```

## The demo loop

1. **Start** → map of Maple Street (Bakery / Garden / Tea Stall).
2. Talk to **Maya**, earn trust until she admits she lost the shed key, then **promise** to keep it secret.
3. Go to **Jules** and either keep quiet or **tell the secret** (betrayal).
4. **Advance to Day 2** — if you told Jules, the rumour spreads and reaches Maya.
5. Talk to Maya again — she **confronts** you (betrayal) or **confides a clue** (kept secret).
6. **Conclude the Case** for the ending. Open the **Memory Debugger** any time to show
   exactly which NPC's Cognee dataset holds which memory.

The dialogue line is LLM-generated from recalled memory; if the model is unavailable
or a guardrail trips, an authored fallback line is shown (badged `TEMPLATE`). Story
truth, flags, and relationships are always decided by the backend, never the model.
