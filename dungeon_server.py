#!/usr/bin/env python3
"""Multiplayer HTTP server that manages game state, player registration,
actions, visibility-filtered state responses, and smart spawn placement."""
import asyncio
import json
import os
import sys
import threading
import time
import uuid

from aiohttp import web
import gzip

PLAYER_TIMEOUT = 30  # seconds of inactivity before considering a player disconnected

from dungeon_crawler import (
    COLOR_CYAN,
    COLOR_GREEN,
    COLOR_MAGENTA,
    COLOR_RED,
    COLOR_YELLOW,
    Game,
    ITEM_PROPS,
    MAP_HEIGHT,
    MAP_WIDTH,
    MAX_DEPTH,
    MAX_SCREEN_X,
    MAX_SCREEN_Y,
    Player,
)

SAVE_PATH = "dungeon_server.json"
PLAYERS_SAVE_PATH = "dungeon_players.json"


def json_response(data, request=None, **kwargs):
    """Return a JSON response."""
    body = json.dumps(data).encode()
    return web.Response(body=body, content_type="application/json", **kwargs)


class GameServer:
    """Thread-safe wrapper around the game state."""

    PLAYER_COLORS = [
        COLOR_YELLOW,
        COLOR_GREEN,
        COLOR_CYAN,
        COLOR_MAGENTA,
        COLOR_RED,
    ]

    def __init__(self):
        """Initialize the server with a fresh game instance."""
        self.lock = threading.RLock()
        self.game = None
        self.running = False
        self.clients = {}
        self.inactive_players = []
        self._last_state_tick = {}
        self._last_activity = {}
        self._next_internal_id = 0
        self._init_game()

    def _init_game(self):
        """Initialize game in headless mode, loading from file if available."""
        if not self._load_state():
            self.game = Game()
            self.game.tick = 0
            self.game.players = []
            self.game.player_visible = []

    @staticmethod
    def _pack_explored(grid):
        """Pack a 2D boolean grid into lists of 32-bit integers."""
        packed = []
        for row in grid:
            row_words = []
            for i in range((len(row) + 31) // 32):
                word = 0
                for j in range(32):
                    if i * 32 + j < len(row) and row[i * 32 + j]:
                        word |= (1 << j)
                row_words.append(word)
            packed.append(row_words)
        return packed

    @staticmethod
    def _unpack_explored(packed, width):
        """Unpack lists of 32-bit integers into a 2D boolean grid."""
        grid = []
        for row_words in packed:
            row = []
            for word_idx, word in enumerate(row_words):
                for j in range(32):
                    pos = word_idx * 32 + j
                    if pos < width:
                        row.append(bool((word >> j) & 1))
            grid.append(row)
        return grid

    def _save_state(self):
        """Serialize game state to JSON file."""
        def serialize_player(p):
            return {
                "name": p.name, "char": p.char,
                "x": p.x, "y": p.y, "depth": p.depth,
                "hp": p.hp, "max_hp": p.max_hp,
                "attack": p.attack, "defense": p.defense,
                "level": p.level, "xp": p.xp,
                "next_level_xp": p.next_level_xp,
                "weapon_bonus": p.weapon_bonus,
                "armor_bonus": p.armor_bonus,
                "gold": p.gold,
                "dead": p.dead, "game_win": p.game_win,
                "server_id": getattr(p, "_server_id", 0),
                "client_id": getattr(p, "_client_id", None),
                "next_tick": p.next_tick,
                "explored": {int(d): self._pack_explored(grid)
                             for d, grid in p.explored.items()},
            }

        state = {
            "tick": self.game.tick,
            "next_internal_id": self._next_internal_id,
            "levels": {},
            "last_state_tick": self._last_state_tick,
        }
        for depth, lvl in self.game.levels.items():
            state["levels"][depth] = {
                "dungeon": lvl["dungeon"],
                "enemies": lvl["enemies"],
                "items": lvl["items"],
                "corpses": lvl["corpses"],
                "generators": lvl.get("generators", []),
                "tick": lvl["tick"],
                "spawn_x": lvl["spawn_x"],
                "spawn_y": lvl["spawn_y"],
                "stairs_down_x": lvl["stairs_down_x"],
                "stairs_down_y": lvl["stairs_down_y"],
                "stairs_up_x": lvl["stairs_up_x"],
                "stairs_up_y": lvl["stairs_up_y"],
            }
        try:
            with open(SAVE_PATH, 'w') as f:
                json.dump(state, f)
        except OSError:
            pass

        player_state = {
            "active_players": [serialize_player(p) for p in self.game.players],
            "inactive_players": [serialize_player(p) for p in self.inactive_players],
        }
        try:
            with open(PLAYERS_SAVE_PATH, 'w') as f:
                json.dump(player_state, f)
        except OSError:
            pass

    def _load_state(self):
        """Restore game state from JSON file."""
        try:
            with open(SAVE_PATH, 'r') as f:
                state = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return False

        self.game = Game()
        self.game.tick = state["tick"]
        self.game.players = []
        self.game.player_visible = []
        self._next_internal_id = state["next_internal_id"]
        self._last_state_tick = state.get("last_state_tick", {})

        # Restore levels
        self.game.levels = {}
        for depth_str, lvl in state["levels"].items():
            depth = int(depth_str)
            self.game.levels[depth] = lvl

        def deserialize_player(pd):
            p = Player(pd["name"], pd["char"], pd["x"], pd["y"],
                       depth=pd["depth"])
            p.hp = pd["hp"]
            p.max_hp = pd["max_hp"]
            p.attack = pd["attack"]
            p.defense = pd["defense"]
            p.level = pd["level"]
            p.xp = pd["xp"]
            p.next_level_xp = pd["next_level_xp"]
            p.weapon_bonus = pd["weapon_bonus"]
            p.armor_bonus = pd["armor_bonus"]
            p.gold = pd["gold"]
            p.dead = pd["dead"]
            p.game_win = pd["game_win"]
            p._server_id = pd["server_id"]
            p._client_id = pd.get("client_id")
            p.next_tick = pd["next_tick"]
            p.explored = {int(d): self._unpack_explored(grid, MAP_WIDTH)
                           for d, grid in pd.get("explored", {}).items()}
            return p

        # Restore players from separate file
        try:
            with open(PLAYERS_SAVE_PATH, 'r') as f:
                player_state = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            player_state = {"active_players": [], "inactive_players": []}

        for pd in player_state["active_players"]:
            p = deserialize_player(pd)
            self.game.players.append(p)
            if p._client_id:
                self.clients[p._client_id] = p

        for pd in player_state["inactive_players"]:
            p = deserialize_player(pd)
            self.inactive_players.append(p)

        self._update_visibility(self.game)
        return True

    def start(self):
        """Start the game loop in a background daemon thread."""
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        """Main game loop: advance ticks and process game state."""
        while self.running:
            with self.lock:
                if self.game.players:
                    self.game.tick += 1
                    self.game._process_tick()
                    if self.game.tick % 500 == 0:
                        self._save_state()
                # Detect and remove stale players
                now = time.time()
                stale = [pid for pid, t in self._last_activity.items()
                         if now - t > PLAYER_TIMEOUT]
                for pid in stale:
                    self.deregister_player(pid)
            time.sleep(0.01)

    def stop(self):
        """Signal the game loop thread to stop."""
        self.running = False

    def _update_visibility(self, g):
        """Recompute visibility from all alive players."""
        g._update_visibility()

    def register_player(self, client_id=None, name=None):
        """Register a new (or returning) player.

        If client_id is provided and matches an inactive player, re-activate them.
        Returns {"client_id": uuid, "player_id": uuid}.
        """
        with self.lock:
            g = self.game
            inactive = None
            if client_id:
                for i, candidate in enumerate(self.inactive_players):
                    if getattr(candidate, '_client_id', None) == client_id \
                            and not candidate.dead and not candidate.game_win:
                        inactive = self.inactive_players.pop(i)
                        break
                if not inactive:
                    for i, candidate in enumerate(g.players):
                        if getattr(candidate, '_client_id', None) == client_id \
                                and not candidate.dead and not candidate.game_win:
                            inactive = g.players.pop(i)
                            break
                if not inactive:
                    return {"error": "player not found"}
            client_id = client_id or str(uuid.uuid4())
            if inactive:
                p = inactive
                p._client_id = client_id
                g.players.append(p)
            else:
                internal_id = self._next_internal_id
                self._next_internal_id += 1
                color = self.PLAYER_COLORS[internal_id % len(self.PLAYER_COLORS)]
                spawn_x, spawn_y = (
                    g.levels[0]["spawn_x"],
                    g.levels[0]["spawn_y"])
                hero_name = name or f"Hero{internal_id + 1}"
                p = Player(
                    hero_name, "@",
                    spawn_x, spawn_y,
                    color, depth=0)
                p._server_id = internal_id
                p._client_id = client_id
                g.players.append(p)
                p.x, p.y = g._find_open_spawn(
                    spawn_x, spawn_y, 0, exclude_player=p)
            self.clients[client_id] = p
            self._last_state_tick[client_id] = 0
            self._last_activity[client_id] = time.time()
            self._update_visibility(g)
            g._update_explored()
            g.game_over = False
            return {"client_id": client_id, "player_id": client_id}

    def deregister_player(self, player_id):
        """Remove a player from the active game.

        Keeps their state for re-entry.
        """
        with self.lock:
            g = self.game
            target = self.clients.get(player_id)
            if target is not None:
                target_idx = None
                for i, pl in enumerate(g.players):
                    if pl is target:
                        target_idx = i
                        break
                if target_idx is not None:
                    self.inactive_players.append(target)
                    g.players.pop(target_idx)
                    self._update_visibility(g)
                self.clients.pop(player_id, None)
                self._last_state_tick.pop(player_id, None)
                self._last_activity.pop(player_id, None)
                self._save_state()
                return {"ok": True}
            return {"error": "player not found"}

    def get_state(self, player_id=0, full=False):
        """Return the visibility-filtered game state for the given player.

        When full is True, sends the complete explored map.
        When full is False, sends only the bounding box of visible tiles.
        """
        with self.lock:
            self._last_activity[player_id] = time.time()
            g = self.game
            if not g.players:
                return {
                    "tick": g.tick,
                    "depth": 0,
                    "map_x": 0,
                    "map_y": 0,
                    "map_w": MAX_SCREEN_X,
                    "map_h": MAX_SCREEN_Y - 4,
                    "map": [
                        " " * MAX_SCREEN_X
                        for _ in range(MAX_SCREEN_Y - 4)
                    ],
                    "visible": [
                        "0" * ((MAX_SCREEN_X + 3) // 4)
                        for _ in range(MAX_SCREEN_Y - 4)
                    ],
                    "players": [],
                    "enemies": [],
                    "items": [],
                    "corpses": [],
                    "messages": [("Waiting for players...", 7)],
                    "game_over": False,
                    "game_win": False,
                    "max_depth": MAX_DEPTH,
                   "map_width": MAP_WIDTH,
                    "map_height": MAP_HEIGHT,
                }
            target = self.clients.get(player_id)
            target_idx = None
            if target:
                for i, pl in enumerate(g.players):
                    if pl is target:
                        target_idx = i
                        break
            if target is None:
                target_idx = 0
                target = g.players[target_idx]

            p_visible = (
                g.player_visible[target_idx]
                if 0 <= target_idx < len(g.player_visible)
                else [[False] * MAP_WIDTH
                      for _ in range(MAP_HEIGHT)]
            )

            if full:
                map_x, map_y = 0, 0
                map_w, map_h = MAP_WIDTH, MAP_HEIGHT
            else:
                min_x, min_y = MAP_WIDTH, MAP_HEIGHT
                max_x, max_y = -1, -1
                for y in range(MAP_HEIGHT):
                    for x in range(MAP_WIDTH):
                        if p_visible[y][x]:
                            if x < min_x:
                                min_x = x
                            if x > max_x:
                                max_x = x
                            if y < min_y:
                                min_y = y
                            if y > max_y:
                                max_y = y
                if max_x < 0:
                    min_x = min_y = max_x = max_y = 0
                map_x = min_x
                map_y = min_y
                map_w = max_x - min_x + 1
                map_h = max_y - min_y + 1

            chars = []
            visible_hex = []
            hex_digits = (map_w + 3) // 4
            for sy in range(map_h):
                row = []
                vis_bits = 0
                for sx in range(map_w):
                    mx = sx + map_x
                    my = sy + map_y
                    row.append(g.get_char_at(mx, my, target_idx))
                    if p_visible[my][mx]:
                        vis_bits |= (1 << sx)
                chars.append(''.join(row))
                visible_hex.append(f"{vis_bits:0{hex_digits}x}")

            depth = target.depth
            enemies = []
            for e in g._get_enemies(depth):
                if e["hp"] > 0 and p_visible[e["y"]][e["x"]]:
                    enemies.append({
                        "x": e["x"], "y": e["y"],
                        "name": e["name"], "char": e["char"],
                        "color": e["color"], "hp": e["hp"],
                        "max_hp": e["max_hp"],
                    })

            items = []
            for it in g._get_items(depth):
                if not p_visible[it["y"]][it["x"]]:
                    continue
                items.append({
                    "x": it["x"], "y": it["y"],
                    "kind": it["kind"],
                    "char": ITEM_PROPS[it["kind"]]["char"],
                })

            explored_grid = target.explored.get(
                depth, [[False] * MAP_WIDTH
                        for _ in range(MAP_HEIGHT)])
            corpses = []
            for c in g._get_corpses(depth):
                if explored_grid[c["y"]][c["x"]]:
                    corpses.append({
                        "x": c["x"], "y": c["y"],
                        "char": "_",
                        "name": c["name"],
                        "level": c["level"],
                        "killer": c["killer"],
                    })

            player_stats = []
            for pl in g.players:
                if pl is target:
                    visible_to_me = True
                else:
                    visible_to_me = (
                        p_visible[pl.y][pl.x]
                        if pl.depth == depth else False
                    )
                if not visible_to_me:
                    continue
                ps = {
                    "id": pl._client_id,
                    "name": pl.name, "char": pl.char,
                    "color": pl.color,
                    "x": pl.x, "y": pl.y,
                    "depth": pl.depth,
                    "hp": pl.hp, "max_hp": pl.max_hp,
                    "level": pl.level, "attack": pl.attack_total(),
                    "defense": pl.defense_total(),
                    "xp": pl.xp, "next_level_xp": pl.next_level_xp,
                    "gold": pl.gold, "dead": pl.dead,
                    "weapon_bonus": pl.weapon_bonus,
                    "armor_bonus": pl.armor_bonus,
                    "visible": True,
                }
                player_stats.append(ps)

            last_tick = self._last_state_tick.get(player_id, 0) if not full else 0
            messages = [(m[0], m[1]) for m in target.messages if m[2] > last_tick]
            if not full:
                self._last_state_tick[player_id] = g.tick

            game_win = target.game_win
            game_over = target.dead
            return {
                "tick": g.tick,
                "depth": depth,
                "map_x": map_x,
                "map_y": map_y,
                "map_w": map_w,
                "map_h": map_h,
                "map": chars,
                "visible": visible_hex,
                "players": player_stats,
                "enemies": enemies,
                "items": items,
                "corpses": corpses,
                "messages": messages,
                "game_over": game_over,
                "game_win": game_win,
                "max_depth": MAX_DEPTH,
                "map_width": MAP_WIDTH,
                "map_height": MAP_HEIGHT,
            }

    def send_action(self, player_id, action):
        """Queue an action for the given player.

        Returns {"ok": True} or an error.
        """
        with self.lock:
            self._last_activity[player_id] = time.time()
            g = self.game
            target = self.clients.get(player_id)
            if not target or target.dead:
                return {"error": "invalid player"}
            target_idx = None
            for i, pl in enumerate(g.players):
                if pl is target:
                    target_idx = i
                    break
            if target_idx is None:
                return {"error": "invalid player"}
            g.queue_player_action(target_idx, action)
            return {"ok": True}

    def validate_player(self, client_id):
        """Check if a client_id corresponds to a valid (active or inactive) player."""
        with self.lock:
            if client_id in self.clients:
                return {"valid": True}
            for p in self.inactive_players:
                if getattr(p, '_client_id', None) == client_id:
                    return {"valid": True}
            return {"valid": False}


# ---------------------------------------------------------------------------
# Async HTTP handlers
# ---------------------------------------------------------------------------

async def health(request):
    """Health check endpoint."""
    return json_response({"status": "ok"}, request)


async def get_state(request):
    """GET /state?player_id=N&full=1 — return game state.

    When full=1, sends complete explored map.
    """
    gs = request.app["gs"]
    player_id = request.query.get("player_id", "")
    full = request.query.get("full", "0") == "1"
    state = await asyncio.to_thread(gs.get_state, player_id, full=full)
    return json_response(state, request)


async def register_player(request):
    """POST /register — register a new (or returning) player."""
    gs = request.app["gs"]
    try:
        data = await request.json()
    except json.JSONDecodeError:
        data = {}
    client_id = data.get("client_id")
    name = data.get("name")
    result = await asyncio.to_thread(gs.register_player, client_id=client_id, name=name)
    return json_response(result, request)


async def deregister_player(request):
    """POST /deregister — remove a player from the active game."""
    gs = request.app["gs"]
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return json_response({"error": "bad json"}, request, status=400)
    pid = data.get("player_id", 0)
    result = await asyncio.to_thread(gs.deregister_player, pid)
    return json_response(result, request)


async def send_action(request):
    """POST /action — queue an action for a player."""
    gs = request.app["gs"]
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return json_response({"error": "bad json"}, request, status=400)
    pid = data.get("player_id", 0)
    action = data.get("action", {})
    result = await asyncio.to_thread(gs.send_action, pid, action)
    return json_response(result, request)


async def validate_player(request):
    """GET /validate?client_id=X — check if a client_id is valid."""
    gs = request.app["gs"]
    client_id = request.query.get("client_id", "")
    result = await asyncio.to_thread(gs.validate_player, client_id)
    return json_response(result, request)


async def serve_index(request):
    """Serve the web client HTML file."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "index.html")
    try:
        with open(path, "rb") as f:
            body = f.read()
    except FileNotFoundError:
        return web.Response(status=404)
    return web.Response(body=body, content_type="text/html")


def create_app():
    """Build and return the aiohttp application with routes."""
    app = web.Application()
    app.router.add_get("/", serve_index)
    app.router.add_get("/health", health)
    app.router.add_get("/state", get_state)
    app.router.add_post("/register", register_player)
    app.router.add_post("/deregister", deregister_player)
    app.router.add_post("/action", send_action)
    app.router.add_get("/validate", validate_player)
    return app


def main():
    """Start the aiohttp server and game loop.

   Uses the given port (default 9999).
   """
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9999

    gs = GameServer()
    gs.start()
    app = create_app()
    app["gs"] = gs

    async def run():
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        print(f"Dungeon server on port {port}")
        try:
            await asyncio.Event().wait()
        finally:
            await runner.cleanup()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nShutting down.")
        gs._save_state()
        gs.stop()


if __name__ == '__main__':
    main()
