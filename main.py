import pygame
import sys
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

TILE_COLORS = {0: GRASS_COLOR, 1: WALL_COLOR, 2: PATH_COLOR, 3: ROOF_COLOR, 4: DOOR_COLOR}

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
tilemap = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,3,3,3,3,0,0,0,0,3,3,3,3,0,0,0,0,3,3,3,3,0,0,3,3,3,3,0,1],
    [1,0,1,1,1,1,0,0,0,0,1,1,1,1,0,0,0,0,1,1,1,1,0,0,1,1,1,1,0,1],
    [1,0,1,1,1,1,0,0,0,0,1,1,1,1,0,0,0,0,1,1,1,1,0,0,1,1,1,1,0,1],
    [1,0,1,4,1,1,0,0,0,0,1,1,4,1,0,0,0,0,1,4,1,1,0,0,1,1,4,1,0,1],
    [1,0,0,2,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,2,0,0,0,0,0,0,2,0,0,1],
    [1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1],
    [1,0,0,2,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,2,0,0,0,0,0,0,2,0,0,1],
    [1,0,3,3,3,3,0,0,0,0,3,3,3,3,0,0,0,0,3,3,3,3,0,0,0,0,0,0,0,1],
    [1,0,1,1,1,1,0,0,0,0,1,1,1,1,0,0,0,0,1,1,1,1,0,0,0,0,0,0,0,1],
    [1,0,1,1,1,1,0,0,0,0,1,1,1,1,0,0,0,0,1,1,1,1,0,0,0,0,0,0,0,1],
    [1,0,1,1,4,1,0,0,0,0,1,4,1,1,0,0,0,0,1,1,4,1,0,0,0,0,0,0,0,1],
    [1,0,0,0,2,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,2,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,1],
    [1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
]

MAP_H = len(tilemap)
MAP_W = len(tilemap[0])
SOLID_TILES = {1, 3}

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

NPC_COLORS = [
    (200, 60, 200), (60, 160, 220), (220, 180, 40),
    (60, 200, 100), (220, 120, 60), (180, 60, 60), (100, 200, 200),
]

INTERACT_DIST = TILE_SIZE * 1.8

# ── Ollama LLM ──────────────────────────────────────────────────
OLLAMA_MODEL = "llama3.1"  # swap to "qwen3.5:0.8b" if llama3.1 not available

