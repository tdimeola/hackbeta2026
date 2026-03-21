# 3D Third-Person Open Terrain Game — Design Spec

## Overview

A third-person 3D game built with Python, uv, and the Ursina engine. The player controls a character that can move around an open terrain with hills, jump, and explore an environment scattered with trees and rocks.

## Tech Stack

- **Python 3.11+** via `uv` for project/dependency management
- **Ursina** as the sole dependency (game engine)
- Single-file architecture (`main.py`)

## Game Components

### Player
- Capsule entity as placeholder geometry
- WASD movement relative to camera facing direction
- Spacebar jump with simple gravity
- Grounded detection to prevent mid-air jumps

### Third-Person Camera
- Follows behind the player at a fixed offset
- Mouse controls orbit/rotation around the player
- Smooth follow behavior

### Terrain
- Ursina's built-in terrain system with heightmap
- Procedurally generated or simple noise-based heightmap
- Provides hills and varied elevation

### Scattered Objects
- **Trees**: green cone on a brown cylinder (simple geometric shapes)
- **Rocks**: gray spheres or cubes of varying sizes
- Randomly placed across the terrain surface

### Lighting & Sky
- Directional light for sun-like illumination
- Ursina's default sky

## Controls

| Input | Action |
|-------|--------|
| W/A/S/D | Move forward/left/back/right |
| Mouse | Orbit camera around player |
| Space | Jump |
| Escape | Quit |

## Non-Goals (for now)
- Enemies or combat
- Inventory or items
- UI/HUD
- Sound
- Multiplayer
