import math
import pygame
import sys
import os
import csv
import random
import re
import threading
import ollama
import numpy as np

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

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

# -- Procedural footstep sounds --
def _bandpass(signal, low_hz, high_hz, sample_rate):
    """Zero-phase FFT bandpass filter."""
    fft = np.fft.rfft(signal)
    freqs = np.fft.rfftfreq(len(signal), 1.0 / sample_rate)
    fft[(freqs < low_hz) | (freqs > high_hz)] = 0
    return np.fft.irfft(fft, len(signal))

def _lowpass(signal, cutoff_hz, sample_rate):
    """Simple IIR low-pass filter."""
    alpha = 1.0 / (1.0 + sample_rate / (2.0 * np.pi * cutoff_hz))
    out = np.zeros_like(signal)
    out[0] = signal[0]
    for i in range(1, len(signal)):
        out[i] = out[i - 1] + alpha * (signal[i] - out[i - 1])
    return out

def _make_footstep(sample_rate=44100, kind="stone"):
    """Generate a layered, realistic footstep sound as a pygame Sound."""
    rng = np.random.default_rng()

    if kind == "stone":
        # Stone/cobblestone: heel click + sole slap + low body thud
        n = int(sample_rate * 0.18)
        t = np.linspace(0, 0.18, n, endpoint=False)
        noise = rng.uniform(-1, 1, n)

        # Layer 1: sharp heel click — high frequencies, very fast decay
        click = _bandpass(noise, 2000, 7000, sample_rate)
        click *= np.exp(-t * 120)
        click *= 0.55

        # Layer 2: sole slap — mid frequencies, medium decay
        slap = _bandpass(noise, 300, 1200, sample_rate)
        slap *= np.exp(-t * 45)
        slap *= 0.7

        # Layer 3: body thud — low sine sweep, slow decay
        thud = np.sin(2 * np.pi * (100 - 40 * t) * t) * np.exp(-t * 30)
        thud *= 0.9

        wave = click + slap + thud

    else:  # grass — soft compression underfoot: rustle + muffled thud
        n = int(sample_rate * 0.22)
        t = np.linspace(0, 0.22, n, endpoint=False)
        noise = rng.uniform(-1, 1, n)

        # Layer 1: high rustle — grass blades, moderate decay
        rustle = _bandpass(noise, 800, 4000, sample_rate)
        rustle *= np.exp(-t * 35) * (1 - np.exp(-t * 80))  # soft attack
        rustle *= 0.45

        # Layer 2: muffled thud — very low, heavily filtered
        thud_noise = rng.uniform(-1, 1, n)
        thud = _lowpass(thud_noise, 180, sample_rate)
        thud *= np.exp(-t * 50)
        thud *= 0.6

        wave = rustle + thud

    # Normalize and add slight random pitch variation for naturalness
    peak = np.max(np.abs(wave))
    if peak > 0:
        wave /= peak
    wave *= 0.75 + rng.uniform(-0.1, 0.1)

    wave = (wave * 32767).clip(-32767, 32767).astype(np.int16)
    if pygame.mixer.get_init()[2] == 2:  # stereo
        wave = np.column_stack([wave, wave])
    sound = pygame.sndarray.make_sound(wave)
    sound.set_volume(0.55)
    return sound

# Pre-generate a small pool of variations so no two steps sound identical
_stone_pool = [_make_footstep(kind="stone") for _ in range(4)]
_grass_pool = [_make_footstep(kind="grass") for _ in range(4)]
_step_index = 0

def play_footstep(kind="stone"):
    global _step_index
    pool = _stone_pool if kind == "stone" else _grass_pool
    pool[_step_index % len(pool)].play()
    _step_index += 1

MENU_MUSIC = "sounds/The_Crimson_Manor.mp3"
DAY_MUSIC = "sounds/in-game-sound-track.mp3"

# Sound effects
sfx_door = pygame.mixer.Sound("sounds/opening_door.mp3")
sfx_door.set_volume(0.7)
EVIDENCE_SOUND = pygame.mixer.Sound("sounds/evidence_sounds.mp3")
EVIDENCE_SOUND.set_volume(0.9)


def music_start_menu():
    """Fade in main menu soundtrack."""
    pygame.mixer.music.load(MENU_MUSIC)
    pygame.mixer.music.set_volume(0.5)
    pygame.mixer.music.play(loops=-1, fade_ms=2000)


def music_start_day():
    """Fade in daytime soundtrack."""
    pygame.mixer.music.load(DAY_MUSIC)
    pygame.mixer.music.set_volume(0.6)
    pygame.mixer.music.play(loops=-1, fade_ms=3000)


def music_stop(fade_ms=2000):
    """Fade out and stop music."""
    pygame.mixer.music.fadeout(fade_ms)

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

PLAYER_SPRITE_SIZE = (TILE_SIZE + 8, TILE_SIZE + 8)  # slightly bigger than a tile

# Idle sprites from rotations/
player_idle_sprites = {}
for d in DIRECTIONS:
    player_idle_sprites[d] = load_sprite(f"assets/characters/detective_hero/rotations/{d}.png", PLAYER_SPRITE_SIZE)

# Walk animation frames
player_walk_frames = {}
for d in DIRECTIONS:
    frames = []
    for i in range(WALK_FRAME_COUNT):
        frame = load_sprite(f"assets/characters/detective_hero/animations/walk/{d}/frame_{i:03d}.png", PLAYER_SPRITE_SIZE)
        frames.append(frame)
    player_walk_frames[d] = frames

# Fallback player image
player_img_fallback = pygame.image.load("character.jpg").convert()
player_img_fallback = pygame.transform.scale(player_img_fallback, (TILE_SIZE - 4, TILE_SIZE - 4))

