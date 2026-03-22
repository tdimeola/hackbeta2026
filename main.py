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

# Render to a fixed-size surface, then scale to display (handles fullscreen properly)
display = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE)
screen = pygame.Surface((SCREEN_W, SCREEN_H))
is_fullscreen = False
pygame.display.set_caption("Quantum Blood")
clock = pygame.time.Clock()

font_sm = pygame.font.SysFont(None, 24)
font_md = pygame.font.SysFont(None, 32)
font_lg = pygame.font.SysFont(None, 48)
font_title = pygame.font.SysFont(None, 72)
# Menu title font — old-style serif, bigger
font_menu_title = pygame.font.SysFont("timesnewroman", 100) or pygame.font.SysFont("serif", 100)

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
    """Generate a subtle, natural footstep sound."""
    rng = np.random.default_rng()

    if kind == "stone":
        # Short, crisp tap — like a shoe on cobblestone
        n = int(sample_rate * 0.08)
        t = np.linspace(0, 0.08, n, endpoint=False)
        noise = rng.uniform(-1, 1, n)
        # Quick filtered tap
        tap = _bandpass(noise, 800, 3000, sample_rate)
        tap *= np.exp(-t * 80)
        # Subtle low impact
        impact = _lowpass(rng.uniform(-1, 1, n), 400, sample_rate)
        impact *= np.exp(-t * 60) * 0.3
        wave = tap * 0.5 + impact

    elif kind == "wood":
        # Hollow, warm tap — like stepping on a wooden floor
        n = int(sample_rate * 0.1)
        t = np.linspace(0, 0.1, n, endpoint=False)
        noise = rng.uniform(-1, 1, n)
        # Mid-range knock
        knock = _bandpass(noise, 300, 1500, sample_rate)
        knock *= np.exp(-t * 50)
        # Subtle hollow resonance
        res_freq = rng.uniform(180, 280)
        resonance = np.sin(2 * np.pi * res_freq * t) * np.exp(-t * 35) * 0.15
        wave = knock * 0.4 + resonance

    else:  # grass
        # Very soft, muffled — like stepping on soft earth
        n = int(sample_rate * 0.1)
        t = np.linspace(0, 0.1, n, endpoint=False)
        noise = rng.uniform(-1, 1, n)
        # Soft filtered noise — no sharp attack
        soft = _lowpass(noise, 1200, sample_rate)
        soft *= np.exp(-t * 40) * (1 - np.exp(-t * 100))
        wave = soft * 0.35

    # Normalize gently and add variation
    peak = np.max(np.abs(wave))
    if peak > 0:
        wave /= peak
    wave *= 0.3 + rng.uniform(-0.05, 0.05)  # much quieter overall

    wave = (wave * 32767).clip(-32767, 32767).astype(np.int16)
    if pygame.mixer.get_init()[2] == 2:  # stereo
        wave = np.column_stack([wave, wave])
    sound = pygame.sndarray.make_sound(wave)
    sound.set_volume(0.25)
    return sound

# Pre-generate a small pool of variations so no two steps sound identical
_stone_pool = [_make_footstep(kind="stone") for _ in range(4)]
_grass_pool = [_make_footstep(kind="grass") for _ in range(4)]
_wood_pool = [_make_footstep(kind="wood") for _ in range(4)]
_step_index = 0

def play_footstep(kind="stone"):
    global _step_index
    if kind == "wood":
        pool = _wood_pool
    elif kind == "stone":
        pool = _stone_pool
    else:
        pool = _grass_pool
    pool[_step_index % len(pool)].play()
    _step_index += 1

MENU_MUSIC = "sounds/The_Crimson_Manor.mp3"
DAY_MUSIC = "sounds/in-game-sound-track.mp3"
CREDITS_MUSIC = "sounds/credits.mp3"

# Sound effects
sfx_door = pygame.mixer.Sound("sounds/opening_door.mp3")
sfx_door.set_volume(0.7)
sfx_pop = pygame.mixer.Sound("sounds/speech.mp3")
sfx_pop.set_volume(0.6)
sfx_speech = pygame.mixer.Sound("sounds/speech.mp3")
sfx_speech.set_volume(1)
EVIDENCE_SOUND = pygame.mixer.Sound("sounds/evidence_sounds.mp3")
EVIDENCE_SOUND.set_volume(0.9)
REVEAL_SOUND = pygame.mixer.Sound("sounds/reveal.mp3")
REVEAL_SOUND.set_volume(0.9)
sfx_reverb_drum = pygame.mixer.Sound("sounds/reverb_drum.mp3")
sfx_reverb_drum.set_volume(0.8)
NIGHT_SOUND = pygame.mixer.Sound("sounds/night_time.mp3")
NIGHT_SOUND.set_volume(0.8)


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
    [1,0,4,4,4,4,0,0,0,0,4,4,4,4,0,0,0,0,4,4,4,4,0,0,4,4,4,4,0,1],
    [1,0,0,2,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,2,0,0,0,0,0,0,2,0,0,1],
    [1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,1],
    [1,0,3,3,3,3,0,0,0,0,3,3,3,3,0,0,0,0,3,3,3,3,0,2,5,5,0,5,0,1],
    [1,0,1,1,1,1,0,0,0,0,1,1,1,1,0,0,0,0,1,1,1,1,0,2,5,0,6,0,5,1],
    [1,0,1,1,1,1,0,0,0,0,1,1,1,1,0,0,0,0,1,1,1,1,0,2,0,5,0,5,0,1],
    [1,0,4,4,4,4,0,0,0,0,4,4,4,4,0,0,0,0,4,4,4,4,0,2,5,0,0,6,5,1],
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
# Building sprites — each covers a 4x4 tile area (192x192px)
BUILDING_SPRITE_SIZE = (TILE_SIZE * 4, TILE_SIZE * 4)
_building_sprite_files = {
    "the Blacksmith":    "assets/buildings/blacksmith.png",
    "the Tavern":        "assets/buildings/tavern.png",
    "the Apothecary":    "assets/buildings/apothecary.png",
    "the Church":        "assets/buildings/church.png",
    "the General Store": "assets/buildings/general_store.png",
    "Town Hall":         "assets/buildings/town_hall.png",
    "the Library":       "assets/buildings/library.png",
}
building_sprites = {}
for _bname, _bpath in _building_sprite_files.items():
    _bsprite = load_sprite(_bpath, BUILDING_SPRITE_SIZE)
    if _bsprite:
        building_sprites[_bname] = _bsprite

# Building top-left tile positions (where to draw the sprite)
BUILDING_SPRITE_POS = {
    "the Blacksmith":    (2, 2),
    "the Tavern":        (10, 2),
    "the Apothecary":    (18, 2),
    "the Church":        (24, 2),
    "the General Store": (2, 9),
    "Town Hall":         (10, 9),
    "the Library":       (18, 9),
}

# Menu background — video clips as pre-extracted frame sequences
def _load_video_frames(folder):
    """Load numbered PNG frames from a folder."""
    import os
    frames = []
    i = 1
    while True:
        path = os.path.join(folder, f"frame_{i:03d}.png")
        if not os.path.exists(path):
            break
        try:
            img = pygame.image.load(path).convert()
            frames.append(img)
        except Exception:
            break
        i += 1
    print(f"Loaded {len(frames)} frames from {folder}")
    return frames

MENU_VIDEO_CLIPS = [
    _load_video_frames("assets/videos/frames_1"),
    _load_video_frames("assets/videos/frames_2"),
    _load_video_frames("assets/videos/frames_3"),
]
MENU_VIDEO_CLIPS = [c for c in MENU_VIDEO_CLIPS if c]  # remove empty
menu_clip_idx = 0      # which video clip is playing
menu_frame_idx = 0     # frame within current clip
menu_frame_timer = 0.0
menu_transition_timer = 0.0  # >0 means fading between clips
MENU_VIDEO_FPS = 15
MENU_TRANSITION_DUR = 1.0  # 1 second fade between clips

player_facing = "south"
player_walking = False
player_anim_timer = 0.0
player_anim_frame = 0

