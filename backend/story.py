"""Authored canonical story — the deterministic truth of the game.

The LLM only *phrases* lines; this module decides *what is true and what branches*.
Flags, relationship deltas, branch outcomes, and the memories that get written all
live here, never in the model (plan §5 / §11).

Structure:
  LOCATIONS     - the 3 clickable places and which NPC is there
  NODES         - flat map of dialogue nodes keyed by node id
                  each: {npc, day, stance, fallback, choices[]}
  start_node()  - the entry node for an (npc, day), branched on flags for day 2
  ENDINGS       - the 2-3 outcomes, chosen by compute_ending(state)

A `choice` is:
  {
    "id": str, "text": str, "next": <node id or None>,
    "requires": {"flags": {...}, "minRel": {"maya.trust": 65}},   # optional gate
    "effects": {                                                  # applied on /game/choose
        "trust": int, "suspicion": int,        # delta to the NPC being talked to
        "rel": {"sam": {"suspicion": 5}},       # cross-NPC deltas (optional)
        "flags": {"playerPromisedMaya": True},
        "notebook": ["clue text", ...],
        "events": [ <memory event>, ... ],      # written to ledger + Cognee
    },
  }

A memory `event` (plan §6 schema). `datasets` says where remember_event writes it:
  {"type","ownerNpc","canonicalText","source","day","importance",
   "privacy","truthStatus","relatedQuest","datasets":[...]}
"""

# --------------------------------------------------------------------------- #
# Locations
# --------------------------------------------------------------------------- #

LOCATIONS = {
    "bakery": {
        "id": "bakery",
        "name": "Maya's Bakery",
        "blurb": "The warm social heart of Maple Street. Flour in the air, tension underneath.",
        "npc": "maya",
    },
    "garden": {
        "id": "garden",
        "name": "Community Garden",
        "blurb": "Vegetable plots and the broken-into shed at the far end.",
        "npc": "sam",
    },
    "teastall": {
        "id": "teastall",
        "name": "The Tea Stall",
        "blurb": "Where every rumour on the street is poured along with the chai.",
        "npc": "jules",
    },
}

NPC_LOCATION = {v["npc"]: k for k, v in LOCATIONS.items()}


# --------------------------------------------------------------------------- #
# Memory event builders (the canonical text written into Cognee + the ledger)
# --------------------------------------------------------------------------- #

def _promise_event():
    return {
        "type": "promise", "ownerNpc": "maya",
        "canonicalText": "The player promised Maya they would not tell Jules that Maya lost the community garden shed key.",
        "source": "direct_conversation", "day": 1, "importance": 0.9,
        "privacy": "secret", "truthStatus": "true", "relatedQuest": "shed_mystery",
        "datasets": ["npc_maya_memory", "player_profile"],
    }


def _secret_event():
    return {
        "type": "secret", "ownerNpc": "maya",
        "canonicalText": "Maya confided to the player that she borrowed the shed key last week and lost it, and is ashamed of it.",
        "source": "direct_conversation", "day": 1, "importance": 0.85,
        "privacy": "secret", "truthStatus": "true", "relatedQuest": "shed_mystery",
        "datasets": ["npc_maya_memory"],
    }


def _gossip_event():
    return {
        "type": "gossip", "ownerNpc": "jules",
        "canonicalText": "The player told Jules that Maya lost the community garden shed key, despite having promised Maya secrecy.",
        "source": "direct_conversation", "day": 1, "importance": 0.85,
        "privacy": "public", "truthStatus": "true", "relatedQuest": "shed_mystery",
        "datasets": ["npc_jules_memory"],
    }


def _sam_clue_event():
    return {
        "type": "clue", "ownerNpc": "sam",
        "canonicalText": "Sam told the player the shed latch was already loose and rusty before that morning, so it did not need to be forced.",
        "source": "direct_conversation", "day": 1, "importance": 0.7,
        "privacy": "public", "truthStatus": "true", "relatedQuest": "shed_mystery",
        "datasets": ["npc_sam_memory"],
    }


