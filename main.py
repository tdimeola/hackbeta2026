import math
import pygame
import sys
import os
import csv
import random
import re
import threading
import ollama

pygame.init()

TILE_SIZE = 48
SCREEN_W, SCREEN_H = 900, 700
FPS = 60

screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Murder Mystery")
clock = pygame.time.Clock()

font_sm = pygame.font.SysFont(None, 24)
font_md = pygame.font.SysFont(None, 32)
font_lg = pygame.font.SysFont(None, 48)
font_title = pygame.font.SysFont(None, 72)

# -- Colors --
GRASS_COLOR = (76, 153, 0)
WALL_COLOR = (90, 70, 50)
ROOF_COLOR = (160, 50, 40)
PATH_COLOR = (180, 160, 120)
DOOR_COLOR = (120, 80, 30)
BG_COLOR = (30, 30, 30)
NIGHT_OVERLAY = (10, 10, 40)
BLOOD_RED = (180, 20, 20)
TREE_COLOR = (30, 90, 20)
SEARCH_COLOR = (100, 170, 60)
INTERIOR_FLOOR_COLOR = (140, 110, 70)
INTERIOR_WALL_COLOR = (60, 50, 45)
FURNITURE_COLOR = (100, 70, 40)

TILE_COLORS = {
    0: GRASS_COLOR, 1: WALL_COLOR, 2: PATH_COLOR, 3: ROOF_COLOR, 4: DOOR_COLOR,
    5: TREE_COLOR, 6: SEARCH_COLOR, 7: INTERIOR_FLOOR_COLOR, 8: INTERIOR_WALL_COLOR,
    9: FURNITURE_COLOR,
}

# -- Load CSV data --
def load_characters(path, count=7):
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    random.shuffle(rows)
    selected = rows[:count]
    characters = []
    for row in selected:
        characters.append({
            "name": row["Name"].strip(),
            "personality": row[" Personality"].strip(),
            "hometown": row[" Hometown"].strip(),
            "weakness": row[" Weakness"].strip(),
            "evilness": int(row[" Evilness"].strip()),
            "power": row[" Power"].strip(),
            "isVillain": row[" isVillain"].strip() == "True",
            "isHuman": row[" isHuman"].strip() == "True",
        })
    return characters

# -- Tile map --
# Tile legend: 0=grass, 1=wall, 2=path, 3=roof, 4=door, 5=tree, 6=search spot
tilemap = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,3,3,3,3,0,0,0,0,3,3,3,3,0,0,0,0,3,3,3,3,0,0,3,3,3,3,0,1],
    [1,0,1,1,1,1,0,0,0,0,1,1,1,1,0,0,0,0,1,1,1,1,0,0,1,1,1,1,0,1],
    [1,0,1,1,1,1,0,0,0,0,1,1,1,1,0,0,0,0,1,1,1,1,0,0,1,1,1,1,0,1],
    [1,0,1,4,1,1,0,0,0,0,1,1,4,1,0,0,0,0,1,4,1,1,0,0,1,1,4,1,0,1],
    [1,0,0,2,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,2,0,0,0,0,0,0,2,0,0,1],
    [1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1],
    [1,0,0,2,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,2,0,0,0,2,0,0,0,0,0,1],
    [1,0,3,3,3,3,0,0,0,0,3,3,3,3,0,0,0,0,3,3,3,3,0,2,5,5,0,5,0,1],
    [1,0,1,1,1,1,0,0,0,0,1,1,1,1,0,0,0,0,1,1,1,1,0,2,5,0,6,0,5,1],
    [1,0,1,1,1,1,0,0,0,0,1,1,1,1,0,0,0,0,1,1,1,1,0,2,0,5,0,5,0,1],
    [1,0,1,1,4,1,0,0,0,0,1,4,1,1,0,0,0,0,1,1,4,1,0,2,5,0,0,6,5,1],
    [1,0,0,0,2,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,2,0,0,2,5,5,0,5,0,1],
    [1,0,0,0,2,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,2,0,0,2,0,0,6,0,0,1],
    [1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
]

MAP_H = len(tilemap)
MAP_W = len(tilemap[0])
SOLID_TILES = {1, 3, 5, 8}

# -- Load pixel art sprites --
def load_sprite(path, size=(TILE_SIZE, TILE_SIZE)):
    """Load a PNG sprite with transparency, scaled to size."""
    try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(img, size)
    except Exception:
        return None

# Player sprite (detective) — 8 directions: idle + walk animations
DIRECTIONS = ["south", "north", "east", "west", "south-east", "south-west", "north-east", "north-west"]
WALK_FRAME_COUNT = 6
WALK_ANIM_SPEED = 10  # frames per second

# Idle sprites from rotations/
player_idle_sprites = {}
for d in DIRECTIONS:
    player_idle_sprites[d] = load_sprite(f"assets/characters/detective_hero/rotations/{d}.png")

# Walk animation frames
player_walk_frames = {}
for d in DIRECTIONS:
    frames = []
    for i in range(WALK_FRAME_COUNT):
        frame = load_sprite(f"assets/characters/detective_hero/animations/walk/{d}/frame_{i:03d}.png")
        frames.append(frame)
    player_walk_frames[d] = frames

# Fallback player image
player_img_fallback = pygame.image.load("character.jpg").convert()
player_img_fallback = pygame.transform.scale(player_img_fallback, (TILE_SIZE - 4, TILE_SIZE - 4))

player_facing = "south"
player_walking = False
player_anim_timer = 0.0
player_anim_frame = 0

# NPC pixel art sprites (south-facing for standing NPCs)
npc_sprite_files = [
    "assets/characters/blacksmith_south.png",
    "assets/characters/villager_south.png",
    None, None, None, None, None,
]
npc_sprites = [load_sprite(f) if f else None for f in npc_sprite_files]

# NPC spawn positions (outside each building door)
NPC_SPAWNS = [
    (3, 6), (12, 6), (19, 6), (26, 6),
    (4, 13), (11, 13), (20, 13),
]

# Named locations for buildings and map landmarks
BUILDING_NAMES = [
    "the Blacksmith",      # top-left building
    "the Tavern",          # top building 2
    "the Apothecary",      # top building 3
    "the Church",          # top-right building
    "the General Store",   # bottom-left building
    "Town Hall",           # bottom building 2
    "the Library",         # bottom building 3
]

# Label positions (tile coords) for drawing building names on the map
BUILDING_LABEL_POS = [
    (2, 1), (10, 1), (18, 1), (24, 1),
    (2, 8), (10, 8), (18, 8),
]

# Area labels (non-building labels drawn on the map)
AREA_LABELS = [
    {"name": "the Forest", "tile": (24, 8)},
]

# Open areas that can be referenced in clues
MAP_LANDMARKS = [
    "the town square",
    "the main road",
    "the alley behind the Tavern",
    "the path between the Apothecary and the Church",
    "the old well near Town Hall",
    "the courtyard behind the General Store",
    "the graveyard beyond the Church walls",
    "the Forest",
]

# -- Searchable spots on the world map --
WORLD_SEARCH_SPOTS = [
    {"tile": (26, 10), "name": "a mossy clearing", "area": "the Forest"},
    {"tile": (27, 12), "name": "a hollow tree stump", "area": "the Forest"},
    {"tile": (26, 14), "name": "a patch of disturbed leaves", "area": "the Forest"},
]

# -- Door positions mapped to building names --
DOOR_TO_BUILDING = {
    (3, 5): "the Blacksmith",
    (12, 5): "the Tavern",
    (19, 5): "the Apothecary",
    (26, 5): "the Church",
    (4, 12): "the General Store",
    (11, 12): "Town Hall",
    (20, 12): "the Library",
}

