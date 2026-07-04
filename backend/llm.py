"""Direct LLM generation via Amazon Bedrock (GLM 5) — the fast path.

When LLM_BACKEND=bedrock, dialogue generation splits in two: cognee still does
memory (remember + retrieval + per-NPC dataset scoping), but the WORDS are
written by GLM 5 on Bedrock, which is much faster than cognee's recall
generation mode and gives us model control.

Uses the bedrock-mantle Chat Completions endpoint (the one AWS recommends)
with Bedrock API-key auth — no SigV4, just AWS_BEARER_TOKEN_BEDROCK:

    LLM_BACKEND=bedrock
    AWS_BEARER_TOKEN_BEDROCK=<Bedrock API key>
    BEDROCK_REGION=ap-south-1
    BEDROCK_MODEL_ID=zai.glm-5

Model card: https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-zai-glm-5.html
"""
import os
import re

import aiohttp

DEFAULT_MODEL = "zai.glm-5"
_TIMEOUT = aiohttp.ClientTimeout(total=60)

# GLM is a reasoning model family; some servings inline the scratchpad as
# <think>...</think> before the answer. Strip it defensively.
_THINK_RE = re.compile(r"<think>.*?</think>", re.S)


def enabled() -> bool:
    return (
        os.environ.get("LLM_BACKEND", "").lower() == "bedrock"
        and bool(os.environ.get("AWS_BEARER_TOKEN_BEDROCK"))
    )


def _endpoint() -> str:
    region = os.environ.get("BEDROCK_REGION", "ap-south-1")
    return f"https://bedrock-mantle.{region}.api.aws/v1/chat/completions"


def clean(text: str) -> str:
    return _THINK_RE.sub("", text or "").strip()


async def chat(system: str, user: str, max_tokens: int = 400) -> str:
    """One non-streaming completion. Raises on any failure — callers already
    have the validate-or-fallback contract, so errors just mean a templated line."""
    payload = {
        "model": os.environ.get("BEDROCK_MODEL_ID", DEFAULT_MODEL),
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
        async with session.post(_endpoint(), json=payload, headers=headers) as resp:
            if resp.status != 200:
                body = (await resp.text())[:200]
                raise RuntimeError(f"Bedrock {resp.status}: {body}")
            data = await resp.json()
    return clean(data["choices"][0]["message"]["content"])