# Written by /day/advance when the player betrayed Maya — the "memory travelled" beat.
def day_advance_spread_events():
    return [
        {
            "type": "gossip", "ownerNpc": "shared",
            "canonicalText": "Word is spreading on Maple Street that Maya lost the shed key and that Jules found out about it.",
            "source": "gossip_spread", "day": 2, "importance": 0.8,
            "privacy": "public", "truthStatus": "true", "relatedQuest": "shed_mystery",
            "datasets": ["shared_neighbourhood_rumours"],
        },
        {
            "type": "betrayal", "ownerNpc": "maya",
            "canonicalText": "Maya has learned that Jules now knows about the lost key. She believes the player broke their promise and betrayed her trust.",
            "source": "gossip_spread", "day": 2, "importance": 0.95,
            "privacy": "public", "truthStatus": "true", "relatedQuest": "shed_mystery",
            "datasets": ["npc_maya_memory"],
        },
    ]


# --------------------------------------------------------------------------- #
# Dialogue nodes
# --------------------------------------------------------------------------- #

NODES = {
    # ---- MAYA — Day 1 (Bakery) ------------------------------------------- #
    "maya_start": {
        "npc": "maya", "day": 1,
        "stance": "Maya is anxious and guarded about the shed break-in, protective of her brother Sam. She greets the newcomer warily.",
        "fallback": "Oh — you're the new face on the street. If you're here about the shed, I've nothing to say. Sam had nothing to do with it.",
        "choices": [
            {"id": "maya_reassure", "text": "You look shaken. I'm not here to cause trouble.",
             "next": "maya_ajar", "effects": {"trust": 10, "suspicion": -2}},
            {"id": "maya_probe", "text": "Were you involved in the shed break-in?",
             "next": "maya_guarded", "effects": {"suspicion": 6, "trust": -3}},
        ],
    },
    "maya_ajar": {
        "npc": "maya", "day": 1,
        "stance": "Maya is softening but still protective of Sam. She is testing whether the player can be trusted.",
        "fallback": "You seem kind enough. It's just... this whole thing has me frightened for Sam. People talk so easily around here.",
        "choices": [
            {"id": "maya_support_sam", "text": "Whatever happened, I won't let Sam be blamed unfairly.",
             "next": "maya_trusting", "effects": {"trust": 10}},
            {"id": "maya_probe2", "text": "Just tell me what you're hiding.",
             "next": "maya_guarded", "effects": {"suspicion": 5, "trust": -3}},
        ],
    },
    "maya_trusting": {
        "npc": "maya", "day": 1,
        "stance": "Maya now trusts the player enough to confide, but is still ashamed and afraid of what she is about to admit.",
        "fallback": "You're the first person who hasn't pointed a finger at Sam. Maybe I can tell you the truth of it.",
        "choices": [
            {"id": "maya_ask_key", "text": "Did you lose the shed key, Maya?",
             "next": "maya_reveal_key",
             "requires": {"minRel": {"maya.trust": 65}},
             "effects": {
                 "flags": {"mayaRevealedLostKey": True},
                 "clues": ["maya_lost_key"],
                 "notebook": ["Maya admits she borrowed the community garden shed key and lost it."],
                 "events": [_secret_event()],
             }},
        ],
    },
    "maya_reveal_key": {
        "npc": "maya", "day": 1,
        "stance": "Maya has just admitted she lost the key. She is ashamed and pleads with the player to keep it quiet — especially from Jules, who would spread it everywhere.",
        "fallback": "Yes. I borrowed the key and I lost it. If Jules hears, the whole street will think Sam used it to break in. Please — keep this between us.",
        "choices": [
            {"id": "maya_promise", "text": "I promise I won't tell Jules about the key.",
             "next": "maya_promised",
             "effects": {
                 "trust": 12,
                 "flags": {"playerPromisedMaya": True},
                 "notebook": ["You promised Maya you would keep the lost key a secret from Jules."],
                 "events": [_promise_event()],
             }},
            {"id": "maya_no_promise", "text": "I can't promise to keep this quiet.",
             "next": "maya_declined",
             "effects": {"trust": -10, "suspicion": 5}},
        ],
    },
    "maya_promised": {
        "npc": "maya", "day": 1,
        "stance": "Maya is relieved and grateful that the player promised to keep her secret. She is warm.",
        "fallback": "Thank you. Truly. I'll sleep a little easier knowing you'll keep this between us.",
        "choices": [],
    },
    "maya_declined": {
        "npc": "maya", "day": 1,
        "stance": "Maya is hurt and withdrawn that the player would not promise discretion.",
        "fallback": "I see. Then I've said too much already. Please just... leave it alone.",
        "choices": [],
    },
    "maya_guarded": {
        "npc": "maya", "day": 1,
        "stance": "Maya is deflecting and will not reveal anything. She feels accused.",
        "fallback": "I don't know what you're implying, but I don't appreciate it. Buy something or move along.",
        "choices": [
            {"id": "maya_apologize", "text": "I'm sorry — I didn't mean to accuse you.",
             "next": "maya_ajar", "effects": {"trust": 6, "suspicion": -4}},
        ],
    },

    # ---- MAYA — Day 2 (Bakery) ------------------------------------------- #
    "maya_d2_confront": {
        "npc": "maya", "day": 2,
        "stance": "Maya has learned Jules knows about the lost key. She is hurt and angry and confronts the player for betraying the promise. This is the emotional climax.",
        "fallback": "You told her, didn't you? I trusted you with one thing. One thing. Now the whole street is whispering about my key — and about Sam.",
        "choices": [
            {"id": "maya_d2_apologize", "text": "I'm sorry, Maya. I shouldn't have told Jules.",
             "next": "maya_d2_cold", "effects": {"trust": 4, "suspicion": -2}},
            {"id": "maya_d2_deny", "text": "I never said a word to her.",
             "next": "maya_d2_cold", "effects": {"trust": -6, "suspicion": 6}},
        ],
    },
    "maya_d2_cold": {
        "npc": "maya", "day": 2,
        "stance": "Maya is still wounded and distant, but admits the truth about the latch so this can be over. Trust is damaged.",
        "fallback": "It doesn't matter now. Just so you know — the latch was already broken. Sam never forced anything. Now please, let me work.",
        "choices": [],
    },
    "maya_d2_trust": {
        "npc": "maya", "day": 2,
        "stance": "Maya kept her trust in the player intact. She is warm and grateful, and confides a helpful clue: Sam later found the key on the path.",
        "fallback": "Thank you for keeping my secret. I'll tell you what I couldn't yesterday: Sam found my key on the garden path afterwards. He never broke in — the latch was already loose.",
        "choices": [
            {"id": "maya_d2_take_clue", "text": "That clears Sam. Thank you for trusting me.",
             "next": "maya_d2_trust",
             "effects": {
                 "flags": {"mayaRevealedSamClue": True},
                 "clues": ["sam_found_key"],
                 "notebook": ["Maya reveals Sam found the lost key on the path later — he never broke in; the latch was already loose."],
             }},
        ],
    },
    "maya_d2_neutral": {
        "npc": "maya", "day": 2,
        "stance": "Maya is distant and unsure about the player, since they never earned her confidence. Polite but closed.",
        "fallback": "Morning. I've nothing new to say about the shed. Best to ask around if you're so curious.",
        "choices": [],
    },

    # ---- SAM — Day 1 (Garden) -------------------------------------------- #
    "sam_start": {
        "npc": "sam", "day": 1,
        "stance": "Sam is nervous and defensive, terrified of being blamed for the break-in he did not commit.",
        "fallback": "Whatever you heard, it wasn't me. I was near the shed, yeah, but I didn't touch the lock. Why does everyone look at me like that?",
        "choices": [
            {"id": "sam_reassure", "text": "I don't think you did it, Sam.",
             "next": "sam_open", "effects": {"trust": 8, "suspicion": -3}},
            {"id": "sam_accuse", "text": "You were right there. Did you break in?",
             "next": "sam_defensive", "effects": {"suspicion": 8, "trust": -4}},
        ],
    },
    "sam_open": {
        "npc": "sam", "day": 1,
        "stance": "Sam relaxes a little and shares what he knows: the latch was already loose, and he found a brass key on the path.",
        "fallback": "Okay. The latch was already broken — rusty for months. And... I found a little brass key on the path a few days back. I never told anyone. I was scared how it'd look.",
        "choices": [
            {"id": "sam_note_latch", "text": "So the shed didn't need forcing at all.",
             "next": "sam_open",
             "effects": {
                 "flags": {"samSharedAlibi": True},
                 "clues": ["latch_broken", "sam_near_shed"],
                 "notebook": ["Sam: the shed latch was already loose; he also found a brass key on the path."],
                 "events": [_sam_clue_event()],
             }},
        ],
    },
    "sam_defensive": {
        "npc": "sam", "day": 1,
        "stance": "Sam shuts down completely, feeling accused like everyone else.",
        "fallback": "Of course. Blame Sam, like always. I'm done talking.",
        "choices": [],
    },

    # ---- SAM — Day 2 (Garden) -------------------------------------------- #
    "sam_d2_rumour": {
        "npc": "sam", "day": 2,
        "stance": "Sam has heard the rumour spreading and is more frightened and defensive than ever.",
        "fallback": "Now people are saying it for sure was me, all because of some story going round. I knew this would happen. I knew it.",
        "choices": [],
    },
    "sam_d2_calm": {
        "npc": "sam", "day": 2,
        "stance": "Sam is calmer; the rumour did not spread, so he feels a little safer.",
        "fallback": "It's been quieter today. Maybe people are finally letting it go. I just want this over with.",
        "choices": [],
    },

    # ---- JULES — Day 1 (Tea Stall) --------------------------------------- #
    "jules_start": {
        "npc": "jules", "day": 1,
        "stance": "Jules is curious and gossipy, fishing the newcomer for any juicy detail about the shed.",
        "fallback": "Ahh, the new face! Sit, sit. So — what do YOU make of the shed business? I have theories. I always have theories.",
        "choices": [
            {"id": "jules_smalltalk", "text": "What's the word around Maple Street?",
             "next": "jules_gossip",
             "effects": {
                 "clues": ["jules_rumour"],
                 "notebook": ["Jules is spreading a rumour that a newcomer was lurking near the shed."],
             }},
            # The betrayal — only available once Maya has actually confided the secret.
            {"id": "jules_tell_secret", "text": "Between us... Maya lost the shed key. That's the whole story.",
             "next": "jules_delighted",
             "requires": {"flags": {"mayaRevealedLostKey": True}},
             "effects": {
                 "trust": 6, "suspicion": -2,
                 "flags": {"playerToldJules": True},
                 "notebook": ["You told Jules that Maya lost the shed key — breaking your promise."],
                 "events": [_gossip_event()],
             }},
            {"id": "jules_keep_quiet", "text": "Nothing worth repeating. I should go.",
             "next": "jules_bored",
             "requires": {"flags": {"playerPromisedMaya": True}},
             "effects": {}},
        ],
    },
    "jules_gossip": {
        "npc": "jules", "day": 1,
        "stance": "Jules eagerly shares the rumour she's heard — that a newcomer was lurking near the shed before noon — and embellishes it.",
        "fallback": "Well! They say someone was skulking near the shed before noon. A newcomer, no less. Present company excepted, of course... probably.",
        "choices": [
            {"id": "jules_back", "text": "Interesting. Let me think on that.",
             "next": "jules_start", "effects": {}},
        ],
    },
    "jules_delighted": {
        "npc": "jules", "day": 1,
        "stance": "Jules is thrilled with the secret and makes no secret she'll spread it everywhere.",
        "fallback": "Maya?! Lost the key herself?? Oh, this is DELICIOUS. Don't you worry, the whole street will know by morning. You're my new favourite.",
        "choices": [],
    },
    "jules_bored": {
        "npc": "jules", "day": 1,
        "stance": "Jules is disappointed the player has nothing to share and loses interest.",
        "fallback": "Hmph. You're no fun at all. Off you go then, keeping your little secrets.",
        "choices": [],
    },

    # ---- JULES — Day 2 (Tea Stall) --------------------------------------- #
    "jules_d2_spreading": {
        "npc": "jules", "day": 2,
        "stance": "Jules is gleefully spreading the lost-key story all over the street.",
        "fallback": "Have you HEARD? Maya lost the key herself! I've told everyone. The looks on their faces — priceless. All thanks to you, darling.",
        "choices": [],
    },
    "jules_d2_quiet": {
        "npc": "jules", "day": 2,
        "stance": "Jules has nothing new and is mildly sulky that no good gossip came her way.",
        "fallback": "Slow week, honestly. Nobody tells me anything anymore. You included.",
        "choices": [],
    },
}


