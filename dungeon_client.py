#!/usr/bin/env python3
"""Curses-based terminal client that connects to the server, renders the map
with colored overlays, and handles player input."""
import curses
import json
import sys
import time
from collections import deque
import urllib.request

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 9999

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


def fetch_state(url, player_id=0):
    """Fetch game state from server. Returns (state_dict, byte_count)."""
    req = urllib.request.Request(f"{url}/state?player_id={player_id}")
    with urllib.request.urlopen(req, timeout=1) as resp:
        raw = resp.read()
    return json.loads(raw), len(raw)


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


def register(url):
    """Register a new player on the server."""
    data = json.dumps({}).encode()
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


def render(stdscr, state, my_player_id, bandwidth=0.0):
    """Render the game map, overlays, status bar, messages, and help text."""
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()

    map_lines = state.get("map", [])
    visible_lines = state.get("visible", [])
    players = state.get("players", [])
    enemies = state.get("enemies", [])
    messages = state.get("messages", [])

    start_x = state.get("start_x", 0)
    start_y = state.get("start_y", 0)

    view_h = state.get("view_h", max_y - 4)
    for sy in range(min(view_h, max_y - 4)):
        line = map_lines[sy] if sy < len(map_lines) else ""
        vis = visible_lines[sy] if sy < len(visible_lines) else ""
        line = line.ljust(max_x)[:max_x]
        vis = vis.ljust(max_x, '0')[:max_x]
        for sx, ch in enumerate(line):
            attr = curses.A_NORMAL if vis[sx] == '1' else curses.A_DIM
            try:
                stdscr.addch(sy, sx, ord(ch), attr)
            except curses.error:
                pass

    # Overlay players with color
    for pl in players:
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

    # Overlay enemies with color
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

    # Find my player
    my_player = None
    for pl in players:
        if pl["id"] == my_player_id:
            my_player = pl
            break
    if my_player is None:
        return

    # Player status bar
    dead = " [DEAD]" if my_player["dead"] else ""
    resting = ""
    if my_player.get("resting"):
        remaining = my_player.get("rest_remaining", 0)
        total = my_player.get("rest_total", 200)
        resting = f" | Resting ({total - remaining}/{total})"
    bar = (f"{my_player['name']} | Lv{my_player['level']} | "
           f"HP {my_player['hp']}/{my_player['max_hp']} | "
           f"ATK {my_player['attack']} | DEF {my_player['defense']} | "
           f"XP {my_player['xp']}/{my_player['next_level_xp']} | "
           f"Gold {my_player['gold']}{dead}{resting}")
    try:
        stdscr.addstr(view_h, 0, bar.ljust(max_x)[:max_x])
    except curses.error:
        pass

    # Messages (last 3, right-aligned; newest in normal color, older in grey)
    msg_start = view_h + 1
    msg_end = max_y - 2  # row just above the help bar
    last_msgs = messages[-3:]
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
        f">:Down  <:Up  g:Grab  /:Rest  "
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


def main(stdscr):
    """Main event loop: register, fetch state, render, and handle input."""
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    for i in range(16):
        curses.init_pair(i + 1, i, -1)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    stdscr.timeout(100)

    host = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HOST
    port = sys.argv[2] if len(sys.argv) > 2 else str(DEFAULT_PORT)
    url = f"http://{host}:{port}"

    result = register(url)
    if "error" in result:
        print(f"Failed to register: {result['error']}")
        return
    player_id = result["player_id"]

    byte_log = deque()
    window = 3.0

    while True:
        now = time.monotonic()
        try:
            state, nbytes = fetch_state(url, player_id)
        except Exception:
            state = {
                "map": [" " * 80 for _ in range(20)],
                "players": [],
                "enemies": [],
                "corpses": [],
                "messages": [("Connecting to server...", 7)],
                "view_h": 20, "view_w": 80,
                "start_x": 0, "start_y": 0,
                "depth": 0, "max_depth": 10,
                "game_over": False, "game_win": False,
            }
            nbytes = 0

        byte_log.append((now, nbytes))
        while byte_log and now - byte_log[0][0] > window:
            byte_log.popleft()
        bandwidth = sum(b for _, b in byte_log) / window

        render(stdscr, state, player_id, bandwidth)

        if state.get("game_over") or state.get("game_win"):
            key = stdscr.getch()
            if key in (ord('q'), ord('Q'), 27):
                deregister(url, player_id)
                break
            if key == ord('n'):
                deregister(url, player_id)
                result = register(url)
                if "error" in result:
                    print(f"Failed to register: {result['error']}")
                    break
                player_id = result["player_id"]
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
        elif key == ord('/'):
            send_action(url, player_id, {"type": "rest"})


if __name__ == "__main__":
    curses.wrapper(main)
