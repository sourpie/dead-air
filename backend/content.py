"""Authored content banks for DEAD AIR — everything hand-written lives here.

This file replaces the authored role of the old story.py: verbs (the player's
question menu), fallback line templates per (crew, verb), the emotion table,
overhear fallbacks, endings, ranks and scoring weights. Templates have {slots}
filled from the generated case, so fallbacks stay exactly as safe as authored
lines — the case dict is deterministic data.
"""
from mystery import CREW_NAMES, FIRST_NAMES, ROOMS

# --------------------------------------------------------------------------- #
# Verbs — the question menu. Instances are synthesized per state by interview.py
# --------------------------------------------------------------------------- #

VERB_KINDS = ["ask_whereabouts", "ask_sabotage", "ask_about", "present_clue", "confront"]

VERB_LABELS = {
    "ask_whereabouts": "Where were you last night?",
    "ask_sabotage": "What do you know about the sabotage?",
    "ask_about": "What do you make of {otherName}?",
    "present_clue": "Show them: {clueTitle}",
    # confront labels come from the case's contradiction records
}

# --------------------------------------------------------------------------- #
# Fallback line templates per (crew, verb kind) — served whenever generation
# fails or a guardrail trips. Slots: {claimText}, {targetName}, {sceneRoom},
# {otherFirst}, {itemText}, {resolutionText}.
# --------------------------------------------------------------------------- #

FALLBACK_LINES = {
    "oda": {
        "ask_whereabouts": "{claimText} That is all in my report.",
        "ask_sabotage": "The {targetName} was deliberately damaged. Until the review is complete, I won't speculate about my crew.",
        "ask_about": "{otherFirst} serves this station. I don't discuss my crew behind their backs.",
        "present_clue": "Noted. Log it properly — evidence handled sloppily is evidence lost.",
        "confront": "…I run this station. Choose your next words carefully.",
        "free_text": "That is not a question I am prepared to entertain right now.",
    },
    "vega": {
        "ask_whereabouts": "{claimText} Check the logs if you don't believe me — oh wait, everyone always blames the engineer anyway.",
        "ask_sabotage": "Whoever cut the {targetName} knew where to reach. That's all I'll say — and no, knowing the system doesn't make me guilty.",
        "ask_about": "{otherFirst}? Ask them yourself. I keep my head in the machines.",
        "present_clue": "Where exactly did you find that? Because I know where it's supposed to live.",
        "confront": "That's— you're twisting it. The readouts will back me up.",
        "free_text": "Look, I've got a station held together with tape. Make it quick.",
    },
    "lin": {
        "ask_whereabouts": "{claimText} Nights are long up here when you can't sleep.",
        "ask_sabotage": "The {targetName}, deliberately… it makes me sick to think one of us did it.",
        "ask_about": "{otherFirst} has been under strain lately. We all have. Be kind when you talk to them.",
        "present_clue": "Oh… oh dear. You should show this to the Captain, gently.",
        "confront": "I— please, let me explain it properly, it isn't what it looks like.",
        "free_text": "Sorry, my head's elsewhere. Ask me again, slowly?",
    },
    "rio": {
        "ask_whereabouts": "{claimText} Boring answer, I know. Not every night is a story.",
        "ask_sabotage": "Officially? No comment. Unofficially? Everyone's whispering and half of it contradicts the other half.",
        "ask_about": "{otherFirst}? Now THERE'S a conversation. Buy me a coffee sometime and I'll tell you what I've heard.",
        "present_clue": "Ooooh. Do you know what this means? Because I could find out.",
        "confront": "Okay— okay. That's not… whoever told you that is missing context.",
        "free_text": "You ask fun questions. Wrong channel though — try me later.",
    },
    "nova": {
        "ask_whereabouts": "{claimText} Why — what have you heard?",
        "ask_sabotage": "The {targetName} failing is convenient for somebody. Work out who benefits and you won't need me.",
        "ask_about": "{otherFirst}? Competent. Beyond that, form your own assessment.",
        "present_clue": "Interesting. And you're showing me because…?",
        "confront": "…You've been thorough. I'll give you that.",
        "free_text": "I don't answer questions I haven't heard the reason for.",
    },
}

# Gossip discretion — whether a crewmate passes on what the investigator tells
# them privately. Deterministic per persona; matches the character sheets:
#   never       — keeps confidences (Oda: "gossip is corrosion"; Nova: hoards info)
#   accusations — only spreads direct accusations (Vega warns people, paranoid)
#   always      — spreads anything juicy (Lin can't help it; Rio is the rumour mill,
#                 and Rio's retellings ALSO land in the shared rumours dataset)
GOSSIP_DISCRETION = {
    "oda": "never",
    "vega": "accusations",
    "lin": "always",
    "rio": "always",
    "nova": "never",
}

# Zero-call greetings: /npc/talk serves these instantly (no generation) — the
# LLM spends credits only on actual questions (/npc/ask, /npc/say).
GREETINGS = {
    "oda": "Investigator. Ask what you need to ask — my crew has work to do.",
    "vega": "Let me guess. Everyone says check with the engineer. Fine. Ask.",
    "lin": "Oh — hello. Awful business, isn't it? Sit, ask me anything.",
    "rio": "Well well, the investigator. I was wondering when you'd get to me.",
    "nova": "You're doing the rounds. Efficient. What do you want to know?",
}

