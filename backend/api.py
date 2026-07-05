"""FastAPI layer for DEAD AIR — the surface the React client calls.

Run:
    .venv/bin/uvicorn api:app --reload --port 8000

Two source-of-truth split:
  * deterministic game state (case/schedule/clues/relationships/ledger) -> gamestate
  * NPC memory recall + LLM phrasing                                     -> dialogue/memory

Every response goes through gamestate.public_state() — the redaction boundary
that keeps the culprit, the lies, the gates and unfired gossip server-side.
"""
import asyncio
import pathlib

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import config  # noqa: F401  -- loads .env + sets cognee dirs on import
import content
import crew
import dialogue
import gamestate
import interview
import llm
import memory
import mystery
from crew import CREW

app = FastAPI(title="DEAD AIR - Game API", version="0.3.0")


@app.on_event("startup")
async def _warm_local_model():
    # Ollama: load the model into RAM before the first real line (best-effort).
    asyncio.get_running_loop().create_task(llm.warmup())

# The Vite dev server (localhost:5173) calls this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #

class StartRequest(BaseModel):
    seed: int | None = None
    reseed: bool = True


class TalkRequest(BaseModel):
    npcId: str


class AskRequest(BaseModel):
    npcId: str
    verb: str
    arg: str | None = None


class SayRequest(BaseModel):
    npcId: str
    text: str


class AdvanceRequest(BaseModel):
    playerRoom: str | None = None


class OverhearRequest(BaseModel):
    encounterId: str
    playerRoom: str


class PrewarmRequest(BaseModel):
    encounterId: str


class ExamineRequest(BaseModel):
    spotId: str


class AccuseRequest(BaseModel):
    npcId: str


def _check_npc(npc_id: str) -> None:
    if npc_id not in CREW:
        raise HTTPException(status_code=404, detail=f"Unknown npcId: {npc_id}")


# --------------------------------------------------------------------------- #
# Meta
# --------------------------------------------------------------------------- #

@app.get("/health")
async def health():
    return {"status": "ok", "crew": list(CREW)}


@app.get("/game/catalog")
async def game_catalog():
    """Static-ish display data: crew, rooms, adjacency. Never leaks the case."""
    return {
        "crew": [{"id": c["id"], "name": c["name"], "post": c["post"]} for c in CREW.values()],
        "rooms": mystery.ROOMS,
        "adjacency": mystery.ADJACENCY,
    }


# --------------------------------------------------------------------------- #
# Game flow
# --------------------------------------------------------------------------- #

@app.get("/game/state")
async def game_state():
    return gamestate.public_state()


@app.post("/game/start")
async def game_start(req: StartRequest):
    """New run: fresh case + schedule immediately; memory forget+seed runs in
    the background (state.seeding tracks it — early lines fall back safely)."""
    await gamestate.start(seed=req.seed, reseed=req.reseed)
    return gamestate.public_state()


@app.post("/npc/talk")
async def npc_talk(req: TalkRequest):
    """Open a conversation: zero-call templated greeting + the live verb menu.
    Also pre-warms this NPC's memory-context cache in the background so the
    player's first real question doesn't pay the retrieval round trip."""
    _check_npc(req.npcId)
    state = gamestate.get_state()
    asyncio.get_running_loop().create_task(dialogue.prefetch_context(req.npcId, state))
    return {
        "npcId": req.npcId,
        "name": CREW[req.npcId]["name"],
        "npcLine": content.GREETINGS[req.npcId],
        "emotion": content.emotion_for(req.npcId, "free_text", 0),
        "source": "script",
        "verbs": interview.available_verbs(state, req.npcId),
        "relationship": state["relationships"][req.npcId],
        "shift": state["shift"],
    }


@app.post("/npc/ask")
async def npc_ask(req: AskRequest):
    """One verb beat: deterministic effects first, then the generated line."""
    _check_npc(req.npcId)
    try:
        applied = gamestate.apply_verb(req.npcId, req.verb, req.arg)
    except PermissionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    state = applied["state"]
    node = interview.synth_node(state, req.npcId, req.verb, req.arg)
    label = next((v["label"] for v in interview.available_verbs(state, req.npcId)
                  if v["verb"] == req.verb and v["arg"] == req.arg), None)
    line = await dialogue.generate_line(req.npcId, node, state, player_said=label)
    return {
        "npcId": req.npcId,
        "name": CREW[req.npcId]["name"],
        "npcLine": line["npcLine"],
        "emotion": line["emotion"],
        "source": line["source"],
        "verbs": interview.available_verbs(state, req.npcId),
        "relationship": state["relationships"][req.npcId],
        "newClues": applied["newClues"],
        "newStatements": applied["newStatements"],
        "state": gamestate.public_state(),
    }


@app.post("/npc/say")
async def npc_say(req: SayRequest):
    """Free-text investigator line — memory write-back + memory-grounded reply."""
    _check_npc(req.npcId)
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")
    if len(text) > 240:
        raise HTTPException(status_code=400, detail="Text too long (max 240 chars)")
    state = await gamestate.apply_free_text(req.npcId, text)
    line = await dialogue.generate_free_reply(req.npcId, state, text)
    return {
        "npcId": req.npcId,
        "name": CREW[req.npcId]["name"],
        "npcLine": line["npcLine"],
        "emotion": line["emotion"],
        "source": line["source"],
        "relationship": state["relationships"][req.npcId],
        "state": gamestate.public_state(),
    }


