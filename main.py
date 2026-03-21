import tkinter as tk
from PIL import Image, ImageTk
from roles import GameState
from dialog import get_npc_dialog

W, H = 1200, 750

DARK_BG  = '#0a0a1e'
PANEL_BG = '#141432'
WHITE    = '#ffffff'
GRAY     = '#6e6e6e'
DGRAY    = '#2a2a2a'
RED      = '#c83232'
GREEN    = '#32b432'
YELLOW   = '#dcc832'
CYAN     = '#32c8dc'
ORANGE   = '#dc9632'

root = tk.Tk()
root.title('Blood on the Clocktower — HackBeta 2026')
root.geometry(f'{W}x{H}')
root.resizable(False, False)

cv = tk.Canvas(root, width=W, height=H, bg=DARK_BG, highlightthickness=0)
cv.place(x=0, y=0)

_btns  = []
_anim  = None   # pending after() id for GIF animation
game   = GameState()

# ── Image loading ─────────────────────────────────────────

gif_frames  = []   # list of (ImageTk.PhotoImage, delay_ms)
night_bg    = None

def _load_images():
    global gif_frames, night_bg

    # Animated village GIF
    try:
        src = Image.open('images/bg_village.gif')
        while True:
            frame = src.copy().convert('RGB').resize((W, H), Image.LANCZOS)
            delay = src.info.get('duration', 80)
            gif_frames.append((ImageTk.PhotoImage(frame), delay))
            try:
                src.seek(src.tell() + 1)
            except EOFError:
                break
    except Exception as e:
        print(f'bg_village.gif not loaded: {e}')

    # Night PNG
    try:
        img = Image.open('images/bg_night.png').convert('RGB').resize((W, H), Image.LANCZOS)
        night_bg = ImageTk.PhotoImage(img)
    except Exception as e:
        print(f'bg_night.png not loaded: {e}')

_load_images()


def _draw_bg(image):
    """Place a background image at canvas origin."""
    if image:
        cv.create_image(0, 0, anchor='nw', image=image, tags='bg')


def _draw_village_last():
    """Draw the last GIF frame as a static background."""
    if gif_frames:
        _draw_bg(gif_frames[-1][0])


def _dim_overlay(alpha=140):
    """Semi-transparent dark overlay so text stays readable over bright backgrounds."""
    # Tkinter has no native transparency; simulate with a stipple rectangle
    cv.create_rectangle(0, 0, W, H, fill='#000000',
                        stipple='gray50', outline='', tags='overlay')


# ── Utilities ─────────────────────────────────────────────

def clear():
    global _anim
    if _anim:
        root.after_cancel(_anim)
        _anim = None
    cv.delete('all')
    cv.configure(bg=DARK_BG)
    for b in _btns:
        b.destroy()
    _btns.clear()


def _animate_gif(idx=0):
    """Advance GIF one frame; stop on the last frame."""
    global _anim
    if not gif_frames:
        return
    frame, delay = gif_frames[idx]
    cv.itemconfig('bg', image=frame)
    if idx < len(gif_frames) - 1:
        _anim = root.after(delay, _animate_gif, idx + 1)


def hc(hex_str):
    h = hex_str.replace('0x', '').replace('#', '').strip()
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f'#{r:02x}{g:02x}{b:02x}'
    except Exception:
        return '#808080'


def dark(tk_color):
    h = tk_color.lstrip('#')
    try:
        r, g, b = int(h[0:2], 16) // 4, int(h[2:4], 16) // 4, int(h[4:6], 16) // 4
        return f'#{r:02x}{g:02x}{b:02x}'
    except Exception:
        return '#1a1a1a'


def T(x, y, text, size=22, color=WHITE, bold=False, anchor='center', width=None):
    kw = dict(font=('Arial', size, 'bold' if bold else 'normal'),
              fill=color, anchor=anchor)
    if width:
        kw['width'] = width
    cv.create_text(x, y, text=text, **kw)