# -- Building interiors (separate maps) --
# Tiles: 7=floor, 8=wall, 4=exit door, 9=furniture
INTERIORS = {
    "the Blacksmith": {
        "map": [
            [8,8,8,8,8,8,8,8],
            [8,7,9,7,7,9,7,8],
            [8,7,7,7,7,7,7,8],
            [8,9,7,7,7,7,9,8],
            [8,7,7,7,7,7,7,8],
            [8,7,7,4,7,7,7,8],
        ],
        "player_start": (3, 4),
        "exit_tile": (3, 5),
        "exit_world_pos": (3, 6),
        "search_spots": [
            {"tile": (2, 1), "name": "the anvil"},
            {"tile": (5, 1), "name": "a tool rack"},
            {"tile": (1, 3), "name": "a storage crate"},
        ],
    },
    "the Tavern": {
        "map": [
            [8,8,8,8,8,8,8,8],
            [8,9,9,7,7,7,9,8],
            [8,7,7,7,7,7,7,8],
            [8,7,7,9,9,7,7,8],
            [8,7,7,7,7,7,7,8],
            [8,7,7,7,4,7,7,8],
        ],
        "player_start": (4, 4),
        "exit_tile": (4, 5),
        "exit_world_pos": (12, 6),
        "search_spots": [
            {"tile": (1, 1), "name": "the bar counter"},
            {"tile": (6, 1), "name": "a shelf of bottles"},
            {"tile": (3, 3), "name": "a table in the corner"},
        ],
    },
    "the Apothecary": {
        "map": [
            [8,8,8,8,8,8,8,8],
            [8,9,7,7,7,9,9,8],
            [8,7,7,7,7,7,7,8],
            [8,7,9,7,7,7,7,8],
            [8,7,7,7,7,7,7,8],
            [8,7,4,7,7,7,7,8],
        ],
        "player_start": (2, 4),
        "exit_tile": (2, 5),
        "exit_world_pos": (19, 6),
        "search_spots": [
            {"tile": (1, 1), "name": "a shelf of potions"},
            {"tile": (5, 1), "name": "a mortar and pestle"},
            {"tile": (2, 3), "name": "a locked cabinet"},
        ],
    },
    "Town Hall": {
        "map": [
            [8,8,8,8,8,8,8,8],
            [8,7,7,9,7,7,7,8],
            [8,7,7,7,7,7,7,8],
            [8,9,7,7,7,9,7,8],
            [8,7,7,7,7,7,7,8],
            [8,7,7,4,7,7,7,8],
        ],
        "player_start": (3, 4),
        "exit_tile": (3, 5),
        "exit_world_pos": (11, 13),
        "search_spots": [
            {"tile": (3, 1), "name": "the mayor's desk"},
            {"tile": (1, 3), "name": "a filing cabinet"},
            {"tile": (5, 3), "name": "a bookshelf"},
        ],
    },
    "the Library": {
        "map": [
            [8,8,8,8,8,8,8,8],
            [8,9,7,9,7,9,7,8],
            [8,7,7,7,7,7,7,8],
            [8,9,7,9,7,7,7,8],
            [8,7,7,7,7,7,7,8],
            [8,7,7,7,4,7,7,8],
        ],
        "player_start": (4, 4),
        "exit_tile": (4, 5),
        "exit_world_pos": (20, 13),
        "search_spots": [
            {"tile": (1, 1), "name": "a dusty bookshelf"},
            {"tile": (3, 1), "name": "the reading desk"},
            {"tile": (1, 3), "name": "a pile of old records"},
        ],
    },
}

NPC_COLORS = [
    (200, 60, 200), (60, 160, 220), (220, 180, 40),
    (60, 200, 100), (220, 120, 60), (180, 60, 60), (100, 200, 200),
]

# Outdoor wandering positions NPCs can appear at (tile coords, area name)
NPC_OUTDOOR_SPOTS = [
    ((7, 7), "the main road"),
    ((14, 7), "the town square"),
    ((20, 7), "the main road"),
    ((7, 15), "the south road"),
    ((14, 15), "the south road"),
    ((4, 1), "near the Blacksmith"),
    ((13, 1), "near the Tavern"),
    ((8, 8), "the town square"),
    ((15, 13), "the south side of town"),
    ((3, 8), "outside the General Store"),
    ((12, 8), "outside Town Hall"),
    ((20, 8), "outside the Library"),
]

INTERACT_DIST = TILE_SIZE * 1.8

# ── Ollama LLM ──────────────────────────────────────────────────
# Set OLLAMA_HOST env var to connect to a remote machine, e.g.:
#   OLLAMA_HOST=http://192.168.1.50:11434 python main.py
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
_ollama_client = ollama.Client(host=OLLAMA_HOST)
print(f"Connecting to Ollama at: {OLLAMA_HOST}")

def _pick_model():
    """Use llama3.1 if available, fall back to qwen3.5."""
    try:
        models = _ollama_client.list()
        names = [m.model for m in models.models]
        for preferred in ["llama3.1", "llama3.1:latest", "qwen3.5:0.8b"]:
            if preferred in names:
                return preferred
    except Exception:
        pass
    return "qwen3.5:0.8b"

OLLAMA_MODEL = _pick_model()
print(f"Using LLM model: {OLLAMA_MODEL}")

def llm_chat(system_prompt, user_prompt):
    """Call ollama synchronously and return the response text."""
    try:
        resp = _ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options={"num_predict": 128},
        )
        return resp["message"]["content"].strip()
    except Exception as e:
        return f"(LLM unavailable: {e})"

# Async wrapper so the game doesn't freeze
_llm_result = {}
_llm_start_time = {}
_llm_lock = threading.Lock()
LLM_TIMEOUT = 30  # seconds before fallback

FALLBACK_LINES = [
    "I... I don't want to talk about it.",
    "Something terrible is happening in this town.",
    "I was home all night, I swear!",
    "Have you checked near the old well?",
    "I heard strange noises last night...",
    "I don't trust anyone anymore.",
    "Please, find whoever is doing this!",
]

def llm_chat_async(key, system_prompt, user_prompt):
    """Fire off an LLM call in a background thread. Poll _llm_result[key]."""
    import time as _time
    def _run():
        result = llm_chat(system_prompt, user_prompt)
        with _llm_lock:
            _llm_result[key] = result
    with _llm_lock:
        _llm_result[key] = None  # None means in-progress
        _llm_start_time[key] = _time.time()
    threading.Thread(target=_run, daemon=True).start()

def llm_get_result(key):
    import time as _time
    with _llm_lock:
        result = _llm_result.get(key, "NOT_STARTED")
        # Check for timeout
        if result is None and key in _llm_start_time:
            elapsed = _time.time() - _llm_start_time[key]
            if elapsed > LLM_TIMEOUT:
                fallback = random.choice(FALLBACK_LINES)
                _llm_result[key] = fallback
                return fallback
        return result


