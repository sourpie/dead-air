"""Direct LLM generation backends — the fast path for dialogue words.

cognee always owns MEMORY (writes, retrieval, per-NPC dataset scoping); this
module only writes the words. Two backends, chosen by LLM_BACKEND in .env:

  * ollama  — local model via the Ollama server (default llama3.1:8b).
              Fast-inference workflow: keep_alive pins the model in RAM,
              warmup() loads it before the first real line, num_predict caps
              generation length, and callers put stable content (persona +
              memories) first so Ollama's prompt-prefix KV cache kicks in for
              consecutive lines from the same NPC.

        LLM_BACKEND=ollama
        OLLAMA_MODEL=llama3.1:8b
        # OLLAMA_URL=http://127.0.0.1:11434   (default)

  * bedrock — GLM 5 on Amazon Bedrock (bedrock-mantle Chat Completions,
              API-key auth — no SigV4).

        LLM_BACKEND=bedrock
        AWS_BEARER_TOKEN_BEDROCK=<Bedrock API key>
        BEDROCK_REGION=ap-south-1
        BEDROCK_MODEL_ID=zai.glm-5
"""
import os
import re

import aiohttp

_TIMEOUT = aiohttp.ClientTimeout(total=90)
_KEEP_ALIVE = "30m"  # keep the local model resident between requests
# Context window for Ollama. Big enough for persona + ~8 memory lines + the
# situation + the answer; tunable for a smaller/faster model. Env-overridable.
_OLLAMA_NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "4096"))

# Some reasoning models inline a scratchpad as <think>...</think>. Strip it.
_THINK_RE = re.compile(r"<think>.*?</think>", re.S)


def backend() -> str | None:
    """The active generation backend, or None → cognee generates the words."""
    b = os.environ.get("LLM_BACKEND", "").lower()
    if b == "ollama":
        return "ollama"
    if b == "bedrock" and os.environ.get("AWS_BEARER_TOKEN_BEDROCK"):
        return "bedrock"
    return None


def enabled() -> bool:
    return backend() is not None


def clean(text: str) -> str:
    return _THINK_RE.sub("", text or "").strip()


async def chat(system: str, user: str, max_tokens: int = 400) -> str:
    """One non-streaming completion on the active backend. Raises on any
    failure — callers have the validate-or-fallback contract."""
    b = backend()
    if b == "ollama":
        return await _ollama_chat(system, user, max_tokens)
    if b == "bedrock":
        return await _bedrock_chat(system, user, max_tokens)
    raise RuntimeError("no LLM backend configured")


async def warmup() -> None:
    """Load the local model into memory so the first real line is fast.
    Called at API startup; best-effort (the model may still be downloading)."""
    if backend() != "ollama":
        return
    try:
        await _ollama_chat("You are a helpful assistant.", "hi", max_tokens=1)
        print(f"  ollama model {_ollama_model()} warmed up")
    except Exception as e:  # noqa: BLE001
        print(f"  ollama warmup skipped: {type(e).__name__}: {str(e)[:80]}")


# ── Ollama (native API: supports keep_alive + num_predict) ──────────────────

def _ollama_model() -> str:
    return os.environ.get("OLLAMA_MODEL", "llama3.1:8b")


async def _ollama_chat(system: str, user: str, max_tokens: int) -> str:
    url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/") + "/api/chat"
    payload = {
        "model": _ollama_model(),
        "stream": False,
        "keep_alive": _KEEP_ALIVE,
        "options": {
            # Cap generation so a rambling model can't stretch a 30-45 word line
            # into hundreds of tokens of latency.
            "num_predict": max_tokens,
            # Size the context to persona + memories + situation so the prompt is
            # never silently truncated (which would drop memories) nor padded to
            # a huge window. Keep it stable so the prompt-prefix KV cache holds.
            "num_ctx": _OLLAMA_NUM_CTX,
        },
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                body = (await resp.text())[:200]
                raise RuntimeError(f"Ollama {resp.status}: {body}")
            data = await resp.json()
    return clean(data["message"]["content"])


# ── Amazon Bedrock (GLM 5 via bedrock-mantle Chat Completions) ───────────────

async def _bedrock_chat(system: str, user: str, max_tokens: int) -> str:
    region = os.environ.get("BEDROCK_REGION", "ap-south-1")
    url = f"https://bedrock-mantle.{region}.api.aws/v1/chat/completions"
    payload = {
        "model": os.environ.get("BEDROCK_MODEL_ID", "zai.glm-5"),
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    headers = {
        "Authorization": f"Bearer {os.environ['AWS_BEARER_TOKEN_BEDROCK']}",
        "Content-Type": "application/json",
    }
    async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                body = (await resp.text())[:200]
                raise RuntimeError(f"Bedrock {resp.status}: {body}")
            data = await resp.json()
    return clean(data["choices"][0]["message"]["content"])