def panel(x1, y1, x2, y2):
    cv.create_rectangle(x1, y1, x2, y2, fill=PANEL_BG, outline='#3c3c5a', width=1)


def mkbtn(text, x, y, w=220, h=52, cmd=None, bg='#004400', fg='white', size=18):
    b = tk.Button(cv, text=text, command=cmd,
                  bg=bg, fg=fg, activebackground='#226622',
                  activeforeground='white',
                  relief='flat', bd=0,
                  highlightthickness=2, highlightbackground=WHITE,
                  font=('Arial', size, 'bold'), cursor='hand2')
    b.place(x=x - w // 2, y=y - h // 2, width=w, height=h)
    _btns.append(b)
    return b


def draw_portrait(player, cx, cy, r=40, tag=None):
    char    = player.character
    fill    = hc(char.favorite_color)
    outline = WHITE
    lw      = 3

    if not player.alive:
        cv.create_oval(cx-r, cy-r, cx+r, cy+r,
                       fill=DGRAY, outline=GRAY, width=2)
        cv.create_line(cx-r+8, cy-r+8, cx+r-8, cy+r-8, fill=RED, width=3)
        cv.create_line(cx+r-8, cy-r+8, cx-r+8, cy+r-8, fill=RED, width=3)
        cv.create_text(cx, cy+r+14, text=char.name[:14],
                       fill=GRAY, font=('Arial', 11), anchor='center')
    else:
        ov_tag  = (f'{tag}_ov',)  if tag else ()
        txt_tag = (f'{tag}_lbl',) if tag else ()
        cv.create_oval(cx-r, cy-r, cx+r, cy+r,
                       fill=fill, outline=outline, width=lw,
                       tags=ov_tag)
        if player.is_human:
            cv.create_oval(cx-10, cy-10, cx+10, cy+10,
                           fill=YELLOW, outline=YELLOW)
        cv.create_text(cx, cy+r+14, text=char.name[:14],
                       fill=WHITE, font=('Arial', 11), anchor='center',
                       tags=txt_tag)


def portraits_layout(players, cy, r=40):
    n       = len(players)
    spacing = min(175, (W - 120) // max(n, 1))
    x0      = W // 2 - (n - 1) * spacing // 2
    return [(p, x0 + i * spacing, cy) for i, p in enumerate(players)]


# ── Screens ───────────────────────────────────────────────

def show_title():
    clear()
    if gif_frames:
        _draw_bg(gif_frames[0][0])   # first frame; animation will overwrite
        _dim_overlay()
        root.after(50, _animate_gif)  # start after canvas is drawn
    T(W//2, 148, 'BLOOD ON THE CLOCKTOWER', size=46, color=YELLOW, bold=True)
    T(W//2, 222, 'HackBeta 2026  --  Into the Codeverse', size=22, color=GRAY)
    T(W//2, 282, 'Six players. One demon. Find it before the town falls.', size=18)
    T(W//2, 318, 'You are a townsfolk. Your nightly clue scales with your stats.',
      size=16, color=CYAN)
    mkbtn('START GAME', W//2, 420, w=240, h=58, cmd=show_hero_select, size=20)


def show_hero_select():
    clear()
    _draw_village_last()
    _dim_overlay()
    T(W//2, 44, 'CHOOSE YOUR HERO', size=34, color=YELLOW, bold=True)
    T(W//2, 94, 'Your stats determine the quality of your nightly clue.', size=16, color=GRAY)

    heroes = game.all_heroes[:10]
    cols   = 5
    cw, ch = 220, 128
    xs     = (W - cols * cw) // 2
    ys     = 128

    def make_cmd(hero):
        return lambda: on_hero(hero)

    for i, h in enumerate(heroes):
        col, row = i % cols, i // cols
        x  = xs + col * cw
        y  = ys + row * (ch + 8)
        fg = hc(h.favorite_color)
        bg = dark(fg)
        label = (f"{h.name}\n"
                 f"{h.personality}\n"
                 f"INT:{h.intelligence:.0f}  PWR:{h.power:.0f}  MGC:{h.magic:.0f}\n"
                 f"{h.hometown[:20]}\n"
                 f"Weak: {h.weakness[:18]}")
        b = tk.Button(cv, text=label, command=make_cmd(h),
                      bg=bg, fg='white',
                      activebackground=fg, activeforeground='white',
                      relief='flat', bd=0,
                      highlightthickness=2, highlightbackground=fg,
                      font=('Arial', 12), cursor='hand2',
                      justify='left', anchor='nw', padx=6, pady=4)
        b.place(x=x+2, y=y+2, width=cw-8, height=ch-8)
        _btns.append(b)


def on_hero(hero):
    game.setup_players(hero)
    show_night()


def show_night():
    victim = game.do_night()
    cv.configure(bg='#050514')
    clear()
    _draw_bg(night_bg)

    T(W//2,  80, f'NIGHT  {game.day}', size=46, color='#5a5ab4', bold=True)
    T(W//2, 188, 'The town falls asleep...', size=24, color=GRAY)

    if victim:
        T(W//2, 275,
          f'{victim.character.name} was found dead at dawn.',
          size=26, color=RED, bold=True)

    T(W//2, 355, game.current_clue, size=18, color=CYAN, width=860)

    mkbtn('BEGIN THE DAY', W//2, 468, w=270, h=56, cmd=show_day,
          bg='#502800', size=18)


def show_day():
    cv.configure(bg=DARK_BG)
    clear()
    _draw_village_last()
    _dim_overlay()

    alive      = game.alive_players()
    npcs_alive = game.alive_npcs()
    vname      = game.last_victim.character.name if game.last_victim else 'no one'
    dialogs    = {p.character.name: get_npc_dialog(p, vname, alive)
                  for p in npcs_alive}

    T(W//2,  30, f'DAY  {game.day}', size=32, color=YELLOW, bold=True)
    if game.last_victim:
        T(W//2,  76, f'Last night: {vname} was found dead.', size=20, color=RED)
    T(W//2, 112, f'Your clue: {game.current_clue}',
      size=16, color=CYAN, width=920)

    layout = portraits_layout(alive, cy=215, r=42)
    for (p, cx, cy) in layout:
        if not p.is_human and p.alive:
            tag = f'npc_{id(p)}'
            draw_portrait(p, cx, cy, r=42, tag=tag)
            def on_click(e, player=p):
                show_vote(player)
            def on_enter(e, t=tag):
                cv.itemconfig(f'{t}_ov', outline=YELLOW, width=5)
                cv.configure(cursor='hand2')
            def on_leave(e, t=tag):
                cv.itemconfig(f'{t}_ov', outline=WHITE, width=3)
                cv.configure(cursor='')
            cv.tag_bind(f'{tag}_ov',  '<Button-1>', on_click)
            cv.tag_bind(f'{tag}_lbl', '<Button-1>', on_click)
            cv.tag_bind(f'{tag}_ov',  '<Enter>', on_enter)
            cv.tag_bind(f'{tag}_ov',  '<Leave>', on_leave)
        else:
            draw_portrait(p, cx, cy, r=42)

    # Dialog panel
    py = 215 + 42 + 45
    panel(40, py, W-40, py + 215)
    T(68, py+16, 'The townspeople speak:', size=16, color=ORANGE, anchor='w')

    yl = py + 44
    for p in list(npcs_alive)[:5]:
        if p.character.name in dialogs:
            line = f'{p.character.name}: "{dialogs[p.character.name]}"'
            T(68, yl, line, size=13, color=WHITE, anchor='w', width=W - 136)
            yl += 34

    T(W//2, py + 225,
      'Click a townsperson to nominate them for execution.',
      size=15, color=GRAY)

    human = game.human_player()
    T(18, H-24, f'YOU: {human.character.name}  (star)', size=13, color=YELLOW, anchor='w')


def show_vote(nominated):
    clear()
    char  = nominated.character
    color = hc(char.favorite_color)

    T(W//2,  70, 'NOMINATE FOR EXECUTION', size=34, color=RED, bold=True)

    cx, cy = W//2, 250
    cv.create_oval(cx-82, cy-82, cx+82, cy+82, fill=color, outline=WHITE, width=4)
    if nominated.is_human:
        cv.create_oval(cx-12, cy-12, cx+12, cy+12, fill=YELLOW, outline=YELLOW)

    T(W//2, 352, char.name,                       size=28, bold=True)
    T(W//2, 392, char.personality,                size=18, color=CYAN)
    T(W//2, 422, f'From: {char.hometown}',        size=16, color=GRAY)
    T(W//2, 452, f'Weakness: {char.weakness}',    size=16, color='#b45050')
    T(W//2, 500, 'Shall the town execute this person?', size=17, color=ORANGE)

    def do_execute():
        won = game.do_vote(nominated)
        show_execution_result(won, nominated)

    mkbtn('EXECUTE', W//2 - 140, 558, w=200, h=54, cmd=do_execute, bg='#780000', size=18)
    mkbtn('CANCEL',  W//2 + 140, 558, w=200, h=54, cmd=show_day,   bg='#282828', size=18)


def show_execution_result(won, executed):
    clear()
    char = executed.character

    if won:
        T(W//2,  90, 'DEMON SLAIN!',                  size=48, color=YELLOW, bold=True)
        T(W//2, 180, f'{char.name} was the demon!',   size=28, color=RED)
        T(W//2, 228, 'The town is saved.',             size=22, color=GREEN)
        T(W//2, 274, f'Evilness: {char.evilness:.0f}  |  Power: {char.power:.0f}',
          size=16, color=GRAY)
    else:
        T(W//2,  90, 'INNOCENT EXECUTED',              size=44, color=RED, bold=True)
        T(W//2, 180, f'{char.name} was not the demon.', size=26, color=ORANGE)
        if game.phase == 'lose':
            T(W//2, 234, 'The demon wins. The town is lost.', size=22, color=RED)
            dc = game.demon().character
            T(W//2, 278, f'The demon was: {dc.name} ({dc.hometown})',
              size=16, color='#b45050')
        else:
            T(W//2, 234, 'The hunt continues...', size=22, color=GRAY)

    if game.phase == 'win':
        next_cmd, label = show_win,  'SEE RESULTS'
    elif game.phase == 'lose':
        next_cmd, label = show_lose, 'SEE RESULTS'
    else:
        next_cmd, label = show_night, 'NEXT NIGHT'

    mkbtn(label, W//2, 395, w=240, h=56, cmd=next_cmd, bg='#004400', size=18)


def show_win():
    clear()
    human = game.human_player()
    T(W//2, 138, 'YOU WIN!',                                  size=56, color=YELLOW, bold=True)
    T(W//2, 228, 'The Codeverse is saved.',                   size=28, color=GREEN)
    T(W//2, 282, f'{human.character.name} has defeated the demon!', size=20)
    T(W//2, 342, 'THE INFINITY CODEX IS YOURS',               size=28, color=YELLOW, bold=True)
    mkbtn('PLAY AGAIN', W//2, 460, w=240, h=56, cmd=restart, bg='#005000', size=20)


def show_lose():
    cv.configure(bg='#120000')
    clear()
    dc = game.demon().character
    T(W//2, 138, 'GAME OVER',                           size=52, color=RED, bold=True)
    T(W//2, 228, 'The demon wins. Darkness falls.',     size=26, color=GRAY)
    T(W//2, 282, f'The demon was: {dc.name}',           size=22, color='#c85050')
    T(W//2, 322, f'From {dc.hometown}  |  Evilness: {dc.evilness:.0f}',
      size=16, color=GRAY)
    mkbtn('TRY AGAIN', W//2, 430, w=240, h=56, cmd=restart, bg='#500000', size=20)


def restart():
    global game
    game = GameState()
    show_title()


# ── Run ───────────────────────────────────────────────────
show_title()
root.mainloop()
