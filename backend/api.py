"""FastAPI layer for Neighbourhood Echoes — the surface the React client calls.

Run:
    .venv/bin/uvicorn api:app --reload --port 8000

Two source-of-truth split (plan §5):
  * deterministic game state (day/flags/relationships/notebook/ledger) -> gamestate
  * NPC memory recall + LLM phrasing                                    -> dialogue/memory

Seeding is heavy (LLM calls); prefer the CLI for it:
    .venv/bin/python ask.py --reset --seed
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config  # noqa: F401  -- loads .env + sets cognee dirs on import
import dialogue
import gamestate
import memory
import story
from npcs import NPCS

app = FastAPI(title="Neighbourhood Echoes - Game API", version="0.2.0")

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
    reseed: bool = False


class TalkRequest(BaseModel):
    npcId: str


class ChooseRequest(BaseModel):
    npcId: str
    choiceId: str


class SolveRequest(BaseModel):
    theoryId: str


# Legacy debug models (kept for back-compat with the Phase-1 tools).
class DialogueRequest(BaseModel):
    npc_id: str
    player_input: str


class RecallRequest(BaseModel):
    npc_id: str
    query: str
    context_only: bool = True


# --------------------------------------------------------------------------- #
# Meta
# --------------------------------------------------------------------------- #

@app.get("/health")
async def health():
    return {"status": "ok", "npcs": list(NPCS)}


@app.get("/npcs")
async def list_npcs():
    return [
        {"id": k, "name": v["name"], "location": story.NPC_LOCATION[k],
         "datasets": v["datasets"]}
        for k, v in NPCS.items()
    ]


@app.get("/locations")
async def list_locations():
    return list(story.LOCATIONS.values())


@app.get("/game/catalog")
async def game_catalog():
    """Clue catalog + accusation theories for the UI. Never leaks the solution."""
    return {"clues": story.clues_catalog(), "theories": story.THEORIES}


# --------------------------------------------------------------------------- #
# Game flow (plan §7)
# --------------------------------------------------------------------------- #

@app.get("/game/state")
async def game_state():
    return gamestate.get_state()


@app.post("/game/start")
async def game_start(req: StartRequest):
    """Reset game state. reseed=True also wipes + reseeds Cognee (heavy, LLM calls)."""
    return await gamestate.start(reseed=req.reseed)


@app.post("/npc/talk")
async def npc_talk(req: TalkRequest):
    """Recall context, generate+validate the NPC's line, attach authored choices.
    Read-only — no state mutation here (mutation happens in /game/choose)."""
    if req.npcId not in NPCS:
        raise HTTPException(status_code=404, detail=f"Unknown npcId: {req.npcId}")
    state = gamestate.get_state()
    node_id = state["convo"][req.npcId]
    node = story.NODES[node_id]
    line = await dialogue.generate_line(req.npcId, node, state)
    return {
        "npcId": req.npcId,
        "name": NPCS[req.npcId]["name"],
        "nodeId": node_id,
        "npcLine": line["npcLine"],
        "emotion": line["emotion"],
        "source": line["source"],
        "choices": gamestate.available_choices(node, state),
        "relationship": state["relationships"][req.npcId],
        "day": state["day"],
    }


@app.post("/game/choose")
async def game_choose(req: ChooseRequest):
    """Apply a choice's authored effects (flags, relationship deltas, notebook,
    Cognee memory write-back) and advance the conversation node."""
    if req.npcId not in NPCS:
        raise HTTPException(status_code=404, detail=f"Unknown npcId: {req.npcId}")
    try:
        state, new_clues = await gamestate.apply_choice(req.npcId, req.choiceId)
    except PermissionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"state": state, "nextNodeId": state["convo"][req.npcId], "newClues": new_clues}


@app.post("/day/advance")
async def day_advance():
    """Day 1 -> Day 2; spreads gossip into shared memory if the player betrayed Maya."""
    return await gamestate.advance_day()


@app.post("/game/solve")
async def game_solve(req: SolveRequest):
    """Make the accusation and get the scored result (clues + correctness + trust)."""
    return gamestate.solve(req.theoryId)


@app.get("/debug/memories/{npc_id}")
async def debug_memories(npc_id: str):
    """Memory Debugger feed: this NPC's ledger entries (owner/type/text/day/importance).
    Deterministic — read straight from the ledger, no LLM."""
    if npc_id not in NPCS:
        raise HTTPException(status_code=404, detail=f"Unknown npc_id: {npc_id}")
    state = gamestate.get_state()
    entries = [e for e in state["ledger"] if e["ownerNpc"] in (npc_id, "shared")]
    return {"npcId": npc_id, "memories": entries}


# --------------------------------------------------------------------------- #
# Legacy debug endpoints (Phase-1 — proof of dataset isolation)
# --------------------------------------------------------------------------- #

@app.post("/dialogue/respond")
async def dialogue_respond(req: DialogueRequest):
    try:
        return await dialogue.generate_response(req.npc_id, req.player_input)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown npc_id: {req.npc_id}")


@app.post("/memory/recall")
async def memory_recall(req: RecallRequest):
    if req.npc_id not in NPCS:
        raise HTTPException(status_code=404, detail=f"Unknown npc_id: {req.npc_id}")
    async with memory.LOCK:
        results = await memory.recall_for_npc(
            req.npc_id, req.query, context_only=req.context_only
        )
    return {"npc_id": req.npc_id, "results": [memory.as_text(r) for r in results]}


@app.post("/admin/reset")
async def admin_reset():
    async with memory.LOCK:
        await memory.reset()
    return {"status": "reset"}
