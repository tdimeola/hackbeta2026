"""Generate unique pixel-art building sprites for the murder mystery game."""
import pygame
import os

pygame.init()

TILE = 48
W = TILE * 4   # 192px wide (4 tiles)
H = TILE * 4   # 192px tall (4 tiles)
OUT = "assets/buildings"
os.makedirs(OUT, exist_ok=True)


def make_surface():
    return pygame.Surface((W, H), pygame.SRCALPHA)


def draw_blacksmith(surf):
    """Dark stone building with chimney, anvil sign, orange forge glow."""
    # Base walls — dark stone
    wall = (85, 65, 50)
    pygame.draw.rect(surf, wall, (10, 60, W - 20, H - 70))
    # Stone mortar
    mortar = (65, 50, 38)
    for y in range(60, H - 10, 10):
        pygame.draw.line(surf, mortar, (10, y), (W - 10, y), 1)
    for x in range(10, W - 10, 24):
        for y in range(60, H - 10, 20):
            off = 12 if (y // 20) % 2 else 0
            pygame.draw.line(surf, mortar, (x + off, y), (x + off, y + 10), 1)
    # Roof — dark slate peaked
    roof = (70, 70, 80)
    pygame.draw.polygon(surf, roof, [(0, 65), (W // 2, 10), (W, 65)])
    pygame.draw.polygon(surf, (55, 55, 65), [(5, 65), (W // 2, 15), (W - 5, 65)], 2)
    # Ridge highlight
    pygame.draw.line(surf, (90, 90, 100), (W // 2 - 40, 30), (W // 2 + 40, 30), 1)
    # Chimney
    pygame.draw.rect(surf, (75, 60, 50), (W - 50, 5, 25, 55))
    pygame.draw.rect(surf, (90, 70, 55), (W - 53, 2, 31, 8))
    # Smoke puffs
    for i, (cx, cy) in enumerate([(W - 38, -5), (W - 42, -15), (W - 35, -25)]):
        r = 6 + i * 2
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (180, 180, 190, 80), (r, r), r)
        surf.blit(s, (cx - r, cy - r))
    # Door
    pygame.draw.rect(surf, (60, 40, 25), (W // 2 - 18, H - 50, 36, 40))
    pygame.draw.rect(surf, (50, 35, 20), (W // 2 - 15, H - 47, 30, 37))
    pygame.draw.circle(surf, (200, 160, 60), (W // 2 + 10, H - 28), 3)
    # Window with forge glow
    wx, wy = 30, 90
    pygame.draw.rect(surf, (40, 30, 20), (wx, wy, 30, 25))
    glow = pygame.Surface((30, 25), pygame.SRCALPHA)
    glow.fill((255, 140, 30, 120))
    surf.blit(glow, (wx, wy))
    pygame.draw.rect(surf, (60, 45, 30), (wx, wy, 30, 25), 2)
    pygame.draw.line(surf, (60, 45, 30), (wx + 15, wy), (wx + 15, wy + 25), 2)
    # Right window
    wx2 = W - 60
    pygame.draw.rect(surf, (40, 30, 20), (wx2, wy, 30, 25))
    glow2 = pygame.Surface((30, 25), pygame.SRCALPHA)
    glow2.fill((255, 140, 30, 80))
    surf.blit(glow2, (wx2, wy))
    pygame.draw.rect(surf, (60, 45, 30), (wx2, wy, 30, 25), 2)
    # Anvil sign
    pygame.draw.line(surf, (100, 80, 50), (W // 2, 68), (W // 2, 80), 2)
    pygame.draw.rect(surf, (120, 100, 60), (W // 2 - 15, 80, 30, 12), border_radius=2)
    # Foundation
    pygame.draw.rect(surf, (60, 50, 38), (8, H - 12, W - 16, 12))


def draw_tavern(surf):
    """Warm wooden building with hanging sign, lanterns, and cozy windows."""
    wall = (120, 88, 55)
    # Base walls — wood planks
    pygame.draw.rect(surf, wall, (8, 55, W - 16, H - 65))
    for y in range(55, H - 10, 8):
        darker = (wall[0] - 10, wall[1] - 8, wall[2] - 5)
        pygame.draw.line(surf, darker, (8, y), (W - 8, y), 1)
    # Roof — warm amber peaked
    roof = (155, 85, 35)
    pygame.draw.polygon(surf, roof, [(0, 60), (W // 2, 8), (W, 60)])
    pygame.draw.polygon(surf, (130, 65, 25), [(3, 60), (W // 2, 11), (W - 3, 60)], 2)
    # Eave shadow
    pygame.draw.line(surf, (120, 55, 20), (0, 60), (W, 60), 2)
    # Door — warm oak with arch
    dx = W // 2 - 16
    pygame.draw.rect(surf, (90, 55, 25), (dx, H - 52, 32, 42))
    pygame.draw.ellipse(surf, (90, 55, 25), (dx, H - 62, 32, 20))
    pygame.draw.rect(surf, (110, 70, 30), (dx + 3, H - 48, 26, 38))
    pygame.draw.circle(surf, (220, 190, 80), (dx + 22, H - 30), 3)
    # Windows with warm glow (2)
    for wx in [22, W - 52]:
        pygame.draw.rect(surf, (35, 25, 15), (wx, 85, 28, 28))
        glow = pygame.Surface((28, 28), pygame.SRCALPHA)
        glow.fill((255, 200, 80, 100))
        surf.blit(glow, (wx, 85))
        pygame.draw.rect(surf, (80, 55, 30), (wx, 85, 28, 28), 2)
        pygame.draw.line(surf, (80, 55, 30), (wx + 14, 85), (wx + 14, 113), 2)
        pygame.draw.line(surf, (80, 55, 30), (wx, 99), (wx + 28, 99), 2)
    # Hanging sign
    pygame.draw.line(surf, (80, 60, 35), (40, 60), (40, 72), 2)
    pygame.draw.rect(surf, (160, 130, 70), (25, 72, 30, 18), border_radius=3)
    pygame.draw.rect(surf, (130, 100, 50), (28, 75, 24, 12), border_radius=2)
    # Lanterns
    for lx in [12, W - 22]:
        pygame.draw.rect(surf, (80, 60, 35), (lx + 3, 70, 4, 10))
        lantern = pygame.Surface((14, 14), pygame.SRCALPHA)
        pygame.draw.circle(lantern, (255, 220, 80, 150), (7, 7), 7)
        surf.blit(lantern, (lx, 78))
    # Foundation
    pygame.draw.rect(surf, (90, 70, 45), (6, H - 12, W - 12, 12))


def draw_apothecary(surf):
    """Mossy green-stone building with arched window, potion bottles."""
    wall = (80, 95, 75)
    pygame.draw.rect(surf, wall, (10, 55, W - 20, H - 65))
    # Stone texture
    mortar = (60, 75, 55)
    for y in range(55, H - 10, 12):
        pygame.draw.line(surf, mortar, (10, y), (W - 10, y), 1)
    for x in range(10, W - 10, 20):
        for yi in range(0, (H - 65) // 12):
            off = 10 if yi % 2 else 0
            pygame.draw.line(surf, mortar, (x + off, 55 + yi * 12), (x + off, 55 + yi * 12 + 12), 1)
    # Roof — green tiles
    roof = (55, 100, 65)
    pygame.draw.polygon(surf, roof, [(2, 60), (W // 2, 12), (W - 2, 60)])
    pygame.draw.polygon(surf, (40, 80, 50), [(5, 60), (W // 2, 15), (W - 5, 60)], 2)
    pygame.draw.line(surf, (40, 80, 50), (2, 60), (W - 2, 60), 2)
    # Arched main window with potions
    wx, wy = W // 2 - 22, 78
    pygame.draw.rect(surf, (30, 45, 30), (wx, wy, 44, 35))
    pygame.draw.ellipse(surf, (30, 45, 30), (wx, wy - 12, 44, 24))
    glow = pygame.Surface((44, 35), pygame.SRCALPHA)
    glow.fill((80, 200, 120, 60))
    surf.blit(glow, (wx, wy))
    pygame.draw.rect(surf, (55, 75, 50), (wx, wy, 44, 35), 2)
    pygame.draw.ellipse(surf, (55, 75, 50), (wx, wy - 12, 44, 24), 2)
    # Potion bottles in window
    colors = [(100, 220, 100), (220, 80, 220), (80, 160, 240), (240, 200, 60)]
    for i, bc in enumerate(colors):
        bx = wx + 6 + i * 10
        pygame.draw.rect(surf, bc, (bx, wy + 18, 6, 12))
        pygame.draw.rect(surf, (min(bc[0] + 20, 255), min(bc[1] + 20, 255), min(bc[2] + 20, 255)), (bx + 1, wy + 15, 4, 5))
    # Door
    dx = W // 2 - 14
    pygame.draw.rect(surf, (55, 75, 45), (dx, H - 48, 28, 38))
    pygame.draw.rect(surf, (65, 85, 55), (dx + 3, H - 45, 22, 35))
    pygame.draw.circle(surf, (150, 200, 120), (dx + 20, H - 28), 3)
    # Herb bundles hanging from eave
    for hx in [25, 55, W - 65, W - 35]:
        pygame.draw.line(surf, (70, 55, 35), (hx, 58), (hx, 68), 2)
        pygame.draw.circle(surf, (60, 110, 50), (hx, 70), 5)
    # Foundation with moss
    pygame.draw.rect(surf, (65, 80, 55), (8, H - 12, W - 16, 12))


def draw_church(surf):
    """Limestone building with tall steeple, cross, stained glass."""
    wall = (140, 135, 120)
    pygame.draw.rect(surf, wall, (20, 70, W - 40, H - 80))
    # Stone lines
    for y in range(70, H - 10, 14):
        pygame.draw.line(surf, (120, 115, 100), (20, y), (W - 20, y), 1)
    # Steeple
    steeple = (100, 95, 110)
    pygame.draw.polygon(surf, steeple, [(W // 2 - 20, 50), (W // 2, 0), (W // 2 + 20, 50)])
    pygame.draw.rect(surf, steeple, (W // 2 - 20, 50, 40, 25))
    # Cross
    pygame.draw.rect(surf, (220, 200, 80), (W // 2 - 2, -8, 4, 20))
    pygame.draw.rect(surf, (220, 200, 80), (W // 2 - 8, -2, 16, 4))
    # Main roof
    roof = (55, 50, 70)
    pygame.draw.polygon(surf, roof, [(15, 75), (W // 2, 35), (W - 15, 75)])
    pygame.draw.polygon(surf, (45, 40, 60), [(18, 75), (W // 2, 38), (W - 18, 75)], 2)
    pygame.draw.line(surf, (45, 40, 60), (15, 75), (W - 15, 75), 2)
    # Stained glass window (large arched)
    wx, wy = W // 2 - 18, 85
    pygame.draw.rect(surf, (30, 25, 40), (wx, wy, 36, 40))
    pygame.draw.ellipse(surf, (30, 25, 40), (wx, wy - 10, 36, 22))
    # Stained glass colors
    glass = [(180, 60, 60), (60, 80, 180), (180, 160, 50), (60, 160, 80)]
    for i, gc in enumerate(glass):
        gx = wx + 3 + (i % 2) * 16
        gy = wy + 3 + (i // 2) * 18
        pygame.draw.rect(surf, gc, (gx, gy, 14, 16))
    pygame.draw.rect(surf, (100, 90, 80), (wx, wy, 36, 40), 2)
    pygame.draw.line(surf, (100, 90, 80), (wx + 18, wy), (wx + 18, wy + 40), 2)
    pygame.draw.line(surf, (100, 90, 80), (wx, wy + 20), (wx + 36, wy + 20), 2)
    # Door — heavy dark mahogany
    dx = W // 2 - 16
    pygame.draw.rect(surf, (65, 40, 30), (dx, H - 48, 32, 38))
    pygame.draw.ellipse(surf, (65, 40, 30), (dx, H - 58, 32, 22))
    pygame.draw.rect(surf, (80, 50, 35), (dx + 3, H - 45, 26, 35))
    pygame.draw.circle(surf, (200, 180, 80), (dx + 24, H - 28), 3)
    # Foundation
    pygame.draw.rect(surf, (110, 105, 90), (18, H - 12, W - 36, 12))


def draw_general_store(surf):
    """Wide storefront with awning, crates, and display window."""
    wall = (110, 85, 60)
    pygame.draw.rect(surf, wall, (6, 55, W - 12, H - 65))
    # Wood plank lines
    for y in range(55, H - 10, 10):
        pygame.draw.line(surf, (95, 70, 48), (6, y), (W - 6, y), 1)
    # Roof — classic red
    roof = (160, 55, 35)
    pygame.draw.polygon(surf, roof, [(0, 60), (W // 2, 15), (W, 60)])
    pygame.draw.polygon(surf, (135, 40, 25), [(3, 60), (W // 2, 18), (W - 3, 60)], 2)
    pygame.draw.line(surf, (135, 40, 25), (0, 60), (W, 60), 2)
    # Awning over storefront
    awning = (180, 50, 35)
    awning_stripe = (220, 200, 170)
    pygame.draw.polygon(surf, awning, [(10, 78), (W - 10, 78), (W - 5, 95), (5, 95)])
    for sx in range(15, W - 15, 20):
        pygame.draw.line(surf, awning_stripe, (sx, 78), (sx - 3, 95), 2)
    # Large display window
    wx, wy = 20, 100
    pygame.draw.rect(surf, (40, 35, 25), (wx, wy, W - 40, 32))
    glow = pygame.Surface((W - 40, 32), pygame.SRCALPHA)
    glow.fill((255, 230, 180, 70))
    surf.blit(glow, (wx, wy))
    pygame.draw.rect(surf, (85, 65, 40), (wx, wy, W - 40, 32), 2)
    pygame.draw.line(surf, (85, 65, 40), (W // 2, wy), (W // 2, wy + 32), 2)
    # Crate display items
    for cx in [wx + 8, wx + 30, W - 70, W - 48]:
        pygame.draw.rect(surf, (140, 110, 60), (cx, wy + 14, 14, 14))
        pygame.draw.line(surf, (110, 80, 40), (cx, wy + 21), (cx + 14, wy + 21), 1)
    # Door
    dx = W // 2 - 14
    pygame.draw.rect(surf, (95, 65, 30), (dx, H - 48, 28, 38))
    pygame.draw.rect(surf, (110, 75, 35), (dx + 3, H - 45, 22, 35))
    pygame.draw.circle(surf, (200, 170, 80), (dx + 18, H - 28), 3)
    # Crates outside
    pygame.draw.rect(surf, (130, 95, 50), (W - 35, H - 25, 22, 18))
    pygame.draw.line(surf, (100, 70, 35), (W - 35, H - 16), (W - 13, H - 16), 1)
    # Foundation
    pygame.draw.rect(surf, (85, 68, 45), (4, H - 12, W - 8, 12))


def draw_town_hall(surf):
    """Grand stone building with columns, clock, and ornate entrance."""
    wall = (130, 120, 100)
    pygame.draw.rect(surf, wall, (12, 60, W - 24, H - 70))
    # Stone lines
    for y in range(60, H - 10, 12):
        pygame.draw.line(surf, (110, 100, 82), (12, y), (W - 12, y), 1)
    # Roof — slate blue-gray with pediment
    roof = (60, 60, 78)
    pygame.draw.polygon(surf, roof, [(5, 65), (W // 2, 12), (W - 5, 65)])
    pygame.draw.polygon(surf, (48, 48, 65), [(8, 65), (W // 2, 15), (W - 8, 65)], 2)
    # Pediment detail — triangular trim
    pygame.draw.polygon(surf, (140, 130, 110), [(15, 64), (W // 2, 22), (W - 15, 64)], 3)
    # Clock in pediment
    cx, cy = W // 2, 42
    pygame.draw.circle(surf, (200, 190, 160), (cx, cy), 12)
    pygame.draw.circle(surf, (160, 150, 120), (cx, cy), 12, 2)
    pygame.draw.line(surf, (80, 70, 50), (cx, cy), (cx, cy - 8), 2)
    pygame.draw.line(surf, (80, 70, 50), (cx, cy), (cx + 6, cy), 2)
    # Columns (2)
    for colx in [30, W - 42]:
        pygame.draw.rect(surf, (155, 145, 125), (colx, 65, 12, H - 80))
        pygame.draw.rect(surf, (165, 155, 135), (colx - 2, 65, 16, 6))
        pygame.draw.rect(surf, (165, 155, 135), (colx - 2, H - 18, 16, 6))
    # Grand door with arch
    dx = W // 2 - 18
    pygame.draw.rect(surf, (85, 55, 30), (dx, H - 55, 36, 45))
    pygame.draw.ellipse(surf, (85, 55, 30), (dx, H - 68, 36, 28))
    pygame.draw.rect(surf, (100, 65, 35), (dx + 3, H - 52, 30, 42))
    pygame.draw.line(surf, (75, 50, 28), (dx + 18, H - 52), (dx + 18, H - 10), 2)
    pygame.draw.circle(surf, (220, 200, 80), (dx + 12, H - 30), 3)
    pygame.draw.circle(surf, (220, 200, 80), (dx + 24, H - 30), 3)
    # Windows (2 tall)
    for wx in [45, W - 70]:
        pygame.draw.rect(surf, (50, 45, 35), (wx, 80, 22, 35))
        glow = pygame.Surface((22, 35), pygame.SRCALPHA)
        glow.fill((255, 240, 200, 60))
        surf.blit(glow, (wx, 80))
        pygame.draw.rect(surf, (100, 90, 70), (wx, 80, 22, 35), 2)
        pygame.draw.line(surf, (100, 90, 70), (wx + 11, 80), (wx + 11, 115), 2)
    # Foundation — grand stone
    pygame.draw.rect(surf, (105, 95, 78), (10, H - 12, W - 20, 12))
    # Gold trim line
    pygame.draw.line(surf, (200, 180, 80), (12, 64), (W - 12, 64), 2)


def draw_library(surf):
    """Dark brick building with large arched window, bookish details."""
    wall = (100, 75, 62)
    pygame.draw.rect(surf, wall, (10, 55, W - 20, H - 65))
    # Brick pattern
    brick = (80, 58, 45)
    for y in range(55, H - 10, 8):
        pygame.draw.line(surf, brick, (10, y), (W - 10, y), 1)
    for x in range(10, W - 10, 16):
        for yi in range(0, (H - 65) // 8):
            off = 8 if yi % 2 else 0
            pygame.draw.line(surf, brick, (x + off, 55 + yi * 8), (x + off, 55 + yi * 8 + 8), 1)
    # Roof — deep red-brown
    roof = (120, 50, 38)
    pygame.draw.polygon(surf, roof, [(2, 60), (W // 2, 10), (W - 2, 60)])
    pygame.draw.polygon(surf, (95, 35, 25), [(5, 60), (W // 2, 13), (W - 5, 60)], 2)
    pygame.draw.line(surf, (95, 35, 25), (2, 60), (W - 2, 60), 2)
    # Large arched window
    wx, wy = W // 2 - 24, 78
    pygame.draw.rect(surf, (35, 28, 22), (wx, wy, 48, 40))
    pygame.draw.ellipse(surf, (35, 28, 22), (wx, wy - 14, 48, 28))
    glow = pygame.Surface((48, 40), pygame.SRCALPHA)
    glow.fill((255, 230, 180, 50))
    surf.blit(glow, (wx, wy))
    pygame.draw.rect(surf, (75, 55, 40), (wx, wy, 48, 40), 2)
    pygame.draw.ellipse(surf, (75, 55, 40), (wx, wy - 14, 48, 28), 2)
    # Book shapes in window
    book_colors = [(180, 50, 40), (40, 70, 140), (50, 120, 60), (160, 130, 40)]
    for i, bc in enumerate(book_colors):
        bx = wx + 6 + i * 11
        pygame.draw.rect(surf, bc, (bx, wy + 22, 8, 14))
    # Small side windows
    for swx in [22, W - 42]:
        pygame.draw.rect(surf, (40, 32, 25), (swx, 95, 18, 22))
        pygame.draw.rect(surf, (75, 55, 40), (swx, 95, 18, 22), 2)
    # Door
    dx = W // 2 - 14
    pygame.draw.rect(surf, (70, 45, 30), (dx, H - 48, 28, 38))
    pygame.draw.rect(surf, (85, 55, 35), (dx + 3, H - 45, 22, 35))
    pygame.draw.circle(surf, (160, 120, 60), (dx + 18, H - 28), 3)
    # Small plaque next to door
    pygame.draw.rect(surf, (140, 120, 70), (dx + 32, H - 40, 20, 12), border_radius=2)
    # Foundation
    pygame.draw.rect(surf, (80, 60, 48), (8, H - 12, W - 16, 12))


# Generate all buildings
buildings = {
    "blacksmith": draw_blacksmith,
    "tavern": draw_tavern,
    "apothecary": draw_apothecary,
    "church": draw_church,
    "general_store": draw_general_store,
    "town_hall": draw_town_hall,
    "library": draw_library,
}

for name, draw_fn in buildings.items():
    surf = make_surface()
    draw_fn(surf)
    path = os.path.join(OUT, f"{name}.png")
    pygame.image.save(surf, path)
    print(f"Saved {path}")

pygame.quit()
print("Done! All building sprites generated.")