@app.post("/shift/advance")
async def shift_advance(req: AdvanceRequest):
    """Close the shift: fire its gossip transfers, open the next shift's plan."""
    r = gamestate.advance_shift(req.playerRoom)
    return {"state": gamestate.public_state(), "firedTransfers": r["firedTransfers"]}


@app.post("/encounter/prewarm")
async def encounter_prewarm(req: PrewarmRequest):
    """Warm both speakers' memory-context caches as the player approaches an
    encounter, so leaning in generates the exchange without paying the cognee
    retrieval round trip. Fire-and-forget — returns immediately."""
    npcs = gamestate.encounter_npcs(req.encounterId)
    if npcs:
        state = gamestate.get_state()
        loop = asyncio.get_running_loop()
        for npc_id in npcs:
            loop.create_task(dialogue.prefetch_context(npc_id, state))
    return {"ok": bool(npcs)}


@app.post("/encounter/overhear")
async def encounter_overhear(req: OverhearRequest):
    """Eavesdrop an active encounter. Clue grant is deterministic; the lines are
    generated lazily (one cognee call) and fall back to a template on failure."""
    try:
        r = gamestate.apply_overhear(req.encounterId, req.playerRoom)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    exchange = await dialogue.generate_exchange(r["state"], r["encounter"])
    return {
        "encounterId": req.encounterId,
        "lines": exchange["lines"],
        "source": exchange["source"],
        "newClues": r["newClues"],
        "state": gamestate.public_state(),
    }


@app.post("/world/examine")
async def world_examine(req: ExamineRequest):
    try:
        state, new_clues, result = gamestate.examine(req.spotId)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown spotId: {req.spotId}")
    return {"state": gamestate.public_state(), "newClues": new_clues, **result}


@app.post("/game/accuse")
async def game_accuse(req: AccuseRequest):
    """The emergency meeting: eject one crewmate, get the scored result."""
    _check_npc(req.npcId)
    gamestate.accuse(req.npcId)
    return gamestate.public_state()


# --------------------------------------------------------------------------- #
# Debug (the Memory Debugger UI + dataset watching)
# --------------------------------------------------------------------------- #

@app.get("/debug/memories/{npc_id}")
async def debug_memories(npc_id: str):
    _check_npc(npc_id)
    state = gamestate.get_state()
    entries = [
        e for e in state["ledger"]
        if e["ownerNpc"] in (npc_id, "shared")
        or npc_id in e.get("participants", [])
        or any(f"npc_{npc_id}_" in d for d in e.get("datasets", []))
    ]
    return {"npcId": npc_id, "memories": entries}


@app.get("/debug/datasets")
async def debug_datasets():
    """Watch per-run dataset lifecycle + which cognee capabilities are live."""
    state = gamestate.get_state()
    return {
        "runId": state["run"]["runId"], "seeding": state["run"]["seeding"],
        "datasets": state["run"]["datasets"],
        "features": {
            "granular": memory.GRANULAR,      # add()+cognify()+search() graph pipeline
            "temporal": memory.TEMPORAL,      # temporal_cognify -> Event/Timestamp nodes
            "ontology": memory.ONTOLOGY,      # OWL grounding (ontology_valid)
            "memify": memory.MEMIFY,          # post-seed enrichment
            "feedbackInfluence": memory.FEEDBACK_INFLUENCE,
            "feedbackLearn": memory.FEEDBACK_LEARN,
            "searchTypes": {"whereabouts": "TEMPORAL", "confront": "GRAPH_COMPLETION_COT",
                            "free_text": "HYBRID_COMPLETION", "default": "GRAPH_COMPLETION"},
        },
    }


_GRAPH_DIR = pathlib.Path(__file__).resolve().parent / ".graphs"


@app.get("/debug/graph/{npc_id}", response_class=HTMLResponse)
async def debug_graph(npc_id: str):
    """Render cognee's own knowledge-graph visualisation of one crewmate's
    memory dataset — the entities + relations cognify extracted, grounded by the
    ontology. The demo money-shot: see who-knows-what as an actual graph."""
    _check_npc(npc_id)
    state = gamestate.get_state()
    dataset = crew.own_dataset(npc_id, state["run"]["runId"])
    _GRAPH_DIR.mkdir(exist_ok=True)
    out = _GRAPH_DIR / f"graph_{npc_id}.html"
    path = await memory.visualize_dataset(dataset, str(out))
    if not path or not pathlib.Path(path).exists():
        raise HTTPException(status_code=503,
                            detail="Graph visualisation unavailable (not seeded, or cloud mode).")
    return HTMLResponse(pathlib.Path(path).read_text())


@app.get("/debug/provenance", response_class=HTMLResponse)
async def debug_provenance():
    """cognee's memory-provenance graph — where every memory came from."""
    _GRAPH_DIR.mkdir(exist_ok=True)
    out = _GRAPH_DIR / "provenance.html"
    path = await memory.visualize_provenance(str(out))
    if not path or not pathlib.Path(path).exists():
        raise HTTPException(status_code=503, detail="Provenance graph unavailable.")
    return HTMLResponse(pathlib.Path(path).read_text())


class AskGraphRequest(BaseModel):
    query: str


@app.post("/debug/ask")
async def debug_ask(req: AskGraphRequest):
    """Investigator console: ask the station's memory graph in natural language
    (cognee NL -> Cypher). Read-only debug tool, scoped to this run's datasets."""
    q = req.query.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Empty query")
    state = gamestate.get_state()
    answer = await memory.ask_graph(state["run"]["datasets"], q)
    return {"query": q, "answer": answer or "(no answer — graph query unavailable in this mode)"}
