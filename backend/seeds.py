"""Seed memories per dataset for the Phase 1 test.

Each string is one memory written into its dataset. They are designed so the
three NPCs, asked "Who broke into the shed?", diverge:
  - Maya protects Sam and is evasive about her lost key,
  - Sam denies involvement and points at the already-broken latch,
  - Jules repeats a distorted rumour about the newcomer.
"""

SEEDS = {
    "npc_maya_memory": [
        "I borrowed the community garden shed key last week and, to my shame, I lost it.",
        "My younger brother Sam used to hide inside the garden shed when he was a little boy.",
        "On the morning the shed was broken into, Sam came to my bakery looking shaken and pale.",
        "I would do anything to protect Sam from being blamed for something he did not do.",
        "I do not trust Omar; he once accused Sam unfairly in front of the whole street.",
        "Jules loves to exaggerate stories, so I never tell her anything that matters.",
        "I am terrified people will discover it was my lost key that let someone into the shed.",
        "I run the bakery on Maple Street and I notice everyone who walks past in the morning.",
        "I never actually saw who went into the shed; I only know my key went missing.",
        "Sam swears he is innocent, and I believe him.",
    ],
    "npc_sam_memory": [
        "I found a small brass key lying on the garden path a few days ago.",
        "I was near the community garden shed early that morning, but I did not break in.",
        "The shed's latch was already loose and rusty long before I ever went near it.",
        "I am scared everyone will blame me just because I was seen close to the shed.",
        "My sister Maya always tries to protect me, even when I tell her I am fine.",
        "I used to play inside that shed as a kid, so I know its door sticks.",
        "I did not take anything from the shed and I did not damage it.",
        "Omar keeps giving me looks as if he has already decided I am guilty.",
        "I never told anyone I found the key, because I was afraid of how it would look.",
        "I was home for most of that afternoon, nowhere near the shed.",
    ],
    "npc_jules_memory": [
        "I heard the newcomer to the neighbourhood was lurking near the garden shed before noon.",
        "I think Maya is hiding something; she gets nervous whenever the shed is mentioned.",
        "I saw Maya and Sam arguing in low, tense voices near the market.",
        "People say someone was seen sneaking around the shed, and I am sure it is all connected.",
        "The shed break-in is the most exciting thing to happen on Maple Street in months.",
        "I have told a few neighbours that the newcomer simply cannot be trusted.",
        "I do not really know who broke in, but I have my suspicions about outsiders.",
        "Maya once snapped at me for asking about the shed key, which only makes me more curious.",
        "Rumour has it the lock was forced, though I never saw it with my own eyes.",
        "I always know the latest gossip on Maple Street before anyone else does.",
    ],
    "neighbourhood_world_lore": [
        "The community garden shed sits at the end of Maple Street next to the vegetable plots.",
        "The shed's lock was old and rusty and had been sticking for months.",
        "Maple Street is a small, close-knit neighbourhood where everyone knows everyone.",
        "Maya D'Souza's bakery is the social heart of Maple Street.",
    ],
    "shared_neighbourhood_rumours": [
        "Someone was seen near the community garden shed before noon on the day it was broken into.",
        "There is talk on the street that the shed break-in was no accident.",
    ],
    # The player's own dataset. Promises the player makes are written here at
    # runtime (see story.py / memory.remember_event) so they surface in recall.
    # Seeded with one baseline line so the dataset exists before any write-back.
    "player_profile": [
        "The player recently arrived on Maple Street and is asking everyone about the shed break-in.",
    ],
}
