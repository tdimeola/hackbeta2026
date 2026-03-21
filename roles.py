import random
from hero import load_characters, get_boss


class Player:
    def __init__(self, character, is_demon=False, is_human=False):
        self.character = character
        self.is_demon = is_demon
        self.is_human = is_human
        self.alive = True

    def __repr__(self):
        role = 'DEMON' if self.is_demon else ('YOU' if self.is_human else 'NPC')
        return f"<Player {self.character.name} [{role}] alive={self.alive}>"


class GameState:
    def __init__(self):
        heroes, villains = load_characters('data.csv')
        self.all_heroes = heroes
        self.demon_char = get_boss(villains)

        self.players = []
        self.day = 1
        self.phase = 'setup'
        self.last_victim = None
        self.current_clue = ''

    def setup_players(self, player_char):
        npc_pool = [h for h in self.all_heroes if h.name != player_char.name]
        random.shuffle(npc_pool)
        npc_townsfolk = npc_pool[:4]

        self.players = []
        self.players.append(Player(player_char, is_demon=False, is_human=True))
        for h in npc_townsfolk:
            self.players.append(Player(h, is_demon=False, is_human=False))
        self.players.append(Player(self.demon_char, is_demon=True, is_human=False))

        random.shuffle(self.players)
        self.phase = 'night'

    # ── Accessors ──────────────────────────────────────────

    def alive_players(self):
        return [p for p in self.players if p.alive]

    def alive_npcs(self):
        return [p for p in self.players if p.alive and not p.is_human]

    def human_player(self):
        return next(p for p in self.players if p.is_human)

    def demon(self):
        return next(p for p in self.players if p.is_demon)

    # ── Night ──────────────────────────────────────────────

    def do_night(self):
        """Demon kills a random alive townsfolk NPC."""
        targets = [p for p in self.alive_npcs() if not p.is_demon]
        victim = random.choice(targets) if targets else None
        if victim:
            victim.alive = False
            self.last_victim = victim
        self.current_clue = self._generate_clue()
        self.phase = 'day'
        return victim

    def _generate_clue(self):
        pc = self.human_player().character
        dc = self.demon().character

        if pc.intelligence > 70:
            return f"Your instincts whisper: the demon's weakness is '{dc.weakness}'."
        elif pc.magic > 70:
            return f"A vision flickers — the demon hails from {dc.hometown}."
        elif pc.speed > 70 and self.last_victim:
            return f"You glimpsed a shadow near {self.last_victim.character.name} before dawn."
        elif pc.power > 70:
            return f"You sense immense evil — evilness rating {dc.evilness:.0f}."
        else:
            return "You sense darkness nearby, but cannot identify its source."

    # ── Vote ───────────────────────────────────────────────

    def do_vote(self, nominated):
        """Execute nominated player. Returns True if demon was killed."""
        nominated.alive = False
        self.day += 1

        if nominated.is_demon:
            self.phase = 'win'
            return True

        if len(self.alive_players()) <= 2:
            self.phase = 'lose'
            return False

        self.phase = 'night'
        return False