# Menu background — load animated GIF frames via Pillow
def _load_gif_frames(path, target_size):
    from PIL import Image
    pil_img = Image.open(path)
    frames = []
    for i in range(pil_img.n_frames):
        pil_img.seek(i)
        frame = pil_img.convert("RGBA")
        raw = frame.tobytes()
        surf = pygame.image.frombytes(raw, frame.size, "RGBA").convert_alpha()
        surf = pygame.transform.smoothscale(surf, target_size)
        frames.append(surf)
    return frames

menu_bg_frames = _load_gif_frames("bg_village.gif", (SCREEN_W, SCREEN_H))
menu_bg_frame_idx = 0
menu_bg_timer = 0.0
MENU_BG_FPS = 15  # playback speed

# Village skin — loaded once, scaled to full map dimensions
def _load_village_skin(path):
    from PIL import Image
    try:
        img = Image.open(path).convert("RGBA")
        img = img.resize((MAP_W * TILE_SIZE, MAP_H * TILE_SIZE), Image.LANCZOS)
        raw = img.tobytes()
        surf = pygame.image.frombytes(raw, img.size, "RGBA").convert_alpha()
        return surf
    except Exception as e:
        print(f"Could not load village skin: {e}")
        return None

village_skin = _load_village_skin("images/village.png")

player_facing = "south"
player_walking = False
player_anim_timer = 0.0
player_anim_frame = 0

# NPC pixel art sprites (south-facing for standing NPCs)
NPC_SPRITE_SIZE = (TILE_SIZE + 8, TILE_SIZE + 8)  # slightly bigger than a tile
npc_sprite_files = [
    "assets/characters/blacksmith_south.png",
    "assets/characters/villager_south.png",
    "assets/characters/blacksmith_south.png",
    "assets/characters/villager_south.png",
    "assets/characters/blacksmith_south.png",
    "assets/characters/villager_south.png",
    "assets/characters/blacksmith_south.png",
]
npc_sprites = [load_sprite(f, NPC_SPRITE_SIZE) if f else None for f in npc_sprite_files]

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

