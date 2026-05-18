#!/usr/bin/env python3
"""Curses-based terminal client that connects to the server, renders the map
with colored overlays, and handles player input."""
import curses
import json
import sys
import time
from collections import deque
import urllib.request
import gzip

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 9999
MAP_WIDTH = 60
MAP_HEIGHT = 60
MAX_MSGS = 6
PLAYER_CACHE_FILE = 'dungeon_client.json'


class LocalMap:
    """Maintains a local copy of the full explored map and visibility grid."""

    def __init__(self):
        self.width = MAP_WIDTH
        self.height = MAP_HEIGHT
        self.chars = [[' '] * self.width for _ in range(self.height)]
        self.visible = [[False] * self.width for _ in range(self.height)]
        self.depth = -1

    def _resize(self, state):
        """Resize internal buffers to match server-provided map dimensions."""
        w = state.get("map_width", self.width)
        h = state.get("map_height", self.height)
        if w == self.width and h == self.height:
            return
        self.width = w
        self.height = h
        self.chars = [[' '] * w for _ in range(h)]
        self.visible = [[False] * w for _ in range(h)]

    def needs_full_update(self, depth):
        """Return True if depth changed and a full update is needed."""
        return self.depth != depth

    def merge(self, state):
        """Merge a windowed or full map update into the local grid."""
        self._resize(state)
        mx = state.get("map_x", 0)
        my = state.get("map_y", 0)
        mw = state.get("map_w", self.width)
        mh = state.get("map_h", self.height)
        map_lines = state.get("map", [])
        vis_lines = state.get("visible", [])
        for sy in range(mh):
            if sy >= self.height:
                break
            row = map_lines[sy] if sy < len(map_lines) else ""
            vis_hex = vis_lines[sy] if sy < len(vis_lines) else ""
            vis_bits = int(vis_hex, 16) if vis_hex else 0
            for sx in range(mw):
                if sx >= self.width:
                    break
                gx = sx + mx
                gy = sy + my
                if 0 <= gx < self.width and 0 <= gy < self.height:
                    self.chars[gy][gx] = row[sx] if sx < len(row) else ' '
                    self.visible[gy][gx] = bool(vis_bits & (1 << sx))
        # Clear visibility for tiles outside the received window.
        # The server's window covers all currently visible tiles,
        # so anything outside it is no longer in view.
        max_x = mx + mw
        max_y = my + mh
        for y in range(self.height):
            for x in range(self.width):
                if x < mx or x >= max_x or y < my or y >= max_y:
                    self.visible[y][x] = False


ACTION_MAP = {
    curses.KEY_LEFT: (-1, 0),
    curses.KEY_DOWN: (0, 1),
    curses.KEY_UP: (0, -1),
    curses.KEY_RIGHT: (1, 0),
    ord('a'): (-1, 0),
    ord('s'): (0, 1),
    ord('w'): (0, -1),
    ord('d'): (1, 0),
}

P1_MOVES = {
    curses.KEY_LEFT, curses.KEY_DOWN, curses.KEY_UP, curses.KEY_RIGHT,
    ord('a'), ord('s'), ord('w'), ord('d'),
}

COLOR_MAP = {
    0: curses.COLOR_BLACK,
    1: curses.COLOR_RED,
    2: curses.COLOR_GREEN,
    3: curses.COLOR_YELLOW,
    4: curses.COLOR_BLUE,
    5: curses.COLOR_MAGENTA,
    6: curses.COLOR_CYAN,
    7: curses.COLOR_WHITE,
}


def fetch_state(url, player_id=0, full=False):
    """Fetch game state from server. Returns (state_dict, byte_count)."""
    full_param = "1" if full else "0"
    req = urllib.request.Request(
        f"{url}/state?player_id={player_id}&full={full_param}",
        headers={"Accept-Encoding": "gzip"},
    )
    with urllib.request.urlopen(req, timeout=1) as resp:
        raw = resp.read()
    wire_bytes = len(raw)
    if resp.headers.get("Content-Encoding") == "gzip":
        raw = gzip.decompress(raw)
    return json.loads(raw), wire_bytes