# --------------------------------------------------------------------------- #
# Emotions — authored per (verb kind, pressure bucket), never model-chosen.
# pressure = number of contradictions already landed on that NPC.
# --------------------------------------------------------------------------- #

EMOTIONS = {
    "ask_whereabouts": {0: "neutral", 1: "guarded", 2: "defensive"},
    "ask_sabotage": {0: "guarded", 1: "guarded", 2: "defensive"},
    "ask_about": {0: "neutral", 1: "neutral", 2: "guarded"},
    "present_clue": {0: "guarded", 1: "anxious", 2: "defensive"},
    "confront": {0: "defensive", 1: "angry", 2: "angry"},
    "free_text": {0: "neutral", 1: "guarded", 2: "defensive"},
}

# Persona base overrides at zero pressure (Lin stays warm, Rio stays excited).
EMOTION_BASE = {"oda": "neutral", "vega": "guarded", "lin": "warm", "rio": "excited", "nova": "guarded"}


def emotion_for(npc_id: str, verb_kind: str, pressure: int) -> str:
    bucket = min(pressure, 2)
    if bucket == 0 and verb_kind in ("ask_about", "free_text"):
        return EMOTION_BASE[npc_id]
    return EMOTIONS.get(verb_kind, EMOTIONS["free_text"])[bucket]


# --------------------------------------------------------------------------- #
# Overhear fallback — a templated two-line exchange from the topic text, used
# when generation fails or the A:/B: parse does. The information (clue grant)
# never depends on this text.
# --------------------------------------------------------------------------- #

def overhear_fallback(a_id: str, b_id: str, topic_text: str) -> list[dict]:
    return [
        {"speaker": a_id, "text": f"…keep this between us. {topic_text}"},
        {"speaker": b_id, "text": "You're sure? …That changes things."},
    ]


# --------------------------------------------------------------------------- #
# Endings, ranks, scoring
# --------------------------------------------------------------------------- #

TOTAL_CLUES = 7

SCORE_WEIGHTS = {"perClue": 10, "correctAccusation": 40, "flustered": 10}


def ending_text(accused: str, culprit: str, motive: str) -> dict:
    correct = accused == culprit
    if correct:
        return {
            "id": "ejected_saboteur",
            "headline": f"{CREW_NAMES[accused]} was The Saboteur.",
            "body": (f"Under the emergency lights, {FIRST_NAMES[accused]} finally stops arguing. "
                     f"The truth: {motive}. The shuttle docks at dawn to take them home for trial. "
                     f"K-7 exhales."),
        }
    return {
        "id": "ejected_innocent",
        "headline": f"{CREW_NAMES[accused]} was not The Saboteur.",
        "body": (f"{FIRST_NAMES[accused]} protests to the last. Weeks later, long after the transfer "
                 f"shuttle has gone, a maintenance drone finds the truth you missed — it was "
                 f"{CREW_NAMES[culprit]} all along. The case file closes wrong."),
    }


def rank_for(correct: bool, clues_found: int, flustered: int) -> dict:
    if correct and clues_found >= 5:
        return {"title": "Station Hero", "icon": "🏆",
                "blurb": "Airtight case, right crewmate ejected. K-7 sleeps easy."}
    if correct and flustered >= 1:
        return {"title": "Sharp Interrogator", "icon": "🕵️",
                "blurb": "You broke their story face to face, then called the meeting."}
    if correct:
        return {"title": "Lucky Shot", "icon": "🎯",
                "blurb": "Right call — thin file. The tribunal will want more than instinct."}
    if clues_found >= 4:
        return {"title": "Wrong Airlock", "icon": "🚪",
                "blurb": "Good evidence, wrong read. The saboteur watched you do it."}
    return {"title": "Spaced the Truth", "icon": "🌑",
            "blurb": "An innocent took the fall and the file stayed open."}


def compute_result(state: dict, accused: str) -> dict:
    case = state["case"]
    culprit = case["culpritId"]
    correct = accused == culprit
    clues_found = len(state["cluesFound"])
    flustered = state.get("flustered", {}).get(culprit, 0)
    score = (clues_found * SCORE_WEIGHTS["perClue"]
             + (SCORE_WEIGHTS["correctAccusation"] if correct else 0)
             + min(flustered, 2) * SCORE_WEIGHTS["flustered"])
    stars = 3 if (correct and clues_found >= 5) else 2 if correct else 1 if clues_found >= 4 else 0
    return {
        "accused": accused,
        "accusedName": CREW_NAMES[accused],
        "saboteur": culprit,
        "saboteurName": CREW_NAMES[culprit],
        "wasSaboteur": correct,
        "solvedCorrectly": correct,
        "score": score,
        "stars": stars,
        "maxStars": 3,
        "cluesFound": clues_found,
        "totalClues": TOTAL_CLUES,
        "flustered": flustered,
        "rank": rank_for(correct, clues_found, flustered),
        "narrative": ending_text(accused, culprit, case["motive"]),
    }
