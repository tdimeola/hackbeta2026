"""Generate detailed pixel-art building sprites for the murder mystery game."""
import pygame
import os
import math

pygame.init()

TILE = 48
W = TILE * 4   # 192px wide
H = TILE * 4   # 192px tall
OUT = "assets/buildings"
os.makedirs(OUT, exist_ok=True)


def make_surface():
    return pygame.Surface((W, H), pygame.SRCALPHA)


def draw_blacksmith(surf):
    """Dark stone forge with chimney, glowing forge opening, anvil."""
    # Foundation
    pygame.draw.rect(surf, (50, 40, 35), (5, H - 16, W - 10, 16))
    pygame.draw.rect(surf, (60, 48, 40), (5, H - 16, W - 10, 3))

    # Main walls - dark rough stone
    pygame.draw.rect(surf, (90, 68, 52), (12, 65, W - 24, H - 81))
    # Stone block pattern
    for row, y in enumerate(range(65, H - 16, 11)):
        off = 14 if row % 2 else 0
        for x in range(12 + off, W - 12, 28):
            w = min(26, W - 12 - x)
            if w > 4:
                pygame.draw.rect(surf, (60, 45, 35), (x, y, w, 10), 1)
                pygame.draw.line(surf, (105, 82, 62), (x + 1, y + 1), (x + w - 2, y + 1), 1)

    # Chimney on right - drawn BEFORE roof so roof overlaps correctly
    chimney_x = W - 52
    pygame.draw.rect(surf, (75, 55, 42), (chimney_x, 5, 30, 65))
    pygame.draw.rect(surf, (85, 65, 48), (chimney_x - 2, 2, 34, 8))
    # Chimney brick lines
    for cy in range(12, 65, 8):
        pygame.draw.line(surf, (60, 42, 32), (chimney_x, cy), (chimney_x + 30, cy), 1)

    # Smoke puffs
    for i, (sx, sy, sr) in enumerate([
        (chimney_x + 15, -5, 7), (chimney_x + 10, -18, 9),
        (chimney_x + 18, -30, 11), (chimney_x + 7, -42, 8),
    ]):
        alpha = 90 - i * 18
        s = pygame.Surface((sr * 2, sr * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (160, 155, 150, max(alpha, 20)), (sr, sr), sr)
        surf.blit(s, (sx - sr, sy - sr))

    # Roof - solid dark slate, no gradient banding
    pygame.draw.polygon(surf, (62, 60, 70), [(4, 70), (W // 2, 30), (W - 4, 70)])
    # Roof outline
    pygame.draw.line(surf, (45, 43, 55), (4, 70), (W - 4, 70), 3)
    pygame.draw.line(surf, (75, 73, 82), (W // 2, 30), (4, 70), 2)
    pygame.draw.line(surf, (50, 48, 58), (W // 2, 30), (W - 4, 70), 2)
    # Simple roof shingle rows
    for ry in range(36, 68, 6):
        t = (ry - 30) / 40.0
        lx = int(4 + (W // 2 - 4) * (1 - t))
        rx = int(W - 4 - (W - 4 - W // 2) * (1 - t))
        shade = 58 + (ry % 12) * 2
        pygame.draw.line(surf, (shade, shade - 2, shade + 6), (lx + 2, ry), (rx - 2, ry), 1)

    # Forge opening - large arch with fire glow
    fx, fy = 25, 92
    fw, fh = 48, 58
    pygame.draw.rect(surf, (30, 20, 15), (fx, fy, fw, fh))
    pygame.draw.ellipse(surf, (30, 20, 15), (fx, fy - 14, fw, 28))
    # Fire glow - simple layered rectangles instead of per-line
    glow_colors = [
        (255, 160, 40, 140), (255, 120, 25, 120),
        (220, 80, 15, 100), (180, 50, 10, 80),
    ]
    for i, gc in enumerate(glow_colors):
        gy = fy + i * (fh // 4)
        gh = fh // 4
        g = pygame.Surface((fw, gh), pygame.SRCALPHA)
        g.fill(gc)
        surf.blit(g, (fx, gy))
    # Embers
    for ex, ey in [(fx + 12, fy + fh - 10), (fx + 24, fy + fh - 14), (fx + 36, fy + fh - 8)]:
        pygame.draw.circle(surf, (255, 200, 50), (ex, ey), 2)
    # Arch border
    pygame.draw.rect(surf, (50, 38, 28), (fx, fy, fw, fh), 3)
    pygame.draw.ellipse(surf, (50, 38, 28), (fx, fy - 14, fw, 28), 3)

    # Side window with orange glow
    wx, wy = W - 70, 90
    pygame.draw.rect(surf, (35, 25, 18), (wx, wy, 22, 26))
    glow_w = pygame.Surface((22, 26), pygame.SRCALPHA)
    glow_w.fill((255, 140, 30, 90))
    surf.blit(glow_w, (wx, wy))
    pygame.draw.rect(surf, (60, 45, 32), (wx, wy, 22, 26), 2)
    pygame.draw.line(surf, (60, 45, 32), (wx + 11, wy), (wx + 11, wy + 26), 2)

    # Door - heavy iron-bound
    dx, dy = W // 2 + 18, H - 55
    pygame.draw.rect(surf, (55, 38, 22), (dx, dy, 30, 39))
    pygame.draw.rect(surf, (65, 45, 28), (dx + 2, dy + 2, 26, 35))
    for by in [dy + 8, dy + 20, dy + 32]:
        pygame.draw.line(surf, (80, 80, 85), (dx + 1, by), (dx + 29, by), 2)
    pygame.draw.circle(surf, (180, 160, 80), (dx + 22, dy + 20), 3)

    # Anvil - bigger and clearer
    ax, ay = 85, H - 26
    pygame.draw.rect(surf, (75, 75, 80), (ax, ay, 30, 8))        # base
    pygame.draw.rect(surf, (85, 85, 90), (ax + 6, ay - 10, 18, 10))  # body
    pygame.draw.rect(surf, (95, 95, 100), (ax + 2, ay - 14, 26, 5))  # top/horn
    # Hammer leaning against it
    pygame.draw.line(surf, (100, 80, 50), (ax + 30, ay - 6), (ax + 42, ay - 22), 3)
    pygame.draw.rect(surf, (90, 90, 95), (ax + 38, ay - 26, 10, 8))


def draw_tavern(surf):
    """Warm two-story Tudor-style building with clean timber framing."""
    # Foundation
    pygame.draw.rect(surf, (80, 65, 48), (4, H - 14, W - 8, 14))
    pygame.draw.rect(surf, (90, 75, 55), (4, H - 14, W - 8, 3))

    # Ground floor walls - warm plaster
    plaster = (175, 155, 120)
    beam = (65, 40, 22)
    pygame.draw.rect(surf, plaster, (8, 100, W - 16, H - 114))

    # Ground floor timber frame - clean horizontal and vertical beams only
    pygame.draw.rect(surf, beam, (8, 98, W - 16, 4))    # top
    pygame.draw.rect(surf, beam, (8, 98, 5, H - 112))   # left
    pygame.draw.rect(surf, beam, (W - 13, 98, 5, H - 112))  # right
    pygame.draw.line(surf, beam, (W // 2, 98), (W // 2, H - 14), 4)  # center

    # Second floor - jettied overhang
    pygame.draw.rect(surf, plaster, (3, 52, W - 6, 48))
    pygame.draw.rect(surf, beam, (3, 50, W - 6, 4))     # top
    pygame.draw.rect(surf, beam, (3, 96, W - 6, 5))     # bottom overhang
    pygame.draw.rect(surf, beam, (3, 50, 5, 50))         # left
    pygame.draw.rect(surf, beam, (W - 8, 50, 5, 50))    # right
    pygame.draw.line(surf, beam, (W // 2, 50), (W // 2, 96), 4)  # center vertical

    # Clean diagonal braces in second floor panels (single diagonals, not X)
    # Left panel: one diagonal
    pygame.draw.line(surf, beam, (10, 54), (W // 2 - 3, 94), 3)
    # Right panel: opposite diagonal
    pygame.draw.line(surf, beam, (W - 10, 54), (W // 2 + 3, 94), 3)

    # Roof - warm thatch, solid fill with edge lines only
    pygame.draw.polygon(surf, (150, 95, 42), [(0, 55), (W // 2, 12), (W, 55)])
    # Subtle darker half for depth (right side in shadow)
    shadow_pts = [(W // 2, 12), (W, 55), (W // 2, 55)]
    shadow = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.polygon(shadow, (0, 0, 0, 25), shadow_pts)
    surf.blit(shadow, (0, 0))
    pygame.draw.line(surf, (120, 70, 30), (0, 55), (W, 55), 3)
    pygame.draw.line(surf, (165, 108, 48), (W // 2, 12), (0, 55), 2)
    pygame.draw.line(surf, (130, 80, 35), (W // 2, 12), (W, 55), 2)

    # Dormer window in roof - bigger
    dw_x = W // 2 - 18
    pygame.draw.polygon(surf, (150, 95, 42), [(dw_x - 6, 44), (dw_x + 18, 22), (dw_x + 42, 44)])
    pygame.draw.rect(surf, plaster, (dw_x + 2, 30, 32, 16))
    pygame.draw.rect(surf, (35, 28, 18), (dw_x + 6, 32, 24, 12))
    glow_d = pygame.Surface((24, 12), pygame.SRCALPHA)
    glow_d.fill((255, 210, 100, 100))
    surf.blit(glow_d, (dw_x + 6, 32))
    pygame.draw.rect(surf, beam, (dw_x + 6, 32, 24, 12), 2)
    pygame.draw.line(surf, beam, (dw_x + 18, 32), (dw_x + 18, 44), 2)

    # Ground floor windows - warm glow
    for wx in [22, W - 55]:
        pygame.draw.rect(surf, (35, 25, 15), (wx, 110, 30, 32))
        glow = pygame.Surface((30, 32), pygame.SRCALPHA)
        glow.fill((255, 200, 80, 110))
        surf.blit(glow, (wx, 110))
        pygame.draw.rect(surf, beam, (wx, 110, 30, 32), 2)
        pygame.draw.line(surf, beam, (wx + 15, 110), (wx + 15, 142), 2)
        pygame.draw.line(surf, beam, (wx, 126), (wx + 30, 126), 2)

    # Second floor windows
    for wx in [18, W - 48]:
        pygame.draw.rect(surf, (35, 25, 15), (wx, 62, 24, 28))
        glow2 = pygame.Surface((24, 28), pygame.SRCALPHA)
        glow2.fill((255, 200, 80, 80))
        surf.blit(glow2, (wx, 62))
        pygame.draw.rect(surf, beam, (wx, 62, 24, 28), 2)
        pygame.draw.line(surf, beam, (wx + 12, 62), (wx + 12, 90), 2)

    # Main door - arched
    dx = W // 2 - 18
    pygame.draw.rect(surf, (85, 50, 22), (dx, H - 55, 36, 41))
    pygame.draw.ellipse(surf, (85, 50, 22), (dx, H - 68, 36, 28))
    pygame.draw.rect(surf, (100, 62, 28), (dx + 3, H - 52, 30, 38))
    pygame.draw.line(surf, (70, 42, 18), (dx + 18, H - 52), (dx + 18, H - 14), 2)
    pygame.draw.circle(surf, (220, 190, 70), (dx + 12, H - 32), 3)
    pygame.draw.circle(surf, (220, 190, 70), (dx + 24, H - 32), 3)

    # Hanging sign on bracket
    sign_x = 15
    pygame.draw.line(surf, (60, 40, 25), (sign_x, 98), (sign_x, 110), 2)
    pygame.draw.line(surf, (60, 40, 25), (sign_x, 110), (sign_x + 32, 110), 2)
    # Chains
    pygame.draw.line(surf, (100, 95, 85), (sign_x + 8, 110), (sign_x + 8, 116), 1)
    pygame.draw.line(surf, (100, 95, 85), (sign_x + 28, 110), (sign_x + 28, 116), 1)
    # Sign board with mug shape
    pygame.draw.rect(surf, (160, 130, 65), (sign_x + 3, 116, 30, 18), border_radius=3)
    # Mug icon
    pygame.draw.rect(surf, (200, 180, 100), (sign_x + 11, 120, 10, 10))
    pygame.draw.rect(surf, (200, 180, 100), (sign_x + 21, 123, 4, 4))

    # Lanterns flanking door
    for lx in [dx - 10, dx + 40]:
        pygame.draw.rect(surf, (60, 45, 30), (lx + 3, H - 58, 3, 8))
        # Lantern body
        pygame.draw.rect(surf, (60, 45, 30), (lx, H - 50, 10, 14), border_radius=2)
        # Glow
        glow_l = pygame.Surface((18, 22), pygame.SRCALPHA)
        pygame.draw.circle(glow_l, (255, 200, 60, 45), (9, 11), 9)
        surf.blit(glow_l, (lx - 4, H - 52))
        pygame.draw.rect(surf, (255, 220, 80), (lx + 3, H - 48, 4, 10))

    # Flower boxes under ground floor windows
    for wx in [22, W - 55]:
        pygame.draw.rect(surf, (80, 55, 30), (wx - 2, 142, 34, 6))
        for fx in range(wx + 2, wx + 28, 7):
            pygame.draw.circle(surf, (200, 60, 70), (fx + 3, 141), 3)
            pygame.draw.line(surf, (50, 100, 40), (fx + 3, 144), (fx + 3, 148), 1)


def draw_apothecary(surf):
    """Mysterious green-stone shop with potions, herbs, and a lived-in feel."""
    # Foundation - mossy stone
    pygame.draw.rect(surf, (55, 70, 50), (8, H - 14, W - 16, 14))
    for mx in range(10, W - 14, 15):
        pygame.draw.circle(surf, (45, 80, 40), (mx + 5, H - 7), 3)

    # Walls - straight green-gray stone (no crooked polygon)
    pygame.draw.rect(surf, (88, 100, 78), (12, 58, W - 24, H - 72))
    # Stone texture
    for row, y in enumerate(range(58, H - 14, 10)):
        off = 10 if row % 2 else 0
        for x in range(12 + off, W - 12, 22):
            sw = min(20, W - 14 - x)
            if sw > 4:
                shade = 78 + (x + y) % 12
                pygame.draw.rect(surf, (shade - 8, shade + 5, shade - 12), (x, y, sw, 9), 1)
                pygame.draw.line(surf, (shade + 5, shade + 12, shade), (x + 1, y + 1), (x + sw - 2, y + 1), 1)

    # Roof - dark green shingles, straight
    pygame.draw.polygon(surf, (48, 72, 50), [(4, 62), (W // 2, 14), (W - 4, 62)])
    # Shingle rows
    for ry in range(18, 60, 5):
        t = (ry - 14) / 48.0
        lx = int(4 + (W // 2 - 4) * (1 - t))
        rx = int(W - 4 - (W - 4 - W // 2) * (1 - t))
        shade = 42 + (ry % 10) * 3
        pygame.draw.line(surf, (shade, shade + 20, shade + 2), (lx + 2, ry), (rx - 2, ry), 1)
    pygame.draw.line(surf, (35, 55, 38), (4, 62), (W - 4, 62), 3)
    pygame.draw.line(surf, (55, 80, 55), (W // 2, 14), (4, 62), 2)
    pygame.draw.line(surf, (40, 62, 42), (W // 2, 14), (W - 4, 62), 2)

    # Large arched display window
    wx, wy = W // 2 - 28, 78
    ww, wh = 56, 42
    pygame.draw.rect(surf, (25, 35, 25), (wx, wy, ww, wh))
    pygame.draw.ellipse(surf, (25, 35, 25), (wx, wy - 14, ww, 28))
    # Green mystical glow - simple solid instead of per-line
    glow = pygame.Surface((ww, wh), pygame.SRCALPHA)
    glow.fill((40, 180, 80, 70))
    surf.blit(glow, (wx, wy))
    pygame.draw.rect(surf, (50, 72, 48), (wx, wy, ww, wh), 2)
    pygame.draw.ellipse(surf, (50, 72, 48), (wx, wy - 14, ww, 28), 2)

    # Potion bottles - clear distinct shapes
    bottles = [
        (wx + 5, 7, 14, (80, 200, 80)),      # tall green
        (wx + 15, 9, 10, (190, 60, 190)),     # purple
        (wx + 26, 6, 16, (60, 130, 220)),     # tall blue
        (wx + 37, 10, 8, (230, 180, 40)),     # short yellow
        (wx + 46, 8, 12, (210, 55, 55)),      # red
    ]
    for bx, bw, bh, bc in bottles:
        by = wy + wh - bh - 2
        pygame.draw.rect(surf, bc, (bx, by, bw, bh))
        # Neck
        pygame.draw.rect(surf, bc, (bx + bw // 2 - 1, by - 4, 3, 5))
        # Cork
        pygame.draw.rect(surf, (160, 130, 80), (bx + bw // 2 - 1, by - 6, 3, 3))
        # Highlight
        pygame.draw.line(surf, (min(bc[0] + 60, 255), min(bc[1] + 60, 255), min(bc[2] + 60, 255)),
                        (bx + 1, by + 1), (bx + 1, by + bh - 2), 1)

    # Door - old wood with ivy growing around frame
    dx, dy = 20, H - 52
    pygame.draw.rect(surf, (58, 68, 45), (dx, dy, 28, 38))
    pygame.draw.rect(surf, (65, 78, 52), (dx + 2, dy + 2, 24, 34))
    # Door planks
    for px in [dx + 9, dx + 16, dx + 23]:
        pygame.draw.line(surf, (50, 60, 38), (px, dy + 2), (px, dy + 36), 1)
    pygame.draw.circle(surf, (140, 180, 100), (dx + 22, dy + 20), 3)
    # Ivy vines around door frame
    for iy in range(dy, dy + 38, 6):
        side = -3 if iy % 12 < 6 else 1
        pygame.draw.circle(surf, (45, 95, 40), (dx + side, iy), 3)
        pygame.draw.circle(surf, (55, 110, 50), (dx + side, iy), 2)
    for iy in range(dy + 3, dy + 38, 8):
        side = 30 if iy % 16 < 8 else 28
        pygame.draw.circle(surf, (45, 95, 40), (dx + side, iy), 3)
        pygame.draw.circle(surf, (55, 110, 50), (dx + side, iy), 2)

    # Hanging herb bundles - cleaner look with leaf clusters
    herbs_x = [35, 65, 100, 130, 158]
    for hx in herbs_x:
        hy = 60
        pygame.draw.line(surf, (80, 60, 35), (hx, hy), (hx, hy + 10), 2)
        # Cluster of leaves instead of single ellipses
        pygame.draw.circle(surf, (50, 100, 40), (hx - 3, hy + 13), 4)
        pygame.draw.circle(surf, (60, 115, 48), (hx + 3, hy + 14), 4)
        pygame.draw.circle(surf, (45, 90, 35), (hx, hy + 17), 3)

    # Small side window
    sw_x = W - 50
    pygame.draw.rect(surf, (28, 38, 28), (sw_x, 90, 20, 24))
    glow_s = pygame.Surface((20, 24), pygame.SRCALPHA)
    glow_s.fill((40, 160, 70, 50))
    surf.blit(glow_s, (sw_x, 90))
    pygame.draw.rect(surf, (50, 72, 48), (sw_x, 90, 20, 24), 2)
    pygame.draw.line(surf, (50, 72, 48), (sw_x + 10, 90), (sw_x + 10, 114), 2)


def draw_church(surf):
    """Tall limestone church with steeple, rose window, and gothic door."""
    # Foundation
    pygame.draw.rect(surf, (100, 95, 82), (18, H - 14, W - 36, 14))

    # Main walls - pale limestone
    wall = (155, 148, 130)
    pygame.draw.rect(surf, wall, (22, 75, W - 44, H - 89))
    # Stone courses
    for y in range(75, H - 14, 10):
        pygame.draw.line(surf, (135, 128, 110), (22, y), (W - 22, y), 1)
    # Quoins (corner stones)
    for y in range(75, H - 14, 14):
        pygame.draw.rect(surf, (140, 133, 115), (22, y, 8, 13))
        pygame.draw.rect(surf, (140, 133, 115), (W - 30, y, 8, 13))

    # Main roof
    roof_col = (52, 48, 62)
    pygame.draw.polygon(surf, roof_col, [(16, 80), (W // 2, 42), (W - 16, 80)])
    # Subtle shadow on right half
    shadow = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.polygon(shadow, (0, 0, 0, 20), [(W // 2, 42), (W - 16, 80), (W // 2, 80)])
    surf.blit(shadow, (0, 0))
    pygame.draw.line(surf, (42, 38, 55), (16, 80), (W - 16, 80), 3)

    # Steeple - extends down to meet roof peak
    sx = W // 2
    steeple_top = 10
    steeple_bot = 42  # matches roof peak y
    pygame.draw.rect(surf, wall, (sx - 16, steeple_top, 32, steeple_bot - steeple_top))
    # Cornice at top of steeple body
    pygame.draw.rect(surf, (145, 138, 120), (sx - 18, steeple_top, 36, 4))
    pygame.draw.polygon(surf, roof_col, [(sx - 20, steeple_top + 2), (sx, -10), (sx + 20, steeple_top + 2)])
    # Steeple window - centered in body
    sw_cy = steeple_top + (steeple_bot - steeple_top) // 2
    pygame.draw.rect(surf, (40, 35, 50), (sx - 5, sw_cy - 4, 10, 12))
    pygame.draw.ellipse(surf, (40, 35, 50), (sx - 5, sw_cy - 8, 10, 10))
    # Bell
    pygame.draw.ellipse(surf, (190, 170, 60), (sx - 3, sw_cy, 6, 6))
    pygame.draw.line(surf, (170, 150, 50), (sx, sw_cy - 4), (sx, sw_cy), 2)

    # Cross on top
    pygame.draw.rect(surf, (210, 190, 70), (sx - 2, -20, 4, 14))
    pygame.draw.rect(surf, (210, 190, 70), (sx - 6, -16, 12, 4))

    # Rose window - clean pie-segment design
    rx, ry = W // 2, 105
    rr = 18
    pygame.draw.circle(surf, (30, 25, 40), (rx, ry), rr)
    # 8 colored pie segments
    colors = [(180, 50, 50), (50, 60, 180), (180, 160, 40), (50, 150, 70),
              (160, 50, 140), (50, 140, 180), (180, 100, 40), (80, 180, 80)]
    for i, gc in enumerate(colors):
        angle = i * math.pi / 4
        next_angle = (i + 1) * math.pi / 4
        mid_r = rr * 0.65
        px = int(rx + math.cos(angle + math.pi / 8) * mid_r)
        py = int(ry + math.sin(angle + math.pi / 8) * mid_r)
        pygame.draw.circle(surf, gc, (px, py), 5)
    # Center gold piece
    pygame.draw.circle(surf, (200, 180, 80), (rx, ry), 4)
    # Lead tracery - clean spokes
    pygame.draw.circle(surf, (65, 58, 52), (rx, ry), rr, 2)
    pygame.draw.circle(surf, (65, 58, 52), (rx, ry), rr // 2, 1)
    for i in range(8):
        angle = i * math.pi / 4
        ex = int(rx + math.cos(angle) * rr)
        ey = int(ry + math.sin(angle) * rr)
        pygame.draw.line(surf, (65, 58, 52), (rx, ry), (ex, ey), 1)

    # Tall narrow side windows with stained glass
    for wx in [36, W - 48]:
        pygame.draw.rect(surf, (35, 30, 48), (wx, 100, 12, 30))
        pygame.draw.ellipse(surf, (35, 30, 48), (wx, 94, 12, 14))
        pygame.draw.rect(surf, (160, 50, 50), (wx + 2, 104, 8, 12))
        pygame.draw.rect(surf, (50, 50, 160), (wx + 2, 116, 8, 12))
        pygame.draw.rect(surf, (55, 50, 52), (wx, 100, 12, 30), 2)

    # Grand entrance - pointed gothic arch double door
    dx = W // 2 - 18
    dw, dh = 36, 45
    pygame.draw.rect(surf, (60, 38, 25), (dx, H - dh - 14, dw, dh))
    pygame.draw.polygon(surf, (60, 38, 25), [(dx, H - dh - 14), (dx + dw // 2, H - dh - 26), (dx + dw, H - dh - 14)])
    # Door panels
    pygame.draw.rect(surf, (72, 48, 30), (dx + 3, H - dh - 10, dw // 2 - 4, dh - 6))
    pygame.draw.rect(surf, (72, 48, 30), (dx + dw // 2 + 1, H - dh - 10, dw // 2 - 4, dh - 6))
    # Handles
    pygame.draw.circle(surf, (200, 180, 70), (dx + dw // 2 - 4, H - 34), 3)
    pygame.draw.circle(surf, (200, 180, 70), (dx + dw // 2 + 4, H - 34), 3)
    # Steps
    pygame.draw.rect(surf, (120, 115, 100), (dx - 4, H - 16, dw + 8, 4))
    pygame.draw.rect(surf, (115, 108, 95), (dx - 8, H - 12, dw + 16, 4))


def draw_general_store(surf):
    """Wide storefront with porch, awning, display window, barrel and crates."""
    # Porch floor
    pygame.draw.rect(surf, (95, 72, 48), (0, H - 18, W, 18))
    for px in range(0, W, 16):
        pygame.draw.line(surf, (80, 60, 38), (px, H - 18), (px, H), 1)

    # Main walls
    wall = (135, 105, 68)
    pygame.draw.rect(surf, wall, (6, 52, W - 12, H - 70))
    # Horizontal plank lines
    for y in range(52, H - 18, 7):
        shade = 120 + (y % 14) * 3
        pygame.draw.line(surf, (shade, shade - 25, shade - 50), (6, y), (W - 6, y), 1)

    # Porch posts
    for px in [10, W - 18]:
        pygame.draw.rect(surf, (90, 65, 38), (px, 90, 8, H - 108))
        pygame.draw.rect(surf, (100, 75, 45), (px - 1, 90, 10, 4))
        pygame.draw.rect(surf, (100, 75, 45), (px - 1, H - 22, 10, 4))

    # Porch roof / awning - clean stripes
    awning_y = 90
    pygame.draw.rect(surf, (150, 55, 35), (0, awning_y, W, 12))
    for ax in range(0, W, 14):
        pygame.draw.rect(surf, (190, 175, 145), (ax, awning_y, 7, 12))

    # Main roof - solid with shadow for depth
    pygame.draw.polygon(surf, (155, 55, 32), [(0, 56), (W // 2, 14), (W, 56)])
    shadow_pts = [(W // 2, 14), (W, 56), (W // 2, 56)]
    shadow = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.polygon(shadow, (0, 0, 0, 25), shadow_pts)
    surf.blit(shadow, (0, 0))
    pygame.draw.line(surf, (130, 42, 22), (0, 56), (W, 56), 3)

    # Store sign - solid colored board, no fake text
    sign_y = 56
    pygame.draw.rect(surf, (45, 32, 18), (20, sign_y, W - 40, 16))
    pygame.draw.rect(surf, (175, 155, 95), (23, sign_y + 2, W - 46, 12), border_radius=2)
    # Border detail on sign
    pygame.draw.rect(surf, (140, 120, 70), (23, sign_y + 2, W - 46, 12), 1, border_radius=2)

    # Large display window with items
    wx, wy = 30, 105
    ww = W - 60
    pygame.draw.rect(surf, (30, 28, 20), (wx, wy, ww, 34))
    glow = pygame.Surface((ww, 34), pygame.SRCALPHA)
    glow.fill((255, 235, 180, 75))
    surf.blit(glow, (wx, wy))
    pygame.draw.rect(surf, (90, 65, 38), (wx, wy, ww, 34), 3)
    # Window dividers
    pygame.draw.line(surf, (90, 65, 38), (wx + ww // 3, wy), (wx + ww // 3, wy + 34), 2)
    pygame.draw.line(surf, (90, 65, 38), (wx + 2 * ww // 3, wy), (wx + 2 * ww // 3, wy + 34), 2)
    # Items in window - varied shapes
    items = [
        (wx + 8, (180, 120, 60), 14, 16),
        (wx + 52, (60, 120, 180), 12, 14),
        (wx + 95, (180, 60, 60), 10, 18),
    ]
    for ix, ic, iw, ih in items:
        iy = wy + 34 - ih - 3
        pygame.draw.rect(surf, ic, (ix, iy, iw, ih))
        pygame.draw.rect(surf, (min(ic[0] + 40, 255), min(ic[1] + 40, 255), min(ic[2] + 40, 255)),
                        (ix + 1, iy + 1, iw - 2, 4))

    # Door with window inset
    dx = W // 2 - 16
    pygame.draw.rect(surf, (90, 60, 28), (dx, H - 55, 32, 37))
    pygame.draw.rect(surf, (105, 72, 34), (dx + 3, H - 52, 26, 34))
    # Door window
    pygame.draw.rect(surf, (35, 30, 22), (dx + 6, H - 48, 20, 14))
    glow_dw = pygame.Surface((20, 14), pygame.SRCALPHA)
    glow_dw.fill((255, 230, 170, 80))
    surf.blit(glow_dw, (dx + 6, H - 48))
    pygame.draw.rect(surf, (80, 55, 30), (dx + 6, H - 48, 20, 14), 1)
    pygame.draw.circle(surf, (200, 170, 70), (dx + 24, H - 32), 3)

    # Barrel on porch - clearer shape
    bx, by = W - 44, H - 42
    pygame.draw.ellipse(surf, (110, 80, 42), (bx, by, 26, 24))
    pygame.draw.ellipse(surf, (120, 88, 48), (bx + 2, by - 2, 22, 8))
    # Barrel bands
    pygame.draw.line(surf, (75, 75, 78), (bx + 2, by + 6), (bx + 24, by + 6), 2)
    pygame.draw.line(surf, (75, 75, 78), (bx + 2, by + 16), (bx + 24, by + 16), 2)
    # Staves
    pygame.draw.line(surf, (95, 68, 35), (bx + 8, by + 2), (bx + 8, by + 22), 1)
    pygame.draw.line(surf, (95, 68, 35), (bx + 18, by + 2), (bx + 18, by + 22), 1)

    # Stacked crates
    cx, cy = 14, H - 40
    pygame.draw.rect(surf, (140, 110, 58), (cx, cy, 20, 18))
    pygame.draw.line(surf, (110, 80, 40), (cx, cy + 9), (cx + 20, cy + 9), 1)
    pygame.draw.line(surf, (110, 80, 40), (cx + 10, cy), (cx + 10, cy + 18), 1)
    # Upper crate
    pygame.draw.rect(surf, (130, 100, 52), (cx + 3, cy - 16, 16, 16))
    pygame.draw.line(surf, (100, 72, 38), (cx + 11, cy - 16), (cx + 11, cy), 1)

    # Sack leaning against crate
    pygame.draw.ellipse(surf, (160, 145, 100), (cx + 22, cy + 2, 14, 16))
    pygame.draw.line(surf, (130, 115, 75), (cx + 29, cy + 2), (cx + 29, cy + 6), 2)


def draw_town_hall(surf):
    """Grand civic building with columns, clock tower, and ornate pediment."""
    # Grand stone steps
    pygame.draw.rect(surf, (115, 108, 92), (8, H - 10, W - 16, 10))
    pygame.draw.rect(surf, (110, 103, 88), (4, H - 14, W - 8, 6))
    pygame.draw.rect(surf, (105, 98, 84), (0, H - 18, W, 6))

    # Main walls - dressed stone
    wall = (148, 138, 118)
    pygame.draw.rect(surf, wall, (16, 72, W - 32, H - 86))
    for y in range(72, H - 14, 10):
        pygame.draw.line(surf, (130, 120, 100), (16, y), (W - 16, y), 1)

    # Columns (4)
    col_positions = [26, 58, W - 70, W - 38]
    for cx in col_positions:
        # Shaft
        pygame.draw.rect(surf, (165, 155, 135), (cx, 78, 12, H - 96))
        # Fluting
        pygame.draw.line(surf, (175, 165, 145), (cx + 3, 84), (cx + 3, H - 22), 1)
        pygame.draw.line(surf, (155, 145, 125), (cx + 9, 84), (cx + 9, H - 22), 1)
        # Capital
        pygame.draw.rect(surf, (175, 165, 145), (cx - 3, 72, 18, 6))
        pygame.draw.rect(surf, (170, 160, 140), (cx - 2, 76, 16, 3))
        # Base
        pygame.draw.rect(surf, (170, 160, 140), (cx - 2, H - 20, 16, 4))
        pygame.draw.rect(surf, (175, 165, 145), (cx - 3, H - 18, 18, 4))

    # Entablature
    pygame.draw.rect(surf, (155, 145, 125), (12, 68, W - 24, 6))
    pygame.draw.rect(surf, (165, 155, 135), (10, 66, W - 20, 4))

    # Pediment - clean triangle
    ped_y = 68
    pygame.draw.polygon(surf, (145, 135, 115), [(10, ped_y), (W // 2, 30), (W - 10, ped_y)])
    pygame.draw.polygon(surf, (135, 125, 105), [(14, ped_y), (W // 2, 34), (W - 14, ped_y)], 2)
    # Simple shield/crest ornament in pediment instead of laurel wreath dots
    shield_cx, shield_cy = W // 2, 50
    pygame.draw.polygon(surf, (165, 155, 135),
                        [(shield_cx - 8, shield_cy - 8),
                         (shield_cx + 8, shield_cy - 8),
                         (shield_cx + 8, shield_cy + 4),
                         (shield_cx, shield_cy + 10),
                         (shield_cx - 8, shield_cy + 4)])
    pygame.draw.polygon(surf, (140, 130, 110),
                        [(shield_cx - 8, shield_cy - 8),
                         (shield_cx + 8, shield_cy - 8),
                         (shield_cx + 8, shield_cy + 4),
                         (shield_cx, shield_cy + 10),
                         (shield_cx - 8, shield_cy + 4)], 2)
    # Shield detail - horizontal band
    pygame.draw.line(surf, (180, 170, 100), (shield_cx - 6, shield_cy), (shield_cx + 6, shield_cy), 2)

    # Clock tower - extends down to meet pediment peak
    tower_w = 34
    tx = W // 2 - tower_w // 2
    tower_top = 8
    tower_bot = ped_y
    pygame.draw.rect(surf, wall, (tx, tower_top, tower_w, tower_bot - tower_top))
    # Cornice at top
    pygame.draw.rect(surf, (155, 145, 125), (tx - 2, tower_top, tower_w + 4, 4))
    # Tower roof
    pygame.draw.polygon(surf, (55, 52, 65), [(tx - 3, tower_top + 2), (W // 2, -8), (tx + tower_w + 3, tower_top + 2)])
    # Finial
    pygame.draw.circle(surf, (200, 180, 70), (W // 2, -10), 4)

    # Clock face - centered in tower
    clock_cx = W // 2
    clock_cy = tower_top + (tower_bot - tower_top) // 2
    pygame.draw.circle(surf, (220, 210, 180), (clock_cx, clock_cy), 9)
    pygame.draw.circle(surf, (180, 170, 140), (clock_cx, clock_cy), 9, 2)
    pygame.draw.line(surf, (60, 50, 40), (clock_cx, clock_cy), (clock_cx, clock_cy - 6), 2)
    pygame.draw.line(surf, (60, 50, 40), (clock_cx, clock_cy), (clock_cx + 4, clock_cy + 2), 2)

    # Tall windows between columns
    for wx in [42, W - 60]:
        pygame.draw.rect(surf, (40, 36, 30), (wx, 88, 18, 38))
        glow = pygame.Surface((18, 38), pygame.SRCALPHA)
        glow.fill((255, 240, 200, 50))
        surf.blit(glow, (wx, 88))
        pygame.draw.rect(surf, (120, 110, 90), (wx, 88, 18, 38), 2)
        pygame.draw.line(surf, (120, 110, 90), (wx + 9, 88), (wx + 9, 126), 2)
        pygame.draw.line(surf, (120, 110, 90), (wx, 107), (wx + 18, 107), 2)
        # Simple cap above window
        pygame.draw.rect(surf, (155, 145, 125), (wx - 2, 86, 22, 4))

    # Grand double door with arch
    dx = W // 2 - 22
    dw, dh = 44, 50
    pygame.draw.rect(surf, (75, 48, 28), (dx, H - dh - 14, dw, dh))
    pygame.draw.ellipse(surf, (75, 48, 28), (dx, H - dh - 24, dw, 22))
    # Door panels
    for di in range(2):
        px = dx + 3 + di * (dw // 2)
        pygame.draw.rect(surf, (88, 58, 33), (px, H - dh - 10, dw // 2 - 4, dh - 6))
        # Raised panels
        pygame.draw.rect(surf, (95, 65, 38), (px + 2, H - dh - 6, dw // 2 - 8, 16), 1)
        pygame.draw.rect(surf, (95, 65, 38), (px + 2, H - 28, dw // 2 - 8, 14), 1)
    # Door handles
    pygame.draw.circle(surf, (210, 190, 80), (dx + dw // 2 - 5, H - 36), 4)
    pygame.draw.circle(surf, (210, 190, 80), (dx + dw // 2 + 5, H - 36), 4)
    pygame.draw.circle(surf, (190, 170, 60), (dx + dw // 2 - 5, H - 36), 4, 1)
    pygame.draw.circle(surf, (190, 170, 60), (dx + dw // 2 + 5, H - 36), 4, 1)

    # Lanterns on outer columns
    for lx in [col_positions[0] + 2, col_positions[-1] + 2]:
        pygame.draw.rect(surf, (100, 80, 50), (lx + 2, 80, 4, 8))
        pygame.draw.rect(surf, (100, 80, 50), (lx, 88, 10, 14), border_radius=2)
        pygame.draw.rect(surf, (255, 230, 100), (lx + 3, 90, 4, 10))


def draw_library(surf):
    """Scholarly dark brick building with gothic arched window and book motifs."""
    # Foundation
    pygame.draw.rect(surf, (72, 55, 42), (6, H - 14, W - 12, 14))
    pygame.draw.rect(surf, (82, 62, 48), (6, H - 14, W - 12, 3))

    # Main walls - dark brick
    wall = (115, 78, 58)
    pygame.draw.rect(surf, wall, (10, 55, W - 20, H - 69))
    # Brick pattern
    for row, y in enumerate(range(55, H - 14, 7)):
        off = 8 if row % 2 else 0
        for x in range(10 + off, W - 10, 16):
            bw = min(15, W - 11 - x)
            if bw > 3:
                pygame.draw.rect(surf, (88, 55, 40), (x, y, bw, 6), 1)
                pygame.draw.line(surf, (125, 88, 65), (x + 1, y + 1), (x + bw - 2, y + 1), 1)

    # Decorative brick dentils below roofline
    for ddx in range(12, W - 12, 8):
        pygame.draw.rect(surf, (100, 65, 48), (ddx, 55, 5, 4))

    # Roof - steep with tile rows
    pygame.draw.polygon(surf, (100, 42, 30), [(2, 58), (W // 2, 8), (W - 2, 58)])
    for ry in range(12, 56, 5):
        t = (ry - 8) / 50.0
        lx = int(2 + (W // 2 - 2) * (1 - t))
        rx = int(W - 2 - (W - 2 - W // 2) * (1 - t))
        shade = 90 + (ry % 10) * 4
        pygame.draw.line(surf, (shade, shade - 50, shade - 60), (lx + 2, ry), (rx - 2, ry), 1)
    pygame.draw.line(surf, (75, 30, 20), (2, 58), (W - 2, 58), 3)
    pygame.draw.line(surf, (120, 55, 38), (W // 2, 8), (2, 58), 2)
    pygame.draw.line(surf, (80, 32, 22), (W // 2, 8), (W - 2, 58), 2)
    # Ridge cap
    pygame.draw.line(surf, (130, 65, 45), (W // 2 - 3, 8), (W // 2 + 3, 8), 4)

    # Large gothic arched window
    wx, wy = W // 2 - 26, 76
    ww, wh = 52, 48
    pygame.draw.rect(surf, (28, 22, 18), (wx, wy, ww, wh))
    pygame.draw.polygon(surf, (28, 22, 18), [(wx, wy), (wx + ww // 2, wy - 16), (wx + ww, wy)])
    # Warm glow
    glow = pygame.Surface((ww, wh), pygame.SRCALPHA)
    glow.fill((255, 220, 160, 55))
    surf.blit(glow, (wx, wy))
    # Gothic tracery frame
    pygame.draw.rect(surf, (75, 52, 38), (wx, wy, ww, wh), 2)
    pygame.draw.polygon(surf, (75, 52, 38), [(wx, wy), (wx + ww // 2, wy - 16), (wx + ww, wy)], 2)
    # Mullions
    pygame.draw.line(surf, (75, 52, 38), (wx + ww // 2, wy - 14), (wx + ww // 2, wy + wh), 2)
    pygame.draw.line(surf, (75, 52, 38), (wx, wy + wh // 2), (wx + ww, wy + wh // 2), 2)

    # Books visible on windowsill
    book_colors = [(170, 40, 35), (35, 55, 140), (50, 120, 55), (150, 120, 30), (140, 40, 100)]
    for i, bc in enumerate(book_colors):
        bx = wx + 5 + i * 9
        pygame.draw.rect(surf, bc, (bx, wy + wh - 16, 7, 14))
        pygame.draw.line(surf, (min(bc[0] + 50, 255), min(bc[1] + 50, 255), min(bc[2] + 50, 255)),
                        (bx + 1, wy + wh - 15), (bx + 1, wy + wh - 3), 1)

    # Small arched side windows
    for swx in [18, W - 36]:
        pygame.draw.rect(surf, (30, 24, 20), (swx, 92, 16, 24))
        pygame.draw.ellipse(surf, (30, 24, 20), (swx, 86, 16, 14))
        glow_s = pygame.Surface((16, 24), pygame.SRCALPHA)
        glow_s.fill((255, 220, 160, 40))
        surf.blit(glow_s, (swx, 92))
        pygame.draw.rect(surf, (75, 52, 38), (swx, 92, 16, 24), 2)
        pygame.draw.ellipse(surf, (75, 52, 38), (swx, 86, 16, 14), 2)

    # Entrance - recessed doorway with clean arch frame
    dx, dy = W // 2 - 16, H - 54
    # Arch frame (stone surround)
    pygame.draw.rect(surf, (95, 68, 50), (dx - 4, dy - 4, 40, 44))
    pygame.draw.ellipse(surf, (95, 68, 50), (dx - 4, dy - 14, 40, 22))
    # Door recess
    pygame.draw.rect(surf, (55, 38, 25), (dx, dy, 32, 40))
    pygame.draw.ellipse(surf, (55, 38, 25), (dx, dy - 10, 32, 20))
    # Door itself
    pygame.draw.rect(surf, (68, 48, 30), (dx + 3, dy, 26, 37))
    pygame.draw.line(surf, (48, 32, 20), (dx + 16, dy), (dx + 16, dy + 37), 2)
    pygame.draw.circle(surf, (160, 130, 60), (dx + 11, dy + 20), 2)
    pygame.draw.circle(surf, (160, 130, 60), (dx + 21, dy + 20), 2)

    # Steps
    pygame.draw.rect(surf, (90, 72, 55), (dx - 4, H - 16, 40, 4))

    # Plaque next to door
    pygame.draw.rect(surf, (140, 120, 70), (dx + 36, dy + 8, 20, 12), border_radius=2)
    pygame.draw.rect(surf, (120, 100, 55), (dx + 38, dy + 10, 16, 8), border_radius=1)


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