def load_heroes():
    """Load list of heroes from local file."""
    try:
        with open(PLAYER_CACHE_FILE, 'r') as f:
            data = json.load(f)
            return data.get("heroes", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_heroes(heroes):
    """Save list of heroes to local file."""
    try:
        with open(PLAYER_CACHE_FILE, 'w') as f:
            json.dump({"heroes": heroes}, f)
    except OSError:
        pass


def validate_hero(url, player_id):
    """Check if a hero is still valid on the server."""
    try:
        req = urllib.request.Request(
            f"{url}/validate?client_id={player_id}",
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            return json.loads(resp.read()).get("valid", False)
    except Exception:
        return False


def remove_hero(player_id):
    """Remove a hero from the local file."""
    heroes = load_heroes()
    heroes = [h for h in heroes if h["player_id"] != player_id]
    save_heroes(heroes)


def add_hero(player_id, name):
    """Add or update a hero in the local file."""
    heroes = load_heroes()
    for h in heroes:
        if h["player_id"] == player_id:
            h["name"] = name
            return
    heroes.append({"player_id": player_id, "name": name})
    save_heroes(heroes)


def select_hero(url):
    """Display hero selection menu. Returns (player_id, name) or (None, None)."""
    heroes = load_heroes()
    if not heroes:
        return None, None
    # Validate cached heroes against the server
    heroes = [h for h in heroes if validate_hero(url, h["player_id"])]
    save_heroes(heroes)
    if not heroes:
        return None, None

    print("Existing heroes:")
    for i, h in enumerate(heroes):
        name = h.get("name") or f"Hero (no name)"
        print(f"  {i + 1}. {name}")

    while True:
        try:
            choice = input("Select hero (q to quit, n for new): ").strip().lower()
            if choice == 'q':
                return None, "quit"
            if choice == 'n':
                return None, None
            idx = int(choice) - 1
            if 0 <= idx < len(heroes):
                return heroes[idx]["player_id"], heroes[idx]["name"]
            else:
                print("Invalid choice.")
        except (ValueError, KeyboardInterrupt):
            print("\nCancelled.")
            return None, "quit"


def prompt_hero_name():
    """Prompt the user for a new hero name."""
    while True:
        try:
            name = input("Enter hero name: ").strip()
            if name:
                return name
            else:
                print("Name cannot be empty.")
        except KeyboardInterrupt:
            print("\nCancelled.")
            return None


def prompt_hero_name_curses(stdscr):
    """Prompt the user for a new hero name using curses."""
    max_y, max_x = stdscr.getmaxyx()
    mid = max_y // 2
    stdscr.nodelay(False)
    stdscr.keypad(False)
    try:
        stdscr.erase()
        stdscr.addstr(mid - 1, 2, "Enter hero name:")
        stdscr.addstr(mid, 2, "_" * 20)
        stdscr.refresh()

        name = ""
        cx = 22
        while True:
            ch = stdscr.getch()
            if ch in (10, 13, ord('\r')):
                return name.strip() if name.strip() else None
            elif ch in (27, ord('q'), ord('Q')):
                return None
            elif ch in (curses.KEY_BACKSPACE, 127, 8):
                if name and cx > 22:
                    name = name[:-1]
                    cx -= 1
                    stdscr.addstr(mid, cx, " ")
            elif 32 <= ch < 127 and len(name) < 20:
                name += chr(ch)
                stdscr.addch(mid, cx, ch)
                cx += 1
            stdscr.refresh()
    finally:
        stdscr.nodelay(True)
        stdscr.keypad(True)


def register(url, client_id=None, name=None):
    """Register a new player on the server, optionally with a cached ID."""
    payload = {}
    if client_id:
        payload["client_id"] = client_id
    if name:
        payload["name"] = name
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url + '/register',
        data=data,
        headers={'Content-Type': 'application/json'},
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            return json.loads(resp.read())
    except Exception:
        return {"error": "connection failed"}


def send_action(url, player_id, action):
    """Send a player action to the server."""
    data = json.dumps({"player_id": player_id, "action": action}).encode()
    req = urllib.request.Request(
        url + '/action',
        data=data,
        headers={'Content-Type': 'application/json'},
    )
    try:
        with urllib.request.urlopen(req, timeout=1) as resp:
            return json.loads(resp.read())
    except Exception:
        return {"error": "connection failed"}


def deregister(url, player_id):
    """Deregister a player from the server."""
    data = json.dumps({"player_id": player_id}).encode()
    req = urllib.request.Request(
        url + '/deregister',
        data=data,
        headers={'Content-Type': 'application/json'},
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            return json.loads(resp.read())
    except Exception:
        return {"error": "connection failed"}


def render(stdscr, state, local_map, my_player_id, bandwidth=0.0,
           messages=None):
    """Render the game map, overlays, status bar, messages, and help text."""
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()

    players = state.get("players", [])
    enemies = state.get("enemies", [])
    if messages is None:
        messages = state.get("messages", [])

    # Compute viewport centered on my player
    my_player = None
    for pl in players:
        if pl["id"] == my_player_id:
            my_player = pl
            break
    if my_player is None:
        return

    start_x = max(0, min(
        my_player["x"] - max_x // 2, local_map.width - max_x))
    msg_rows = max(3, (max_y - 22) // 2 + 1)
    baseline_h = max_y - msg_rows - 2
    start_y = max(0, min(
        my_player["y"] - baseline_h // 2,
        local_map.height - baseline_h))

    view_h = min(max_y - msg_rows - 2, local_map.height - start_y)
    view_w = min(max_x, local_map.width - start_x)

    for sy in range(view_h):
        gy = sy + start_y
        for sx in range(view_w):
            gx = sx + start_x
            ch = local_map.chars[gy][gx]
            attr = (
                curses.A_NORMAL
                if local_map.visible[gy][gx]
                else curses.A_DIM
            )
            try:
                stdscr.addch(sy, sx, ord(ch), attr)
            except curses.error:
                pass

    # Overlay items with color
    items = state.get("items", [])
    for it in items:
        ix = it["x"] - start_x
        iy = it["y"] - start_y
        if 0 <= iy < view_h and 0 <= ix < max_x:
            color = COLOR_MAP.get(
                {"potion": 1, "sword": 7,
                 "shield": 6, "gold": 3}.get(it["kind"], 7), 7)
            attr = curses.color_pair(min(color + 1, 16))
            try:
                stdscr.addch(iy, ix, ord(it["char"]), attr)
            except curses.error:
                pass

    # Overlay corpses (dimmed, explored but not necessarily visible)
    corpses = state.get("corpses", [])
    for c in corpses:
        cx = c["x"] - start_x
        cy = c["y"] - start_y
        if 0 <= cy < view_h and 0 <= cx < max_x:
            try:
                stdscr.addch(cy, cx, ord(c["char"]), curses.A_DIM)
            except curses.error:
                pass

    # Overlay enemies on top of items, corpses, and stairs
    for e in enemies:
        ex = e["x"] - start_x
        ey = e["y"] - start_y
        if 0 <= ey < view_h and 0 <= ex < max_x:
            color = COLOR_MAP.get(e.get("color", 1), curses.COLOR_RED)
            attr = curses.color_pair(min(color + 1, 16)) | curses.A_BOLD
            try:
                stdscr.addch(ey, ex, ord(e["char"]), attr)
            except curses.error:
                pass

    # Overlay players last so they appear on top of everything,
    # with my own character drawn last so it's never obscured
    for pl in players:
        if pl["id"] == my_player_id:
            continue
        if pl["dead"] or not pl.get("visible", True):
            continue
        px = pl["x"] - start_x
        py = pl["y"] - start_y
        if 0 <= py < view_h and 0 <= px < max_x:
            color = COLOR_MAP.get(pl.get("color", 7), curses.COLOR_WHITE)
            attr = curses.color_pair(min(color + 1, 16)) | curses.A_BOLD
            try:
                stdscr.addch(py, px, ord('@'), attr)
            except curses.error:
                pass
    if my_player and not my_player["dead"]:
        px = my_player["x"] - start_x
        py = my_player["y"] - start_y
        if 0 <= py < view_h and 0 <= px < max_x:
            color = COLOR_MAP.get(my_player.get("color", 7), curses.COLOR_WHITE)
            attr = curses.color_pair(min(color + 1, 16)) | curses.A_BOLD
            try:
                stdscr.addch(py, px, ord('@'), attr)
            except curses.error:
                pass

    # Player status bar
    dead = " [DEAD]" if my_player["dead"] else ""
    bar = (f"{my_player['name']} | Lv{my_player['level']} | "
           f"HP {my_player['hp']}/{my_player['max_hp']} | "
           f"ATK {my_player['attack']} | DEF {my_player['defense']} | "
           f"XP {my_player['xp']}/{my_player['next_level_xp']} | "
           f"Gold {my_player['gold']}{dead}")
    try:
        stdscr.addstr(view_h, 0, bar.ljust(max_x)[:max_x])
    except curses.error:
        pass

    # Messages (oldest on top in grey, newest at bottom in normal color)
    msg_start = view_h + 1
    msg_end = max_y - 2  # row just above the help bar
    last_msgs = messages[-msg_rows:]
    offset = msg_end - (msg_start + len(last_msgs) - 1)
    for j, msg in enumerate(last_msgs):
        row = msg_start + offset + j
        if row < msg_start or row > msg_end:
            continue
        attr = curses.A_DIM if j < len(last_msgs) - 1 else curses.A_NORMAL
        try:
            stdscr.addstr(row, 0, (msg[0] + " " * max_x)[:max_x], attr)
        except curses.error:
            pass

    # Help bar
    depth = state.get("depth", 0)
    max_depth = state.get("max_depth", 10)
    bw_label = f"{bandwidth / 1024:.1f} KB/s" if bandwidth > 0 else "--- KB/s"
    help_text = (
        f">:Down  <:Up  g:Grab  .:Wait  "
        f"Depth {depth + 1}/{max_depth}  q:Quit  "
        f"↓ {bw_label}"
    )
    try:
        stdscr.addstr(max_y - 1, 0, help_text.ljust(max_x)[:max_x])
    except curses.error:
        pass

    # Game over / win overlay
    if state.get("game_over"):
        try:
            stdscr.addstr(
                10, 25, "YOU HAVE DIED",
                curses.color_pair(curses.COLOR_RED + 1)
                | curses.A_BOLD)
        except curses.error:
            pass
        try:
            stdscr.addstr(11, 22, "n:New Game  q:Quit")
        except curses.error:
            pass
    elif state.get("game_win"):
        try:
            stdscr.addstr(
                10, 20, "YOU CONQUERED THE DUNGEON!",
                curses.color_pair(curses.COLOR_GREEN + 1)
                | curses.A_BOLD)
        except curses.error:
            pass
        try:
            stdscr.addstr(11, 22, "n:New Game  q:Quit")
        except curses.error:
            pass

    stdscr.refresh()


def main(stdscr, url, player_id):
    """Main event loop: register, fetch state, render, and handle input."""
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    for i in range(16):
        curses.init_pair(i + 1, i, -1)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    stdscr.timeout(100)

    local_map = LocalMap()
    local_messages = []
    byte_log = deque()
    window = 3.0
    last_state = None

    while True:
        now = time.monotonic()
        try:
            state, nbytes = fetch_state(url, player_id)
        except Exception:
            state = {
                "map_x": 0, "map_y": 0,
                "map_w": 0, "map_h": 0,
                "map": [], "visible": [],
                "players": [],
                "enemies": [],
                "corpses": [],
                "messages": [("Connecting to server...", 7)],
                "depth": 0, "max_depth": 10,
                "game_over": False, "game_win": False,
            }
            nbytes = 0

        depth = state.get("depth", 0)

        # Minimal response — nothing changed, render with last state to update bandwidth
        if "map" not in state:
            byte_log.append((now, nbytes))
            while byte_log and now - byte_log[0][0] > window:
                byte_log.popleft()
            bandwidth = sum(b for _, b in byte_log) / window
            if last_state is not None:
                render(stdscr, last_state, local_map, player_id, bandwidth,
                       local_messages)
            key = stdscr.getch()
            if key == -1:
                continue
            if key in (ord('q'), ord('Q'), 27):
                deregister(url, player_id)
                break
            if key in P1_MOVES and key in ACTION_MAP:
                dx, dy = ACTION_MAP[key]
                send_action(url, player_id, {"type": "move", "dx": dx, "dy": dy})
            elif key in (ord('>'), ord('=')):
                send_action(url, player_id, {"type": "stairs_down"})
            elif key in (ord('<'), ord('-')):
                send_action(url, player_id, {"type": "stairs_up"})
            elif key == ord('g'):
                send_action(url, player_id, {"type": "grab"})
            elif key == ord('.'):
                send_action(url, player_id, {"type": "wait"})
            continue

        full_update = local_map.needs_full_update(depth)
        if full_update:
            local_map.depth = depth
            try:
                full_state, full_bytes = fetch_state(
                    url, player_id, full=True)
                nbytes += full_bytes
                local_map.merge(full_state)
                local_messages = list(full_state.get("messages", []))
            except Exception:
                pass

        local_map.merge(state)
        new_msgs = state.get("messages", [])
        if new_msgs:
            local_messages.extend(new_msgs)
            if len(local_messages) > MAX_MSGS:
                local_messages = local_messages[-MAX_MSGS:]

        byte_log.append((now, nbytes))
        while byte_log and now - byte_log[0][0] > window:
            byte_log.popleft()
        bandwidth = sum(b for _, b in byte_log) / window

        render(stdscr, state, local_map, player_id, bandwidth,
                local_messages)
        last_state = state

        if state.get("game_over") or state.get("game_win"):
            if state.get("game_over"):
                remove_hero(player_id)
            key = stdscr.getch()
            if key in (ord('q'), ord('Q'), 27):
                deregister(url, player_id)
                break
            if key == ord('n'):
                deregister(url, player_id)
                hero_name = prompt_hero_name_curses(stdscr)
                if not hero_name:
                    break
                result = register(url, name=hero_name)
                if "error" in result:
                    break
                player_id = result["player_id"]
                add_hero(player_id, hero_name)
                local_map = LocalMap()
                local_messages = []
                last_state = None
                continue
            continue

        key = stdscr.getch()
        if key == -1:
            continue

        if key in (ord('q'), ord('Q'), 27):
            deregister(url, player_id)
            break

        if key in P1_MOVES and key in ACTION_MAP:
            dx, dy = ACTION_MAP[key]
            send_action(url, player_id, {"type": "move", "dx": dx, "dy": dy})
        elif key in (ord('>'), ord('=')):
            send_action(url, player_id, {"type": "stairs_down"})
        elif key in (ord('<'), ord('-')):
            send_action(url, player_id, {"type": "stairs_up"})
        elif key == ord('g'):
            send_action(url, player_id, {"type": "grab"})
        elif key == ord('.'):
            send_action(url, player_id, {"type": "wait"})


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HOST
    port = sys.argv[2] if len(sys.argv) > 2 else str(DEFAULT_PORT)
    url = f"http://{host}:{port}"

    cached_id, hero_name = select_hero(url)
    if hero_name == "quit":
        sys.exit(0)
    if cached_id is None and hero_name is None:
        hero_name = prompt_hero_name()
    if not hero_name:
        sys.exit(0)
    result = register(url, client_id=cached_id, name=hero_name)
    if "error" in result:
        if cached_id:
            remove_hero(cached_id)
            print(f"Hero no longer available. Creating new hero...")
            hero_name = prompt_hero_name()
            if not hero_name:
                sys.exit(0)
            result = register(url, name=hero_name)
    if "error" in result:
        print(f"Failed to register: {result['error']}")
        sys.exit(1)
    player_id = result["player_id"]
    add_hero(player_id, hero_name)

    curses.wrapper(lambda stdscr: main(stdscr, url, player_id))