# --------------------------------------------------------------------------- #
# Day-branched entry nodes
# --------------------------------------------------------------------------- #

def start_node(npc_id: str, state: dict) -> str:
    """The node a conversation opens on for (npc, current day), branched on flags."""
    day = state["day"]
    flags = state["flags"]
    if day == 1:
        return {"maya": "maya_start", "sam": "sam_start", "jules": "jules_start"}[npc_id]

    # Day 2 — branch on what the player did on Day 1.
    if npc_id == "maya":
        if flags.get("playerToldJules"):
            return "maya_d2_confront"
        if flags.get("playerPromisedMaya"):
            return "maya_d2_trust"
        return "maya_d2_neutral"
    if npc_id == "sam":
        return "sam_d2_rumour" if flags.get("playerToldJules") else "sam_d2_calm"
    if npc_id == "jules":
        return "jules_d2_spreading" if flags.get("playerToldJules") else "jules_d2_quiet"
    raise KeyError(npc_id)


# --------------------------------------------------------------------------- #
# Endings
# --------------------------------------------------------------------------- #

ENDINGS = {
    "broken_trust": {
        "id": "broken_trust",
        "title": "The Rumour Won",
        "mystery": "The truth comes out — the latch was already broken, Sam was innocent — but only after the rumour has done its damage.",
        "relationship": "Maya no longer trusts you. Sam is more frightened than ever. The neighbourhood remembers who talked.",
        "memory": "Your promise, your betrayal, and the gossip that spread from Jules to Maya are all still in the NPCs' memories.",
    },
    "peaceful_resolution": {
        "id": "peaceful_resolution",
        "title": "Trust Kept, Case Closed",
        "mystery": "With Maya's confidence and Sam's account, you piece it together: the latch was already loose, Sam found the lost key, no one broke in.",
        "relationship": "Maya trusts you completely and Sam feels safe. You kept your word and the street stayed calm.",
        "memory": "Maya remembers the promise you kept. No gossip ever reached her.",
    },
    "cold_case": {
        "id": "cold_case",
        "title": "Cold Case",
        "mystery": "Without anyone's confidence, the shed mystery stays murky and unresolved.",
        "relationship": "Nobody opened up to you. The neighbourhood stays wary of the newcomer.",
        "memory": "Few memories were made — you never got close enough for anyone to confide.",
    },
}


