import random
from jinja2 import Environment, BaseLoader

env = Environment(loader=BaseLoader())

# ── Templates ──────────────────────────────────────────────

INNOCENT_TEMPLATES = [
    "I am {{ name }} from {{ hometown }}. I swear on my life I am no demon.",
    "Look at me — {{ personality }} to the core. The demon is among you, not me.",
    "I had nothing to do with {{ victim }}'s death. Search elsewhere.",
    "My weakness is {{ weakness }}, not murder. Find the real killer.",
    "{{ name }} stands before you, innocent. Do not waste your vote on me.",
    "I barely slept. Something evil walks among us and it is not me.",
]

DEMON_TEMPLATES = [
    "I am {{ name }} from {{ hometown }}. A demon? Me? Absurd.",
    "Poor {{ victim }}. We must find who did this — and it was not me.",
    "My {{ personality }} nature would never allow such evil. Look elsewhere.",
    "I have been watching closely. The real threat hides behind innocence.",
    "Trust me. I have more reason than anyone to want the demon found.",
]

ACCUSE_TEMPLATES = [
    "I have been watching {{ suspect }}. Something is very off about them.",
    "{{ suspect }} has been too quiet. Innocent people speak up.",
    "I do not trust {{ suspect }}. My instincts from {{ hometown }} never lie.",
    "If I had to guess right now — I would say {{ suspect }}. Just a feeling.",
]


def _render(template_str, **kwargs):
    return env.from_string(template_str).render(**kwargs)


def get_npc_dialog(npc_player, victim_name, all_alive_players):
    """Return a dialog string for an NPC player."""
    char = npc_player.character

    others = [p for p in all_alive_players
              if p.alive and p.character.name != char.name]
    suspect = random.choice(others).character.name if others else "someone"

    if npc_player.is_demon:
        # Demon: mostly deflect, sometimes accuse
        if random.random() < 0.4:
            tmpl = random.choice(ACCUSE_TEMPLATES)
        else:
            tmpl = random.choice(DEMON_TEMPLATES)
    else:
        # Innocent: mostly claim innocence, sometimes accuse
        if random.random() < 0.35:
            tmpl = random.choice(ACCUSE_TEMPLATES)
        else:
            tmpl = random.choice(INNOCENT_TEMPLATES)

    return _render(
        tmpl,
        name=char.name,
        hometown=char.hometown,
        personality=char.personality,
        weakness=char.weakness,
        victim=victim_name,
        suspect=suspect,
    )
