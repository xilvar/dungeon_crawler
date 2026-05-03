# Dungeon Crawler

A terminal-based roguelike dungeon crawler with multiplayer support, implemented as a server-client architecture.

**Note:** This README must be kept up to date whenever changes are made to the project.

## Modules

- **dungeon_crawler.py** — Core game logic: dungeon generation, FOV, combat, entities, items, and a text-mode renderer for debugging.
- **dungeon_server.py** — Multiplayer HTTP server that manages game state, player registration, actions, and visibility-filtered state responses.
- **dungeon_client.py** — Curses-based terminal client that connects to the server, renders the map, and handles player input.

## Running

1. Start the server: `python3 dungeon_server.py [port]` (default port 9999)
2. Connect clients: `python3 dungeon_client.py [host] [port]`

## Controls

Arrow keys or `y/u/b/n` to move, `>`/`<` for stairs, `g` to grab items, `/` to rest, `q` to quit.