# ── Game State ──────────────────────────────────────────────────
class Game:
    def __init__(self):
        self.state = "MENU"  # MENU, NIGHT, DAY, ACCUSE, ACCUSE_RESULT, WIN, LOSE
        self.night_num = 0
        self.wrong_guesses = 0
        self.characters = []
        self.alive = []
        self.villain_name = ""
        self.killed_tonight = None
        self.night_timer = 0
        self.storyteller_text = ""
        self.dialogue_target = None
        self.dialogue_text = ""
        self.dialogue_loading = False
        self.accuse_selection = 0
        self.accuse_result_correct = False
        self.talked_to = set()
        self.player_x = 0.0
        self.player_y = 0.0
        # Dynamic state: ordered log of events across all days/nights
        self.history = []  # list of dicts: {type, day, ...details}
        self.night_clues = {}  # clue data for the current night's murder
        # Interior / search state
        self.current_interior = None  # None = town map, or key into INTERIORS
        self.evidence_found = []      # persistent list of evidence dicts
        self.searched_spots = set()   # (area, spot_name) tuples searched this day
        self.evidence_placements = {} # maps (area, spot_name) -> evidence dict
        self.active_spots = set()    # which search spots are available this night
        self.search_result_text = ""
        self.search_result_timer = 0.0
        self.showing_evidence_log = False
        self.evidence_log_scroll = 0

    def new_game(self):
        self.characters = load_characters("data (1).csv", 7)
        # Ensure exactly one villain
        for c in self.characters:
            c["is_villain"] = False
        villain = random.choice(self.characters)
        villain["is_villain"] = True
        self.villain_name = villain["name"]

        self.alive = list(self.characters)
        self.night_num = 0
        self.wrong_guesses = 0
        self.killed_tonight = None
        self.dialogue_target = None
        self.dialogue_text = ""
        self.dialogue_loading = False
        self.history = []
        self.current_interior = None
        self.evidence_found = []
        self.searched_spots = set()
        self.evidence_placements = {}
        self.active_spots = set()
        self.search_result_text = ""
        self.search_result_timer = 0.0
        self.showing_evidence_log = False
        self.evidence_log_scroll = 0

        # Place NPCs and assign home buildings
        for i, c in enumerate(self.characters):
            spawn = NPC_SPAWNS[i]
            c["tile_x"] = spawn[0]
            c["tile_y"] = spawn[1]
            c["x"] = spawn[0] * TILE_SIZE
            c["y"] = spawn[1] * TILE_SIZE
            c["color"] = NPC_COLORS[i]
            c["home"] = BUILDING_NAMES[i] if i < len(BUILDING_NAMES) else "their home"
            c["location_type"] = "outside"
            c["location_building"] = None
            c["location_desc"] = f"outside {c['home']}"

        # Player start
        self.player_x = 14.0 * TILE_SIZE
        self.player_y = 7.0 * TILE_SIZE

        self.start_night()

    def start_night(self):
        self.night_num += 1
        self.state = "NIGHT"
        self.night_timer = 3.0  # seconds to show night screen
        self.dialogue_target = None
        self.dialogue_text = ""
        self.night_clues = {}
        self.searched_spots = set()
        self.evidence_placements = {}
        self.current_interior = None

        if self.night_num == 1:
            self.storyteller_text = "Night falls on the town...\nA villain lurks among you."
            self.killed_tonight = None
            self.history.append({"type": "night", "day": 1, "victim": None,
                                  "description": "The first night fell. No one was killed, but there are rumors of a murderer among the townspeople."})
        else:
            # Villain kills someone
            innocents = [c for c in self.alive if not c["is_villain"]]
            if innocents:
                victim = random.choice(innocents)
                self.killed_tonight = victim
                self.alive.remove(victim)

                # Generate rich murder details
                villain = next(c for c in self.alive if c["is_villain"])
                self.night_clues = self._generate_night_clues(victim, villain)

                self.storyteller_text = (
                    f"Night {self.night_num}...\n"
                    f"{victim['name']} was found {self.night_clues['discovery']}!"
                )
                self.history.append({
                    "type": "night", "day": self.night_num,
                    "victim": victim["name"],
                    "description": (
                        f"On the morning of day {self.night_num}, "
                        f"{victim['name']} was found {self.night_clues['discovery']}. "
                        f"{self.night_clues['scene_evidence']}"
                    ),
                })
            else:
                self.storyteller_text = f"Night {self.night_num}..."

    def _generate_night_clues(self, victim, villain):
        """Generate specific, interconnected clues for this night's murder."""
        # Where the victim's body was found
        murder_locations = [
            ("behind the Blacksmith", "the Blacksmith"),
            ("slumped against the Tavern wall", "the Tavern"),
            ("inside the Apothecary's back room", "the Apothecary"),
            ("on the steps of the Church", "the Church"),
            ("in the storeroom of the General Store", "the General Store"),
            ("on the floor of Town Hall", "Town Hall"),
            ("among the shelves of the Library", "the Library"),
            ("in the alley behind the Tavern", "the Tavern"),
            ("near the old well by Town Hall", "Town Hall"),
            ("in the courtyard behind the General Store", "the General Store"),
        ]
        # How they were killed
        cause_of_death = [
            ("a deep stab wound in the chest", "a bloodied knife", "a blade"),
            ("blunt force trauma to the head", "a heavy iron hammer from the Blacksmith", "something heavy"),
            ("strangulation marks around the neck", "torn fabric under their fingernails", "bare hands"),
            ("signs of poisoning — dark veins and pale skin", "a broken vial with purple residue from the Apothecary", "poison"),
            ("a crossbow bolt in the back", "a rare iron-tipped bolt", "a crossbow"),
        ]
        time_of_death = [
            ("just after midnight", "around midnight"),
            ("deep in the night, around 2 AM", "in the dead of night"),
            ("shortly before dawn", "near dawn"),
        ]

        loc = random.choice(murder_locations)
        weapon = random.choice(cause_of_death)
        tod = random.choice(time_of_death)

        # Physical evidence at the scene
        scene_evidence = random.choice([
            f"Boot prints in the mud led away from {loc[1]} toward the main road.",
            f"A torn piece of dark cloth was snagged on a nail outside {loc[1]}.",
            f"There were signs of a struggle — crates toppled and scratch marks on the walls of {loc[1]}.",
            f"A strange symbol was scratched into the dirt near the body outside {loc[1]}.",
            f"The victim's belongings were scattered across the floor of {loc[1]}, but nothing was stolen.",
        ])

        # Something that subtly ties to the villain
        villain_trace = random.choice([
            f"a faint smell of forge smoke lingering near {loc[1]}, far from the Blacksmith",
            f"a coin from {villain['hometown']} found clutched in the victim's hand",
            f"fresh scratches on the door of {loc[1]}, as if someone forced it open in a hurry",
            f"a button torn from a coat lying in the dirt near {loc[1]}",
            f"traces of ash near the body, as if someone burned something at {loc[1]}",
        ])

        # Assign each surviving innocent a specific clue
        alive_innocents = [c for c in self.alive if not c["is_villain"]]
        npc_clues = {}

        # Get the building where this NPC lives (by index)
        def npc_building(npc):
            idx = self.characters.index(npc)
            return BUILDING_NAMES[idx] if idx < len(BUILDING_NAMES) else "their home"

        witness_pool = [
            f"I heard a muffled scream coming from {loc[1]} {tod[1]}. I looked out my window at {npc_building(villain)} but saw no light there — {villain['name']}'s place was dark and empty.",
            f"I saw a figure hurrying away from {loc[1]} {tod[1]}. They turned toward the main road. I couldn't see their face, but they moved like someone who knew the town well.",
            f"I was restless and stepped outside {npc_building(alive_innocents[0]) if alive_innocents else 'my house'} for air {tod[1]}. I noticed the door to {loc[1]} was ajar — it's never left open at night.",
            f"I found {villain_trace} this morning when I walked past {loc[1]}. That's strange — why would that be there?",
            f"Last evening before the murder, I saw {victim['name']} and {villain['name']} having a tense conversation near {loc[1]}. {victim['name']} looked upset and walked away quickly.",
            f"{victim['name']} told me yesterday they felt someone had been following them near {loc[1]}. They seemed genuinely frightened.",
            f"I heard footsteps running past my door {tod[1]}, heading from {loc[1]} toward the north end of town. Heavy boots, moving fast.",
            f"When I passed {loc[1]} this morning, I noticed {scene_evidence.lower()} and also found {weapon[1]} partially hidden nearby.",
            f"I saw someone washing their hands at the well near Town Hall just before dawn. I couldn't make out who, but they were scrubbing hard, like they were trying to clean something off.",
            f"I remember {villain['name']} asking about {victim['name']}'s routine yesterday — what time they usually close up, whether they'd be alone. It seemed odd at the time.",
        ]

        random.shuffle(witness_pool)
        for i, npc in enumerate(alive_innocents):
            if i < len(witness_pool):
                npc_clues[npc["name"]] = witness_pool[i]
            else:
                npc_clues[npc["name"]] = f"I was asleep all night at {npc_building(npc)}, but I'm devastated about {victim['name']}. We have to find who did this."

        # Villain's alibi (will have holes other NPCs can contradict)
        villain_claimed_location = random.choice([
            n for n in BUILDING_NAMES if n != loc[1]
        ]) if len(BUILDING_NAMES) > 1 else "my home"
        villain_alibi = random.choice([
            f"I was asleep at {npc_building(villain)} all night. I didn't hear a thing until the commotion this morning.",
            f"I was up late reading at {npc_building(villain)} and never stepped outside. This is terrible news.",
            f"I spent the evening at {villain_claimed_location} and went straight home. I had no idea anything happened until now.",
            f"I was tending to some work at {npc_building(villain)} all night. You can check — my candle was burning late.",
            f"I took a walk to clear my head last night, but I went toward the Church, nowhere near {loc[1]}. I swear it.",
        ])

        npc_clues[villain["name"]] = villain_alibi

        # Generate physical evidence items for searchable spots
        physical_evidence = [
            {
                "name": weapon[1],
                "description": f"You found {weapon[1]} hidden nearby. This appears to be the murder weapon used to kill {victim['name']}.",
                "type": "weapon",
                "day": self.night_num,
            },
            {
                "name": "traces at the scene",
                "description": f"{scene_evidence} This could help identify the killer.",
                "type": "scene",
                "day": self.night_num,
            },
            {
                "name": villain_trace.split(",")[0] if "," in villain_trace else villain_trace[:50],
                "description": f"You discovered {villain_trace}. This seems out of place and could point to the killer.",
                "type": "trace",
                "day": self.night_num,
            },
        ]
        # 50% chance of a red herring
        if random.random() > 0.5:
            physical_evidence.append({
                "name": random.choice(["a worn journal page", "a strange coin", "a crumpled note"]),
                "description": "This seems interesting but may not be related to the murder.",
                "type": "herring",
                "day": self.night_num,
            })

        return {
            "discovery": f"dead {loc[0]}, with {weapon[0]}",
            "murder_location": loc[1],
            "cause_of_death": weapon,
            "time_of_death": tod,
            "scene_evidence": scene_evidence,
            "villain_trace": villain_trace,
            "npc_clues": npc_clues,
            "villain_alibi": villain_alibi,
            "victim_name": victim["name"],
            "physical_evidence": physical_evidence,
        }

    def start_day(self):
        self.state = "DAY"
        self.dialogue_target = None
        self.dialogue_text = ""
        self.talked_to = set()  # track who we've talked to this day
        self.search_result_text = ""
        self.search_result_timer = 0.0
        self._place_npcs_for_day()
        self._place_evidence()
        self._prefetch_dialogues()

    def _place_npcs_for_day(self):
        """Randomly place NPCs around town — some outside, some inside buildings.
        The villain's placement subtly contradicts their alibi."""
        clues = getattr(self, 'night_clues', {})
        murder_loc = clues.get("murder_location", None)

        # Collect available interior spots (buildings the NPC doesn't live in add variety)
        interior_buildings = [b for b in INTERIORS.keys()]

        # Collect outdoor spots, shuffle them
        outdoor_spots = list(NPC_OUTDOOR_SPOTS)
        random.shuffle(outdoor_spots)
        outdoor_idx = 0

        for npc in self.alive:
            npc_idx = self.characters.index(npc)
            home = BUILDING_NAMES[npc_idx] if npc_idx < len(BUILDING_NAMES) else "their home"

            if npc["is_villain"] and murder_loc and self.night_num > 1:
                # Villain placement: put them somewhere suspicious —
                # near the murder location or NOT where their alibi says
                villain_spots = []
                # Try to place near murder location building
                if murder_loc in INTERIORS:
                    interior = INTERIORS[murder_loc]
                    # Place on a walkable floor tile inside the murder building
                    for r, row in enumerate(interior["map"]):
                        for c, tile in enumerate(row):
                            if tile == 7:  # floor tile
                                villain_spots.append(("interior", murder_loc, (c, r)))
                                break
                        if villain_spots:
                            break
                # Also offer placing them outside near the murder building door
                for door_pos, bname in DOOR_TO_BUILDING.items():
                    if bname == murder_loc:
                        villain_spots.append(("outside", None, (door_pos[0], door_pos[1] + 1)))
                # Fallback: random outdoor
                if not villain_spots and outdoor_idx < len(outdoor_spots):
                    pos, area = outdoor_spots[outdoor_idx]
                    villain_spots.append(("outside", None, pos))
                    outdoor_idx += 1

                choice = random.choice(villain_spots) if villain_spots else ("home", None, None)
                if choice[0] == "interior":
                    npc["location_type"] = "interior"
                    npc["location_building"] = choice[1]
                    npc["location_desc"] = f"inside {choice[1]}"
                    ix, iy = choice[2]
                    npc["x"] = ix * TILE_SIZE
                    npc["y"] = iy * TILE_SIZE
                    npc["tile_x"] = ix
                    npc["tile_y"] = iy
                elif choice[0] == "outside":
                    npc["location_type"] = "outside"
                    npc["location_building"] = None
                    npc["location_desc"] = f"near {murder_loc}" if murder_loc else "in town"
                    tx, ty = choice[2]
                    npc["x"] = tx * TILE_SIZE
                    npc["y"] = ty * TILE_SIZE
                    npc["tile_x"] = tx
                    npc["tile_y"] = ty
                else:
                    # Fallback to home door
                    spawn = NPC_SPAWNS[npc_idx]
                    npc["location_type"] = "outside"
                    npc["location_building"] = None
                    npc["location_desc"] = f"outside {home}"
                    npc["x"] = spawn[0] * TILE_SIZE
                    npc["y"] = spawn[1] * TILE_SIZE
                    npc["tile_x"] = spawn[0]
                    npc["tile_y"] = spawn[1]
            else:
                # Innocent NPCs: randomly place at home, inside a building, or wandering
                roll = random.random()
                if roll < 0.35 and interior_buildings:
                    # Inside a random building
                    bname = random.choice(interior_buildings)
                    interior = INTERIORS[bname]
                    # Find a walkable floor tile
                    floor_tiles = []
                    for r, row in enumerate(interior["map"]):
                        for c, tile in enumerate(row):
                            if tile == 7:
                                floor_tiles.append((c, r))
                    if floor_tiles:
                        ix, iy = random.choice(floor_tiles)
                        npc["location_type"] = "interior"
                        npc["location_building"] = bname
                        npc["location_desc"] = f"inside {bname}"
                        npc["x"] = ix * TILE_SIZE
                        npc["y"] = iy * TILE_SIZE
                        npc["tile_x"] = ix
                        npc["tile_y"] = iy
                        continue
                if roll < 0.65 and outdoor_idx < len(outdoor_spots):
                    # Wandering outside
                    pos, area = outdoor_spots[outdoor_idx]
                    outdoor_idx += 1
                    npc["location_type"] = "outside"
                    npc["location_building"] = None
                    npc["location_desc"] = f"at {area}"
                    npc["x"] = pos[0] * TILE_SIZE
                    npc["y"] = pos[1] * TILE_SIZE
                    npc["tile_x"] = pos[0]
                    npc["tile_y"] = pos[1]
                else:
                    # At their home door
                    spawn = NPC_SPAWNS[npc_idx]
                    npc["location_type"] = "outside"
                    npc["location_building"] = None
                    npc["location_desc"] = f"outside {home}"
                    npc["x"] = spawn[0] * TILE_SIZE
                    npc["y"] = spawn[1] * TILE_SIZE
                    npc["tile_x"] = spawn[0]
                    npc["tile_y"] = spawn[1]

    def _place_evidence(self):
        """Pick a random subset of search spots to be active, then assign evidence."""
        # Gather all possible spots
        all_spots = []
        for spot in WORLD_SEARCH_SPOTS:
            all_spots.append((spot["area"], spot["name"]))
        for bname, interior in INTERIORS.items():
            for spot in interior["search_spots"]:
                all_spots.append((bname, spot["name"]))

        # Randomly activate only some spots each night (40-60% of total)
        random.shuffle(all_spots)
        active_count = max(3, int(len(all_spots) * random.uniform(0.4, 0.6)))
        self.active_spots = set(all_spots[:active_count])

        # Place evidence at active spots only
        evidence_list = self.night_clues.get("physical_evidence", [])
        active_list = list(self.active_spots)
        random.shuffle(active_list)
        self.evidence_placements = {}
        for i, ev in enumerate(evidence_list):
            if i < len(active_list):
                self.evidence_placements[active_list[i]] = ev

    def _build_history_context(self):
        """Return a human-readable summary of all past events for LLM context."""
        if not self.history:
            return ""
        lines = ["Here is what has happened so far in the town:"]
        for event in self.history:
            lines.append(f"- {event['description']}")
        return " ".join(lines)

    def _prefetch_dialogues(self):
        """Pre-generate all NPC dialogue for this day so responses are instant."""
        alive_names = [c["name"] for c in self.alive]
        dead_names = [c["name"] for c in self.characters if c not in self.alive]
        history_context = self._build_history_context()
        clues = getattr(self, 'night_clues', {})

        for npc in self.alive:
            is_villain = npc["is_villain"]
            npc_idx = self.characters.index(npc)
            npc_home = BUILDING_NAMES[npc_idx] if npc_idx < len(BUILDING_NAMES) else "their home"

            # Base identity
            npc_location = npc.get("location_desc", f"outside {npc_home}")
            system = (
                f"You are {npc['name']}, a resident of a small town in a murder mystery. "
                f"You live and work at {npc_home}. "
                f"Right now you are {npc_location}. "
                f"Personality: {npc['personality']}. Originally from: {npc['hometown']}. "
                f"Known weakness: {npc['weakness']}. "
                f"The surviving townspeople are: {', '.join(n for n in alive_names if n != npc['name'])}. "
                f"The town has these locations: {', '.join(BUILDING_NAMES[:len(self.characters)])} along with the main road, the town square, the Forest, and the old well. "
                f"IMPORTANT: Only refer to people and places by their exact names listed above. Do NOT invent names or locations. "
                f"RULE: You must ALWAYS speak in first person as {npc['name']}. Use 'I', 'me', 'my'. "
                f"NEVER use third person. NEVER say '{npc['name']} thinks' or '{npc['name']} says' — say 'I think' or 'I saw'. "
                f"You ARE this character speaking directly to the detective. "
            )

            if dead_names:
                system += f"The dead so far: {', '.join(dead_names)}. "

            if history_context:
                system += f"\n{history_context}\n"

            # Day 1: no murder yet — build atmosphere and relationships
            if self.night_num == 1:
                if is_villain:
                    system += (
                        "You are secretly the killer. No one has died yet, but you are planning. "
                        "Act friendly and normal, but subtly steer conversation away from yourself. "
                        "Maybe mention how safe the town usually is, or comment on another townsperson. "
                        "Never confess. Keep responses to 2-3 sentences."
                    )
                else:
                    system += (
                        "No one has been killed yet, but rumors of danger have everyone on edge. "
                        "Share something about your daily life at " + npc_home + ", mention your neighbors, "
                        "or express worry about the rumors. Be specific — mention a location or person by name. "
                        "Keep responses to 2-3 sentences."
                    )
            # Later days: murder happened, share specific clues
            else:
                npc_clue = clues.get("npc_clues", {}).get(npc["name"], "")
                murder_loc = clues.get("murder_location", "somewhere in town")
                victim_name = clues.get("victim_name", "someone")
                cause = clues.get("cause_of_death", ("unknown injuries", "", ""))[0]
                time_desc = clues.get("time_of_death", ("last night", "last night"))[0]

                if is_villain:
                    system += (
                        f"{victim_name} was found dead at {murder_loc} with {cause}, killed {time_desc}. "
                        f"You are the killer. Your alibi: {npc_clue} "
                        f"The detective found you {npc_location} — if asked why you are here, have a plausible excuse. "
                        f"Deliver your alibi naturally, as if just making conversation. "
                        f"Act shocked and saddened. If pressed, subtly cast suspicion on another living townsperson by name. "
                        f"Never confess or admit guilt. Keep responses to 2-3 sentences."
                    )
                else:
                    # Tell innocent NPCs where other people are, so they can mention it
                    other_locations = []
                    for other in self.alive:
                        if other["name"] != npc["name"]:
                            other_locations.append(f"{other['name']} is {other.get('location_desc', 'in town')}")
                    system += (
                        f"{victim_name} was found dead at {murder_loc} with {cause}, killed {time_desc}. "
                        f"YOUR SPECIFIC OBSERVATION: {npc_clue} "
                        f"You can see where other people are today: {'; '.join(other_locations)}. "
                        f"You MUST share your observation with the detective — it's the most important thing you know. "
                        f"If you notice someone is in a suspicious location (near the murder scene), you may mention it. "
                        f"Weave it naturally into your response. You are scared and want justice. "
                        f"Keep responses to 2-3 sentences."
                    )

            user_msg = (
                f"The detective approaches you on day {self.night_num}. "
                f"Respond as yourself speaking directly to the detective. Use 'I' and 'me', never your own name in third person. "
                f"Example format: 'I heard something last night...' NOT '{npc['name']} heard something last night...'"
            )
            llm_chat_async(f"npc_{npc['name']}_{self.night_num}", system, user_msg)

    def open_accuse(self):
        self.state = "ACCUSE"
        self.accuse_selection = 0

    def do_accuse(self, character):
        if character["is_villain"]:
            self.state = "WIN"
            self.storyteller_text = (
                f"You accused {character['name']}...\n"
                f"They WERE the villain! The town is saved!"
            )
            self.history.append({
                "type": "accusation", "day": self.night_num,
                "accused": character["name"], "correct": True,
                "description": (
                    f"On day {self.night_num}, the detective correctly identified "
                    f"{character['name']} as the villain. The town is saved."
                ),
            })
        else:
            self.wrong_guesses += 1
            self.accuse_result_correct = False
            self.history.append({
                "type": "accusation", "day": self.night_num,
                "accused": character["name"], "correct": False,
                "description": (
                    f"On day {self.night_num}, the detective accused {character['name']}, "
                    f"but they were innocent. The town was shocked and the real killer is still at large."
                ),
            })
            if self.wrong_guesses >= 3:
                self.state = "LOSE"
                self.storyteller_text = (
                    f"{character['name']} was innocent!\n"
                    f"You've run out of guesses.\n"
                    f"The villain {self.villain_name} wins!"
                )
            else:
                self.state = "ACCUSE_RESULT"
                self.storyteller_text = (
                    f"{character['name']} was innocent!\n"
                    f"Wrong guess! {3 - self.wrong_guesses} guesses remaining."
                )

    def talk_to_npc(self, npc):
        if self.dialogue_loading:
            return
        self.dialogue_target = npc
        self.talked_to.add(npc["name"])

        # Check if pre-fetched response is ready
        key = f"npc_{npc['name']}_{self.night_num}"
        result = llm_get_result(key)
        if result and result != "NOT_STARTED" and result is not None:
            text = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL).strip()
            self.dialogue_text = text if text else result.strip()
            self.dialogue_loading = False
        else:
            # Still generating, show loading
            self.dialogue_text = ""
            self.dialogue_loading = True

    def try_search(self):
        """Check if player is near an active searchable spot and search it."""
        ptx = int((self.player_x + (TILE_SIZE - 4) / 2) // TILE_SIZE)
        pty = int((self.player_y + (TILE_SIZE - 4) / 2) // TILE_SIZE)

        if self.current_interior:
            interior = INTERIORS[self.current_interior]
            spots = interior["search_spots"]
            area = self.current_interior
        else:
            spots = WORLD_SEARCH_SPOTS
            area = None

        for spot in spots:
            sx, sy = spot["tile"]
            if abs(ptx - sx) <= 1 and abs(pty - sy) <= 1:
                spot_area = area or spot.get("area", "unknown")
                key = (spot_area, spot["name"])

                # Only active spots can be searched
                if key not in self.active_spots:
                    return False

                if key in self.searched_spots:
                    self.show_search_result(f"You've already searched {spot['name']} today.")
                    return True

                self.searched_spots.add(key)

                if key in self.evidence_placements:
                    ev = self.evidence_placements[key]
                    self.evidence_found.append(ev)
                    self.show_search_result(f"EVIDENCE FOUND: {ev['description']}")
                    self.history.append({
                        "type": "evidence", "day": self.night_num,
                        "description": f"The detective found {ev['name']} at {spot['name']}.",
                    })
                else:
                    flavor = random.choice([
                        f"You search {spot['name']} carefully but find nothing useful.",
                        f"Nothing of interest at {spot['name']}.",
                        f"You examine {spot['name']} — just dust and shadows.",
                    ])
                    self.show_search_result(flavor)
                return True
        return False

    def show_search_result(self, text):
        self.search_result_text = text
        self.search_result_timer = 4.0

    def try_enter_building(self):
        """Check if player is on a door tile and enter the building interior."""
        ptx = int((self.player_x + (TILE_SIZE - 4) / 2) // TILE_SIZE)
        pty = int((self.player_y + (TILE_SIZE - 4) / 2) // TILE_SIZE)
        building = DOOR_TO_BUILDING.get((ptx, pty))
        if building and building in INTERIORS:
            interior = INTERIORS[building]
            self.current_interior = building
            sx, sy = interior["player_start"]
            self.player_x = sx * TILE_SIZE
            self.player_y = sy * TILE_SIZE
            return True
        return False

    def try_exit_interior(self):
        """Check if player is on the exit door tile of the current interior."""
        if not self.current_interior:
            return False
        interior = INTERIORS[self.current_interior]
        ptx = int((self.player_x + (TILE_SIZE - 4) / 2) // TILE_SIZE)
        pty = int((self.player_y + (TILE_SIZE - 4) / 2) // TILE_SIZE)
        ex, ey = interior["exit_tile"]
        if ptx == ex and pty == ey:
            wx, wy = interior["exit_world_pos"]
            self.player_x = wx * TILE_SIZE
            self.player_y = wy * TILE_SIZE
            self.current_interior = None
            return True
        return False

    def get_nearby_search_spot(self):
        """Return the nearest active search spot if player is close, else None."""
        ptx = int((self.player_x + (TILE_SIZE - 4) / 2) // TILE_SIZE)
        pty = int((self.player_y + (TILE_SIZE - 4) / 2) // TILE_SIZE)
        if self.current_interior:
            spots = INTERIORS[self.current_interior]["search_spots"]
            area = self.current_interior
        else:
            spots = WORLD_SEARCH_SPOTS
            area = None
        for spot in spots:
            sx, sy = spot["tile"]
            if abs(ptx - sx) <= 1 and abs(pty - sy) <= 1:
                spot_area = area or spot.get("area", "")
                key = (spot_area, spot["name"])
                if key in self.active_spots:
                    return spot
        return None

    def is_on_door(self):
        """Check if player is standing on a door tile (for enter prompt)."""
        ptx = int((self.player_x + (TILE_SIZE - 4) / 2) // TILE_SIZE)
        pty = int((self.player_y + (TILE_SIZE - 4) / 2) // TILE_SIZE)
        building = DOOR_TO_BUILDING.get((ptx, pty))
        return building if building and building in INTERIORS else None

    def is_on_exit(self):
        """Check if player is on the exit tile of current interior."""
        if not self.current_interior:
            return False
        interior = INTERIORS[self.current_interior]
        ptx = int((self.player_x + (TILE_SIZE - 4) / 2) // TILE_SIZE)
        pty = int((self.player_y + (TILE_SIZE - 4) / 2) // TILE_SIZE)
        ex, ey = interior["exit_tile"]
        return ptx == ex and pty == ey


game = Game()

# ── Helpers ─────────────────────────────────────────────────────
def is_wall(px, py, w, h):
    if game.current_interior:
        imap = INTERIORS[game.current_interior]["map"]
        ih = len(imap)
        iw = len(imap[0])
        left = int(px) // TILE_SIZE
        right = int(px + w - 1) // TILE_SIZE
        top = int(py) // TILE_SIZE
        bottom = int(py + h - 1) // TILE_SIZE
        for r in range(top, bottom + 1):
            for c in range(left, right + 1):
                if r < 0 or r >= ih or c < 0 or c >= iw:
                    return True
                if imap[r][c] in SOLID_TILES:
                    return True
        return False
    else:
        left = int(px) // TILE_SIZE
        right = int(px + w - 1) // TILE_SIZE
        top = int(py) // TILE_SIZE
        bottom = int(py + h - 1) // TILE_SIZE
        for r in range(top, bottom + 1):
            for c in range(left, right + 1):
                if r < 0 or r >= MAP_H or c < 0 or c >= MAP_W:
                    return True
                if tilemap[r][c] in SOLID_TILES:
                    return True
        return False

def player_near(npc):
    pcx = game.player_x + (TILE_SIZE - 4) / 2
    pcy = game.player_y + (TILE_SIZE - 4) / 2
    ncx = npc["x"] + (TILE_SIZE - 4) / 2
    ncy = npc["y"] + (TILE_SIZE - 4) / 2
    return ((pcx - ncx)**2 + (pcy - ncy)**2) ** 0.5 < INTERACT_DIST

def draw_text_wrapped(surface, text, font, color, rect, line_spacing=4):
    """Draw word-wrapped text inside a rect."""
    words = text.split(' ')
    lines = []
    current = ""
    for word in words:
        test = current + " " + word if current else word
        if font.size(test)[0] <= rect.width - 16:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    y = rect.y + 8
    for line in lines:
        if y + font.get_height() > rect.y + rect.height - 8:
            break
        surf = font.render(line, True, color)
        surface.blit(surf, (rect.x + 8, y))
        y += font.get_height() + line_spacing

def draw_centered_text(surface, text, font, color, y):
    surf = font.render(text, True, color)
    surface.blit(surf, (SCREEN_W // 2 - surf.get_width() // 2, y))

def draw_centered_text_wrapped(surface, text, font, color, y, max_width=None, line_spacing=8):
    """Draw word-wrapped, centered text. Returns the y position after the last line."""
    if max_width is None:
        max_width = SCREEN_W - 80
    words = text.split(' ')
    lines = []
    current = ""
    for word in words:
        test = current + " " + word if current else word
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    for line in lines:
        surf = font.render(line, True, color)
        surface.blit(surf, (SCREEN_W // 2 - surf.get_width() // 2, y))
        y += font.get_height() + line_spacing
    return y


# ── Main Loop ───────────────────────────────────────────────────
running = True
while running:
    dt = clock.tick(FPS) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if game.state in ("DAY", "ACCUSE"):
                    if game.state == "ACCUSE":
                        game.state = "DAY"
                    elif game.showing_evidence_log:
                        game.showing_evidence_log = False
                    elif game.search_result_timer > 0:
                        game.search_result_timer = 0
                        game.search_result_text = ""
                    elif game.dialogue_target:
                        game.dialogue_target = None
                        game.dialogue_text = ""
                        game.dialogue_loading = False
                    elif game.current_interior:
                        # Exit interior back to town
                        interior = INTERIORS[game.current_interior]
                        wx, wy = interior["exit_world_pos"]
                        game.player_x = wx * TILE_SIZE
                        game.player_y = wy * TILE_SIZE
                        game.current_interior = None
                    else:
                        running = False
                else:
                    running = False

            # Menu
            if game.state == "MENU" and event.key == pygame.K_RETURN:
                game.new_game()

            # Night — skip with any key after timer
            if game.state == "NIGHT" and game.night_timer <= 0:
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    game.start_day()

            # Day
            if game.state == "DAY":
                if event.key == pygame.K_e:
                    # Dismiss search result
                    if game.search_result_timer > 0:
                        game.search_result_timer = 0
                        game.search_result_text = ""
                    # Close dialogue
                    elif game.dialogue_target:
                        game.dialogue_target = None
                        game.dialogue_text = ""
                        game.dialogue_loading = False
                    # Close evidence log
                    elif game.showing_evidence_log:
                        game.showing_evidence_log = False
                    # Try exit interior
                    elif game.current_interior and game.is_on_exit():
                        game.try_exit_interior()
                    # Try enter building
                    elif not game.current_interior and game.is_on_door():
                        game.try_enter_building()
                    # Try talk to NPC or search (works in town and interiors)
                    else:
                        talked = False
                        for npc in game.alive:
                            # Only interact with NPCs in the same map
                            if game.current_interior:
                                if npc.get("location_type") != "interior" or npc.get("location_building") != game.current_interior:
                                    continue
                            else:
                                if npc.get("location_type") == "interior":
                                    continue
                            if player_near(npc):
                                game.talk_to_npc(npc)
                                talked = True
                                break
                        if not talked:
                            game.try_search()

                if event.key == pygame.K_l:
                    game.showing_evidence_log = not game.showing_evidence_log
                    game.evidence_log_scroll = 0

                if event.key == pygame.K_TAB and not game.showing_evidence_log:
                    game.open_accuse()

                # Scroll evidence log
                if game.showing_evidence_log:
                    if event.key == pygame.K_UP:
                        game.evidence_log_scroll = max(0, game.evidence_log_scroll - 1)
                    if event.key == pygame.K_DOWN:
                        game.evidence_log_scroll += 1

            # Accuse menu
            elif game.state == "ACCUSE":
                suspects = [c for c in game.alive if not (game.killed_tonight and c is game.killed_tonight)]
                if event.key == pygame.K_UP:
                    game.accuse_selection = (game.accuse_selection - 1) % len(suspects)
                if event.key == pygame.K_DOWN:
                    game.accuse_selection = (game.accuse_selection + 1) % len(suspects)
                if event.key == pygame.K_RETURN:
                    if suspects:
                        game.do_accuse(suspects[game.accuse_selection])

            # Accuse result — wrong guess, continue to next night
            elif game.state == "ACCUSE_RESULT":
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    game.start_night()

            # Win/Lose
            elif game.state in ("WIN", "LOSE"):
                if event.key == pygame.K_RETURN:
                    game.state = "MENU"

    # ── Update ──────────────────────────────────────────────────
    if game.state == "NIGHT":
        game.night_timer -= dt

    if game.state == "DAY":
        # Movement
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1

        # Update facing direction
        if dx != 0 or dy != 0:
            if dx == 0 and dy == -1: player_facing = "north"
            elif dx == 0 and dy == 1: player_facing = "south"
            elif dx == -1 and dy == 0: player_facing = "west"
            elif dx == 1 and dy == 0: player_facing = "east"
            elif dx == 1 and dy == -1: player_facing = "north-east"
            elif dx == -1 and dy == -1: player_facing = "north-west"
            elif dx == 1 and dy == 1: player_facing = "south-east"
            elif dx == -1 and dy == 1: player_facing = "south-west"

        pw, ph = TILE_SIZE - 4, TILE_SIZE - 4
        speed = 200

        new_x = game.player_x + dx * speed * dt
        if not is_wall(new_x, game.player_y, pw, ph):
            game.player_x = new_x
        new_y = game.player_y + dy * speed * dt
        if not is_wall(game.player_x, new_y, pw, ph):
            game.player_y = new_y

        # Update walk animation
        if dx != 0 or dy != 0:
            player_walking = True
            player_anim_timer += dt
            frame_duration = 1.0 / WALK_ANIM_SPEED
            if player_anim_timer >= frame_duration:
                player_anim_timer -= frame_duration
                player_anim_frame = (player_anim_frame + 1) % WALK_FRAME_COUNT
        else:
            player_walking = False
            player_anim_timer = 0.0
            player_anim_frame = 0

        # Update search result timer
        if game.search_result_timer > 0:
            game.search_result_timer -= dt
            if game.search_result_timer <= 0:
                game.search_result_text = ""

        # Check LLM responses
        if game.dialogue_loading and game.dialogue_target:
            key = f"npc_{game.dialogue_target['name']}_{game.night_num}"
            result = llm_get_result(key)
            if result is not None and result != "NOT_STARTED":
                # Strip <think>...</think> blocks (qwen3.5 outputs these)
                text = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL).strip()
                if not text:
                    text = result.strip()
                game.dialogue_text = text
                game.dialogue_loading = False

    # ── Draw ────────────────────────────────────────────────────
    screen.fill(BG_COLOR)

    if game.state == "MENU":
        draw_centered_text(screen, "MURDER MYSTERY", font_title, BLOOD_RED, 180)
        draw_centered_text(screen, "A villain hides among the townspeople.", font_md, (200, 200, 200), 270)
        draw_centered_text(screen, "Find them before it's too late.", font_md, (200, 200, 200), 310)
        draw_centered_text(screen, "Press ENTER to begin", font_md, (255, 255, 255), 420)
        draw_centered_text(screen, "[WASD] Move  [E] Talk/Search/Enter  [L] Evidence Log  [TAB] Accuse", font_sm, (150, 150, 150), 500)

    elif game.state == "NIGHT":
        screen.fill(NIGHT_OVERLAY)
        cur_y = 200
        for line in game.storyteller_text.split("\n"):
            cur_y = draw_centered_text_wrapped(screen, line, font_lg, (220, 220, 255), cur_y)
            cur_y += 10  # extra gap between paragraphs
        if game.night_timer <= 0:
            draw_centered_text(screen, "Press ENTER to continue", font_md, (150, 150, 180), 500)

    elif game.state in ("DAY", "ACCUSE"):
        pw, ph = TILE_SIZE - 4, TILE_SIZE - 4
        cam_x = game.player_x + pw / 2 - SCREEN_W / 2
        cam_y = game.player_y + ph / 2 - SCREEN_H / 2

        if game.current_interior:
            # ── Draw interior map ──
            imap = INTERIORS[game.current_interior]["map"]
            ih, iw = len(imap), len(imap[0])
            for row in range(ih):
                for col in range(iw):
                    rect = pygame.Rect(
                        col * TILE_SIZE - cam_x,
                        row * TILE_SIZE - cam_y,
                        TILE_SIZE, TILE_SIZE,
                    )
                    pygame.draw.rect(screen, TILE_COLORS.get(imap[row][col], BG_COLOR), rect)

            # Draw subtle glint on active search spots in interior
            interior = INTERIORS[game.current_interior]
            t = pygame.time.get_ticks()
            for spot in interior["search_spots"]:
                sx, sy = spot["tile"]
                key = (game.current_interior, spot["name"])
                if key not in game.active_spots:
                    continue
                scr_x = sx * TILE_SIZE - cam_x + TILE_SIZE // 2
                scr_y = sy * TILE_SIZE - cam_y + TILE_SIZE // 2
                if key not in game.searched_spots:
                    # Subtle flickering glint — small dot that fades in and out
                    flicker = max(0, math.sin(t * 0.003 + hash(spot["name"]) % 100))
                    alpha = int(60 + 80 * flicker)
                    glint = pygame.Surface((6, 6), pygame.SRCALPHA)
                    glint.fill((255, 255, 200, alpha))
                    screen.blit(glint, (scr_x - 3, scr_y - 3))

            # Draw NPCs that are inside this building
            for npc in game.alive:
                if npc.get("location_type") == "interior" and npc.get("location_building") == game.current_interior:
                    sx = npc["x"] - cam_x
                    sy = npc["y"] - cam_y
                    idx = game.characters.index(npc) if npc in game.characters else -1
                    sprite = npc_sprites[idx] if 0 <= idx < len(npc_sprites) else None
                    if sprite:
                        screen.blit(sprite, (sx, sy))
                    else:
                        pygame.draw.rect(screen, npc["color"], (sx, sy, TILE_SIZE - 4, TILE_SIZE - 4))
                    name_surf = font_sm.render(npc["name"], True, (255, 255, 255))
                    screen.blit(name_surf, (sx + (TILE_SIZE - 4) / 2 - name_surf.get_width() / 2, sy - 20))
                    if player_near(npc) and not game.dialogue_target:
                        if npc["name"] in game.talked_to:
                            hint = font_sm.render("(already spoke)", True, (150, 150, 150))
                        else:
                            hint = font_sm.render("[E] Talk", True, (255, 255, 200))
                        screen.blit(hint, (sx - 5, sy - 38))

            # Interior name header
            int_label = font_md.render(f"Inside {game.current_interior}  [ESC] Exit", True, (255, 255, 220))
            lbg = pygame.Surface((int_label.get_width() + 16, int_label.get_height() + 8), pygame.SRCALPHA)
            lbg.fill((0, 0, 0, 180))
            screen.blit(lbg, (SCREEN_W // 2 - int_label.get_width() // 2 - 8, 50))
            screen.blit(int_label, (SCREEN_W // 2 - int_label.get_width() // 2, 54))

        else:
            # ── Draw town map ──
            for row in range(MAP_H):
                for col in range(MAP_W):
                    rect = pygame.Rect(
                        col * TILE_SIZE - cam_x,
                        row * TILE_SIZE - cam_y,
                        TILE_SIZE, TILE_SIZE,
                    )
                    pygame.draw.rect(screen, TILE_COLORS[tilemap[row][col]], rect)

            # Draw building name labels
            for i, (lx, ly) in enumerate(BUILDING_LABEL_POS):
                if i < len(BUILDING_NAMES):
                    label = font_sm.render(BUILDING_NAMES[i], True, (255, 255, 220))
                    lsx = lx * TILE_SIZE - cam_x + TILE_SIZE * 2 - label.get_width() / 2
                    lsy = ly * TILE_SIZE - cam_y + 4
                    bg_rect = pygame.Rect(lsx - 4, lsy - 2, label.get_width() + 8, label.get_height() + 4)
                    bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
                    bg_surf.fill((0, 0, 0, 160))
                    screen.blit(bg_surf, bg_rect)
                    screen.blit(label, (lsx, lsy))

            # Draw area labels (Forest, etc.)
            for area in AREA_LABELS:
                lx, ly = area["tile"]
                label = font_sm.render(area["name"], True, (200, 255, 200))
                lsx = lx * TILE_SIZE - cam_x + TILE_SIZE * 2 - label.get_width() / 2
                lsy = ly * TILE_SIZE - cam_y + 4
                bg_rect = pygame.Rect(lsx - 4, lsy - 2, label.get_width() + 8, label.get_height() + 4)
                bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
                bg_surf.fill((0, 0, 0, 160))
                screen.blit(bg_surf, bg_rect)
                screen.blit(label, (lsx, lsy))

            # Draw subtle glint on active search spots on world map
            t = pygame.time.get_ticks()
            for spot in WORLD_SEARCH_SPOTS:
                sx, sy = spot["tile"]
                key = (spot["area"], spot["name"])
                if key not in game.active_spots:
                    continue
                scr_x = sx * TILE_SIZE - cam_x + TILE_SIZE // 2
                scr_y = sy * TILE_SIZE - cam_y + TILE_SIZE // 2
                if key not in game.searched_spots:
                    flicker = max(0, math.sin(t * 0.003 + hash(spot["name"]) % 100))
                    alpha = int(60 + 80 * flicker)
                    glint = pygame.Surface((6, 6), pygame.SRCALPHA)
                    glint.fill((255, 255, 200, alpha))
                    screen.blit(glint, (scr_x - 3, scr_y - 3))

            # Draw NPCs that are outside (on town map)
            for npc in game.alive:
                if npc.get("location_type") == "interior":
                    continue  # Skip NPCs inside buildings
                sx = npc["x"] - cam_x
                sy = npc["y"] - cam_y
                idx = game.characters.index(npc) if npc in game.characters else -1
                sprite = npc_sprites[idx] if 0 <= idx < len(npc_sprites) else None
                if sprite:
                    screen.blit(sprite, (sx, sy))
                else:
                    pygame.draw.rect(screen, npc["color"], (sx, sy, TILE_SIZE - 4, TILE_SIZE - 4))
                name_surf = font_sm.render(npc["name"], True, (255, 255, 255))
                screen.blit(name_surf, (sx + (TILE_SIZE - 4) / 2 - name_surf.get_width() / 2, sy - 20))

                # Interaction hint
                if player_near(npc) and not game.dialogue_target:
                    if npc["name"] in game.talked_to:
                        hint = font_sm.render("(already spoke)", True, (150, 150, 150))
                    else:
                        hint = font_sm.render("[E] Talk", True, (255, 255, 200))
                    screen.blit(hint, (sx - 5, sy - 38))

            # Door enter hint
            door_building = game.is_on_door()
            if door_building and not game.dialogue_target:
                hint = font_sm.render(f"[E] Enter {door_building}", True, (255, 255, 200))
                screen.blit(hint, (game.player_x - cam_x - hint.get_width() // 2 + pw // 2, game.player_y - cam_y - 25))

        # Draw player (both town and interior)
        if player_walking:
            frames = player_walk_frames.get(player_facing)
            p_sprite = frames[player_anim_frame] if frames else None
        else:
            p_sprite = player_idle_sprites.get(player_facing)
        if p_sprite:
            screen.blit(p_sprite, (game.player_x - cam_x, game.player_y - cam_y))
        else:
            screen.blit(player_img_fallback, (game.player_x - cam_x, game.player_y - cam_y))

        # Search spot hint (both maps)
        nearby_spot = game.get_nearby_search_spot()
        if nearby_spot and not game.dialogue_target and game.search_result_timer <= 0:
            spot_area = game.current_interior or nearby_spot.get("area", "")
            key = (spot_area, nearby_spot["name"])
            if key in game.searched_spots:
                hint = font_sm.render(f"(searched)", True, (150, 150, 150))
            else:
                hint = font_sm.render(f"[E] Search {nearby_spot['name']}", True, (255, 255, 200))
            screen.blit(hint, (game.player_x - cam_x - hint.get_width() // 2 + pw // 2, game.player_y - cam_y - 25))

        # Exit hint in interior
        if game.current_interior and game.is_on_exit():
            hint = font_sm.render("[E] Exit", True, (255, 255, 200))
            screen.blit(hint, (game.player_x - cam_x - hint.get_width() // 2 + pw // 2, game.player_y - cam_y - 25))

        # HUD
        hud_y = 10
        ev_count = len(game.evidence_found)
        loc_text = f"  |  Inside {game.current_interior}" if game.current_interior else ""
        hud_text = f"Day {game.night_num}  |  Guesses: {3 - game.wrong_guesses}  |  Evidence: {ev_count}  |  [TAB] Accuse  [L] Log{loc_text}"
        day_surf = font_md.render(hud_text, True, (255, 255, 255))
        pygame.draw.rect(screen, (0, 0, 0, 180), (0, 0, SCREEN_W, 45))
        screen.blit(day_surf, (15, hud_y))

        # Dialogue box
        if game.dialogue_target and not game.current_interior:
            box_h = 160
            box_rect = pygame.Rect(20, SCREEN_H - box_h - 20, SCREEN_W - 40, box_h)
            pygame.draw.rect(screen, (20, 20, 30), box_rect, border_radius=8)
            pygame.draw.rect(screen, (100, 100, 120), box_rect, 2, border_radius=8)

            name_surf = font_md.render(game.dialogue_target["name"], True, game.dialogue_target["color"])
            screen.blit(name_surf, (box_rect.x + 12, box_rect.y + 8))

            if game.dialogue_loading:
                draw_text_wrapped(screen, "...", font_sm, (200, 200, 200),
                    pygame.Rect(box_rect.x, box_rect.y + 40, box_rect.width, box_rect.height - 40))
            else:
                draw_text_wrapped(screen, game.dialogue_text, font_sm, (220, 220, 220),
                    pygame.Rect(box_rect.x, box_rect.y + 40, box_rect.width, box_rect.height - 40))

        # Search result box
        if game.search_result_text and game.search_result_timer > 0:
            box_h = 120
            box_rect = pygame.Rect(20, SCREEN_H - box_h - 20, SCREEN_W - 40, box_h)
            is_evidence = game.search_result_text.startswith("EVIDENCE")
            bg_col = (30, 25, 10) if is_evidence else (20, 20, 30)
            border_col = (220, 180, 40) if is_evidence else (100, 100, 120)
            pygame.draw.rect(screen, bg_col, box_rect, border_radius=8)
            pygame.draw.rect(screen, border_col, box_rect, 2, border_radius=8)

            header = "Evidence Found!" if is_evidence else "Investigation"
            header_col = (255, 220, 60) if is_evidence else (180, 180, 200)
            header_surf = font_md.render(header, True, header_col)
            screen.blit(header_surf, (box_rect.x + 12, box_rect.y + 8))

            display_text = game.search_result_text.replace("EVIDENCE FOUND: ", "") if is_evidence else game.search_result_text
            draw_text_wrapped(screen, display_text, font_sm, (220, 220, 220),
                pygame.Rect(box_rect.x, box_rect.y + 36, box_rect.width, box_rect.height - 36))

        # Evidence log overlay
        if game.showing_evidence_log:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))

            draw_centered_text(screen, "EVIDENCE LOG", font_lg, (255, 220, 60), 40)
            draw_centered_text(screen, "[UP/DOWN] Scroll  [L/ESC] Close", font_sm, (180, 180, 180), 85)

            if not game.evidence_found:
                draw_centered_text(screen, "No evidence collected yet.", font_md, (150, 150, 150), 200)
            else:
                # Group evidence by day
                by_day = {}
                for ev in game.evidence_found:
                    d = ev.get("day", "?")
                    by_day.setdefault(d, []).append(ev)

                log_lines = []
                for day in sorted(by_day.keys()):
                    log_lines.append((f"Day {day}:", (220, 180, 40), font_md))
                    for ev in by_day[day]:
                        log_lines.append((f"  - {ev['name']}: {ev['description']}", (200, 200, 200), font_sm))

                visible_start = game.evidence_log_scroll
                visible_end = min(visible_start + 12, len(log_lines))
                game.evidence_log_scroll = min(game.evidence_log_scroll, max(0, len(log_lines) - 12))

                y_pos = 120
                for i in range(visible_start, visible_end):
                    line_text, line_col, line_font = log_lines[i]
                    # Word-wrap long evidence lines
                    y_pos = draw_centered_text_wrapped(screen, line_text, line_font, line_col, y_pos, max_width=SCREEN_W - 100)
                    y_pos += 4

        # Accusation overlay
        if game.state == "ACCUSE":
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))

            draw_centered_text(screen, "Who do you accuse?", font_lg, BLOOD_RED, 80)
            draw_centered_text(screen, "[UP/DOWN] Select  [ENTER] Confirm  [ESC] Cancel", font_sm, (180, 180, 180), 130)

            suspects = [c for c in game.alive]
            for i, c in enumerate(suspects):
                y_pos = 180 + i * 50
                col = (255, 255, 100) if i == game.accuse_selection else (200, 200, 200)
                prefix = "> " if i == game.accuse_selection else "  "
                text = f"{prefix}{c['name']}  ({c['personality']}, from {c['hometown']})"
                draw_centered_text(screen, text, font_md, col, y_pos)

    elif game.state == "ACCUSE_RESULT":
        screen.fill((40, 30, 10))
        cur_y = 220
        for line in game.storyteller_text.split("\n"):
            cur_y = draw_centered_text_wrapped(screen, line, font_lg, (255, 200, 80), cur_y)
        draw_centered_text(screen, "Press ENTER to continue", font_md, (200, 200, 180), 500)

    elif game.state == "WIN":
        screen.fill((10, 40, 10))
        cur_y = 200
        for line in game.storyteller_text.split("\n"):
            cur_y = draw_centered_text_wrapped(screen, line, font_lg, (100, 255, 100), cur_y)
        draw_centered_text(screen, "Press ENTER for main menu", font_md, (180, 255, 180), 500)

    elif game.state == "LOSE":
        screen.fill((40, 10, 10))
        cur_y = 160
        for line in game.storyteller_text.split("\n"):
            cur_y = draw_centered_text_wrapped(screen, line, font_lg, BLOOD_RED, cur_y)
        draw_centered_text(screen, "Press ENTER for main menu", font_md, (255, 180, 180), 500)

    pygame.display.flip()

pygame.quit()
sys.exit()
