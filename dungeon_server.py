#!/usr/bin/env python3
"""
Dungeon Crawler Server - runs the game and exposes a REST API.
"""
import json
import threading
import http.server
import socketserver
import sys

sys.path.insert(0, '/Users/xilvar/src/test')


class _FakeCurses:
    """Minimal curses shim for headless game."""

    COLOR_BLACK = 0
    COLOR_RED = 1
    COLOR_GREEN = 2
    COLOR_YELLOW = 3
    COLOR_BLUE = 4
    COLOR_MAGENTA = 5
    COLOR_CYAN = 6
    COLOR_WHITE = 7
    A_BOLD = 0
    A_DIM = 0
    error = Exception
    KEY_LEFT = 261
    KEY_DOWN = 258
    KEY_UP = 259
    KEY_RIGHT = 260

    def curs_set(self, *_):  # noqa: E704
        pass
    def start_color(self):  # noqa: E704
        pass
    def use_default_colors(self):  # noqa: E704
        pass
    def init_pair(self, *_):  # noqa: E704
        pass
    def nodelay(self, *_):  # noqa: E704
        pass
    def keypad(self, *_):  # noqa: E704
        pass
    def timeout(self, *_):  # noqa: E704
        pass
    def wrapper(self, func):  # noqa: E704
        return func
    def color_pair(self, n):  # noqa: E704
        return 0


# Patch curses before importing dungeon_crawler
_fake = _FakeCurses()
sys.modules['curses'] = _fake
from dungeon_crawler import (
    Game,
    ITEM_PROPS,
    MAP_WIDTH, MAP_HEIGHT, MAX_SCREEN_X, MAX_SCREEN_Y,
    MAX_DEPTH, TICK_PLAYER_REST,
)
# Restore real curses
import curses as _real_curses
sys.modules['curses'] = _real_curses


class GameServer:
    """Thread-safe wrapper around the game state."""

    def __init__(self):
        self.lock = threading.Lock()
        self.game = None
        self.running = False
        self._init_game()

    def _init_game(self):
        """Initialize game with a dummy curses screen."""
        fake_curses = _FakeCurses()
        self.game = Game(fake_curses)
        self.game.tick = 0

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

    def get_state(self):
        with self.lock:
            g = self.game
            if not g.players:
                return {"error": "no game"}
            p = g.players[0]
            view_h = MAX_SCREEN_Y - 4
            view_w = MAX_SCREEN_X
            start_x = max(0, min(p.x - view_w // 2, MAP_WIDTH - view_w))
            start_y = max(0, min(p.y - view_h // 2, MAP_HEIGHT - view_h))

            chars = []
            for sy in range(view_h):
                row = []
                for sx in range(view_w):
                    mx = sx + start_x
                    my = sy + start_y
                    row.append(g.get_char_at(mx, my))
                chars.append(''.join(row))

            enemies = []
            for e in g.enemies:
                if e["hp"] > 0 and g.visible[e["y"]][e["x"]]:
                    enemies.append({
                        "x": e["x"], "y": e["y"],
                        "name": e["name"], "char": e["char"],
                        "color": e["color"], "hp": e["hp"],
                        "max_hp": e["max_hp"],
                    })

            items = []
            for it in g.items:
                items.append({
                    "x": it["x"], "y": it["y"],
                    "kind": it["kind"],
                    "char": ITEM_PROPS[it["kind"]]["char"],
                })

            player_stats = []
            for pl in g.players:
                ps = {
                    "id": g.players.index(pl),
                    "name": pl.name, "char": pl.char,
                    "color": pl.color,
                    "x": pl.x, "y": pl.y,
                    "hp": pl.hp, "max_hp": pl.max_hp,
                    "level": pl.level, "attack": pl.attack_total(),
                    "defense": pl.defense_total(),
                    "xp": pl.xp, "next_level_xp": pl.next_level_xp,
                    "gold": pl.gold, "dead": pl.dead,
                    "weapon_bonus": pl.weapon_bonus,
                    "armor_bonus": pl.armor_bonus,
                }
                if pl.rest_end_tick and g.tick < pl.rest_end_tick:
                    remaining = pl.rest_end_tick - g.tick
                    ps["resting"] = True
                    ps["rest_remaining"] = remaining
                    ps["rest_total"] = TICK_PLAYER_REST
                else:
                    ps["resting"] = False
                player_stats.append(ps)

            messages = [(m[0], m[1]) for m in g.message_log[-3:]]

            return {
                "tick": g.tick,
                "depth": g.depth,
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
                "game_win": g.game_win,
                "max_depth": MAX_DEPTH,
            }

    def send_action(self, player_id, action):
        with self.lock:
            g = self.game
            if player_id >= len(g.players) or g.players[player_id].dead:
                return {"error": "invalid player"}
            g.queue_player_action(player_id, action)
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
        if self.path == '/state':
            if self.server_side is None:
                self._send_json({"error": "no server"}, 500)
                return
            state = self.server_side.get_state()
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
