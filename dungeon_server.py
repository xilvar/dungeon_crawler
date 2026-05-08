#!/usr/bin/env python3
"""Multiplayer HTTP server that manages game state, player registration,
actions, visibility-filtered state responses, and smart spawn placement."""
import asyncio
import json
import sys
import threading
import time

from aiohttp import web
import gzip

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
    TICK_PLAYER_REST,
)


def json_response(data, request=None, **kwargs):
    """Return a JSON response, compressed with gzip if client accepts it."""
    body = json.dumps(data).encode()
    if request and "gzip" in request.headers.get("Accept-Encoding", ""):
        compressed = gzip.compress(body, compresslevel=6)
        return web.Response(
            body=compressed,
            content_type="application/json",
            headers={
                "Content-Encoding": "gzip",
                "Content-Length": str(len(compressed)),
            },
            **kwargs,
        )
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
        self.lock = threading.Lock()
        self.game = None
        self.running = False
        self.clients = {}
        self.inactive_players = []
        self._next_id = 0
        self._last_state_tick = {}
        self._init_game()

    def _init_game(self):
        """Initialize game in headless mode."""
        self.game = Game()
        self.game.tick = 0
        self.game.players = []
        self.game.player_visible = []

    def start(self):
        """Start the game loop in a background daemon thread."""
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        """Main game loop: advance ticks and process game state."""
        while self.running:
            with self.lock:
                self.game.tick += 1
                self.game._process_tick()
            time.sleep(0.01)

    def stop(self):
        """Signal the game loop thread to stop."""
        self.running = False

    def _update_visibility(self, g):
        """Recompute visibility from all alive players."""
        g._update_visibility()

    def register_player(self):
        """Register a new (or returning) player.

        Returns {"client_id": id, "player_id": id}.
        """
        with self.lock:
            g = self.game
            inactive = None
            for i, candidate in enumerate(self.inactive_players):
                if not candidate.dead and not candidate.game_win:
                    inactive = self.inactive_players.pop(i)
                    break
            if inactive:
                p = inactive
                g.players.append(p)
                pid = p._server_id
            else:
                pid = self._next_id
                self._next_id += 1
                color = self.PLAYER_COLORS[pid % len(self.PLAYER_COLORS)]
                spawn_x, spawn_y = (
                    g.levels[0]["spawn_x"],
                    g.levels[0]["spawn_y"])
                p = Player(
                    f"Hero{pid + 1}", "@",
                    spawn_x, spawn_y,
                    color, depth=0)
                p._server_id = pid
                g.players.append(p)
                p.x, p.y = g._find_open_spawn(
                    spawn_x, spawn_y, 0, exclude_player=p)
            self.clients[pid] = p
            self._last_state_tick[pid] = 0
            self._update_visibility(g)
            g._update_explored()
            g.game_over = False
            return {"client_id": pid, "player_id": pid}

    def deregister_player(self, player_id):
        """Remove a player from the active game.

        Keeps their state for re-entry.
        """
        with self.lock:
            g = self.game
            target = None
            target_idx = None
            for i, pl in enumerate(g.players):
                if pl._server_id == player_id:
                    target = pl
                    target_idx = i
                    break
            if target is not None:
                self.inactive_players.append(target)
                g.players.pop(target_idx)
                self._update_visibility(g)
                self.clients.pop(player_id, None)
                return {"ok": True}
            return {"error": "player not found"}

    def get_state(self, player_id=0, full=False):
        """Return the visibility-filtered game state for the given player.

        When full is True, sends the complete explored map.
        When full is False, sends only the bounding box of visible tiles.
        """
        with self.lock:
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
            target = None
            target_idx = None
            for i, pl in enumerate(g.players):
                if pl._server_id == player_id:
                    target = pl
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
                    "id": pl._server_id,
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
                if pl.rest_end_tick and g.tick < pl.rest_end_tick:
                    remaining = pl.rest_end_tick - g.tick
                    ps["resting"] = True
                    ps["rest_remaining"] = remaining
                    ps["rest_total"] = TICK_PLAYER_REST
                else:
                    ps["resting"] = False
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
            g = self.game
            target_idx = None
            for i, pl in enumerate(g.players):
                if pl._server_id == player_id:
                    target_idx = i
                    if pl.dead:
                        return {"error": "invalid player"}
                    break
            if target_idx is None:
                return {"error": "invalid player"}
            g.queue_player_action(target_idx, action)
            return {"ok": True}


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
    player_id = int(request.query.get("player_id", 0))
    full = request.query.get("full", "0") == "1"
    state = await asyncio.to_thread(gs.get_state, player_id, full=full)
    return json_response(state, request)


async def register_player(request):
    """POST /register — register a new (or returning) player."""
    gs = request.app["gs"]
    result = await asyncio.to_thread(gs.register_player)
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


def create_app():
    """Build and return the aiohttp application with routes."""
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/state", get_state)
    app.router.add_post("/register", register_player)
    app.router.add_post("/deregister", deregister_player)
    app.router.add_post("/action", send_action)
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
        gs.stop()


if __name__ == '__main__':
    main()