# Visual styles for building interiors (floor tint, accent color, furniture style)
INTERIOR_STYLES = {
    "the Blacksmith":    {"floor": (130, 100, 60), "accent": (200, 100, 30), "style": "forge"},
    "the Tavern":        {"floor": (120, 90, 55),  "accent": (160, 120, 50), "style": "tavern"},
    "the Apothecary":    {"floor": (110, 115, 90), "accent": (80, 160, 100), "style": "potions"},
    "Town Hall":         {"floor": (140, 120, 80), "accent": (180, 160, 100),"style": "office"},
    "the Library":       {"floor": (125, 105, 75), "accent": (140, 80, 50),  "style": "books"},
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
        # Relationships & memory
        self.relationships = {}       # (name_a, name_b) -> {"type": str, "detail": str}
        self.npc_memory = {}          # name -> list of short memory strings
        self.npc_emotional_state = {} # name -> {"fear": int, "anger": int, "desperation": int}
        self.suspicion_log = []       # list of {"day": int, "source": str, "text": str}
        self.showing_clue_tracker = False
        self.clue_tracker_scroll = 0
        # Fade transition system
        self.fade_alpha = 0
        self.fade_direction = 0   # 1=fading out, -1=fading in, 0=idle
        self.fade_callback = None
        self.fade_speed = 600     # alpha per second
        self.loading_dot_timer = 0.0
        # Journal
        self.showing_journal = False
        self.journal_page = 0  # index into self.characters

    def start_fade(self, callback=None):
        """Start a fade-to-black transition. Callback fires at peak darkness."""
        self.fade_direction = 1
        self.fade_callback = callback
        self.fade_alpha = 0

    @property
    def fading(self):
        return self.fade_direction != 0

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
        self.suspicion_log = []
        self.showing_clue_tracker = False
        self.clue_tracker_scroll = 0

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

        # Init per-NPC memory and emotions
        self.npc_memory = {}
        self.npc_emotional_state = {}
        for c in self.characters:
            self.npc_memory[c["name"]] = []
            self.npc_emotional_state[c["name"]] = {"fear": 0, "anger": 0, "desperation": 0}

        # Generate relationships
        self._generate_relationships()

        # Player start
        self.player_x = 14.0 * TILE_SIZE
        self.player_y = 7.0 * TILE_SIZE

        self.start_night()

    def _generate_relationships(self):
        """Generate relationships between NPCs. Villain always has motive-type relationships."""
        MOTIVE_TYPES = ["rivals", "old_grudge", "romantic"]
        OTHER_TYPES = ["friends", "business_partners", "mentor_student"]
        ALL_TYPES = MOTIVE_TYPES + OTHER_TYPES

        TEMPLATES = {
            "rivals": [
                "{a} and {b} have competed for business for years.",
                "{a} and {b} have clashed over influence in town.",
                "{a} and {b} both wanted the same position at {a_home}.",
            ],
            "old_grudge": [
                "{a} blames {b} for something from back in {a_town}.",
                "{b} wronged {a} years ago and it was never forgiven.",
                "{a} and {b} had a falling out that split the town.",
            ],
            "romantic": [
                "{a} and {b} were once close, but things ended badly.",
                "{a} still has feelings for {b}, but {b} moved on.",
                "{a} and {b} had a secret relationship that fell apart.",
            ],
            "friends": [
                "{a} and {b} are close friends who look out for each other.",
                "{a} and {b} have been loyal friends since childhood.",
                "{a} and {b} share meals at {b_home} most evenings.",
            ],
            "business_partners": [
                "{a} and {b} trade goods between {a_home} and {b_home}.",
                "{a} supplies materials to {b} regularly.",
                "{a} and {b} work together on town projects.",
            ],
            "mentor_student": [
                "{a} taught {b} everything they know.",
                "{b} apprenticed under {a} at {a_home} years ago.",
                "{a} took {b} in when they first arrived from {b_town}.",
            ],
        }

        self.relationships = {}
        villain = next(c for c in self.characters if c["is_villain"])

        for i, a in enumerate(self.characters):
            for j, b in enumerate(self.characters):
                if j <= i:
                    continue
                a_home = a.get("home", "town")
                b_home = b.get("home", "town")

                # Villain must have a motive with everyone
                if a["is_villain"] or b["is_villain"]:
                    rtype = random.choice(MOTIVE_TYPES)
                elif random.random() < 0.4:
                    rtype = random.choice(ALL_TYPES)
                else:
                    continue

                template = random.choice(TEMPLATES[rtype])
                detail = template.format(
                    a=a["name"], b=b["name"],
                    a_home=a_home, b_home=b_home,
                    a_town=a["hometown"], b_town=b["hometown"],
                )
                self.relationships[(a["name"], b["name"])] = {"type": rtype, "detail": detail}

    def get_relationship(self, name_a, name_b):
        """Look up relationship between two NPCs (checks both orderings)."""
        r = self.relationships.get((name_a, name_b))
        if r:
            return r
        return self.relationships.get((name_b, name_a))

    def start_night(self):
        self.night_num += 1
        self.state = "NIGHT"
        music_stop(fade_ms=2000)
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
                # Record murder memory and escalate emotions for all survivors
                for npc in self.alive:
                    name = npc["name"]
                    if name in self.npc_memory:
                        self.npc_memory[name].append(f"Day {self.night_num}: {victim['name']} was murdered.")
                    if name in self.npc_emotional_state:
                        self.npc_emotional_state[name]["fear"] += 1
                        self.npc_emotional_state[name]["anger"] += 1
            else:
                self.storyteller_text = f"Night {self.night_num}..."

        # Escalate fear for all survivors each night
        for npc in self.alive:
            if npc["name"] in self.npc_emotional_state:
                self.npc_emotional_state[npc["name"]]["fear"] += 1

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
            "motive_hint": self._get_motive_hint(villain, victim),
        }

    def _get_motive_hint(self, villain, victim):
        """Look up the relationship between villain and victim for motive context."""
        rel = self.get_relationship(villain["name"], victim["name"])
        if rel:
            return f"{villain['name']} and {victim['name']} were {rel['type'].replace('_', ' ')}. {rel['detail']}"
        return ""

    def start_day(self):
        self.state = "DAY"
        self.dialogue_target = None
        self.dialogue_text = ""
        self.talked_to = set()  # track who we've talked to this day
        self.search_result_text = ""
        self.search_result_timer = 0.0
        music_start_day()
        self._place_npcs_for_day()
        self._place_evidence()
        self._prefetch_dialogues()

    def _place_npcs_for_day(self):
        """Randomly place NPCs around town — some outside, some inside buildings.
        No two NPCs can occupy the same tile."""
        clues = getattr(self, 'night_clues', {})
        murder_loc = clues.get("murder_location", None)
        interior_buildings = [b for b in INTERIORS.keys()]
        outdoor_spots = list(NPC_OUTDOOR_SPOTS)
        random.shuffle(outdoor_spots)
        outdoor_idx = 0

        # Track occupied positions: ("outside", tx, ty) or ("interior", building, tx, ty)
        occupied = set()

        def is_occupied(loc_type, building, tx, ty):
            if loc_type == "interior":
                return ("interior", building, tx, ty) in occupied
            return ("outside", None, tx, ty) in occupied

        def mark_occupied(loc_type, building, tx, ty):
            if loc_type == "interior":
                occupied.add(("interior", building, tx, ty))
            else:
                occupied.add(("outside", None, tx, ty))

        def place_npc(npc, loc_type, building, tx, ty, desc):
            npc["location_type"] = loc_type
            npc["location_building"] = building
            npc["location_desc"] = desc
            npc["x"] = tx * TILE_SIZE
            npc["y"] = ty * TILE_SIZE
            npc["tile_x"] = tx
            npc["tile_y"] = ty
            mark_occupied(loc_type, building, tx, ty)

        for npc in self.alive:
            npc_idx = self.characters.index(npc)
            home = BUILDING_NAMES[npc_idx] if npc_idx < len(BUILDING_NAMES) else "their home"

            if npc["is_villain"] and murder_loc and self.night_num > 1:
                # Villain: place near murder location
                placed = False
                if murder_loc in INTERIORS:
                    interior = INTERIORS[murder_loc]
                    for r, row in enumerate(interior["map"]):
                        for c, tile in enumerate(row):
                            if tile == 7 and not is_occupied("interior", murder_loc, c, r):
                                place_npc(npc, "interior", murder_loc, c, r, f"inside {murder_loc}")
                                placed = True
                                break
                        if placed:
                            break
                if not placed:
                    for door_pos, bname in DOOR_TO_BUILDING.items():
                        if bname == murder_loc:
                            tx, ty = door_pos[0], door_pos[1] + 1
                            if not is_occupied("outside", None, tx, ty):
                                place_npc(npc, "outside", None, tx, ty, f"near {murder_loc}")
                                placed = True
                                break
                if not placed:
                    while outdoor_idx < len(outdoor_spots):
                        pos, area = outdoor_spots[outdoor_idx]
                        outdoor_idx += 1
                        if not is_occupied("outside", None, pos[0], pos[1]):
                            place_npc(npc, "outside", None, pos[0], pos[1], f"at {area}")
                            placed = True
                            break
                if not placed:
                    spawn = NPC_SPAWNS[npc_idx]
                    place_npc(npc, "outside", None, spawn[0], spawn[1], f"outside {home}")
            else:
                # Innocent NPCs: randomly place at home, inside a building, or wandering
                placed = False
                roll = random.random()
                if roll < 0.35 and interior_buildings:
                    bname = random.choice(interior_buildings)
                    interior = INTERIORS[bname]
                    floor_tiles = [(c, r) for r, row in enumerate(interior["map"])
                                   for c, tile in enumerate(row)
                                   if tile == 7 and not is_occupied("interior", bname, c, r)]
                    if floor_tiles:
                        ix, iy = random.choice(floor_tiles)
                        place_npc(npc, "interior", bname, ix, iy, f"inside {bname}")
                        placed = True
                if not placed and roll < 0.65:
                    while outdoor_idx < len(outdoor_spots):
                        pos, area = outdoor_spots[outdoor_idx]
                        outdoor_idx += 1
                        if not is_occupied("outside", None, pos[0], pos[1]):
                            place_npc(npc, "outside", None, pos[0], pos[1], f"at {area}")
                            placed = True
                            break
                if not placed:
                    spawn = NPC_SPAWNS[npc_idx]
                    if not is_occupied("outside", None, spawn[0], spawn[1]):
                        place_npc(npc, "outside", None, spawn[0], spawn[1], f"outside {home}")
                    else:
                        # Home is taken, find any free outdoor spot
                        while outdoor_idx < len(outdoor_spots):
                            pos, area = outdoor_spots[outdoor_idx]
                            outdoor_idx += 1
                            if not is_occupied("outside", None, pos[0], pos[1]):
                                place_npc(npc, "outside", None, pos[0], pos[1], f"at {area}")
                                break
                        else:
                            # Last resort: offset from home
                            place_npc(npc, "outside", None, spawn[0] + 1, spawn[1], f"outside {home}")

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

            # Relationships
            rel_parts = []
            for other in self.alive:
                if other["name"] == npc["name"]:
                    continue
                rel = self.get_relationship(npc["name"], other["name"])
                if rel:
                    rel_parts.append(f"{rel['type'].replace('_', ' ')} with {other['name']}")
            if rel_parts:
                system += f"Your relationships: {'; '.join(rel_parts)}. "

            # Memory (last 4 entries)
            memories = self.npc_memory.get(npc["name"], [])
            if memories:
                recent = memories[-4:]
                system += f"Your recent memories: {'; '.join(recent)}. "

            # Emotional state
            emo = self.npc_emotional_state.get(npc["name"], {})
            fear = emo.get("fear", 0)
            if is_villain:
                desp = emo.get("desperation", 0)
                if desp >= 2:
                    system += "Suspicion may be mounting. Aggressively deflect blame onto others. Act offended if questioned. "
                elif desp >= 1:
                    system += "You sense the detective is getting closer. Be more careful with your words. "
            else:
                if fear >= 3:
                    system += "You are terrified and desperate for answers. "
                elif fear >= 2:
                    system += "You are very scared and anxious. "
                elif fear >= 1:
                    system += "You are nervous and on edge. "

            # Accusation awareness
            past_accusations = [e for e in self.history if e["type"] == "accusation" and not e["correct"]]
            if past_accusations:
                if is_villain:
                    names = [e["accused"] for e in past_accusations]
                    system += f"The detective wrongly accused {', '.join(names)} before. Use this — suggest the detective is confused. "
                elif any(e["accused"] == npc["name"] for e in past_accusations):
                    system += "You were wrongly accused before and you are angry about it. Remind the detective of their mistake. "

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
                    motive = clues.get("motive_hint", "")
                    motive_line = f"Motive to consider: {motive} " if motive else ""
                    system += (
                        f"{victim_name} was found dead at {murder_loc} with {cause}, killed {time_desc}. "
                        f"YOUR SPECIFIC OBSERVATION: {npc_clue} "
                        f"{motive_line}"
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
            music_stop(fade_ms=1500)
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
            # Record accusation in NPC memories
            for npc in self.alive:
                name = npc["name"]
                if name in self.npc_memory:
                    self.npc_memory[name].append(f"Day {self.night_num}: Detective wrongly accused {character['name']}.")
            # Villain becomes more desperate
            villain_npc = next((c for c in self.alive if c["is_villain"]), None)
            if villain_npc and villain_npc["name"] in self.npc_emotional_state:
                self.npc_emotional_state[villain_npc["name"]]["desperation"] += 1
            if self.wrong_guesses >= 3:
                music_stop(fade_ms=1500)
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
            # Record memory and suspicion log
            if npc["name"] in self.npc_memory:
                self.npc_memory[npc["name"]].append(f"Day {self.night_num}: Spoke to the detective.")
            self.suspicion_log.append({
                "day": self.night_num,
                "source": npc["name"],
                "text": self.dialogue_text[:150],
            })
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
                EVIDENCE_SOUND.play()

                if key in self.evidence_placements:
                    ev = self.evidence_placements[key]
                    self.evidence_found.append(ev)
                    self.show_search_result(f"EVIDENCE FOUND: {ev['description']}")
                    self.history.append({
                        "type": "evidence", "day": self.night_num,
                        "description": f"The detective found {ev['name']} at {spot['name']}.",
                    })
                    self.suspicion_log.append({
                        "day": self.night_num,
                        "source": "Investigation",
                        "text": f"Found {ev['name']} at {spot['name']}.",
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
music_start_menu()

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

def blit_clamped(surface, surf, x, y):
    """Blit a surface clamped within screen bounds."""
    x = max(4, min(x, SCREEN_W - surf.get_width() - 4))
    y = max(48, min(y, SCREEN_H - surf.get_height() - 4))
    surface.blit(surf, (x, y))

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
                    elif game.showing_clue_tracker:
                        game.showing_clue_tracker = False
                    elif game.showing_journal:
                        game.showing_journal = False
                    elif game.search_result_timer > 0:
                        game.search_result_timer = 0
                        game.search_result_text = ""
                    elif game.dialogue_target:
                        game.dialogue_target = None
                        game.dialogue_text = ""
                        game.dialogue_loading = False
                    elif game.current_interior and not game.fading:
                        sfx_door.play()
                        # Exit interior back to town with fade
                        game.start_fade(lambda: game.try_exit_interior())
                    else:
                        running = False
                else:
                    running = False

            # Menu
            if game.state == "MENU" and event.key == pygame.K_RETURN and not game.fading:
                game.start_fade(lambda: game.new_game())

            # Night — skip with any key after timer
            if game.state == "NIGHT" and game.night_timer <= 0 and not game.fading:
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    game.start_fade(lambda: game.start_day())

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
                    elif game.current_interior and game.is_on_exit() and not game.fading:
                        sfx_door.play()
                        game.start_fade(lambda: game.try_exit_interior())
                    # Try enter building
                    elif not game.current_interior and game.is_on_door() and not game.fading:
                        sfx_door.play()
                        game.start_fade(lambda: game.try_enter_building())
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
                    game.showing_clue_tracker = False
                    game.showing_journal = False
                    game.evidence_log_scroll = 0

                if event.key == pygame.K_j:
                    game.showing_clue_tracker = not game.showing_clue_tracker
                    game.showing_evidence_log = False
                    game.showing_journal = False
                    game.clue_tracker_scroll = 0

                if event.key == pygame.K_b:
                    game.showing_journal = not game.showing_journal
                    game.showing_evidence_log = False
                    game.showing_clue_tracker = False
                    game.journal_page = 0

                if event.key == pygame.K_TAB and not game.showing_evidence_log and not game.showing_clue_tracker and not game.showing_journal:
                    game.open_accuse()

                # Scroll overlays
                if game.showing_evidence_log:
                    if event.key == pygame.K_UP:
                        game.evidence_log_scroll = max(0, game.evidence_log_scroll - 1)
                    if event.key == pygame.K_DOWN:
                        game.evidence_log_scroll += 1
                if game.showing_clue_tracker:
                    if event.key == pygame.K_UP:
                        game.clue_tracker_scroll = max(0, game.clue_tracker_scroll - 1)
                    if event.key == pygame.K_DOWN:
                        game.clue_tracker_scroll += 1
                if game.showing_journal:
                    if event.key == pygame.K_LEFT:
                        game.journal_page = (game.journal_page - 1) % len(game.characters)
                    if event.key == pygame.K_RIGHT:
                        game.journal_page = (game.journal_page + 1) % len(game.characters)

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
                if (event.key == pygame.K_RETURN or event.key == pygame.K_SPACE) and not game.fading:
                    game.start_fade(lambda: game.start_night())

            # Win/Lose
            elif game.state in ("WIN", "LOSE"):
                if event.key == pygame.K_RETURN and not game.fading:
                    def _to_menu():
                        game.state = "MENU"
                        music_start_menu()
                    game.start_fade(_to_menu)

    # ── Update ──────────────────────────────────────────────────
    # Fade transition
    if game.fade_direction == 1:
        game.fade_alpha += game.fade_speed * dt
        if game.fade_alpha >= 255:
            game.fade_alpha = 255
            if game.fade_callback:
                game.fade_callback()
                game.fade_callback = None
            game.fade_direction = -1
    elif game.fade_direction == -1:
        game.fade_alpha -= game.fade_speed * dt
        if game.fade_alpha <= 0:
            game.fade_alpha = 0
            game.fade_direction = 0

    # Loading dot animation
    game.loading_dot_timer += dt

    if game.state == "NIGHT":
        game.night_timer -= dt

    if game.state == "DAY" and not game.showing_journal and not game.showing_evidence_log and not game.showing_clue_tracker:
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
                # Play footstep on every other frame (left foot / right foot)
                if player_anim_frame % 3 == 0:
                    ptx = int((game.player_x + (TILE_SIZE - 4) / 2) // TILE_SIZE)
                    pty = int((game.player_y + (TILE_SIZE - 4) / 2) // TILE_SIZE)
                    if game.current_interior:
                        imap = INTERIORS[game.current_interior]["map"]
                        tile = imap[pty][ptx] if 0 <= pty < len(imap) and 0 <= ptx < len(imap[0]) else 7
                        play_footstep("stone" if tile in (7, 8) else "grass")
                    else:
                        tile = tilemap[pty][ptx] if 0 <= pty < MAP_H and 0 <= ptx < MAP_W else 0
                        play_footstep("stone" if tile == 2 else "grass")
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
        # Animate GIF background
        menu_bg_timer += dt
        if menu_bg_timer >= 1.0 / MENU_BG_FPS:
            menu_bg_timer -= 1.0 / MENU_BG_FPS
            menu_bg_frame_idx = (menu_bg_frame_idx + 1) % len(menu_bg_frames)
        screen.blit(menu_bg_frames[menu_bg_frame_idx], (0, 0))
        draw_centered_text(screen, "MURDER MYSTERY", font_title, BLOOD_RED, 180)
        draw_centered_text(screen, "A villain hides among the townspeople.", font_md, (200, 200, 200), 270)
        draw_centered_text(screen, "Find them before it's too late.", font_md, (200, 200, 200), 310)
        draw_centered_text(screen, "Press ENTER to begin", font_md, (255, 255, 255), 420)
        draw_centered_text(screen, "[WASD] Move  [E] Interact  [B] Journal  [L] Log  [J] Clues  [TAB] Accuse", font_sm, (150, 150, 150), 500)

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
            # ── Draw interior map with visual polish ──
            imap = INTERIORS[game.current_interior]["map"]
            ih, iw = len(imap), len(imap[0])
            style = INTERIOR_STYLES.get(game.current_interior, {"floor": INTERIOR_FLOOR_COLOR, "accent": (150, 100, 50), "style": "office"})
            floor_col = style["floor"]
            floor_col_alt = (floor_col[0] - 10, floor_col[1] - 10, floor_col[2] - 10)
            accent_col = style["accent"]
            bld_style = style["style"]

            for row in range(ih):
                for col in range(iw):
                    tile = imap[row][col]
                    rect = pygame.Rect(
                        col * TILE_SIZE - cam_x,
                        row * TILE_SIZE - cam_y,
                        TILE_SIZE, TILE_SIZE,
                    )

                    if tile == 7:  # Floor — wood plank effect
                        base = floor_col if row % 2 == 0 else floor_col_alt
                        pygame.draw.rect(screen, base, rect)
                        # Plank lines
                        for py in range(0, TILE_SIZE, 12):
                            pygame.draw.line(screen, (base[0] - 15, base[1] - 15, base[2] - 15),
                                (rect.x, rect.y + py), (rect.x + TILE_SIZE, rect.y + py), 1)
                    elif tile == 8:  # Wall — with baseboard and trim
                        pygame.draw.rect(screen, INTERIOR_WALL_COLOR, rect)
                        # Lighter trim at top
                        pygame.draw.rect(screen, (80, 70, 60), (rect.x, rect.y, TILE_SIZE, 4))
                        # Darker baseboard at bottom
                        pygame.draw.rect(screen, (40, 35, 30), (rect.x, rect.y + TILE_SIZE - 5, TILE_SIZE, 5))
                    elif tile == 9:  # Furniture — styled per building
                        pygame.draw.rect(screen, FURNITURE_COLOR, rect)
                        inner = rect.inflate(-8, -8)
                        if bld_style == "forge":
                            # Orange glow for anvil/forge
                            pygame.draw.rect(screen, accent_col, inner)
                            glow = pygame.Surface((inner.width, inner.height), pygame.SRCALPHA)
                            glow.fill((255, 120, 20, 60))
                            screen.blit(glow, inner)
                        elif bld_style == "tavern":
                            # Barrel/keg shapes
                            pygame.draw.rect(screen, accent_col, inner)
                            pygame.draw.ellipse(screen, (accent_col[0] + 20, accent_col[1] + 20, accent_col[2] + 10), inner.inflate(-4, -12))
                        elif bld_style == "books":
                            # Book spines — vertical lines (deterministic colors by position)
                            book_colors = [(180, 60, 50), (50, 80, 140), (60, 130, 70), (160, 140, 50)]
                            pygame.draw.rect(screen, accent_col, inner)
                            bi = 0
                            for bx in range(inner.x + 3, inner.x + inner.width - 3, 5):
                                pygame.draw.line(screen, book_colors[(bi + col) % len(book_colors)],
                                    (bx, inner.y + 2), (bx, inner.y + inner.height - 2), 3)
                                bi += 1
                        elif bld_style == "potions":
                            # Vial circles (deterministic colors by position)
                            vial_colors = [(100, 200, 100), (200, 80, 200), (80, 150, 220)]
                            pygame.draw.rect(screen, accent_col, inner)
                            vi = 0
                            for vx in range(inner.x + 8, inner.x + inner.width - 4, 12):
                                pygame.draw.circle(screen, vial_colors[(vi + row) % len(vial_colors)],
                                    (vx, inner.centery), 4)
                                vi += 1
                        elif bld_style == "office":
                            # Desk with paper
                            pygame.draw.rect(screen, accent_col, inner)
                            paper = inner.inflate(-16, -10)
                            pygame.draw.rect(screen, (230, 225, 210), paper)
                        else:
                            pygame.draw.rect(screen, accent_col, inner)
                    elif tile == 4:  # Door — visible frame with handle
                        pygame.draw.rect(screen, (80, 60, 35), rect)  # frame
                        door_inner = rect.inflate(-10, -6)
                        door_inner.y += 3
                        pygame.draw.rect(screen, DOOR_COLOR, door_inner)
                        # Handle
                        pygame.draw.circle(screen, (200, 180, 100), (door_inner.x + door_inner.width - 8, door_inner.centery), 3)
                    else:
                        pygame.draw.rect(screen, TILE_COLORS.get(tile, BG_COLOR), rect)

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
            npc_off = (NPC_SPRITE_SIZE[0] - TILE_SIZE) // 2
            for npc in game.alive:
                if npc.get("location_type") == "interior" and npc.get("location_building") == game.current_interior:
                    sx = npc["x"] - cam_x
                    sy = npc["y"] - cam_y
                    idx = game.characters.index(npc) if npc in game.characters else -1
                    sprite = npc_sprites[idx] if 0 <= idx < len(npc_sprites) else None
                    if sprite:
                        screen.blit(sprite, (sx - npc_off, sy - npc_off))
                    else:
                        pygame.draw.rect(screen, npc["color"], (sx, sy, TILE_SIZE - 4, TILE_SIZE - 4))
                    name_surf = font_sm.render(npc["name"], True, (255, 255, 255))
                    screen.blit(name_surf, (sx + TILE_SIZE / 2 - name_surf.get_width() / 2, sy - 22))
                    if player_near(npc) and not game.dialogue_target:
                        if npc["name"] in game.talked_to:
                            hint = font_sm.render("(already spoke)", True, (150, 150, 150))
                        else:
                            hint = font_sm.render("[E] Talk", True, (255, 255, 200))
                        blit_clamped(screen, hint, sx - 5, sy - 38)

        else:
            # ── Draw town map ──
            if village_skin:
                screen.blit(village_skin, (-cam_x, -cam_y))
            else:
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
            npc_off = (NPC_SPRITE_SIZE[0] - TILE_SIZE) // 2
            for npc in game.alive:
                if npc.get("location_type") == "interior":
                    continue  # Skip NPCs inside buildings
                sx = npc["x"] - cam_x
                sy = npc["y"] - cam_y
                idx = game.characters.index(npc) if npc in game.characters else -1
                sprite = npc_sprites[idx] if 0 <= idx < len(npc_sprites) else None
                if sprite:
                    screen.blit(sprite, (sx - npc_off, sy - npc_off))
                else:
                    pygame.draw.rect(screen, npc["color"], (sx, sy, TILE_SIZE - 4, TILE_SIZE - 4))
                name_surf = font_sm.render(npc["name"], True, (255, 255, 255))
                screen.blit(name_surf, (sx + TILE_SIZE / 2 - name_surf.get_width() / 2, sy - 22))

                # Interaction hint
                if player_near(npc) and not game.dialogue_target:
                    if npc["name"] in game.talked_to:
                        hint = font_sm.render("(already spoke)", True, (150, 150, 150))
                    else:
                        hint = font_sm.render("[E] Talk", True, (255, 255, 200))
                    blit_clamped(screen, hint, sx - 5, sy - 38)

            # Door enter hint
            door_building = game.is_on_door()
            if door_building and not game.dialogue_target:
                hint = font_sm.render(f"[E] Enter {door_building}", True, (255, 255, 200))
                blit_clamped(screen, hint, game.player_x - cam_x - hint.get_width() // 2 + pw // 2, game.player_y - cam_y - 25)

        # Draw player (both town and interior)
        if player_walking:
            frames = player_walk_frames.get(player_facing)
            p_sprite = frames[player_anim_frame] if frames else None
        else:
            p_sprite = player_idle_sprites.get(player_facing)
        p_off = (PLAYER_SPRITE_SIZE[0] - TILE_SIZE) // 2
        if p_sprite:
            screen.blit(p_sprite, (game.player_x - cam_x - p_off, game.player_y - cam_y - p_off))
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
            blit_clamped(screen, hint, game.player_x - cam_x - hint.get_width() // 2 + pw // 2, game.player_y - cam_y - 25)

        # Exit hint in interior
        if game.current_interior and game.is_on_exit():
            hint = font_sm.render("[E] Exit", True, (255, 255, 200))
            blit_clamped(screen, hint, game.player_x - cam_x - hint.get_width() // 2 + pw // 2, game.player_y - cam_y - 25)

        # HUD — split left/right to prevent overflow
        hud_y = 10
        ev_count = len(game.evidence_found)
        hud_h = 45
        if game.current_interior:
            hud_h = 65  # extra row for location
        pygame.draw.rect(screen, (0, 0, 0, 180), (0, 0, SCREEN_W, hud_h))

        hud_left = font_md.render(f"Day {game.night_num}  |  Guesses: {3 - game.wrong_guesses}  |  Evidence: {ev_count}", True, (255, 255, 255))
        hud_right = font_sm.render("[TAB] Accuse  [L] Log  [J] Clues  [B] Journal", True, (180, 180, 180))
        screen.blit(hud_left, (15, hud_y))
        screen.blit(hud_right, (SCREEN_W - hud_right.get_width() - 15, hud_y + 5))

        if game.current_interior:
            loc_surf = font_sm.render(f"Inside {game.current_interior}  |  [ESC] Exit", True, (200, 200, 150))
            screen.blit(loc_surf, (SCREEN_W // 2 - loc_surf.get_width() // 2, hud_y + 32))

        # Journal side button
        if not game.showing_journal and not game.showing_evidence_log and not game.showing_clue_tracker:
            jbtn = pygame.Rect(SCREEN_W - 85, SCREEN_H // 2 - 30, 75, 60)
            pygame.draw.rect(screen, (55, 40, 28), jbtn, border_radius=5)
            pygame.draw.rect(screen, (100, 80, 50), jbtn, 2, border_radius=5)
            jtext = font_sm.render("Journal", True, (200, 190, 150))
            screen.blit(jtext, (jbtn.x + jbtn.width // 2 - jtext.get_width() // 2, jbtn.y + 8))
            jkey = font_sm.render("[B]", True, (150, 140, 110))
            screen.blit(jkey, (jbtn.x + jbtn.width // 2 - jkey.get_width() // 2, jbtn.y + 32))

        # Dialogue box
        if game.dialogue_target:
            box_h = 160
            box_rect = pygame.Rect(20, SCREEN_H - box_h - 20, SCREEN_W - 40, box_h)
            pygame.draw.rect(screen, (20, 20, 30), box_rect, border_radius=8)
            pygame.draw.rect(screen, (100, 100, 120), box_rect, 2, border_radius=8)

            name_surf = font_md.render(game.dialogue_target["name"], True, game.dialogue_target["color"])
            screen.blit(name_surf, (box_rect.x + 12, box_rect.y + 8))

            if game.dialogue_loading:
                dots = "." * (int(game.loading_dot_timer / 0.4) % 3 + 1)
                draw_text_wrapped(screen, f"Thinking{dots}", font_sm, (160, 160, 180),
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

                # Scroll indicators
                if visible_start > 0:
                    draw_centered_text(screen, "▲", font_md, (180, 180, 180), 105)
                y_pos = 120
                for i in range(visible_start, visible_end):
                    line_text, line_col, line_font = log_lines[i]
                    y_pos = draw_centered_text_wrapped(screen, line_text, line_font, line_col, y_pos, max_width=SCREEN_W - 100)
                    y_pos += 4
                if visible_end < len(log_lines):
                    draw_centered_text(screen, "▼", font_md, (180, 180, 180), SCREEN_H - 40)

        # Clue tracker overlay
        if game.showing_clue_tracker:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))

            draw_centered_text(screen, "CLUE TRACKER", font_lg, (100, 200, 255), 40)
            draw_centered_text(screen, "[UP/DOWN] Scroll  [J/ESC] Close", font_sm, (180, 180, 180), 85)

            if not game.suspicion_log:
                draw_centered_text(screen, "No clues collected yet. Talk to people and search.", font_md, (150, 150, 150), 200)
            else:
                # Group by day
                by_day = {}
                for entry in game.suspicion_log:
                    d = entry.get("day", "?")
                    by_day.setdefault(d, []).append(entry)

                log_lines = []
                for day in sorted(by_day.keys()):
                    log_lines.append((f"Day {day}:", (100, 200, 255), font_md))
                    for entry in by_day[day]:
                        src = entry["source"]
                        txt = entry["text"]
                        log_lines.append((f"  [{src}] {txt}", (200, 200, 200), font_sm))

                visible_start = game.clue_tracker_scroll
                visible_end = min(visible_start + 12, len(log_lines))
                game.clue_tracker_scroll = min(game.clue_tracker_scroll, max(0, len(log_lines) - 12))

                if visible_start > 0:
                    draw_centered_text(screen, "▲", font_md, (180, 180, 180), 105)
                y_pos = 120
                for i in range(visible_start, visible_end):
                    line_text, line_col, line_font = log_lines[i]
                    y_pos = draw_centered_text_wrapped(screen, line_text, line_font, line_col, y_pos, max_width=SCREEN_W - 100)
                    y_pos += 4
                if visible_end < len(log_lines):
                    draw_centered_text(screen, "▼", font_md, (180, 180, 180), SCREEN_H - 40)

        # Journal overlay
        if game.showing_journal and game.characters:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            screen.blit(overlay, (0, 0))

            # Book background
            book = pygame.Rect(60, 30, SCREEN_W - 120, SCREEN_H - 60)
            pygame.draw.rect(screen, (45, 35, 25), book, border_radius=6)
            pygame.draw.rect(screen, (90, 70, 45), book, 3, border_radius=6)
            pygame.draw.line(screen, (70, 55, 35),
                (book.centerx, book.y + 10), (book.centerx, book.y + book.height - 10), 2)

            pg = game.journal_page
            total = len(game.characters)
            c = game.characters[pg]
            alive = c in game.alive
            status_col = (100, 200, 100) if alive else BLOOD_RED

            # Navigation
            draw_centered_text(screen, f"< {pg + 1} / {total} >", font_sm, (160, 150, 120), book.y + book.height - 30)
            draw_centered_text(screen, "[LEFT/RIGHT] Turn Page  [B/ESC] Close", font_sm, (120, 110, 90), book.y + book.height - 12)

            # ── Left page: portrait + identity ──
            lx, ly = book.x + 30, book.y + 20
            name_surf = font_lg.render(c["name"], True, (220, 210, 180))
            screen.blit(name_surf, (lx, ly))
            ly += 55
            screen.blit(font_md.render("ALIVE" if alive else "DECEASED", True, status_col), (lx, ly))
            ly += 40

            # Portrait
            idx = game.characters.index(c)
            sprite = npc_sprites[idx] if 0 <= idx < len(npc_sprites) else None
            if sprite:
                portrait = pygame.transform.smoothscale(sprite, (80, 80))
                screen.blit(portrait, (lx, ly))
            else:
                pygame.draw.rect(screen, c["color"], (lx, ly, 80, 80))
            ly += 95

            left_w = book.width // 2 - 50
            draw_text_wrapped(screen, f"Residence: {c.get('home', '?')}", font_sm, (180, 170, 140),
                pygame.Rect(lx, ly, left_w, 30))
            ly += 28
            if alive:
                draw_text_wrapped(screen, f"Last seen: {c.get('location_desc', '?')}", font_sm, (180, 170, 140),
                    pygame.Rect(lx, ly, left_w, 30))

            # ── Right page: details + relationships ──
            rx, ry = book.centerx + 20, book.y + 25
            right_w = book.width // 2 - 50

            for label, value in [
                ("Personality", c.get("personality", "?")),
                ("Hometown", c.get("hometown", "?")),
                ("Weakness", c.get("weakness", "?")),
                ("Power", c.get("power", "?")),
                ("Type", "Human" if c.get("isHuman") else "Non-Human"),
            ]:
                screen.blit(font_sm.render(f"{label}:", True, (160, 140, 100)), (rx, ry))
                ry += 22
                draw_text_wrapped(screen, value, font_md, (220, 210, 180),
                    pygame.Rect(rx + 10, ry, right_w, 40))
                ry += 38

            ry += 5
            screen.blit(font_sm.render("Relationships:", True, (160, 140, 100)), (rx, ry))
            ry += 24
            has_rel = False
            for other in game.characters:
                if other["name"] == c["name"]:
                    continue
                rel = game.get_relationship(c["name"], other["name"])
                if rel:
                    draw_text_wrapped(screen,
                        f"- {rel['type'].replace('_', ' ').title()} with {other['name']}",
                        font_sm, (200, 190, 160), pygame.Rect(rx + 5, ry, right_w, 25))
                    ry += 22
                    has_rel = True
                    if ry > book.y + book.height - 60:
                        break
            if not has_rel:
                draw_text_wrapped(screen, "No known relationships.", font_sm, (140, 130, 110),
                    pygame.Rect(rx + 5, ry, right_w, 25))

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

    # Fade overlay (drawn over everything)
    if game.fade_alpha > 0:
        fade_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        fade_surf.fill((0, 0, 0, int(game.fade_alpha)))
        screen.blit(fade_surf, (0, 0))

    pygame.display.flip()

pygame.quit()
sys.exit()
