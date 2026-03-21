# Blood on the Clocktower — HackBeta 2026

A single-player social deduction game built for the HackBeta 2026 hackathon.
Theme: *Into the Codeverse*

## Premise

Six players. One demon. You are a townsfolk in an Elizabethan village market.
Each night someone is killed. Each day you question the survivors and vote to execute.
Find the demon before the town falls.

## Requirements

- Python 3.8 or higher
- pip

## Setup

```bash
git clone https://github.com/tdimeola/hackbeta2026
cd hackbeta2026
git checkout botc-game
pip install jinja2 Pillow
python main.py
```

## How to Play

1. **Choose your hero** — your stats determine the quality of your nightly clue
2. **Night phase** — the demon kills a townsfolk; you receive a clue based on your stats
3. **Day phase** — surviving townspeople speak; some tell the truth, some lie
4. **Nominate** — click a townsperson to nominate them for execution
5. **Vote** — confirm or cancel the execution
6. **Win** by executing the demon before only 2 players remain

### Clue quality scales with your hero's stats

| Stat | Clue |
|------|------|
| Intelligence > 70 | Demon's exact weakness |
| Magic > 70 | Demon's hometown |
| Speed > 70 | Who the demon targeted |
| Power > 70 | Demon's evilness rating |
| Other | Vague — good luck |

## Files

| File | Description |
|------|-------------|
| `main.py` | Game UI (tkinter) |
| `roles.py` | Game state, night/vote logic |
| `dialog.py` | NPC speech templates (Jinja2) |
| `hero.py` | Character class and CSV loader |
| `data.csv` | Superhero dataset |
| `images/` | Background images |

## Team

HackBeta 2026 — Ole Miss
