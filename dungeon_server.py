#!/usr/bin/env python3
"""Multiplayer HTTP server that manages game state, player registration,
actions, visibility-filtered state responses, and smart spawn placement."""
import asyncio
import hashlib
import json
import logging
import os
import queue
import sys
import threading
import time
import uuid

from aiohttp import web
import gzip

logger = logging.getLogger("dungeon_server")

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
    SHIELD_NONE,
    WEAPON_FISTS,
)

SAVE_PATH = "dungeon_server.json"
PLAYERS_SAVE_PATH = "dungeon_players.json"


def json_response(data, request=None, **kwargs):
    """Return a JSON response."""
    body = json.dumps(data).encode()
    if request and "gzip" in request.headers.get("Accept-Encoding", ""):
        body = gzip.compress(body)
        kwargs["headers"] = {"Content-Encoding": "gzip"}
        return web.Response(body=body, content_type="application/json", **kwargs)
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
        self._last_state_hash = {}
        self._last_activity = {}
        self._next_internal_id = 0
        # Snapshot of precomputed per-player views (game loop writes, handlers read)
        self._latest_views = {}
        self._views_tick = 0
        # Lock-free action queue: (player_id, action, timestamp)
        self._action_queue = queue.Queue()
        # Dict-based player lookup: client_id -> index in g.players
        self._client_to_idx = {}
        # Throttle stale/dead player cleanup
        self._last_cleanup = 0
        self._init_game()

    def _init_game(self):
        """Initialize game in headless mode, loading from file if available."""
        loaded = self._load_state()
        if not loaded:
            logger.info("Started fresh game (no save data found)")
            self.game = Game()
            self.game.tick = 0
            self.game.players = []
            self.game.player_visible = []
        else:
            logger.info("Loaded game state: tick=%d, levels=%d, active_players=%d, inactive_players=%d",
                        self.game.tick, len(self.game.levels),
                        len(self.game.players), len(self.inactive_players))

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

    def _build_player_view(self, player, player_idx):
        """Build a visibility-filtered game state view for one player.

        Called from the game loop under the lock. The resulting dict is
        stored in ``_latest_views`` so HTTP handlers can read it without
        holding the lock.
        """
        g = self.game
        depth = player.depth

        p_visible = (
            g.player_visible[player_idx]
            if 0 <= player_idx < len(g.player_visible)
            else [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
        )

        # Compute visible-window bounds
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
        map_x, map_y = min_x, min_y
        map_w, map_h = max_x - min_x + 1, max_y - min_y + 1

        # Build map characters and visibility hex
        chars = []
        visible_hex = []
        hex_digits = (map_w + 3) // 4
        for sy in range(map_h):
            row = []
            vis_bits = 0
            for sx in range(map_w):
                mx, my = sx + map_x, sy + map_y
                row.append(g.get_char_at(mx, my, player_idx))
                if p_visible[my][mx]:
                    vis_bits |= 1 << sx
            chars.append("".join(row))
            visible_hex.append(f"{vis_bits:0{hex_digits}x}")

        # Filter enemies (only visible ones)
        enemies = []
        for e in g._get_enemies(depth):
            if e["hp"] <= 0:
                continue
            if e.get("water"):
                if not e.get("visible", False):
                    continue
            else:
                if not p_visible[e["y"]][e["x"]]:
                    continue
            enemies.append(
                {"x": e["x"], "y": e["y"], "name": e["name"],
                 "char": e["char"], "color": e["color"],
                 "hp": e["hp"], "max_hp": e["max_hp"]}
            )

        # Filter items (only visible ones)
        items = []
        for it in g._get_items(depth):
            if not p_visible[it["y"]][it["x"]]:
                continue
            items.append(
                {"x": it["x"], "y": it["y"], "kind": it["kind"],
                 "char": ITEM_PROPS[it["kind"]]["char"]}
            )

        # Corpses are visible on explored tiles
        explored_grid = player.explored.get(
            depth, [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
        )
        corpses = []
        for c in g._get_corpses(depth):
            if explored_grid[c["y"]][c["x"]]:
                corpses.append(
                    {"x": c["x"], "y": c["y"], "char": "_",
                     "name": c["name"], "level": c["level"],
                     "killer": c["killer"]}
                )

        # Other players visible in FOV
        player_stats = []
        for pl in g.players:
            if pl is player:
                visible_to_me = True
            else:
                visible_to_me = (
                    p_visible[pl.y][pl.x] if pl.depth == depth else False
                )
            if not visible_to_me:
                continue
            player_stats.append({
                "id": pl._client_id, "name": pl.name, "char": pl.char,
                "color": pl.color, "x": pl.x, "y": pl.y,
                "depth": pl.depth,
                "hp": pl.hp, "max_hp": pl.max_hp,
                "level": pl.level, "attack": pl.defense_total(),
                "defense": pl.defense_total(),
                "xp": pl.xp, "next_level_xp": pl.next_level_xp,
                "gold": pl.gold, "dead": pl.dead,
                "equipped_weapon": pl.equipped_weapon,
                "equipped_shield": pl.equipped_shield,
                "weapon_name": pl.weapon_name(),
                "shield_name": pl.shield_name(),
                "weapon_display": pl._weapon_display(),
                "shield_display": pl._shield_display(),
                "status_effects": pl.status_effects,
                "visible": True,
            })

        # Messages since last tick for this player (read-only — do NOT
        # update _last_state_tick here; that happens in get_state() when
        # the client actually receives the state).
        last_tick = self._last_state_tick.get(player._client_id, 0)
        messages = [
            (m[0], m[1]) for m in player.messages if m[2] > last_tick
        ]

        return {
            "tick": g.tick,
            "depth": depth,
            "map_x": map_x, "map_y": map_y,
            "map_w": map_w, "map_h": map_h,
            "map": chars, "visible": visible_hex,
            "players": player_stats,
            "enemies": enemies, "items": items, "corpses": corpses,
            "messages": messages,
            "game_over": player.dead,
            "game_win": player.game_win,
            "max_depth": MAX_DEPTH,
            "map_width": MAP_WIDTH, "map_height": MAP_HEIGHT,
        }

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
                "equipped_weapon": getattr(p, "equipped_weapon", WEAPON_FISTS),
                "equipped_shield": getattr(p, "equipped_shield", SHIELD_NONE),
                "gold": p.gold,
                "dead": p.dead, "game_win": p.game_win,
                "server_id": getattr(p, "_server_id", 0),
                "client_id": getattr(p, "_client_id", None),
                "next_tick": p.next_tick,
 "explored": {int(d): self._pack_explored(grid)
                              for d, grid in p.explored.items()},
                "entrance_shown": list(getattr(p, "_entrance_shown", set())),
                "status_effects": dict(getattr(p, "status_effects", {})),
                "discovered_traps": {
                    int(d): [list(c) for c in traps]
                    for d, traps in getattr(p, "discovered_traps", {}).items()
                },
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
                "dungeon_type": lvl.get("dungeon_type", "rooms"),
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
            logger.info("Saved game state: tick=%d, levels=%d",
                        state["tick"], len(state["levels"]))
        except OSError:
            logger.exception("Failed to save game state")

        player_state = {
            "active_players": [serialize_player(p) for p in self.game.players],
            "inactive_players": [serialize_player(p) for p in self.inactive_players],
        }
        try:
            with open(PLAYERS_SAVE_PATH, 'w') as f:
                json.dump(player_state, f)
        except OSError:
            logger.exception("Failed to save player state")

    def _load_state(self):
        """Restore game state from JSON file."""
        try:
            with open(SAVE_PATH, 'r') as f:
                state = json.load(f)
            logger.info("Found save file: tick=%d, levels=%d",
                        state.get("tick", 0), len(state.get("levels", {})))
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
            p.equipped_weapon = pd.get("equipped_weapon", WEAPON_FISTS)
            p.equipped_shield = pd.get("equipped_shield", SHIELD_NONE)
            p.gold = pd["gold"]
            p.dead = pd["dead"]
            p.game_win = pd["game_win"]
            p._server_id = pd["server_id"]
            p._client_id = pd.get("client_id")
            p.next_tick = pd["next_tick"]
            p.explored = {int(d): self._unpack_explored(grid, MAP_WIDTH)
                            for d, grid in pd.get("explored", {}).items()}
            p._entrance_shown = set(pd.get("entrance_shown", []))
            p.status_effects = pd.get("status_effects", {})
            p.discovered_traps = {
                int(d): {tuple(c) for c in traps}
                for d, traps in pd.get("discovered_traps", {}).items()
            }
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

        logger.info("Loaded players: %d active, %d inactive",
                    len(self.game.players), len(self.inactive_players))
        self._rebuild_client_to_idx()
        self._update_visibility(self.game)
        return True

    def start(self):
        """Start the game loop in a background daemon thread."""
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        logger.info("Game loop started")

    def _loop(self):
        """Main game loop: advance ticks, process game state, and precompute player views."""
        last_log_tick = 0
        while self.running:
            with self.lock:
                g = self.game
                # Drain lock-free action queue
                while not self._action_queue.empty():
                    player_id, action, ts = self._action_queue.get()
                    self._last_activity[player_id] = ts
                    target = self.clients.get(player_id)
                    if target and not target.dead:
                        target_idx = self._client_to_idx.get(player_id)
                        if target_idx is not None:
                            g.queue_player_action(target_idx, action)
                if g.players:
                    g.tick += 1
                    alive_before = {id(p) for p in g.players if not p.dead}
                    g._process_tick()
                    # Build death views before deregistering
                    newly_dead = []
                    for p in g.players:
                        if id(p) in alive_before and p.dead and p._client_id:
                            idx = self._client_to_idx.get(p._client_id)
                            if idx is not None:
                                self._latest_views[p._client_id] = self._build_player_view(p, idx)
                            newly_dead.append(p._client_id)
                    for pid in newly_dead:
                        result = self.deregister_player(pid)
                        if result.get("ok"):
                            logger.info("Player died and deregistered: client_id=%s",
                                        pid[:12])
                    # Rebuild index dict after player list changes
                    self._rebuild_client_to_idx()
                    # Precompute visibility-filtered views for surviving players
                    views = {}
                    for idx, p in enumerate(g.players):
                        if p._client_id:
                            views[p._client_id] = self._build_player_view(p, idx)
                    self._latest_views.update(views)
                    self._views_tick = g.tick
                    if g.tick % 500 == 0 and any(not p.dead for p in g.players):
                        self._save_state()
                    # Log every 500 ticks (every ~5 seconds)
                    if g.tick - last_log_tick >= 500:
                        active = sum(1 for p in g.players if not p.dead)
                        dead = sum(1 for p in g.players if p.dead)
                        logger.debug("Tick %d: %d active, %d dead, %d levels",
                                     g.tick, active, dead, len(g.levels))
                        last_log_tick = g.tick
                # Throttle stale player cleanup to every 500ms
                now = time.time()
                if now - self._last_cleanup > 0.5:
                    self._last_cleanup = now
                    stale = [(pid, t) for pid, t in self._last_activity.items()
                              if now - t > PLAYER_TIMEOUT]
                    for pid, t in stale:
                        self._last_activity.pop(pid, None)
                        result = self.deregister_player(pid)
                        if result.get("ok"):
                            logger.info("Stale player removed: client_id=%s (%.0fs idle)",
                                        pid[:12], now - t)
            time.sleep(0.01)

    def stop(self):
        """Signal the game loop thread to stop."""
        self.running = False

    def _rebuild_client_to_idx(self):
        """Rebuild the client_id -> player index mapping."""
        self._client_to_idx = {p._client_id: i
                               for i, p in enumerate(self.game.players)
                               if p._client_id}

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
                    logger.warning("Re-registration failed: client_id=%s not found",
                                   client_id[:12] if client_id else "None")
                    return {"error": "player not found"}
            client_id = client_id or str(uuid.uuid4())
            if inactive:
                p = inactive
                p._client_id = client_id
                g.players.append(p)
                # Clear cached state hash so client gets full state on reconnect
                self._last_state_hash.pop(client_id, None)
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
                g._show_entrance(p)
            self.clients[client_id] = p
            self._last_activity[client_id] = time.time()
            self._update_visibility(g)
            g._update_explored()
            g.game_over = False
            self._rebuild_client_to_idx()
            status = "re-activated" if inactive else "new"
            logger.info("Player registered (%s): name=%s, client_id=%s, total_players=%d",
                        status, p.name, client_id[:12], len(g.players))
            return {"client_id": client_id, "player_id": client_id}

    def deregister_player(self, player_id):
        """Remove a player from the active game.

        Keeps their state for re-entry.
        """
        with self.lock:
            g = self.game
            target = self.clients.get(player_id)
            if target is not None:
                target_idx = self._client_to_idx.get(player_id)
                if target_idx is not None:
                    self.inactive_players.append(target)
                    g.players.pop(target_idx)
                    self._update_visibility(g)
                    logger.info("Player deregistered: name=%s, client_id=%s, remaining=%d",
                                target.name, player_id[:12], len(g.players))
                self.clients.pop(player_id, None)
                self._last_state_tick.pop(player_id, None)
                self._last_activity.pop(player_id, None)
                self._client_to_idx.pop(player_id, None)
                self._save_state()
                return {"ok": True}
            return {"error": "player not found"}

    def get_state(self, player_id=0, full=False):
        """Return the visibility-filtered game state for the given player.

        Reads from a precomputed snapshot built by the game loop, so the
        global lock is not held during state delivery.

        When full is True, sends the complete explored map (computed
        on-demand since the snapshot only stores windowed views).
        """
        self._last_activity[player_id] = time.time()
        g = self.game

        # Check for cached death view before empty-players fallback
        cached_view = self._latest_views.get(player_id)
        if cached_view and cached_view.get("game_over"):
            last_sent = self._last_state_tick.get(player_id, -1)
            if cached_view["tick"] == last_sent:
                return {"tick": cached_view["tick"]}
            self._last_state_tick[player_id] = cached_view["tick"]
            return cached_view

        # No players registered yet
        if not g.players:
            return {
                "tick": g.tick,
                "depth": 0,
                "map_x": 0, "map_y": 0,
                "map_w": MAX_SCREEN_X, "map_h": MAX_SCREEN_Y - 4,
                "map": [" " * MAX_SCREEN_X for _ in range(MAX_SCREEN_Y - 4)],
                "visible": ["0" * ((MAX_SCREEN_X + 3) // 4)
                            for _ in range(MAX_SCREEN_Y - 4)],
                "players": [], "enemies": [], "items": [], "corpses": [],
                "messages": [("Waiting for players...", 7)],
                "game_over": False, "game_win": False,
                "max_depth": MAX_DEPTH,
                "map_width": MAP_WIDTH, "map_height": MAP_HEIGHT,
            }

       # Is this player still registered?
        target = self.clients.get(player_id)
        if target is None:
            return {"tick": g.tick}

        # --- full map requested: compute on-demand ---
        if full:
            return self._build_full_view(target)

        # --- read from precomputed snapshot ---
        views = self._latest_views
        view = views.get(player_id)

        # Player not yet in snapshot (e.g. just registered, or snapshot
        # is from a stale tick).  Compute on-demand as a fallback.
        if view is None:
            with self.lock:
                idx = None
                for i, p in enumerate(g.players):
                    if p is target:
                        idx = i
                        break
                if idx is None:
                    return {"tick": g.tick}
                view = self._build_player_view(target, idx)
            # Store it so the next poll hits the fast path
            views[player_id] = view
            self._latest_views = views

        # Delta check: if the view tick matches what we last sent,
        # nothing changed — return a minimal response.
        last_sent = self._last_state_tick.get(player_id, -1)
        if view["tick"] == last_sent:
            return {"tick": view["tick"]}

        # Mark this tick as sent so the next poll can do delta detection.
        self._last_state_tick[player_id] = view["tick"]
        return view

    def _build_full_view(self, player):
        """Build a *full* (explored-map) view for one player.

        Called on-demand when the client requests ``full=1`` (typically
        after changing depth).  Holds the lock because it reads game state.
        """
        with self.lock:
            g = self.game
            target_idx = None
            for i, p in enumerate(g.players):
                if p is player:
                    target_idx = i
                    break
            if target_idx is None:
                return {"tick": g.tick}

            p_visible = (
                g.player_visible[target_idx]
                if 0 <= target_idx < len(g.player_visible)
                else [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
            )

            map_x, map_y = 0, 0
            map_w, map_h = MAP_WIDTH, MAP_HEIGHT
            depth = player.depth

            chars = []
            visible_hex = []
            hex_digits = (map_w + 3) // 4
            for sy in range(map_h):
                row = []
                vis_bits = 0
                for sx in range(map_w):
                    mx, my = sx + map_x, sy + map_y
                    row.append(g.get_char_at(mx, my, target_idx))
                    if p_visible[my][mx]:
                        vis_bits |= 1 << sx
                chars.append("".join(row))
                visible_hex.append(f"{vis_bits:0{hex_digits}x}")

            enemies = []
            for e in g._get_enemies(depth):
                if e["hp"] <= 0:
                    continue
                if e.get("water"):
                    if not e.get("visible", False):
                        continue
                else:
                    if not p_visible[e["y"]][e["x"]]:
                        continue
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

            explored_grid = player.explored.get(
                depth, [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
            )
            corpses = []
            for c in g._get_corpses(depth):
                if explored_grid[c["y"]][c["x"]]:
                    corpses.append({
                        "x": c["x"], "y": c["y"],
                        "char": "_", "name": c["name"],
                        "level": c["level"], "killer": c["killer"],
                    })

            player_stats = []
            for pl in g.players:
                if pl is player:
                    visible_to_me = True
                else:
                    visible_to_me = (
                        p_visible[pl.y][pl.x] if pl.depth == depth else False
                    )
                if not visible_to_me:
                    continue
                player_stats.append({
                    "id": pl._client_id, "name": pl.name, "char": pl.char,
                    "color": pl.color, "x": pl.x, "y": pl.y,
                    "depth": pl.depth,
                    "hp": pl.hp, "max_hp": pl.max_hp,
                    "level": pl.level, "attack": pl.defense_total(),
                    "defense": pl.defense_total(),
                    "xp": pl.xp, "next_level_xp": pl.next_level_xp,
                    "gold": pl.gold, "dead": pl.dead,
                    "equipped_weapon": pl.equipped_weapon,
                    "equipped_shield": pl.equipped_shield,
                    "weapon_name": pl.weapon_name(),
                    "shield_name": pl.shield_name(),
                    "weapon_display": pl._weapon_display(),
                    "shield_display": pl._shield_display(),
                    "status_effects": pl.status_effects,
                    "visible": True,
                })

            messages = [(m[0], m[1]) for m in player.messages]
            game_over = player.dead
            game_win = player.game_win

            return {
                "tick": g.tick,
                "depth": depth,
                "map_x": map_x, "map_y": map_y,
                "map_w": map_w, "map_h": map_h,
                "map": chars, "visible": visible_hex,
                "players": player_stats,
                "enemies": enemies, "items": items, "corpses": corpses,
                "messages": messages,
                "game_over": game_over,
                "game_win": game_win,
                "max_depth": MAX_DEPTH,
                "map_width": MAP_WIDTH, "map_height": MAP_HEIGHT,
            }

    def send_action(self, player_id, action):
        """Queue an action for the given player.

        Lock-free: appends to the action queue. Validation happens in the
        game loop when the queue is drained. Returns {"queued": True}.
        """
        self._action_queue.put((player_id, action, time.time()))
        return {"queued": True}

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

   Uses the given port (default 9999) and optional log level.
   Usage: dungeon_server.py [port] [log_level]
   Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
   """
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9999
    log_level = sys.argv[2].upper() if len(sys.argv) > 2 else "INFO"

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    logger.info("Starting dungeon server on port %d (log_level=%s)", port, log_level)

    # Disable aiohttp's default access log (too verbose for a game server)
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)

    gs = GameServer()
    gs.start()
    app = create_app()
    app["gs"] = gs

    async def run():
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info("HTTP server listening on port %d", port)
        try:
            await asyncio.Event().wait()
        finally:
            await runner.cleanup()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        gs._save_state()
        gs.stop()
        logger.info("Server stopped")


if __name__ == '__main__':
    main()