def compute_ending(state: dict) -> dict:
    flags = state["flags"]
    if flags.get("playerToldJules"):
        return ENDINGS["broken_trust"]
    if flags.get("mayaRevealedSamClue") or flags.get("samSharedAlibi"):
        return ENDINGS["peaceful_resolution"]
    return ENDINGS["cold_case"]


# --------------------------------------------------------------------------- #
# Authored emotion per node (canonical — the LLM only phrases the WORDS, never
# decides the mood). Merged onto NODES at import. Values are from validators.EMOTIONS.
# --------------------------------------------------------------------------- #

NODE_EMOTION = {
    "maya_start": "anxious", "maya_ajar": "guarded", "maya_trusting": "warm",
    "maya_reveal_key": "anxious", "maya_promised": "relieved", "maya_declined": "hurt",
    "maya_guarded": "defensive", "maya_d2_confront": "hurt", "maya_d2_cold": "sad",
    "maya_d2_trust": "warm", "maya_d2_neutral": "neutral",
    "sam_start": "defensive", "sam_open": "anxious", "sam_defensive": "angry",
    "sam_d2_rumour": "anxious", "sam_d2_calm": "relieved",
    "jules_start": "excited", "jules_gossip": "smug", "jules_delighted": "excited",
    "jules_bored": "neutral", "jules_d2_spreading": "smug", "jules_d2_quiet": "neutral",
}