# NPC animated sprites — townsperson skin for all NPCs
NPC_SPRITE_SIZE = (TILE_SIZE + 8, TILE_SIZE + 8)
NPC_WALK_FRAME_COUNT = 6
NPC_WALK_ANIM_SPEED = 8  # frames per second
NPC_MOVE_SPEED = 60  # pixels per second (slower than player)

# Load townsperson idle sprites (8 directions)
npc_idle_sprites = {}
for d in DIRECTIONS:
    npc_idle_sprites[d] = load_sprite(f"assets/characters/townsperson/rotations/{d}.png", NPC_SPRITE_SIZE)

# Load townsperson walk animation frames (8 directions x 6 frames)
npc_walk_frames = {}
for d in DIRECTIONS:
    frames = []
    for i in range(NPC_WALK_FRAME_COUNT):
        frame = load_sprite(f"assets/characters/townsperson/animations/walk/{d}/frame_{i:03d}.png", NPC_SPRITE_SIZE)
        frames.append(frame)
    npc_walk_frames[d] = frames

# Legacy static sprites (kept for fallback)
npc_sprites = [None] * 7

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

# Per-building visual styles for the town map
BUILDING_EXTERIOR_STYLES = {
    "the Blacksmith": {
        "wall": (100, 75, 55),   # warm brown stone
        "roof": (80, 80, 90),    # dark gray slate
        "door": (90, 55, 25),    # dark oak
        "mortar": (75, 60, 40),
        "accent": (200, 100, 30),  # orange forge glow on walls
    },
    "the Tavern": {
        "wall": (110, 85, 60),   # lighter warm wood
        "roof": (140, 70, 35),   # warm amber
        "door": (130, 85, 35),   # golden oak
        "mortar": (85, 65, 42),
        "accent": (180, 150, 60),  # lantern yellow
    },
    "the Apothecary": {
        "wall": (85, 95, 80),    # mossy gray-green
        "roof": (60, 100, 70),   # green tiles
        "door": (70, 90, 60),    # green-stained
        "mortar": (65, 75, 60),
        "accent": (100, 200, 120),  # potion green
    },
    "the Church": {
        "wall": (130, 125, 115), # light stone / limestone
        "roof": (60, 55, 75),    # deep purple-gray
        "door": (80, 50, 40),    # dark mahogany
        "mortar": (105, 100, 90),
        "accent": (200, 180, 100),  # gold cross
    },
    "the General Store": {
        "wall": (105, 80, 55),   # standard brown
        "roof": (150, 60, 40),   # classic red
        "door": (110, 75, 35),   # pine
        "mortar": (80, 60, 38),
        "accent": (180, 160, 100),
    },
    "Town Hall": {
        "wall": (120, 110, 95),  # dignified tan stone
        "roof": (50, 50, 65),    # slate blue-gray
        "door": (100, 65, 35),   # polished wood
        "mortar": (95, 85, 70),
        "accent": (200, 180, 80),  # gold trim
    },
    "the Library": {
        "wall": (95, 75, 65),    # dark warm brick
        "roof": (110, 50, 40),   # deep red-brown
        "door": (85, 55, 35),    # aged wood
        "mortar": (70, 55, 45),
        "accent": (160, 120, 60),  # leather brown
    },
}

