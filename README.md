# Dungeon Crawler

A terminal-based roguelike dungeon crawler with multiplayer support, implemented as a server-client architecture.

## Modules

- **dungeon_messages.py** — All player-facing message strings: enemy sounds, hit messages, ambient sounds, and broadcast/tell templates.
- **dungeon_crawler.py** — Core game logic: dungeon generation, FOV, combat, entities, items, corpses, monster generators, and a text-mode renderer for debugging.
- **dungeon_server.py** — Multiplayer HTTP server that manages game state, player registration, actions, visibility-filtered state responses, smart spawn placement, and persistent save/load.
- **dungeon_client.py** — Curses-based terminal client that connects to the server, renders the map with colored overlays, handles player input, and caches hero profiles.

## Running

**Server** — requires third-party dependencies listed in `pyproject.toml`. We recommend [uv](https://docs.astral.sh/uv/) for fast, hassle-free dependency management:

```
uv sync          # installs dependencies into a .venv
uv run dungeon_server.py [port]   # default 9999
```

**Client** — no third-party dependencies beyond Python 3 and `curses` (included in the standard library on Linux/macOS; install via `python3-dev` or your package manager if missing).

```
python3 dungeon_client.py [host] [port]
```

## Features

- **Multiplayer** — Multiple players share the same dungeon, each with independent field of view. Walk over other players to see contextual messages.
- **Procedural Dungeons** — 10 randomly generated dungeon levels. Each level is randomly either a room-based dungeon (with rooms, corridors, and doors) or an organic cave (generated via cellular automata).
- **Field of View** — Raycasted visibility; explored-but-unseen areas render dimmed. Enemies, items, and corpses are overlaid on the map so they never leave stale characters behind.
- **Combat & Leveling** — Bump enemies to attack. Gain XP, level up, and improve stats. 33 enemy types across 8 tiers, from rats and bats to balors and dragons.
- **Items** — Collect health potions, swords, shields, and gold. Walk over items, corpses, or stairs to see contextual messages.
- **Monster Generators** — Each level contains pulsing portals (`~`) that periodically spawn new enemies. Attack and destroy them to slow the onslaught; they respawn after 60 seconds at a new location.
- **Doors** — Corridor-room boundaries may have closed doors (`+`). Walk into them to open (`-`).
- **Corpses** — Dead players leave a `_` marker that overlays the terrain. Walk over a corpse to learn who died there and what killed them.
- **Ambient Sounds** — Hear faint sounds of other players and monsters on the same level: footsteps, combat, death, stair movement, and enemy activity. Sounds from visible players are suppressed; only hidden actions produce ambient hints.
- **Enemy Awareness** — A message announces when a new enemy or generator comes into view.
- **Smart Spawning** — New players and those arriving via stairs are placed in the nearest free tile (within 2 spaces), avoiding overlap with other players and enemies.
- **Persistent State** — The server saves game state to `dungeon_server.json` periodically and on player disconnect, allowing the dungeon to persist across server restarts. The client caches hero profiles in `dungeon_client.json` for quick re-entry.
- **Efficient Networking** — The server sends only the visible map window with gzip compression and bit-packed visibility data, keeping bandwidth low even at high poll rates. The client displays real-time bandwidth usage.

## Controls

| Key | Action |
|---|---|
| Arrow keys / `WASD` | Move |
| `>` or `=` | Descend stairs |
| `<` or `-` | Ascend stairs |
| `g` | Grab item |
| `/` | Rest (heals HP over time, but may attract enemies) |
| `q` / `Esc` | Quit |
| `n` | New game (after death or victory) |

## License

© 2025. All rights reserved.

This repository is publicly accessible but is not open source. No rights to use, reproduce, modify, or distribute this software are granted without explicit written permission from the copyright holder.