for _nid, _emo in NODE_EMOTION.items():
    NODES[_nid]["emotion"] = _emo


# --------------------------------------------------------------------------- #
# Clues — the collectibles the player gathers to solve the case (the win goal).
# Choice effects grant clue ids (see "clues" above); the UI shows progress X/5.
# --------------------------------------------------------------------------- #

CLUES = {
    "maya_lost_key": {
        "title": "Maya lost the shed key",
        "icon": "🔑",
        "hint": "Earn Maya's trust at the Bakery",
    },
    "latch_broken": {
        "title": "The latch was already broken",
        "icon": "🔓",
        "hint": "Talk it through with Sam at the Garden",
    },
    "sam_near_shed": {
        "title": "Sam was nearby — but didn't break in",
        "icon": "👣",
        "hint": "Talk it through with Sam at the Garden",
    },
    "sam_found_key": {
        "title": "Sam later found the lost key",
        "icon": "🧲",
        "hint": "Keep Maya's trust into Day 2",
    },
    "jules_rumour": {
        "title": "Jules is spreading a false rumour",
        "icon": "🗣️",
        "hint": "Hear the gossip at the Tea Stall",
    },
}


def clues_catalog() -> list[dict]:
    return [{"id": k, **v} for k, v in CLUES.items()]


# --------------------------------------------------------------------------- #
# The accusation — pick what really happened. SOLUTION is never sent to the client.
# --------------------------------------------------------------------------- #

