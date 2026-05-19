# Dungeon Crawler

A multiplayer roguelike dungeon crawler with a server-client architecture. Play via the curses terminal client or the built-in web client.

## Modules

- **dungeon_messages.py** — All player-facing message strings: enemy sounds, hit messages, ambient sounds, and broadcast/tell templates.
- **dungeon_crawler.py** — Core game logic: dungeon generation, FOV, combat, entities, items, corpses, monster generators, and a text-mode renderer for debugging.
- **dungeon_server.py** — Multiplayer HTTP server that manages game state, player registration, actions, visibility-filtered state responses, smart spawn placement, and persistent save/load.
- **dungeon_client.py** — Curses-based terminal client that connects to the server, renders the map with colored overlays, handles player input, and caches hero profiles.
- **index.html** — Browser-based web client with canvas rendering, served at `/` by the server.

## Running

**Server** — requires third-party dependencies listed in `pyproject.toml`. We recommend [uv](https://docs.astral.sh/uv/) for fast, hassle-free dependency management:

```
uv sync          # installs dependencies into a .venv
uv run dungeon_server.py [port]   # default 9999
```

**Terminal Client** — no third-party dependencies beyond Python 3 and `curses` (included in the standard library on Linux/macOS; install via `python3-dev` or your package manager if missing).

```
python3 dungeon_client.py [host] [port]
```

**Web Client** — open a browser to `http://localhost:9999` while the server is running. No separate installation needed.

## Features

- **Multiplayer** — Multiple players share the same dungeon, each with independent field of view. Walk over other players to see contextual messages.
- **4 Dungeon Types** — 10 randomly generated levels, each independently chosen from four styles:
    - **Rooms** — Classic room-and-corridor dungeons with doors.
    - **Caves** — Organic caverns generated via cellular automata, with natural water pools that harbor aquatic enemies.
    - **Labyrinth** — Tight mazes built by recursive backtracking, with traps hidden in dead-end corridors.
    - **Tower** — Concentric rings of chambers connected by passages, culminating in a central boss arena (forced on the final level).
- **Field of View** — Raycasted visibility; explored-but-unseen areas render dimmed. Enemies, items, and corpses are overlaid on the map so they never leave stale characters behind.
- **Combat & Leveling** — Bump enemies to attack. Gain XP, level up, and improve stats. 37 enemy types across 8 tiers, from rats and bats to balors and dragons, plus 5 water-exclusive creatures.
- **Items** — Collect health potions, swords, shields, and gold. Walk over items, corpses, or stairs to see contextual messages.
- **Monster Generators** — Each level contains pulsing portals (`*`) that periodically spawn new enemies. Attack and destroy them to slow the onslaught; they respawn after 60 seconds at a new location.
- **Doors** — Corridor-room boundaries may have closed doors (`+`). Walk into them to open (`-`).
- **Water** — Cave levels contain water tiles (`~`) with hidden aquatic enemies: Water Mites, Water Snakes, Deep Ones, Water Elementals, and Krakens.
- **Traps** — Labyrinth levels place hidden traps (`^`) in dead-end corridors that deal damage when stepped on.
- **Corpses** — Dead players leave a `_` marker that overlays the terrain. Walk over a corpse to learn who died there and what killed them.
- **Ambient Sounds** — Hear faint sounds of other players and monsters on the same level: footsteps, combat, death, stair movement, and enemy activity. Sounds from visible players are suppressed; only hidden actions produce ambient hints.
- **Enemy Awareness** — A message announces when a new enemy or generator comes into view.
- **Smart Spawning** — New players and those arriving via stairs are placed in the nearest free tile (within 2 spaces), avoiding overlap with other players and enemies.
- **Hero Persistence** — Both clients cache hero profiles for quick re-entry. The terminal client uses `dungeon_client.json`; the web client uses browser localStorage. The server saves full game state to `dungeon_server.json` and `dungeon_players.json` periodically and on disconnect.
- **Efficient Networking** — The server sends only the visible map window with gzip compression and bit-packed visibility data. An MD5-based delta check suppresses updates when nothing has changed, keeping bandwidth low even at high poll rates. Both clients display real-time bandwidth usage.

## Controls

| Key | Action |
|---|---|
| Arrow keys / `WASD` | Move |
| `>` or `=` | Descend stairs |
| `<` or `-` | Ascend stairs |
| `g` | Grab item |
| `.` | Wait (heals HP over time, but may attract enemies) |
| `q` / `Esc` | Quit |
| `n` | New game (after death or victory) |

## Server API

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/state?player_id=<id>&full=<0\|1>` | Game state (delta or full explored map) |
| POST | `/register` | Register a new or returning player |
| POST | `/deregister` | Remove a player from the active game |
| POST | `/action` | Queue an action for a player |
| GET | `/validate?client_id=<id>` | Check if a client ID is valid |

## License

© 2025. All rights reserved.

This repository is publicly accessible but is not open source. No rights to use, reproduce, modify, or distribute this software are granted without explicit written permission from the copyright holder.
