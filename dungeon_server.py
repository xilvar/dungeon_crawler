#!/usr/bin/env python3
"""
Dungeon Crawler Server - runs the game and exposes a REST API.
"""
import json
import random
import threading
import http.server
import socketserver
import sys
import os
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dungeon_crawler import (
    Game, Player,
    create_dungeon, place_entities, compute_fov,
    ITEM_PROPS, TILE_WALL,
    MAP_WIDTH, MAP_HEIGHT, MAX_SCREEN_X, MAX_SCREEN_Y,
    MAX_DEPTH, TICK_PLAYER_REST,
    COLOR_YELLOW, COLOR_GREEN, COLOR_CYAN, COLOR_MAGENTA, COLOR_RED,
)


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
        self.lock = threading.Lock()
        self.game = None
        self.running = False
        self.clients = {}
        self.inactive_players = []
        self._next_id = 0
        self._init_game()

    def _init_game(self):
        """Initialize game in headless mode."""
        self.game = Game()
        self.game.tick = 0
        self.game.players = []
        self.game.player_visible = []

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while self.running:
            with self.lock:
                self.game.tick += 10
                self.game._process_tick()
            _sleep_ms(100)

    def stop(self):
        self.running = False

    @staticmethod
    def _random_floor_pos(dungeon):
        """Pick a random floor tile from the dungeon."""
        positions = []
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                if dungeon[y][x] != TILE_WALL:
                    positions.append((x, y))
        if not positions:
            return 10, 10
        return random.choice(positions)

    def _update_visibility(self, g):
        """Recompute visibility from all alive players."""
        g._update_visibility()

    def register_player(self):
        with self.lock:
            g = self.game
            inactive = self.inactive_players.pop(0) if self.inactive_players else None
            if inactive:
                p = inactive
                p.dead = False
                p.game_win = False
                g.players.append(p)
                pid = p._server_id
            else:
                pid = self._next_id
                self._next_id += 1
                color = self.PLAYER_COLORS[pid % len(self.PLAYER_COLORS)]
                spawn_x, spawn_y = g.levels[0]["spawn_x"], g.levels[0]["spawn_y"]
                p = Player(
                    f"Hero{pid + 1}", "@",
                    spawn_x, spawn_y,
                    color, depth=0)
                p._server_id = pid
                g.players.append(p)
            self.clients[pid] = p
            self._update_visibility(g)
            return {"client_id": pid, "player_id": pid}

    def deregister_player(self, player_id):
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

    def get_state(self, player_id=0):
        with self.lock:
            g = self.game
            if not g.players:
                return {
                    "tick": g.tick,
                    "depth": 0,
                    "view_h": MAX_SCREEN_Y - 4,
                    "view_w": MAX_SCREEN_X,
                    "start_x": 0,
                    "start_y": 0,
                    "map": [" " * MAX_SCREEN_X for _ in range(MAX_SCREEN_Y - 4)],
                    "players": [],
                    "enemies": [],
                    "items": [],
                    "messages": [("Waiting for players...", 7)],
                    "game_over": False,
                    "game_win": False,
                    "max_depth": MAX_DEPTH,
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
            view_h = MAX_SCREEN_Y - 4
            view_w = MAX_SCREEN_X
            start_x = max(0, min(target.x - view_w // 2, MAP_WIDTH - view_w))
            start_y = max(0, min(target.y - view_h // 2, MAP_HEIGHT - view_h))

            chars = []
            for sy in range(view_h):
                row = []
                for sx in range(view_w):
                    mx = sx + start_x
                    my = sy + start_y
                    row.append(g.get_char_at(mx, my, target_idx))
                chars.append(''.join(row))

            p_visible = g.player_visible[target_idx] if 0 <= target_idx < len(g.player_visible) else [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
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
                items.append({
                    "x": it["x"], "y": it["y"],
                    "kind": it["kind"],
                    "char": ITEM_PROPS[it["kind"]]["char"],
                })

            player_stats = []
            for pl in g.players:
                visible_to_me = p_visible[pl.y][pl.x] if pl.depth == depth else False
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
                    "visible": visible_to_me,
                }
                if pl.rest_end_tick and g.tick < pl.rest_end_tick:
                    remaining = pl.rest_end_tick - g.tick
                    ps["resting"] = True
                    ps["rest_remaining"] = remaining
                    ps["rest_total"] = TICK_PLAYER_REST
                else:
                    ps["resting"] = False
                player_stats.append(ps)

            messages = [(m[0], m[1]) for m in target.messages[-3:]]

            game_win = target.game_win
            return {
                "tick": g.tick,
                "depth": depth,
                "view_h": view_h,
                "view_w": view_w,
                "start_x": start_x,
                "start_y": start_y,
                "map": chars,
                "players": player_stats,
                "enemies": enemies,
                "items": items,
                "messages": messages,
                "game_over": g.game_over,
                "game_win": game_win,
                "max_depth": MAX_DEPTH,
            }

    def send_action(self, player_id, action):
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


class GameHandler(http.server.BaseHTTPRequestHandler):
    server_side = None  # type: GameServer | None

    def log_message(self, format, *args):
        pass  # Suppress request logging

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith('/state'):
            if self.server_side is None:
                self._send_json({"error": "no server"}, 500)
                return
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            player_id = int(params.get("player_id", [0])[0])
            state = self.server_side.get_state(player_id)
            self._send_json(state)
        elif self.path == '/health':
            self._send_json({"status": "ok"})
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path == '/action':
            if self.server_side is None:
                self._send_json({"error": "no server"}, 500)
                return
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                self._send_json({"error": "bad json"}, 400)
                return
            pid = data.get("player_id", 0)
            action = data.get("action", {})
            result = self.server_side.send_action(pid, action)
            self._send_json(result)
        elif self.path == '/register':
            if self.server_side is None:
                self._send_json({"error": "no server"}, 500)
                return
            result = self.server_side.register_player()
            self._send_json(result)
        elif self.path == '/deregister':
            if self.server_side is None:
                self._send_json({"error": "no server"}, 500)
                return
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                self._send_json({"error": "bad json"}, 400)
                return
            pid = data.get("player_id", 0)
            result = self.server_side.deregister_player(pid)
            self._send_json(result)
        else:
            self._send_json({"error": "not found"}, 404)


def _sleep_ms(ms):
    """Sleep with interruptibility."""
    import time
    time.sleep(ms / 1000.0)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9999

    gs = GameServer()

    class Handler(GameHandler):
        pass

    Handler.server_side = gs

    class ThreadedHTTPServer(socketserver.ThreadingMixIn,
                             http.server.HTTPServer):
        allow_reuse_address = True
        daemon_threads = True

    server = ThreadedHTTPServer(('0.0.0.0', port), Handler)
    print(f"Dungeon server on port {port}")

    gs.start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        gs.stop()
        server.shutdown()


if __name__ == '__main__':
    main()
