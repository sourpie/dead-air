"""Validation guardrail between the LLM and the player (plan §7 / §24).

The LLM is asked for JSON {npcLine, emotion}. Before that line ever reaches the
player we:
  1. parse it (Pydantic) — malformed JSON => reject,
  2. reject any line that leaks a *locked fact* whose story gate isn't met yet
     (e.g. an NPC blurting that Maya lost the key before she has confided it),
  3. trim to the plan's 30-45 word pacing budget.

A rejection raises ValueError; the dialogue layer then serves the node's authored
fallback line, so story truth never depends on the model behaving.
"""
import re

from pydantic import BaseModel, field_validator

_MAX_WORDS = 45

EMOTIONS = {
    "neutral", "warm", "anxious", "defensive", "hurt", "angry",
    "relieved", "excited", "smug", "guarded", "sad",
}

# (pattern, flag that must be True for the fact to be sayable). If the flag is
# False and a generated line matches the pattern, it's an early leak => reject.
# Proximity-based so "lost the shed key" / "the key Maya lost" both trip it.
_LOCKED_FACTS = [
    (re.compile(r"lost\b[^.!?]{0,25}\bkey\b", re.I), "mayaRevealedLostKey"),
    (re.compile(r"\bkey\b[^.!?]{0,25}\blost\b", re.I), "mayaRevealedLostKey"),
]


class NpcLine(BaseModel):
    npcLine: str
    emotion: str = "neutral"

    @field_validator("npcLine")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("empty npcLine")
        return v

    @field_validator("emotion")
    @classmethod
    def _known_emotion(cls, v: str) -> str:
        v = (v or "").strip().lower()
        return v if v in EMOTIONS else "neutral"


def _trim_words(text: str, limit: int = _MAX_WORDS) -> str:
    words = text.split()
    if len(words) <= limit:
        return text
    clipped = " ".join(words[:limit])
    # Prefer ending on sentence punctuation within the budget.
    m = re.search(r"^(.*[.!?])", clipped)
    return (m.group(1) if m else clipped.rstrip(",;:") + "…")


def validate_text(text: str, state: dict) -> str:
    """Validate a generated NPC line (plain text) against the current state.

    Returns the (possibly trimmed) line. Raises ValueError on an empty line or a
    locked-fact leak — the caller then falls back to the authored line.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("empty line")
    flags = state.get("flags", {})
    for pattern, required_flag in _LOCKED_FACTS:
        if pattern.search(text) and not flags.get(required_flag):
            raise ValueError(f"locked fact leaked (gate {required_flag} not met)")
    return _trim_words(text)


def validate_line(raw: dict, state: dict) -> tuple[str, str]:
    """Validate a structured {npcLine, emotion} payload (kept for back-compat)."""
    parsed = NpcLine.model_validate(raw)
    return validate_text(parsed.npcLine, state), parsed.emotion