def _pick_model():
    """Use llama3.1 if available, fall back to qwen3.5."""
    try:
        models = ollama.list()
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
        resp = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
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

        # Place NPCs
        for i, c in enumerate(self.characters):
            spawn = NPC_SPAWNS[i]
            c["tile_x"] = spawn[0]
            c["tile_y"] = spawn[1]
            c["x"] = spawn[0] * TILE_SIZE
            c["y"] = spawn[1] * TILE_SIZE
            c["color"] = NPC_COLORS[i]

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

        if self.night_num == 1:
            self.storyteller_text = "Night falls on the town...\nA villain lurks among you."
            self.killed_tonight = None
            self.history.append({"type": "night", "day": 1, "victim": None,
                                  "description": "The first night fell. No one was killed, but there are rumors of a murderer on the loose."})
        else:
            # Villain kills someone
            innocents = [c for c in self.alive if not c["is_villain"]]
            if innocents:
                victim = random.choice(innocents)
                self.killed_tonight = victim
                self.alive.remove(victim)
                self.storyteller_text = (
                    f"Night {self.night_num}...\n"
                    f"{victim['name']} was found dead this morning!"
                )
                self.history.append({
                    "type": "night", "day": self.night_num,
                    "victim": victim["name"],
                    "description": (
                        f"On the morning of day {self.night_num}, "
                        f"{victim['name']} was found dead. "
                        f"The town is grieving and afraid."
                    ),
                })
            else:
                self.storyteller_text = f"Night {self.night_num}..."

    def start_day(self):
        self.state = "DAY"
        self.dialogue_target = None
        self.dialogue_text = ""
        self.talked_to = set()  # track who we've talked to this day
        self._prefetch_dialogues()

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

        for npc in self.alive:
            is_villain = npc["is_villain"]
            system = (
                f"You are {npc['name']}, a character in a murder mystery game. "
                f"Personality: {npc['personality']}. From: {npc['hometown']}. "
                f"Weakness: {npc['weakness']}. "
                f"The other living townspeople are: {', '.join(n for n in alive_names if n != npc['name'])}. "
                f"IMPORTANT: Only refer to these people by their exact names. Do NOT invent any names."
            )
            if dead_names:
                system += f"The following people have been killed: {', '.join(dead_names)}. "
            if history_context:
                system += f"{history_context} React naturally to these events — reference specific deaths, false accusations, and rising fear as appropriate. "
            if is_villain:
                system += (
                    "You are secretly the villain. You must act innocent but occasionally "
                    "let subtle hints slip. Be evasive about your whereabouts last night. "
                    "If an innocent person was recently falsely accused, you may quietly deflect suspicion onto others. "
                    "Never directly confess. Keep responses to 2-3 sentences. Do not speak in third person."
                )
            else:
                system += (
                    "You are an innocent townsperson. You are scared and want to help "
                    "find the villain. Share your observations, reference the deaths you know about, "
                    "and let your fear and grief grow with each passing night. "
                    "You don't know who the villain is. Keep responses to 2-3 sentences. Do not speak in third person."
                )

            user_msg = (
                f"The detective approaches you to talk. It is day {self.night_num}. "
                f"Respond to the detective's question:Considering everything that has happened so far, what do you say?"
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


game = Game()

# ── Helpers ─────────────────────────────────────────────────────
def is_wall(px, py, w, h):
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
                    elif game.dialogue_target:
                        game.dialogue_target = None
                        game.dialogue_text = ""
                        game.dialogue_loading = False
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
                    if game.dialogue_target:
                        game.dialogue_target = None
                        game.dialogue_text = ""
                        game.dialogue_loading = False
                    else:
                        for npc in game.alive:
                            if player_near(npc):
                                game.talk_to_npc(npc)
                                break

                if event.key == pygame.K_TAB:
                    game.open_accuse()

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
        draw_centered_text(screen, "[WASD] Move  [E] Talk  [TAB] Accuse  [ESC] Quit", font_sm, (150, 150, 150), 500)

    elif game.state == "NIGHT":
        screen.fill(NIGHT_OVERLAY)
        lines = game.storyteller_text.split("\n")
        for i, line in enumerate(lines):
            draw_centered_text(screen, line, font_lg, (220, 220, 255), 200 + i * 60)
        if game.night_timer <= 0:
            draw_centered_text(screen, "Press ENTER to continue", font_md, (150, 150, 180), 500)

    elif game.state in ("DAY", "ACCUSE"):
        pw, ph = TILE_SIZE - 4, TILE_SIZE - 4
        cam_x = game.player_x + pw / 2 - SCREEN_W / 2
        cam_y = game.player_y + ph / 2 - SCREEN_H / 2

        # Draw tiles
        for row in range(MAP_H):
            for col in range(MAP_W):
                rect = pygame.Rect(
                    col * TILE_SIZE - cam_x,
                    row * TILE_SIZE - cam_y,
                    TILE_SIZE, TILE_SIZE,
                )
                pygame.draw.rect(screen, TILE_COLORS[tilemap[row][col]], rect)

        # Draw NPCs
        for npc in game.alive:
            sx = npc["x"] - cam_x
            sy = npc["y"] - cam_y
            idx = game.characters.index(npc) if npc in game.characters else -1
            sprite = npc_sprites[idx] if 0 <= idx < len(npc_sprites) else None
            if sprite:
                screen.blit(sprite, (sx, sy))
            else:
                pygame.draw.rect(screen, npc["color"], (sx, sy, TILE_SIZE - 4, TILE_SIZE - 4))
            # Name label
            name_surf = font_sm.render(npc["name"], True, (255, 255, 255))
            screen.blit(name_surf, (sx + (TILE_SIZE - 4) / 2 - name_surf.get_width() / 2, sy - 20))

            # Interaction hint
            if player_near(npc) and not game.dialogue_target:
                if npc["name"] in game.talked_to:
                    hint = font_sm.render("(already spoke)", True, (150, 150, 150))
                else:
                    hint = font_sm.render("[E] Talk", True, (255, 255, 200))
                screen.blit(hint, (sx - 5, sy - 38))

        # Draw player
        if player_walking:
            frames = player_walk_frames.get(player_facing)
            p_sprite = frames[player_anim_frame] if frames else None
        else:
            p_sprite = player_idle_sprites.get(player_facing)
        if p_sprite:
            screen.blit(p_sprite, (game.player_x - cam_x, game.player_y - cam_y))
        else:
            screen.blit(player_img_fallback, (game.player_x - cam_x, game.player_y - cam_y))

        # HUD
        hud_y = 10
        day_surf = font_md.render(f"Day {game.night_num}  |  Guesses left: {3 - game.wrong_guesses}  |  [TAB] Accuse", True, (255, 255, 255))
        pygame.draw.rect(screen, (0, 0, 0, 180), (0, 0, SCREEN_W, 45))
        screen.blit(day_surf, (15, hud_y))

        # Dialogue box
        if game.dialogue_target:
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
        lines = game.storyteller_text.split("\n")
        for i, line in enumerate(lines):
            draw_centered_text(screen, line, font_lg, (255, 200, 80), 220 + i * 60)
        draw_centered_text(screen, "Press ENTER to continue", font_md, (200, 200, 180), 500)

    elif game.state == "WIN":
        screen.fill((10, 40, 10))
        lines = game.storyteller_text.split("\n")
        for i, line in enumerate(lines):
            draw_centered_text(screen, line, font_lg, (100, 255, 100), 200 + i * 60)
        draw_centered_text(screen, "Press ENTER for main menu", font_md, (180, 255, 180), 500)

    elif game.state == "LOSE":
        screen.fill((40, 10, 10))
        lines = game.storyteller_text.split("\n")
        for i, line in enumerate(lines):
            draw_centered_text(screen, line, font_lg, BLOOD_RED, 160 + i * 60)
        draw_centered_text(screen, "Press ENTER for main menu", font_md, (255, 180, 180), 500)

    pygame.display.flip()

pygame.quit()
sys.exit()
