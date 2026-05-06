# Dungeon Crawler

A terminal-based roguelike dungeon crawler with multiplayer support, implemented as a server-client architecture.

## Modules

- **dungeon_messages.py** — All player-facing message strings: enemy sounds, hit messages, ambient sounds, and broadcast/tell templates.
- **dungeon_crawler.py** — Core game logic: dungeon generation, FOV, combat, entities, items, corpses, and a text-mode renderer for debugging.
- **dungeon_server.py** — Multiplayer HTTP server that manages game state, player registration, actions, visibility-filtered state responses, and smart spawn placement.
- **dungeon_client.py** — Curses-based terminal client that connects to the server, renders the map with colored overlays, and handles player input.

## Running

1. Start the server: `python3 dungeon_server.py [port]` (default port 9999)
2. Connect clients: `python3 dungeon_client.py [host] [port]`

## Features

- **Multiplayer** — Multiple players share the same dungeon, each with independent field of view.
- **Procedural Dungeons** — 10 randomly generated dungeon levels with rooms, corridors, and doors.
- **Field of View** — Raycasted visibility; explored areas remain visible as fog.
- **Combat & Leveling** — Bump enemies to attack. Gain XP, level up, and improve stats.
- **Items** — Collect health potions, swords, shields, and gold.
- **Corpses** — Dead players leave a `_` marker. Walk over a corpse to learn who died there and what killed them.
- **Ambient Sounds** — Hear faint sounds of other players and monsters on the same level: footsteps, combat, death, stair movement, and enemy activity. Sounds from visible players are suppressed; only hidden actions produce ambient hints.
- **Enemy Awareness** — A message announces when a new enemy comes into view.
- **Smart Spawning** — New players and those arriving via stairs are placed in the nearest free tile (within 2 spaces), avoiding overlap with other players and enemies.

## Controls

| Key | Action |
|---|---|
| Arrow keys / `WASD` | Move |
| `>` or `=` | Descend stairs |
| `<` or `-` | Ascend stairs |
| `g` | Grab item |
| `/` | Rest |
| `q` / `Esc` | Quit |
| `n` | New game (after death or victory) |

## License

© 2025. All rights reserved.

This repository is publicly accessible but is not open source. No rights to use, reproduce, modify, or distribute this software are granted without explicit written permission from the copyright holder.