# Map each building tile (col, row) to its building name
# Top row buildings: cols 2-5, 10-13, 18-21, 24-27 | rows 2-5
# Bottom row buildings: cols 2-5, 10-13, 18-21 | rows 9-12
BUILDING_TILE_MAP = {}
_building_bounds = [
    ("the Blacksmith",    2, 5, 2, 5),   # (name, col_start, col_end, row_start, row_end)
    ("the Tavern",       10, 13, 2, 5),
    ("the Apothecary",   18, 21, 2, 5),
    ("the Church",       24, 27, 2, 5),
    ("the General Store", 2, 5, 9, 12),
    ("Town Hall",        10, 13, 9, 12),
    ("the Library",      18, 21, 9, 12),
]
for _bname, _c0, _c1, _r0, _r1 in _building_bounds:
    for _r in range(_r0, _r1 + 1):
        for _c in range(_c0, _c1 + 1):
            BUILDING_TILE_MAP[(_c, _r)] = _bname

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
        self.state = "MENU"  # MENU, NIGHT, DAY, ACCUSE, REVEAL, ACCUSE_RESULT, WIN, LOSE
        # Reveal animation state
        self.reveal_timer = 0.0
        self.reveal_duration = 4.35    # total seconds for suspense animation
        self.reveal_target_state = ""  # WIN, LOSE, or ACCUSE_RESULT
        self.reveal_accused = None     # character dict being accused
        self.reveal_correct = False
        self.reveal_done = False
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
        # Crime scene
        self.crime_scene_building = None
        self.crime_scene_seen = False  # has player entered the crime scene this day
        # Tutorial
        self.tutorial_step = 0  # 0=not started, 1=talk hint, 2=journal hint, 3=accuse hint, 4=done
        # Recap
        self.recap_scroll = 0
        # Credits
        self.credits_scroll_y = SCREEN_H  # starts below screen, scrolls up
        self.credits_timer = 0.0

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
        self.storyteller_text = ""
        self.dialogue_target = None
        self.dialogue_text = ""
        self.dialogue_loading = False
        self.accuse_selection = 0
        self.accuse_result_correct = False
        self.talked_to = set()
        self.history = []
        self.night_clues = {}
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
        # Reveal state
        self.reveal_timer = 0.0
        self.reveal_target_state = ""
        self.reveal_accused = None
        self.reveal_correct = False
        self.reveal_done = False
        # Crime scene
        self.crime_scene_building = None
        self.crime_scene_seen = False
        # Tutorial
        self.tutorial_step = 0
        # Recap
        self.recap_scroll = 0
        # Journal
        self.showing_journal = False
        self.journal_page = 0
        # Fade
        self.fade_alpha = 0
        self.fade_direction = 0
        self.fade_callback = None
        self.loading_dot_timer = 0.0

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
            # NPC movement/animation state
            c["facing"] = "south"
            c["npc_walking"] = False
            c["npc_anim_timer"] = 0.0
            c["npc_anim_frame"] = 0
            c["move_target"] = None  # (tx, ty) pixel target or None
            c["move_pause"] = random.uniform(1.0, 4.0)  # seconds to wait before next move
            c["talking"] = False  # True when player is talking to this NPC

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
        NIGHT_SOUND.play()
        self.night_timer = 3.0  # seconds to show night screen
        self.dialogue_target = None
        self.dialogue_text = ""
        self.night_clues = {}
        self.searched_spots = set()
        self.evidence_placements = {}
        self.current_interior = None
        # Reset player to town center so they don't spawn inside a building
        self.player_x = 14.0 * TILE_SIZE
        self.player_y = 7.0 * TILE_SIZE

        if self.night_num == 1:
            self.storyteller_text = "Night falls on the town...\nA villain lurks among the townspeople.\nSpeak to the residents and uncover the truth."
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
                self.crime_scene_building = self.night_clues.get("murder_location")
                self.crime_scene_seen = False

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
        if self.night_num == 1:
            self.tutorial_step = 1
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

        # Shuffle placement order so no NPC consistently gets first/last pick of spots
        placement_order = list(self.alive)
        random.shuffle(placement_order)

        for npc in placement_order:
            npc_idx = self.characters.index(npc)
            home = BUILDING_NAMES[npc_idx] if npc_idx < len(BUILDING_NAMES) else "their home"

            # Randomly place at home, inside a building, or wandering
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
                    while outdoor_idx < len(outdoor_spots):
                        pos, area = outdoor_spots[outdoor_idx]
                        outdoor_idx += 1
                        if not is_occupied("outside", None, pos[0], pos[1]):
                            place_npc(npc, "outside", None, pos[0], pos[1], f"at {area}")
                            break
                    else:
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

        # Place evidence at active spots — force weapon at crime scene building
        evidence_list = self.night_clues.get("physical_evidence", [])
        self.evidence_placements = {}

        # Force weapon evidence into a crime scene building search spot
        crime_bld = self.crime_scene_building
        if crime_bld and crime_bld in INTERIORS:
            crime_spots = [(crime_bld, s["name"]) for s in INTERIORS[crime_bld]["search_spots"]]
            for ev in evidence_list:
                if ev.get("type") == "weapon" and crime_spots:
                    key = crime_spots[0]
                    self.active_spots.add(key)
                    self.evidence_placements[key] = ev
                    evidence_list = [e for e in evidence_list if e is not ev]
                    break

        # Place remaining evidence at random active spots
        active_list = [s for s in self.active_spots if s not in self.evidence_placements]
        random.shuffle(active_list)
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
        # Start reveal animation — actual result resolves when timer ends
        self.reveal_accused = character
        self.reveal_correct = character["is_villain"]
        self.reveal_timer = 0.0
        self.reveal_done = False
        self.state = "REVEAL"
        music_stop(fade_ms=1500)
        REVEAL_SOUND.play()

    def _finish_reveal(self):
        """Called when the reveal animation timer expires. Resolves the accusation but stays on REVEAL screen."""
        character = self.reveal_accused
        self.reveal_done = True
        if self.reveal_correct:
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
            self.history.append({
                "type": "accusation", "day": self.night_num,
                "accused": character["name"], "correct": False,
                "description": (
                    f"On day {self.night_num}, the detective accused {character['name']}, "
                    f"but they were innocent. The town was shocked and the real killer is still at large."
                ),
            })
            for npc in self.alive:
                name = npc["name"]
                if name in self.npc_memory:
                    self.npc_memory[name].append(f"Day {self.night_num}: Detective wrongly accused {character['name']}.")
            villain_npc = next((c for c in self.alive if c["is_villain"]), None)
            if villain_npc and villain_npc["name"] in self.npc_emotional_state:
                self.npc_emotional_state[villain_npc["name"]]["desperation"] += 1

    def _advance_from_reveal(self):
        """Called when player presses ENTER on the reveal screen."""
        if self.reveal_correct or self.wrong_guesses >= 3:
            self.state = "RECAP"
            self.recap_scroll = 0
        else:
            self.start_night()

    def _update_npcs(self, dt):
        """Update NPC autonomous movement — they wander around the town."""
        for npc in self.alive:
            # Don't move if talking to player — face the detective
            if npc.get("talking") or self.dialogue_target is npc:
                npc["npc_walking"] = False
                dx_p = self.player_x - npc["x"]
                dy_p = self.player_y - npc["y"]
                if abs(dx_p) > abs(dy_p):
                    if dx_p > 0:
                        npc["facing"] = "east" if abs(dy_p) < abs(dx_p) * 0.5 else ("south-east" if dy_p > 0 else "north-east")
                    else:
                        npc["facing"] = "west" if abs(dy_p) < abs(dx_p) * 0.5 else ("south-west" if dy_p > 0 else "north-west")
                else:
                    if dy_p > 0:
                        npc["facing"] = "south" if abs(dx_p) < abs(dy_p) * 0.5 else ("south-east" if dx_p > 0 else "south-west")
                    else:
                        npc["facing"] = "north" if abs(dx_p) < abs(dy_p) * 0.5 else ("north-east" if dx_p > 0 else "north-west")
                continue
            # Don't move NPCs in interiors (they stay put)
            if npc.get("location_type") == "interior":
                npc["npc_walking"] = False
                continue

            # If no target, count down pause then pick a new destination
            if npc.get("move_target") is None:
                npc["npc_walking"] = False
                npc["move_pause"] = npc.get("move_pause", 2.0) - dt
                if npc["move_pause"] <= 0:
                    # Pick a random nearby walkable tile as target
                    cx = int(npc["x"] // TILE_SIZE)
                    cy = int(npc["y"] // TILE_SIZE)
                    attempts = 0
                    while attempts < 10:
                        tx = cx + random.randint(-3, 3)
                        ty = cy + random.randint(-3, 3)
                        if 0 <= tx < MAP_W and 0 <= ty < MAP_H and tilemap[ty][tx] not in SOLID_TILES:
                            npc["move_target"] = (tx * TILE_SIZE, ty * TILE_SIZE)
                            break
                        attempts += 1
                    npc["move_pause"] = random.uniform(2.0, 6.0)
            else:
                # Move toward target
                tx, ty = npc["move_target"]
                dx_npc = tx - npc["x"]
                dy_npc = ty - npc["y"]
                dist = max(1, (dx_npc ** 2 + dy_npc ** 2) ** 0.5)

                if dist < 4:
                    # Arrived
                    npc["x"] = tx
                    npc["y"] = ty
                    npc["move_target"] = None
                    npc["npc_walking"] = False
                    npc["move_pause"] = random.uniform(2.0, 6.0)
                else:
                    # Move
                    move_x = (dx_npc / dist) * NPC_MOVE_SPEED * dt
                    move_y = (dy_npc / dist) * NPC_MOVE_SPEED * dt
                    new_x = npc["x"] + move_x
                    new_y = npc["y"] + move_y

                    # Collision check
                    pw, ph = TILE_SIZE - 4, TILE_SIZE - 4
                    blocked = False
                    left = int(new_x) // TILE_SIZE
                    right = int(new_x + pw - 1) // TILE_SIZE
                    top = int(new_y) // TILE_SIZE
                    bottom = int(new_y + ph - 1) // TILE_SIZE
                    for r in range(top, bottom + 1):
                        for c_col in range(left, right + 1):
                            if r < 0 or r >= MAP_H or c_col < 0 or c_col >= MAP_W:
                                blocked = True
                            elif tilemap[r][c_col] in SOLID_TILES:
                                blocked = True

                    if blocked:
                        npc["move_target"] = None
                        npc["npc_walking"] = False
                    else:
                        npc["x"] = new_x
                        npc["y"] = new_y
                        npc["npc_walking"] = True

                        # Update facing direction
                        if abs(dx_npc) > abs(dy_npc):
                            if dx_npc > 0:
                                npc["facing"] = "east" if abs(dy_npc) < abs(dx_npc) * 0.5 else ("south-east" if dy_npc > 0 else "north-east")
                            else:
                                npc["facing"] = "west" if abs(dy_npc) < abs(dx_npc) * 0.5 else ("south-west" if dy_npc > 0 else "north-west")
                        else:
                            if dy_npc > 0:
                                npc["facing"] = "south" if abs(dx_npc) < abs(dy_npc) * 0.5 else ("south-east" if dx_npc > 0 else "south-west")
                            else:
                                npc["facing"] = "north" if abs(dx_npc) < abs(dy_npc) * 0.5 else ("north-east" if dx_npc > 0 else "north-west")

                # Update walk animation
                if npc.get("npc_walking"):
                    npc["npc_anim_timer"] = npc.get("npc_anim_timer", 0) + dt
                    frame_dur = 1.0 / NPC_WALK_ANIM_SPEED
                    if npc["npc_anim_timer"] >= frame_dur:
                        npc["npc_anim_timer"] -= frame_dur
                        npc["npc_anim_frame"] = (npc.get("npc_anim_frame", 0) + 1) % NPC_WALK_FRAME_COUNT
                else:
                    npc["npc_anim_timer"] = 0
                    npc["npc_anim_frame"] = 0

    def talk_to_npc(self, npc):
        if self.dialogue_loading:
            return
        sfx_speech.play()
        self.dialogue_target = npc
        self.talked_to.add(npc["name"])
        npc["talking"] = True
        npc["npc_walking"] = False
        npc["move_target"] = None

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
            if self.tutorial_step == 1:
                self.tutorial_step = 2
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

def draw_town_tile(surface, tile, rect, row, col):
    """Draw a detailed town map tile with per-building unique styles."""
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    seed = row * 31 + col * 17

    # Look up building ownership for this tile
    bld = BUILDING_TILE_MAP.get((col, row))
    bstyle = BUILDING_EXTERIOR_STYLES.get(bld) if bld else None

    if tile == 0 or tile == 6:  # Grass
        base = (72, 148, 0) if (row + col) % 2 == 0 else (80, 158, 5)
        pygame.draw.rect(surface, base, rect)
        tuft_col = (55, 120, 0)
        for i in range(3):
            tx = x + ((seed + i * 13) % (w - 6)) + 3
            ty = y + ((seed + i * 7 + 5) % (h - 6)) + 3
            pygame.draw.line(surface, tuft_col, (tx, ty + 4), (tx, ty), 1)
            pygame.draw.line(surface, tuft_col, (tx + 2, ty + 4), (tx + 3, ty + 1), 1)
        if tile == 6:
            cs = pygame.Surface((12, 12), pygame.SRCALPHA)
            cs.fill((255, 255, 200, 25))
            surface.blit(cs, (x + w // 2 - 6, y + h // 2 - 6))

    elif tile == 1:  # Wall — unique per building
        base = bstyle["wall"] if bstyle else WALL_COLOR
        mortar = bstyle["mortar"] if bstyle else (70, 55, 38)
        accent = bstyle["accent"] if bstyle else None
        pygame.draw.rect(surface, base, rect)
        # Stone block mortar pattern
        for ly in range(0, h, 12):
            pygame.draw.line(surface, mortar, (x, y + ly), (x + w, y + ly), 1)
        v_offset = 0 if (row % 2 == 0) else w // 4
        for lx in range(v_offset, w, w // 2):
            for ry in range(0, h, 12):
                pygame.draw.line(surface, mortar, (x + lx, y + ry), (x + lx, y + ry + 12), 1)
        # Block color variation
        for by in range(0, h, 12):
            for bx in range(0, w, w // 2):
                boff = ((row + by // 12) * 7 + (col + bx // (w // 2)) * 3) % 5
                if boff > 2:
                    hl = pygame.Surface((w // 2 - 1, 11), pygame.SRCALPHA)
                    hl.fill((255, 255, 255, 10))
                    surface.blit(hl, (x + bx + 1, y + by + 1))
        # Accent detail (e.g., forge glow for blacksmith)
        if accent and bld:
            # Small accent mark on certain wall tiles
            if (row + col) % 5 == 0:
                ag = pygame.Surface((w, h), pygame.SRCALPHA)
                ag.fill((accent[0], accent[1], accent[2], 20))
                surface.blit(ag, (x, y))
        # Shadow at bottom
        shadow = (max(base[0] - 30, 0), max(base[1] - 25, 0), max(base[2] - 20, 0))
        pygame.draw.line(surface, shadow, (x, y + h - 1), (x + w, y + h - 1), 2)

    elif tile == 2:  # Path — cobblestone
        base = (170, 150, 110)
        pygame.draw.rect(surface, base, rect)
        mortar = (140, 125, 90)
        stone_w, stone_h = 10, 10
        offset_x = (row % 2) * (stone_w // 2)
        for sy in range(0, h, stone_h + 2):
            for sx in range(0, w, stone_w + 2):
                actual_x = sx + offset_x
                if actual_x >= w:
                    actual_x -= w
                sv = ((row * 3 + sy // stone_h) * 7 + (col * 5 + sx // stone_w) * 11) % 3
                shade = [(175, 155, 115), (165, 145, 105), (180, 162, 122)][sv]
                sr = pygame.Rect(x + actual_x, y + sy, stone_w, stone_h)
                pygame.draw.rect(surface, shade, sr, border_radius=2)
        for sy in range(0, h, stone_h + 2):
            pygame.draw.line(surface, mortar, (x, y + sy + stone_h), (x + w, y + sy + stone_h), 1)
        for sx in range(0, w, stone_w + 2):
            pygame.draw.line(surface, mortar, (x + sx + offset_x, y), (x + sx + offset_x, y + h), 1)

    elif tile == 3:  # Roof — unique per building
        base = bstyle["roof"] if bstyle else ROOF_COLOR
        pygame.draw.rect(surface, base, rect)
        shingle_h = 8
        line_col = (max(base[0] - 20, 0), max(base[1] - 15, 0), max(base[2] - 12, 0))
        for sy in range(0, h, shingle_h):
            row_off = (shingle_h // 2) if ((row * 4 + sy // shingle_h) % 2 == 1) else 0
            pygame.draw.line(surface, line_col, (x, y + sy), (x + w, y + sy), 1)
            for sx in range(row_off, w, 16):
                pygame.draw.line(surface, line_col, (x + sx, y + sy), (x + sx, y + sy + shingle_h), 1)
        # Ridge highlight at top
        ridge = (min(base[0] + 20, 255), min(base[1] + 15, 255), min(base[2] + 15, 255))
        pygame.draw.line(surface, ridge, (x, y + 1), (x + w, y + 1), 1)
        # Overhang shadow at bottom
        overhang = (max(base[0] - 40, 0), max(base[1] - 30, 0), max(base[2] - 25, 0))
        pygame.draw.rect(surface, overhang, (x, y + h - 3, w, 3))

    elif tile == 4:  # Door — unique per building
        door_col = bstyle["door"] if bstyle else DOOR_COLOR
        frame_col = (max(door_col[0] - 30, 0), max(door_col[1] - 25, 0), max(door_col[2] - 15, 0))
        # Frame
        pygame.draw.rect(surface, frame_col, rect)
        # Inner panel
        di = rect.inflate(-10, -6)
        di.y += 3
        pygame.draw.rect(surface, door_col, di)
        # Panel lines
        ph = di.height // 2 - 3
        panel_line = (min(door_col[0] + 20, 255), min(door_col[1] + 15, 255), min(door_col[2] + 10, 255))
        pygame.draw.rect(surface, panel_line, (di.x + 4, di.y + 3, di.width - 8, ph), 1)
        pygame.draw.rect(surface, panel_line, (di.x + 4, di.y + ph + 6, di.width - 8, ph), 1)
        # Handle
        handle_col = bstyle["accent"] if bstyle else (200, 180, 100)
        pygame.draw.circle(surface, handle_col, (di.x + di.width - 8, di.centery), 3)

    elif tile == 5:  # Tree
        grass_base = (65, 130, 0) if (row + col) % 2 == 0 else (70, 140, 5)
        pygame.draw.rect(surface, grass_base, rect)
        # Trunk
        tw, th = 8, 14
        pygame.draw.rect(surface, (90, 60, 30), (x + w // 2 - tw // 2, y + h - th - 2, tw, th))
        # Canopy
        cr = w // 2 - 4
        cx, cy = x + w // 2, y + h // 2 - 4
        cs = (seed % 3) * 8
        cc = (25 + cs, 85 + cs, 15)
        pygame.draw.circle(surface, cc, (cx, cy), cr)
        # Canopy highlight
        pygame.draw.circle(surface, (cc[0] + 15, cc[1] + 15, cc[2] + 10), (cx - 3, cy - 3), cr // 2)

    else:
        pygame.draw.rect(surface, TILE_COLORS.get(tile, BG_COLOR), rect)


def get_npc_sprite(npc):
    """Get the current sprite for an NPC based on their movement state."""
    facing = npc.get("facing", "south")
    if npc.get("npc_walking"):
        frames = npc_walk_frames.get(facing)
        if frames:
            idx = npc.get("npc_anim_frame", 0) % len(frames)
            return frames[idx]
    return npc_idle_sprites.get(facing)

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
            if event.key == pygame.K_F11:
                is_fullscreen = not is_fullscreen
                if is_fullscreen:
                    display = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                else:
                    display = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE)
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
                        if game.dialogue_target:
                            game.dialogue_target["talking"] = False
                        game.dialogue_target = None
                        game.dialogue_text = ""
                        game.dialogue_loading = False
                    elif game.current_interior and not game.fading:
                        sfx_door.play()
                        _esc_interior = INTERIORS[game.current_interior]
                        _esc_wx, _esc_wy = _esc_interior["exit_world_pos"]
                        def _do_esc_exit(wx=_esc_wx, wy=_esc_wy):
                            game.player_x = wx * TILE_SIZE
                            game.player_y = wy * TILE_SIZE
                            game.current_interior = None
                        game.start_fade(_do_esc_exit)
                    else:
                        running = False
                else:
                    running = False

            # Menu
            if game.state == "MENU" and event.key == pygame.K_RETURN and not game.fading:
                game.start_fade(lambda: game.new_game())
            if game.state == "MENU" and event.key == pygame.K_c and not game.fading:
                def _start_credits():
                    game.state = "CREDITS"
                    game.credits_scroll_y = SCREEN_H
                    game.credits_timer = 0.0
                    music_stop(fade_ms=500)
                    pygame.mixer.music.load(CREDITS_MUSIC)
                    pygame.mixer.music.set_volume(0.7)
                    pygame.mixer.music.play()
                game.start_fade(_start_credits)

            # Night — skip with any key after timer
            if game.state == "NIGHT" and game.night_timer <= 0 and not game.fading:
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    game.start_fade(lambda: game.start_day())

            # Day
            if game.state == "DAY":
                # Tutorial step 3: dismiss on any key
                if game.tutorial_step == 3 and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
                    game.tutorial_step = 4

                if event.key == pygame.K_e:
                    # Dismiss search result
                    if game.search_result_timer > 0:
                        game.search_result_timer = 0
                        game.search_result_text = ""
                    # Close dialogue
                    elif game.dialogue_target:
                        game.dialogue_target["talking"] = False
                        game.dialogue_target = None
                        game.dialogue_text = ""
                        game.dialogue_loading = False
                    # Close evidence log
                    elif game.showing_evidence_log:
                        game.showing_evidence_log = False
                    # Try exit interior
                    elif game.current_interior and game.is_on_exit() and not game.fading:
                        sfx_door.play()
                        # Capture exit data now so walking off the tile doesn't cancel it
                        _exit_interior = INTERIORS[game.current_interior]
                        _exit_wx, _exit_wy = _exit_interior["exit_world_pos"]
                        def _do_exit(wx=_exit_wx, wy=_exit_wy):
                            game.player_x = wx * TILE_SIZE
                            game.player_y = wy * TILE_SIZE
                            game.current_interior = None
                        game.start_fade(_do_exit)
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
                    sfx_pop.play()
                    game.showing_evidence_log = not game.showing_evidence_log
                    game.showing_clue_tracker = False
                    game.showing_journal = False
                    game.evidence_log_scroll = 0

                if event.key == pygame.K_j:
                    sfx_pop.play()
                    game.showing_clue_tracker = not game.showing_clue_tracker
                    game.showing_evidence_log = False
                    game.showing_journal = False
                    game.clue_tracker_scroll = 0

                if event.key == pygame.K_b:
                    sfx_pop.play()
                    game.showing_journal = not game.showing_journal
                    game.showing_evidence_log = False
                    game.showing_clue_tracker = False
                    game.journal_page = 0
                    if game.tutorial_step == 2:
                        game.tutorial_step = 3

                if event.key == pygame.K_TAB and not game.showing_evidence_log and not game.showing_clue_tracker and not game.showing_journal:
                    sfx_pop.play()
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

            # Reveal screen — press ENTER after verdict shown
            elif game.state == "REVEAL" and game.reveal_done:
                if (event.key == pygame.K_RETURN or event.key == pygame.K_SPACE) and not game.fading:
                    game.start_fade(lambda: game._advance_from_reveal())

            # Accuse result — wrong guess, continue to next night
            elif game.state == "ACCUSE_RESULT":
                if (event.key == pygame.K_RETURN or event.key == pygame.K_SPACE) and not game.fading:
                    game.start_fade(lambda: game.start_night())

            # Recap
            elif game.state == "RECAP":
                if event.key == pygame.K_RETURN and not game.fading:
                    def _to_credits():
                        game.state = "CREDITS"
                        game.credits_scroll_y = SCREEN_H
                        game.credits_timer = 0.0
                        music_stop(fade_ms=500)
                        pygame.mixer.music.load(CREDITS_MUSIC)
                        pygame.mixer.music.set_volume(0.7)
                        pygame.mixer.music.play()
                    game.start_fade(_to_credits)
                if event.key == pygame.K_UP:
                    game.recap_scroll = max(0, game.recap_scroll - 1)
                if event.key == pygame.K_DOWN:
                    game.recap_scroll += 1

            # Credits
            elif game.state == "CREDITS":
                if event.key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_SPACE) and not game.fading:
                    def _credits_to_menu():
                        global menu_clip_idx, menu_frame_idx, menu_frame_timer, menu_transition_timer
                        game.state = "MENU"
                        menu_clip_idx = 0
                        menu_frame_idx = 0
                        menu_frame_timer = 0.0
                        menu_transition_timer = 0.0
                        music_start_menu()
                    game.start_fade(_credits_to_menu)

            # Win/Lose
            elif game.state in ("WIN", "LOSE"):
                if event.key == pygame.K_RETURN and not game.fading:
                    def _to_menu():
                        global menu_clip_idx, menu_frame_idx, menu_frame_timer, menu_transition_timer
                        game.state = "MENU"
                        menu_clip_idx = 0
                        menu_frame_idx = 0
                        menu_frame_timer = 0.0
                        menu_transition_timer = 0.0
                        music_start_menu()
                    game.start_fade(_to_menu)

    # ── Update ──────────────────────────────────────────────────
    # Credits auto-scroll + 30s fade-out to menu
    if game.state == "CREDITS":
        game.credits_scroll_y -= 40 * dt
        game.credits_timer += dt
        # Fade music out during last 5 seconds
        if game.credits_timer > 25.0:
            vol = max(0.0, 0.7 * (1.0 - (game.credits_timer - 25.0) / 5.0))
            pygame.mixer.music.set_volume(vol)
        # Return to menu at 30s
        if game.credits_timer >= 30.0 and not game.fading:
            def _credits_done():
                global menu_clip_idx, menu_frame_idx, menu_frame_timer, menu_transition_timer
                game.state = "MENU"
                menu_clip_idx = 0
                menu_frame_idx = 0
                menu_frame_timer = 0.0
                menu_transition_timer = 0.0
                music_start_menu()
            game.start_fade(_credits_done)

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

    if game.state == "REVEAL":
        prev = game.reveal_timer
        game.reveal_timer += dt
        # Play drum hit at the moment the verdict appears (50% mark)
        half = game.reveal_duration * 0.5
        if prev < half <= game.reveal_timer:
            sfx_reverb_drum.play()
        if game.reveal_timer >= game.reveal_duration and not game.reveal_done:
            game._finish_reveal()

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
                        # Interior: wood floors
                        play_footstep("wood")
                    else:
                        tile = tilemap[pty][ptx] if 0 <= pty < MAP_H and 0 <= ptx < MAP_W else 0
                        if tile == 2:
                            play_footstep("stone")   # cobblestone paths
                        elif tile == 4:
                            play_footstep("wood")    # door threshold
                        else:
                            play_footstep("grass")   # grass, forest, etc.
        else:
            player_walking = False
            player_anim_timer = 0.0
            player_anim_frame = 0

        # Update search result timer
        if game.search_result_timer > 0:
            game.search_result_timer -= dt
            if game.search_result_timer <= 0:
                game.search_result_text = ""

        # Update NPC movement
        game._update_npcs(dt)

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
        t = pygame.time.get_ticks() / 1000.0

        # Video background — loops clips with crossfade
        if MENU_VIDEO_CLIPS:
            clip = MENU_VIDEO_CLIPS[menu_clip_idx % len(MENU_VIDEO_CLIPS)]
            fade_frames = int(MENU_VIDEO_FPS * 0.5)  # frames for fade (0.5s)

            # Advance frame
            menu_frame_timer += dt
            if menu_frame_timer >= 1.0 / MENU_VIDEO_FPS:
                menu_frame_timer -= 1.0 / MENU_VIDEO_FPS
                menu_frame_idx += 1

            if menu_frame_idx >= len(clip):
                menu_clip_idx = (menu_clip_idx + 1) % len(MENU_VIDEO_CLIPS)
                menu_frame_idx = 0
                menu_frame_timer = 0.0
                clip = MENU_VIDEO_CLIPS[menu_clip_idx]

            # Draw current frame
            frame_idx = min(menu_frame_idx, len(clip) - 1)
            screen.blit(clip[frame_idx], (0, 0))

            # Fade in at start of clip
            if menu_frame_idx < fade_frames:
                alpha = int(255 * (1.0 - menu_frame_idx / fade_frames))
                fade_s = pygame.Surface((SCREEN_W, SCREEN_H))
                fade_s.fill((0, 0, 0))
                fade_s.set_alpha(alpha)
                screen.blit(fade_s, (0, 0))

            # Fade out at end of clip
            frames_left = len(clip) - menu_frame_idx
            if frames_left <= fade_frames:
                alpha = int(255 * (1.0 - frames_left / fade_frames))
                fade_s = pygame.Surface((SCREEN_W, SCREEN_H))
                fade_s.fill((0, 0, 0))
                fade_s.set_alpha(alpha)
                screen.blit(fade_s, (0, 0))

            # Dark overlay for text readability
            _menu_ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            _menu_ov.fill((0, 0, 0, 120))
            screen.blit(_menu_ov, (0, 0))
        else:
            # Fallback dark gradient if no videos found
            for y_line in range(SCREEN_H):
                frac = y_line / SCREEN_H
                pygame.draw.line(screen, (int(8 + 15 * frac), int(5 + 8 * frac), int(18 + 12 * (1 - frac))),
                    (0, y_line), (SCREEN_W, y_line))

        # Blood drips from top of screen
        drip_positions = [
            (85, 0.6, 55, 3), (150, 0.9, 40, 2), (230, 0.5, 70, 3),
            (310, 1.1, 35, 2), (390, 0.7, 60, 3), (470, 0.4, 80, 2),
            (540, 0.8, 45, 3), (620, 1.0, 50, 2), (700, 0.6, 65, 3),
            (780, 0.7, 38, 2), (840, 0.5, 55, 3),
        ]
        for dx, spd, length_base, w in drip_positions:
            cycle = (t * spd + dx * 0.01) % 4.0
            if cycle < 3.0:
                drip_len = int(length_base * min(1.0, cycle / 1.5))
                for dy in range(drip_len):
                    alpha_frac = 1.0 - (dy / max(drip_len, 1)) * 0.6
                    col = (int(150 * alpha_frac), int(15 * alpha_frac), int(15 * alpha_frac))
                    pygame.draw.rect(screen, col, (dx, dy, w, 1))
                if drip_len > 10:
                    pygame.draw.circle(screen, (140, 18, 18), (dx + w // 2, drip_len), w)

        # Title with drop shadow — large serif font
        title_y = 120
        title_cx = SCREEN_W // 2
        # Deep shadow
        s1 = font_menu_title.render("QUANTUM BLOOD", True, (0, 0, 0))
        screen.blit(s1, (title_cx - s1.get_width() // 2 + 4, title_y + 5))
        # Mid shadow
        s2 = font_menu_title.render("QUANTUM BLOOD", True, (30, 3, 3))
        screen.blit(s2, (title_cx - s2.get_width() // 2 + 2, title_y + 3))
        # Main title
        pulse = 0.85 + 0.15 * math.sin(t * 2)
        title_col = (int(220 * pulse), int(25 * pulse), int(25 * pulse))
        title_surf = font_menu_title.render("QUANTUM BLOOD", True, title_col)
        screen.blit(title_surf, (title_cx - title_surf.get_width() // 2, title_y))

        # Subtitle — brighter for contrast
        draw_centered_text(screen, "A villain hides among the townspeople.", font_md, (220, 215, 200), 250)
        draw_centered_text(screen, "Find them before it's too late.", font_md, (200, 195, 180), 285)

        # Pulsing "Press ENTER" — brighter
        enter_alpha = 180 + int(75 * math.sin(t * 3))
        enter_surf = font_md.render("Press ENTER to begin", True, (enter_alpha, enter_alpha, enter_alpha))
        screen.blit(enter_surf, (SCREEN_W // 2 - enter_surf.get_width() // 2, 380))

        # Controls — brighter
        draw_centered_text(screen, "[WASD] Move   [E] Interact   [B] Journal   [TAB] Accuse", font_sm, (170, 165, 155), 520)
        draw_centered_text(screen, "[L] Evidence Log   [J] Clue Tracker   [C] Credits   [F11] Fullscreen", font_sm, (170, 165, 155), 545)

    elif game.state == "NIGHT":
        t = pygame.time.get_ticks() / 1000.0

        # Dark sky gradient
        for y_line in range(SCREEN_H):
            frac = y_line / SCREEN_H
            r = int(5 + 8 * frac)
            g = int(5 + 6 * frac)
            b = int(25 + 20 * (1 - frac))
            pygame.draw.line(screen, (r, g, b), (0, y_line), (SCREEN_W, y_line))

        # Stars
        for i in range(60):
            sx = (i * 97 + 31) % SCREEN_W
            sy = (i * 53 + 17) % (SCREEN_H - 100) + 10
            twinkle = 80 + int(100 * max(0, math.sin(t * 1.2 + i * 0.9)))
            size = 1 if i % 3 != 0 else 2
            pygame.draw.circle(screen, (twinkle, twinkle, twinkle + 30), (sx, sy), size)

        # Moon with glow
        moon_x, moon_y = 150, 80
        # Outer glow
        for gr in range(50, 15, -5):
            glow_s = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_s, (180, 180, 200, 6), (gr, gr), gr)
            screen.blit(glow_s, (moon_x - gr, moon_y - gr))
        # Moon body
        pygame.draw.circle(screen, (220, 218, 200), (moon_x, moon_y), 25)
        pygame.draw.circle(screen, (200, 198, 180), (moon_x - 6, moon_y - 4), 22)
        # Craters
        pygame.draw.circle(screen, (195, 192, 175), (moon_x + 8, moon_y - 5), 4)
        pygame.draw.circle(screen, (195, 192, 175), (moon_x - 3, moon_y + 8), 3)

        # Subtle clouds drifting
        for i in range(5):
            cx = (int(t * 8 + i * 200) % (SCREEN_W + 200)) - 100
            cy = 50 + i * 120 + int(math.sin(t * 0.3 + i) * 10)
            cloud = pygame.Surface((120 + i * 20, 20), pygame.SRCALPHA)
            cloud.fill((40, 40, 60, 12 + i * 3))
            screen.blit(cloud, (cx, cy))

        # Storyteller text
        cur_y = 220
        for line in game.storyteller_text.split("\n"):
            cur_y = draw_centered_text_wrapped(screen, line, font_lg, (220, 220, 255), cur_y)
            cur_y += 10
        if game.night_timer <= 0:
            enter_a = 150 + int(80 * math.sin(t * 3))
            enter_surf = font_md.render("Press ENTER to continue", True, (enter_a, enter_a, min(255, int(enter_a * 1.2))))
            screen.blit(enter_surf, (SCREEN_W // 2 - enter_surf.get_width() // 2, 520))

    elif game.state in ("DAY", "ACCUSE"):
        pw, ph = TILE_SIZE - 4, TILE_SIZE - 4
        cam_x = int(game.player_x + pw / 2 - SCREEN_W / 2)
        cam_y = int(game.player_y + ph / 2 - SCREEN_H / 2)

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

            # Crime scene details inside building
            if game.current_interior == game.crime_scene_building:
                for ci, (cr, cc) in enumerate([(2, 2), (3, 3), (4, 2)]):
                    if cr < ih and cc < iw and imap[cr][cc] == 7:
                        fx = cc * TILE_SIZE - cam_x
                        fy = cr * TILE_SIZE - cam_y
                        # Blood splatters
                        splat = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                        for si in range(3 + ci):
                            sx2 = 8 + ((ci * 17 + si * 11) % (TILE_SIZE - 16))
                            sy2 = 8 + ((ci * 13 + si * 7) % (TILE_SIZE - 16))
                            pygame.draw.circle(splat, (160, 20, 20, 120), (sx2, sy2), 3 + si % 3)
                        screen.blit(splat, (fx, fy))
                # Body outline on tile (2, 3)
                if 3 < ih and 2 < iw and imap[3][2] == 7:
                    ox2 = 2 * TILE_SIZE - cam_x
                    oy2 = 3 * TILE_SIZE - cam_y
                    # Simple chalk outline
                    outline_col = (220, 220, 200, 150)
                    os2 = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                    # Head
                    pygame.draw.circle(os2, outline_col, (24, 10), 6, 1)
                    # Body
                    pygame.draw.line(os2, outline_col, (24, 16), (24, 32), 1)
                    # Arms
                    pygame.draw.line(os2, outline_col, (24, 22), (14, 28), 1)
                    pygame.draw.line(os2, outline_col, (24, 22), (34, 28), 1)
                    # Legs
                    pygame.draw.line(os2, outline_col, (24, 32), (16, 44), 1)
                    pygame.draw.line(os2, outline_col, (24, 32), (32, 44), 1)
                    screen.blit(os2, (ox2, oy2))
                # Crime scene description popup (first visit)
                if not game.crime_scene_seen:
                    game.crime_scene_seen = True
                    scene_desc = game.night_clues.get("scene_evidence", "")
                    if scene_desc:
                        game.show_search_result(f"CRIME SCENE: {scene_desc}")

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
                    sprite = get_npc_sprite(npc)
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
            # ── Draw town map with detailed tiles ──
            for row in range(MAP_H):
                for col in range(MAP_W):
                    tile = tilemap[row][col]
                    # Skip building tiles that will be covered by sprites
                    if (col, row) in BUILDING_TILE_MAP and tile in (1, 3, 4):
                        # Draw grass underneath so there's no black gap
                        rect = pygame.Rect(col * TILE_SIZE - cam_x, row * TILE_SIZE - cam_y, TILE_SIZE, TILE_SIZE)
                        draw_town_tile(screen, 0, rect, row, col)
                        continue
                    rect = pygame.Rect(
                        col * TILE_SIZE - cam_x,
                        row * TILE_SIZE - cam_y,
                        TILE_SIZE, TILE_SIZE,
                    )
                    draw_town_tile(screen, tile, rect, row, col)

            # Draw building sprites on top
            for bname, (bx, by) in BUILDING_SPRITE_POS.items():
                if bname in building_sprites:
                    sx = bx * TILE_SIZE - cam_x
                    sy = by * TILE_SIZE - cam_y
                    screen.blit(building_sprites[bname], (sx, sy))
                    # Crime scene red tint
                    if bname == game.crime_scene_building:
                        tint = pygame.Surface(BUILDING_SPRITE_SIZE, pygame.SRCALPHA)
                        tint.fill((200, 20, 20, 40))
                        screen.blit(tint, (sx, sy))
                        # "!" marker near door
                        mark = font_md.render("!", True, (255, 60, 60))
                        screen.blit(mark, (sx + BUILDING_SPRITE_SIZE[0] // 2 - mark.get_width() // 2,
                                           sy + BUILDING_SPRITE_SIZE[1] + 2))

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
                sprite = get_npc_sprite(npc)
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

        # Mini-map (town map only, no overlays)
        if not game.current_interior and not game.dialogue_target and not game.showing_journal and not game.showing_evidence_log and not game.showing_clue_tracker and game.tutorial_step >= 4:
            mm_w, mm_h = 150, 90
            mm_x, mm_y = SCREEN_W - mm_w - 10, SCREEN_H - mm_h - 190
            mm_sx = mm_w / (MAP_W * TILE_SIZE)
            mm_sy = mm_h / (MAP_H * TILE_SIZE)
            # Background
            mm_bg = pygame.Surface((mm_w, mm_h), pygame.SRCALPHA)
            mm_bg.fill((0, 0, 0, 140))
            screen.blit(mm_bg, (mm_x, mm_y))
            # Buildings
            for bname, (bx, by) in BUILDING_SPRITE_POS.items():
                bstyle = BUILDING_EXTERIOR_STYLES.get(bname)
                bc = bstyle["wall"] if bstyle else (100, 80, 60)
                br = pygame.Rect(mm_x + bx * TILE_SIZE * mm_sx, mm_y + by * TILE_SIZE * mm_sy,
                                 4 * TILE_SIZE * mm_sx, 4 * TILE_SIZE * mm_sy)
                pygame.draw.rect(screen, bc, br)
                # Crime scene marker
                if bname == game.crime_scene_building:
                    pygame.draw.rect(screen, (255, 50, 50), br, 1)
            # Paths (simplified — draw the two horizontal road rows)
            for pr in [7, 15]:
                py2 = mm_y + pr * TILE_SIZE * mm_sy
                pygame.draw.line(screen, (150, 135, 100), (mm_x, int(py2)), (mm_x + mm_w, int(py2)), 1)
            # Forest
            pygame.draw.rect(screen, (30, 80, 20),
                (mm_x + 24 * TILE_SIZE * mm_sx, mm_y + 9 * TILE_SIZE * mm_sy,
                 5 * TILE_SIZE * mm_sx, 6 * TILE_SIZE * mm_sy))
            # NPC dots
            for npc in game.alive:
                if npc.get("location_type") == "interior":
                    continue
                nx = mm_x + npc["x"] * mm_sx
                ny = mm_y + npc["y"] * mm_sy
                pygame.draw.circle(screen, npc["color"], (int(nx), int(ny)), 2)
            # Player dot (pulsing white)
            pp = 0.6 + 0.4 * math.sin(pygame.time.get_ticks() * 0.005)
            px2 = mm_x + game.player_x * mm_sx
            py2 = mm_y + game.player_y * mm_sy
            pygame.draw.circle(screen, (int(255 * pp), int(255 * pp), int(255 * pp)), (int(px2), int(py2)), 3)
            # Border
            pygame.draw.rect(screen, (100, 100, 100), (mm_x, mm_y, mm_w, mm_h), 1)

        # Tutorial messages (Day 1 only)
        if game.tutorial_step in (1, 2, 3):
            tut_msgs = {
                1: "Press [E] near a townsperson to speak with them.",
                2: "Press [B] to open your Journal and learn about the residents.",
                3: "Press [TAB] when ready to accuse. Good luck, detective!",
            }
            tut_text = tut_msgs.get(game.tutorial_step, "")
            if tut_text:
                tw = SCREEN_W - 100
                tut_surf = font_md.render(tut_text, True, (255, 255, 220))
                tbg_w = min(tut_surf.get_width() + 30, tw)
                tbg_h = 40
                tbg_x = SCREEN_W // 2 - tbg_w // 2
                tbg_y = hud_h + 8
                tbg = pygame.Surface((tbg_w, tbg_h), pygame.SRCALPHA)
                tbg.fill((20, 15, 40, 200))
                screen.blit(tbg, (tbg_x, tbg_y))
                pygame.draw.rect(screen, (100, 80, 180), (tbg_x, tbg_y, tbg_w, tbg_h), 1, border_radius=4)
                screen.blit(tut_surf, (SCREEN_W // 2 - tut_surf.get_width() // 2, tbg_y + 8))

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
            portrait_sprite = npc_idle_sprites.get("south")
            if portrait_sprite:
                portrait = pygame.transform.smoothscale(portrait_sprite, (80, 80))
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

    elif game.state == "REVEAL":
        t = game.reveal_timer
        dur = game.reveal_duration
        progress = min(t / dur, 1.0)
        accused = game.reveal_accused

        screen.fill((10, 8, 15))

        if accused:
            if progress < 0.5:
                # Suspense: "You accused..." then name fades in
                fade_in = min(1.0, t / (dur * 0.25))
                text_surf = font_lg.render("You accused...", True, (200, 200, 220))
                text_surf.set_alpha(int(255 * fade_in))
                screen.blit(text_surf, (SCREEN_W // 2 - text_surf.get_width() // 2, 220))

                if progress > 0.15:
                    name_surf = font_title.render(accused["name"], True, (255, 255, 255))
                    name_surf.set_alpha(int(255 * min(1.0, (progress - 0.15) / 0.15)))
                    screen.blit(name_surf, (SCREEN_W // 2 - name_surf.get_width() // 2, 310))
            else:
                # Reveal: flash then verdict
                flash_progress = (progress - 0.5) / 0.5
                if flash_progress < 0.2:
                    flash = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                    flash.fill((255, 255, 255, int(255 * (1.0 - flash_progress / 0.2))))
                    screen.blit(flash, (0, 0))

                draw_centered_text(screen, accused["name"], font_title, (255, 255, 255), 200)
                if game.reveal_correct:
                    draw_centered_text(screen, "VILLAIN!", font_title, (255, 80, 80), 290)
                else:
                    draw_centered_text(screen, "INNOCENT...", font_title, (100, 200, 255), 290)

                # After animation is done, show details and prompt
                if game.reveal_done:
                    if game.reveal_correct:
                        draw_centered_text(screen, "The town is saved!", font_md, (100, 255, 100), 390)
                    else:
                        guesses_left = 3 - game.wrong_guesses
                        if guesses_left <= 0:
                            draw_centered_text(screen, "You have no guesses remaining...", font_md, BLOOD_RED, 390)
                            draw_centered_text(screen, f"The villain {game.villain_name} wins!", font_md, BLOOD_RED, 430)
                        else:
                            draw_centered_text(screen, f"{guesses_left} guess{'es' if guesses_left > 1 else ''} remaining.", font_md, (200, 200, 180), 390)
                            # Show who was killed if there was a victim
                            if game.killed_tonight:
                                draw_centered_text(screen, f"{game.killed_tonight['name']} was murdered last night.", font_md, (220, 160, 160), 430)

                    draw_centered_text(screen, "Press ENTER to continue", font_md, (180, 180, 180), 530)

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

    elif game.state == "RECAP":
        screen.fill((15, 12, 8))
        # Build recap lines
        recap_lines = []
        won = game.reveal_correct
        if won:
            recap_lines.append(("CASE CLOSED", (255, 220, 60), font_title))
            recap_lines.append(("", (0, 0, 0), font_sm))  # spacer
        else:
            recap_lines.append(("CASE UNSOLVED", BLOOD_RED, font_title))
            recap_lines.append(("", (0, 0, 0), font_sm))

        # The villain
        villain_c = next((c for c in game.characters if c["is_villain"]), None)
        if villain_c:
            recap_lines.append(("The Villain:", (200, 180, 100), font_md))
            recap_lines.append((f"  {villain_c['name']} — {villain_c['personality']}, from {villain_c['hometown']}", (220, 210, 180), font_sm))
            recap_lines.append(("", (0, 0, 0), font_sm))

        # Motives
        victims = [e for e in game.history if e["type"] == "night" and e.get("victim")]
        if victims and villain_c:
            recap_lines.append(("Motives:", (200, 180, 100), font_md))
            for ev in victims:
                vname = ev["victim"]
                rel = game.get_relationship(villain_c["name"], vname)
                if rel:
                    recap_lines.append((f"  {vname}: {rel['detail']}", (220, 210, 180), font_sm))
                else:
                    recap_lines.append((f"  {vname}: No known motive", (180, 170, 150), font_sm))
            recap_lines.append(("", (0, 0, 0), font_sm))

        # Victims timeline
        recap_lines.append(("Timeline:", (200, 180, 100), font_md))
        for ev in game.history:
            recap_lines.append((f"  {ev['description']}", (200, 195, 170), font_sm))
        recap_lines.append(("", (0, 0, 0), font_sm))

        # Evidence found
        if game.evidence_found:
            recap_lines.append(("Evidence Collected:", (200, 180, 100), font_md))
            for ef in game.evidence_found:
                recap_lines.append((f"  - {ef['name']}", (200, 195, 170), font_sm))

        # Render with scrolling
        visible_start = game.recap_scroll
        visible_end = min(visible_start + 16, len(recap_lines))
        game.recap_scroll = min(game.recap_scroll, max(0, len(recap_lines) - 16))

        if visible_start > 0:
            draw_centered_text(screen, "▲", font_md, (180, 180, 180), 25)
        y_pos = 40
        for i in range(visible_start, visible_end):
            txt, col, fnt = recap_lines[i]
            if txt:
                y_pos = draw_centered_text_wrapped(screen, txt, fnt, col, y_pos, max_width=SCREEN_W - 100)
            y_pos += 6
        if visible_end < len(recap_lines):
            draw_centered_text(screen, "▼", font_md, (180, 180, 180), SCREEN_H - 60)
        draw_centered_text(screen, "Press ENTER to return to menu", font_md, (150, 150, 130), SCREEN_H - 35)

    elif game.state == "CREDITS":
        screen.fill((5, 3, 8))
        cy = game.credits_scroll_y
        credits_content = [
            ("QUANTUM BLOOD", font_title, (180, 20, 20)),
            ("", font_sm, (0, 0, 0)),
            ("A Murder Mystery Game", font_lg, (200, 190, 160)),
            ("", font_sm, (0, 0, 0)),
            ("", font_sm, (0, 0, 0)),
            ("— Development —", font_md, (160, 140, 100)),
            ("", font_sm, (0, 0, 0)),
            ("Game Design & Programming", font_sm, (140, 130, 110)),
            ("Garrett Bradham", font_md, (220, 210, 180)),
            ("Will", font_md, (220, 210, 180)),
            ("Taz", font_md, (220, 210, 180)),
            ("Teresa", font_md, (220, 210, 180)),
            ("", font_sm, (0, 0, 0)),
            ("AI Integration", font_sm, (140, 130, 110)),
            ("Powered by Ollama + Llama 3.1", font_md, (220, 210, 180)),
            ("", font_sm, (0, 0, 0)),
            ("", font_sm, (0, 0, 0)),
            ("— Art & Assets —", font_md, (160, 140, 100)),
            ("", font_sm, (0, 0, 0)),
            ("Character Sprites", font_sm, (140, 130, 110)),
            ("Pixel Art Generation", font_md, (220, 210, 180)),
            ("", font_sm, (0, 0, 0)),
            ("Building Design", font_sm, (140, 130, 110)),
            ("Procedural Generation", font_md, (220, 210, 180)),
            ("", font_sm, (0, 0, 0)),
            ("", font_sm, (0, 0, 0)),
            ("— Audio —", font_md, (160, 140, 100)),
            ("", font_sm, (0, 0, 0)),
            ("Music & Sound Effects", font_sm, (140, 130, 110)),
            ("Original Compositions", font_md, (220, 210, 180)),
            ("", font_sm, (0, 0, 0)),
            ("", font_sm, (0, 0, 0)),
            ("Thank you for playing!", font_lg, (180, 20, 20)),
            ("", font_sm, (0, 0, 0)),
            ("", font_sm, (0, 0, 0)),
            ("Press ENTER to return to menu", font_sm, (100, 95, 85)),
        ]
        for text, fnt, col in credits_content:
            if text:
                surf = fnt.render(text, True, col)
                screen.blit(surf, (SCREEN_W // 2 - surf.get_width() // 2, int(cy)))
                cy += surf.get_height() + 8
            else:
                cy += 20  # spacer

    # Fade overlay (drawn over everything)
    if game.fade_alpha > 0:
        fade_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        fade_surf.fill((0, 0, 0, int(game.fade_alpha)))
        screen.blit(fade_surf, (0, 0))

    # Scale render surface to display (handles fullscreen + window resize)
    dw, dh = display.get_size()
    scale = min(dw / SCREEN_W, dh / SCREEN_H)
    sw, sh = int(SCREEN_W * scale), int(SCREEN_H * scale)
    ox, oy = (dw - sw) // 2, (dh - sh) // 2
    display.fill((0, 0, 0))
    display.blit(pygame.transform.smoothscale(screen, (sw, sh)), (ox, oy))
    pygame.display.flip()

pygame.quit()
sys.exit()
