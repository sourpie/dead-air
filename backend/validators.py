"""Validation guardrail between the LLM and the player.

Before any generated line reaches the player we:
  1. reject empty lines,
  2. enforce the per-run gates the mystery generator emitted —
     * confession gate: the culprit must never admit the act, and must never
       place themselves at the scene during the night,
     * locked-fact gates: keyword co-occurrence sets that block a key fact
       (sighting, door-log gap, secret, motive) until its clue is found,
  3. trim to the 45-word pacing budget.

A rejection raises ValueError; the dialogue layer then serves the deterministic
templated fallback, so story truth never depends on the model behaving. Gates
are deliberately coarse — a false positive only costs us a fallback line.
"""
import re

_MAX_WORDS = 45

# Static admission shapes; combined with the per-run culprit id from the gates.
_ADMISSION = re.compile(
    r"\b(it was me|i did it|i'?m the one|i am the one|"
    r"i (sabotaged|cut|broke|disabled|wrecked|damaged) (it|the|that))\b",
    re.I,
)

# Night-time markers for the placement check (culprit + scene room + night).
_NIGHT = re.compile(r"\b(that night|last night|2[23]:00|0[0-3]:00|midnight)\b", re.I)


def _trim_words(text: str, limit: int = _MAX_WORDS) -> str:
    words = text.split()
    if len(words) <= limit:
        return text
    clipped = " ".join(words[:limit])
    m = re.search(r"^(.*[.!?])", clipped)
    return (m.group(1) if m else clipped.rstrip(",;:") + "…")


def validate_text(text: str, state: dict, speaker: str | None = None) -> str:
    """Validate a generated line against the current state's per-run gates.

    Returns the (possibly trimmed) line. Raises ValueError on an empty line or
    any gate trip — the caller then falls back to the templated line.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("empty line")
    lower = text.lower()
    gates = state.get("case", {}).get("gates", {})

    confession = gates.get("confession")
    if confession and speaker == confession["npc"]:
        if _ADMISSION.search(text):
            raise ValueError("confession gate: admission phrasing")
        scene_word = confession["keywords"][-1]
        if scene_word in lower and _NIGHT.search(text) and re.search(r"\bi\b", lower):
            raise ValueError("confession gate: self-placement at the scene")

    found = set(state.get("cluesFound", []))
    for gate in gates.get("locked", []):
        if gate["clueId"] in found:
            continue
        if all(k in lower for k in gate["keywords"]):
            raise ValueError(f"locked fact leaked (clue {gate['clueId']} not found)")

    return _trim_words(text)