THEORIES = [
    {"id": "sam_did_it", "text": "Sam broke in — he was right there that morning."},
    {"id": "newcomer", "text": "A newcomer forced the lock, just like Jules says."},
    {"id": "accident",
     "text": "No one broke in. The latch was already broken, Maya lost the key, and Sam found it. It was a misunderstanding."},
    {"id": "maya_staged", "text": "Maya staged the whole thing for sympathy."},
]
SOLUTION = "accident"

RANKS = {
    "hero": {"title": "Maple Street Hero", "icon": "🏆",
             "blurb": "You cracked the case AND kept the neighbourhood's trust. Nobody does it better."},
    "cold_detective": {"title": "Sharp Eyes, Cold Heart", "icon": "🕵️",
                       "blurb": "You found the truth — but you broke a promise to get there, and the street remembers."},
    "closed": {"title": "Case Closed", "icon": "🔍",
               "blurb": "You solved it. A few more clues and a little more trust would have made it spotless."},
    "cold_case": {"title": "Cold Case", "icon": "❄️",
                  "blurb": "Wrong call. The real story slipped away with the rumours."},
}


def compute_result(state: dict, theory_id: str) -> dict:
    """Score the accusation: clues found + correct solution + trust kept."""
    n = len(state["cluesFound"])
    total = len(CLUES)
    correct = theory_id == SOLUTION
    betrayed = bool(state["flags"].get("playerToldJules"))
    maya_trust = state["relationships"]["maya"]["trust"]

    score = n * 10 + (40 if correct else 0) + (0 if betrayed else 20) + (10 if maya_trust >= 70 else 0)

    if correct and not betrayed and n >= 4:
        stars, rank = 3, RANKS["hero"]
    elif correct and betrayed:
        stars, rank = 2, RANKS["cold_detective"]
    elif correct:
        stars, rank = 2, RANKS["closed"]
    else:
        stars, rank = (1 if n >= 2 else 0), RANKS["cold_case"]

    narrative = compute_ending(state)
    return {
        "solvedCorrectly": correct,
        "chosenTheory": theory_id,
        "correctTheory": SOLUTION,
        "correctText": next(t["text"] for t in THEORIES if t["id"] == SOLUTION),
        "score": score,
        "stars": stars,
        "maxStars": 3,
        "cluesFound": n,
        "totalClues": total,
        "betrayed": betrayed,
        "rank": rank,
        "narrative": narrative,
    }
