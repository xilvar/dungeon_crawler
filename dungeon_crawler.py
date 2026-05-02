#!/usr/bin/env python3
"""
Dungeon Crawler - A terminal roguelike game.
Use arrow keys or WASD to move. Bump into enemies to attack.
Press > or . to go down stairs. g to grab items.
"""

import copy
import random
import sys

# --- Constants ---
# Color constants (match curses.COLOR_* values for compatibility)
COLOR_BLACK = 0
COLOR_RED = 1
COLOR_GREEN = 2
COLOR_YELLOW = 3
COLOR_BLUE = 4
COLOR_MAGENTA = 5
COLOR_CYAN = 6
COLOR_WHITE = 7

MAX_SCREEN_X = 80
MAX_SCREEN_Y = 24
MAP_WIDTH = 80
MAP_HEIGHT = 45
MAX_ROOMS = 30
MIN_ROOM_SIZE = 4
MAX_ROOM_SIZE = 12
MAX_ENEMIES_PER_ROOM = 3
MAX_MSGS = 6
MAX_DEPTH = 10
FOV_RADIUS = 8
TICKS_PER_SECOND = 100
TICK_MOVE = 50
TICK_ATTACK = 100
TICK_WAIT = 50
TICK_PLAYER_MOVE = 25
TICK_PLAYER_REST = 200

# Tile types
TILE_WALL = 0
TILE_FLOOR = 1
TILE_DOOR = 2
TILE_STAIRS_DOWN = 3
TILE_STAIRS_UP = 4

# Tile rendering
TILE_CHAR = {
    TILE_WALL: "#",
    TILE_FLOOR: ".",
    TILE_DOOR: "+",
    TILE_STAIRS_DOWN: ">",
    TILE_STAIRS_UP: "<",
}

TILE_COLOR = {
    TILE_WALL: COLOR_BLUE,
    TILE_FLOOR: COLOR_BLUE,
    TILE_DOOR: COLOR_YELLOW,
    TILE_STAIRS_DOWN: COLOR_YELLOW,
    TILE_STAIRS_UP: COLOR_YELLOW,
}

# Entity types
ENEMY_RAT = "rat"
ENEMY_BAT = "bat"
ENEMY_SPIDER = "spider"
ENEMY_KOBOLD = "kobold"
ENEMY_GNOME = "gnome"
ENEMY_IMP = "imp"
ENEMY_SKELETON = "skeleton"
ENEMY_ZOMBIE = "zombie"
ENEMY_WOLF = "wolf"
ENEMY_HYDRA = "hydra"
ENEMY_MUMMY = "mummy"
ENEMY_WRAITH = "wraith"
ENEMY_TROLL = "troll"
ENEMY_MINOTAUR = "minotaur"
ENEMY_MEDUSA = "medusa"
ENEMY_OWLBEAR = "owlbear"
ENEMY_HOOK_HORROR = "hook_horror"
ENEMY_PHASE_SPIDER = "phase_spider"
ENEMY_BASILISK = "basilisk"
ENEMY_WYVERN = "wyvern"
ENEMY_PHOENIX = "phoenix"
ENEMY_GRUE = "grue"
ENEMY_GELATINOUS_CUBE = "gelatinous_cube"
ENEMY_REMORHAZ = "remorhaz"
ENEMY_ICE_DEVIL = "ice_devil"
ENEMY_LICH = "lich"
ENEMY_BEHOLDER = "beholder"
ENEMY_BALOR = "balor"
ENEMY_ORC = "orc"
ENEMY_GOLEM = "golem"
ENEMY_SNAKE = "snake"
ENEMY_DEMON = "demon"
ENEMY_DRAGON = "dragon"

ENEMY_PROPS = {
    # Tier 1 - vermin/scavengers
    ENEMY_RAT: {"char": "r", "color": COLOR_YELLOW, "name": "Rat", "hp": 3, "attack": 1, "defense": 0, "xp": 1},
    ENEMY_BAT: {"char": "b", "color": COLOR_YELLOW, "name": "Bat", "hp": 2, "attack": 1, "defense": 0, "xp": 1},
    ENEMY_SPIDER: {"char": "S", "color": COLOR_YELLOW, "name": "Spider", "hp": 4, "attack": 2, "defense": 0, "xp": 2},
    ENEMY_KOBOLD: {"char": "k", "color": COLOR_YELLOW, "name": "Kobold", "hp": 5, "attack": 2, "defense": 0, "xp": 2},
    ENEMY_GNOME: {"char": "g", "color": COLOR_YELLOW, "name": "Goblin", "hp": 7, "attack": 2, "defense": 0, "xp": 2},
    # Tier 2 - common threats
    ENEMY_IMP: {"char": "i", "color": COLOR_RED, "name": "Imp", "hp": 6, "attack": 3, "defense": 0, "xp": 4},
    ENEMY_SKELETON: {"char": "s", "color": COLOR_WHITE, "name": "Skeleton", "hp": 8, "attack": 3, "defense": 1, "xp": 4},
    ENEMY_ZOMBIE: {"char": "Z", "color": COLOR_GREEN, "name": "Zombie", "hp": 12, "attack": 2, "defense": 0, "xp": 3},
    ENEMY_WOLF: {"char": "W", "color": COLOR_WHITE, "name": "Wolf", "hp": 8, "attack": 4, "defense": 0, "xp": 3},
    # Tier 3 - undead/horrors
    ENEMY_HYDRA: {"char": "H", "color": COLOR_GREEN, "name": "Hydra", "hp": 35, "attack": 8, "defense": 3, "xp": 30},
    ENEMY_MUMMY: {"char": "M", "color": COLOR_YELLOW, "name": "Mummy", "hp": 18, "attack": 4, "defense": 2, "xp": 10},
    ENEMY_WRAITH: {"char": "W", "color": COLOR_CYAN, "name": "Wraith", "hp": 15, "attack": 5, "defense": 2, "xp": 12},
    ENEMY_TROLL: {"char": "T", "color": COLOR_GREEN, "name": "Troll", "hp": 25, "attack": 6, "defense": 2, "xp": 20},
    # Tier 4 - formidable beasts
    ENEMY_MINOTAUR: {"char": "N", "color": COLOR_YELLOW, "name": "Minotaur", "hp": 25, "attack": 7, "defense": 2, "xp": 20},
    ENEMY_MEDUSA: {"char": "m", "color": COLOR_GREEN, "name": "Medusa", "hp": 24, "attack": 6, "defense": 2, "xp": 20},
    ENEMY_OWLBEAR: {"char": "O", "color": COLOR_YELLOW, "name": "Owlbear", "hp": 22, "attack": 6, "defense": 1, "xp": 15},
    ENEMY_HOOK_HORROR: {"char": "h", "color": COLOR_YELLOW, "name": "Hook Horror", "hp": 26, "attack": 7, "defense": 2, "xp": 20},
    # Tier 5 - exotic threats
    ENEMY_PHASE_SPIDER: {"char": "P", "color": COLOR_RED, "name": "Phase Spider", "hp": 18, "attack": 5, "defense": 1, "xp": 12},
    ENEMY_BASILISK: {"char": "B", "color": COLOR_GREEN, "name": "Basilisk", "hp": 20, "attack": 6, "defense": 3, "xp": 18},
    ENEMY_WYVERN: {"char": "Y", "color": COLOR_GREEN, "name": "Wyvern", "hp": 32, "attack": 9, "defense": 3, "xp": 25},
    # Tier 6 - powerful creatures
    ENEMY_PHOENIX: {"char": "F", "color": COLOR_RED, "name": "Phoenix", "hp": 28, "attack": 8, "defense": 2, "xp": 22},
    ENEMY_GRUE: {"char": "X", "color": COLOR_MAGENTA, "name": "Grue", "hp": 15, "attack": 5, "defense": 1, "xp": 12},
    ENEMY_GELATINOUS_CUBE: {"char": "C", "color": COLOR_CYAN, "name": "Gelatinous Cube", "hp": 28, "attack": 4, "defense": 1, "xp": 15},
    ENEMY_REMORHAZ: {"char": "R", "color": COLOR_RED, "name": "Remorhaz", "hp": 40, "attack": 10, "defense": 4, "xp": 35},
    ENEMY_ICE_DEVIL: {"char": "I", "color": COLOR_CYAN, "name": "Ice Devil", "hp": 35, "attack": 9, "defense": 3, "xp": 30},
    # Tier 7 - legendary threats
    ENEMY_LICH: {"char": "L", "color": COLOR_WHITE, "name": "Lich", "hp": 45, "attack": 10, "defense": 4, "xp": 45},
    ENEMY_BEHOLDER: {"char": "E", "color": COLOR_YELLOW, "name": "Beholder", "hp": 40, "attack": 9, "defense": 4, "xp": 40},
    # Tier 8 - ultimate bosses
    ENEMY_BALOR: {"char": "B", "color": COLOR_RED, "name": "Balor", "hp": 60, "attack": 14, "defense": 5, "xp": 60},
    # Keep old enemies for compatibility
    ENEMY_ORC: {"char": "o", "color": COLOR_GREEN, "name": "Orc", "hp": 10, "attack": 3, "defense": 1, "xp": 5},
    ENEMY_GOLEM: {"char": "G", "color": COLOR_CYAN, "name": "Golem", "hp": 20, "attack": 5, "defense": 4, "xp": 15},
    ENEMY_SNAKE: {"char": "n", "color": COLOR_RED, "name": "Snake", "hp": 5, "attack": 2, "defense": 0, "xp": 3},
    ENEMY_DEMON: {"char": "D", "color": COLOR_RED, "name": "Demon", "hp": 30, "attack": 8, "defense": 3, "xp": 30},
    ENEMY_DRAGON: {"char": "d", "color": COLOR_RED, "name": "Dragon", "hp": 50, "attack": 12, "defense": 5, "xp": 50},
}

ITEM_POTION = "potion"
ITEM_SWORD = "sword"
ITEM_SHIELD = "shield"
ITEM_GOLD = "gold"

ITEM_PROPS = {
    ITEM_POTION: {"char": "!", "color": COLOR_RED, "name": "Health Potion"},
    ITEM_SWORD: {"char": "/", "color": COLOR_WHITE, "name": "Sword"},
    ITEM_SHIELD: {"char": ")", "color": COLOR_CYAN, "name": "Shield"},
    ITEM_GOLD: {"char": ",", "color": COLOR_YELLOW, "name": "Gold"},
}


class GameOverError(Exception):
    pass


class GameWinError(Exception):
    pass


# --- Dungeon Generation ---
class Room:
    def __init__(self, x1, y1, x2, y2):
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2
        self.center_x = (x1 + x2) // 2
        self.center_y = (y1 + y2) // 2


def create_dungeon(depth):
    """Generate a random dungeon with rooms and corridors."""
    dungeon = [[TILE_WALL for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]
    rooms = []

    for _ in range(MAX_ROOMS):
        w = random.randint(MIN_ROOM_SIZE, MAX_ROOM_SIZE)
        h = random.randint(MIN_ROOM_SIZE, MAX_ROOM_SIZE)
        x = random.randint(1, MAP_WIDTH - w - 1)
        y = random.randint(1, MAP_HEIGHT - h - 1)
        new_room = Room(x, y, x + w - 1, y + h - 1)

        # Check overlap
        failed = False
        for other in rooms:
            if new_room.x1 <= other.x2 and new_room.x2 >= other.x1 and \
                    new_room.y1 <= other.y2 and \
                    new_room.y2 >= other.y1:
                failed = True
                break
        if failed:
            continue

        # Carve room
        for ry in range(new_room.y1, new_room.y2 + 1):
            for rx in range(new_room.x1, new_room.x2 + 1):
                dungeon[ry][rx] = TILE_FLOOR

        if rooms:
            # Connect to previous room with L-shaped corridor
            prev = rooms[-1]
            px, py = prev.center_x, prev.center_y
            cx, cy = new_room.center_x, new_room.center_y

            if random.random() < 0.5:
                # Horizontal then vertical
                for x in range(min(px, cx), max(px, cx) + 1):
                    if dungeon[py][x] == TILE_WALL:
                        dungeon[py][x] = TILE_FLOOR
                for y in range(min(py, cy), max(py, cy) + 1):
                    if dungeon[y][cx] == TILE_WALL:
                        dungeon[y][cx] = TILE_FLOOR
            else:
                # Vertical then horizontal
                for y in range(min(py, cy), max(py, cy) + 1):
                    if dungeon[y][px] == TILE_WALL:
                        dungeon[y][px] = TILE_FLOOR
                for x in range(min(px, cx), max(px, cx) + 1):
                    if dungeon[cy][x] == TILE_WALL:
                        dungeon[cy][x] = TILE_FLOOR

        rooms.append(new_room)

        if len(rooms) >= 5:
            break

    if len(rooms) < 2:
        return create_dungeon(depth)

    # Place doors between adjacent floor tiles that border walls
    for r in rooms:
        for y in range(r.y1, r.y2 + 1):
            for x in range(r.x1, r.x2 + 1):
                # Check if this floor tile borders a wall outside the room
                neighbors_wall = 0
                for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < MAP_HEIGHT and 0 <= nx < MAP_WIDTH:
                        if dungeon[ny][nx] == TILE_WALL:
                            neighbors_wall += 1
                # If exactly 2 wall neighbors in a line, it's a corridor opening
                if neighbors_wall == 2:
                    vertical = y - 1 >= 0 and \
                        dungeon[y - 1][x] == TILE_WALL and \
                        y + 1 < MAP_HEIGHT and \
                        dungeon[y + 1][x] == TILE_WALL
                    horizontal = x - 1 >= 0 and \
                        dungeon[y][x - 1] == TILE_WALL and \
                        x + 1 < MAP_WIDTH and \
                        dungeon[y][x + 1] == TILE_WALL
                    if vertical or horizontal:
                        dungeon[y][x] = TILE_DOOR

    return dungeon, rooms


def place_entities(rooms, dungeon, depth):
    """Place player, enemies, items, and stairs in rooms."""
    enemies = []
    items = []

    # Player in first room
    start_room = rooms[0]
    player_x = start_room.center_x
    player_y = start_room.center_y

    # Stairs down in last room
    end_room = rooms[-1]
    stairs_x = end_room.center_x
    stairs_y = end_room.center_y
    dungeon[stairs_y][stairs_x] = TILE_STAIRS_DOWN

    # Populate intermediate rooms
    enemy_types_by_depth = {
        0: [ENEMY_RAT, ENEMY_RAT, ENEMY_BAT, ENEMY_SPIDER, ENEMY_SNAKE],
        1: [ENEMY_RAT, ENEMY_SPIDER, ENEMY_KOBOLD, ENEMY_GNOME, ENEMY_SNAKE],
        2: [ENEMY_KOBOLD, ENEMY_GNOME, ENEMY_IMP, ENEMY_SKELETON, ENEMY_ZOMBIE, ENEMY_WOLF],
        3: [ENEMY_GNOME, ENEMY_SKELETON, ENEMY_ZOMBIE, ENEMY_WOLF, ENEMY_MUMMY, ENEMY_WRAITH],
        4: [ENEMY_SKELETON, ENEMY_WOLF, ENEMY_MUMMY, ENEMY_TROLL, ENEMY_MINOTAUR, ENEMY_MEDUSA],
        5: [ENEMY_MUMMY, ENEMY_TROLL, ENEMY_MINOTAUR, ENEMY_OWLBEAR, ENEMY_HOOK_HORROR, ENEMY_PHASE_SPIDER],
        6: [ENEMY_TROLL, ENEMY_MEDUSA, ENEMY_BASILISK, ENEMY_WYVERN, ENEMY_GELATINOUS_CUBE, ENEMY_REMORHAZ],
        7: [ENEMY_MINOTAUR, ENEMY_WYVERN, ENEMY_PHOENIX, ENEMY_ICE_DEVIL, ENEMY_LICH, ENEMY_BEHOLDER],
        8: [ENEMY_LICH, ENEMY_BEHOLDER, ENEMY_BALOR, ENEMY_HYDRA],
        9: [ENEMY_LICH, ENEMY_BEHOLDER, ENEMY_BALOR, ENEMY_DRAGON],
    }

    for i, room in enumerate(rooms):
        if room is start_room or room is end_room:
            # Place some items in start room
            if room is start_room:
                for _ in range(random.randint(1, 3)):
                    ix = random.randint(room.x1 + 1, room.x2 - 1)
                    iy = random.randint(room.y1 + 1, room.y2 - 1)
                    items.append({"x": ix, "y": iy, "kind": ITEM_POTION})
            continue

        # Enemies
        num_enemies = random.randint(1, MAX_ENEMIES_PER_ROOM)
        etypes = enemy_types_by_depth.get(depth, [ENEMY_ORC])
        for _ in range(num_enemies):
            ex = random.randint(room.x1 + 1, room.x2 - 1)
            ey = random.randint(room.y1 + 1, room.y2 - 1)
            etype = random.choice(etypes)
            prop = ENEMY_PROPS[etype]
            # Scale with depth
            scale = 1 + depth * 0.15
            enemies.append({
                "x": ex, "y": ey,
                "kind": etype,
                "name": prop["name"],
                "char": prop["char"],
                "color": prop["color"],
                "hp": int(prop["hp"] * scale),
                "max_hp": int(prop["hp"] * scale),
                "attack": int(prop["attack"] * scale),
                "defense": int(prop["defense"] * scale),
                "xp": int(prop["xp"] * scale),
            })

        # Items
        if random.random() < 0.5:
            ix = random.randint(room.x1 + 1, room.x2 - 1)
            iy = random.randint(room.y1 + 1, room.y2 - 1)
            items.append({"x": ix, "y": iy, "kind": ITEM_POTION})
        if random.random() < 0.3:
            ix = random.randint(room.x1 + 1, room.x2 - 1)
            iy = random.randint(room.y1 + 1, room.y2 - 1)
            items.append({"x": ix, "y": iy, "kind": ITEM_GOLD, "value": random.randint(5, 15) * (depth + 1)})
        if random.random() < 0.15:
            ix = random.randint(room.x1 + 1, room.x2 - 1)
            iy = random.randint(room.y1 + 1, room.y2 - 1)
            items.append({"x": ix, "y": iy, "kind": ITEM_SWORD, "bonus": random.randint(1, 3)})
        if random.random() < 0.1:
            ix = random.randint(room.x1 + 1, room.x2 - 1)
            iy = random.randint(room.y1 + 1, room.y2 - 1)
            items.append({"x": ix, "y": iy, "kind": ITEM_SHIELD, "bonus": random.randint(1, 2)})

    return player_x, player_y, enemies, items


# --- Field of View (raycasting) ---
def compute_fov(map_grid, px, py, radius):
    visible = [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
    visible[py][px] = True
    r2 = radius * radius
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy > r2:
                continue
            nx, ny = px + dx, py + dy
            if nx < 0 or nx >= MAP_WIDTH or ny < 0 or ny >= MAP_HEIGHT:
                continue
            if visible[ny][nx]:
                continue
            if _has_line_of_sight(map_grid, px, py, nx, ny):
                visible[ny][nx] = True
    return visible


def _has_line_of_sight(map_grid, x0, y0, x1, y1):
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    x, y = x0, y0
    while True:
        if (x, y) == (x1, y1):
            return True
        if map_grid[y][x] == TILE_WALL and (x, y) != (x0, y0):
            return False
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy


# --- Player ---
class Player:
    def __init__(self, name, char, x, y, color=COLOR_WHITE):
        self.name = name
        self.char = char
        self.color = color
        self.x = x
        self.y = y
        self.hp = 30
        self.max_hp = 30
        self.attack = 5
        self.defense = 1
        self.level = 1
        self.xp = 0
        self.next_level_xp = 10
        self.weapon_bonus = 0
        self.armor_bonus = 0
        self.gold = 0
        self.next_tick = random.randint(0, 99)
        self.queued_action = None
        self.rest_end_tick = None
        self.rest_progress_shown = 0
        self.dead = False
        # Per-depth explored grids: {depth: 2D boolean grid}
        self.explored = {}

    def attack_total(self):
        return self.attack + self.weapon_bonus

    def defense_total(self):
        return self.defense + self.armor_bonus


# --- Game State ---
class Game:
    def __init__(self):
        self.depth = 0
        self.messages = []
        self.game_over = False
        self.game_win = False
        self.message_log = []
        self.players = []
        self.consecutive_waits = 0
        self.levels = {}
        self.tick = 0

        self.new_dungeon()

    def _save_current_level(self):
        """Save the current state of the level to cache."""
        self.levels[self.depth] = {
            "dungeon": copy.deepcopy(self.dungeon),
            "enemies": copy.deepcopy(self.enemies),
            "items": copy.deepcopy(self.items),
            "players": copy.deepcopy(self.players),
            "stairs_x": self.players[0].x,
            "stairs_y": self.players[0].y,
        }

    def _ensure_player_explored(self, player):
        """Ensure a player has an explored grid for the current depth."""
        if self.depth not in player.explored:
            player.explored[self.depth] = [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]

    def new_dungeon(self, from_stairs_up=False):
        if self.depth in self.levels:
            level = self.levels[self.depth]
            self.dungeon = copy.deepcopy(level["dungeon"])
            self.enemies = copy.deepcopy(level["enemies"])
            self.items = copy.deepcopy(level["items"])
            self.players = copy.deepcopy(level.get("players", []))
        else:
            self.dungeon, rooms = create_dungeon(self.depth)
            px, py, self.enemies, self.items = place_entities(rooms, self.dungeon, self.depth)
            if not self.players:
                p1 = Player("Hero1", "@", px, py, COLOR_YELLOW)
                p2 = Player("Hero2", "@", px + 1, py, COLOR_GREEN)
                self.players = [p1, p2]
            else:
                for i, p in enumerate(self.players):
                    p.x = px + i
                    p.y = py
                    p.dead = False
            start_room = rooms[0]
            ux = start_room.center_x
            uy = start_room.center_y
            if ux == self.players[0].x and uy == self.players[0].y:
                uy = start_room.center_y + 1
            if from_stairs_up and self.depth > 0:
                self.dungeon[uy][ux] = TILE_STAIRS_DOWN
            elif not from_stairs_up and self.depth > 0:
                self.dungeon[uy][ux] = TILE_STAIRS_UP
            self._save_current_level()
        for e in self.enemies:
            e["next_tick"] = self.tick + random.randint(0, 99)
        for p in self.players:
            p.next_tick = self.tick + random.randint(0, 99)
            p.queued_action = None
            p.rest_end_tick = None
            p.rest_progress_shown = 0
            if p.dead:
                p.dead = False
                p.hp = p.max_hp
            self._ensure_player_explored(p)
        self._update_visibility()
        self._update_explored()
        self.consecutive_waits = 0
        if not from_stairs_up:
            self.msg(f"You descend into the dungeon. (Depth: {self.depth + 1})")
        else:
            self.msg(f"You go back up. (Depth: {self.depth + 1})")

    def _update_visibility(self):
        self.player_visible = []
        self.visible = [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
        for p in self.players:
            if not p.dead:
                fov = compute_fov(self.dungeon, p.x, p.y, FOV_RADIUS)
                self.player_visible.append(fov)
                for y in range(MAP_HEIGHT):
                    for x in range(MAP_WIDTH):
                        if fov[y][x]:
                            self.visible[y][x] = True
            else:
                self.player_visible.append([[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)])

    def _update_explored(self):
        for i, p in enumerate(self.players):
            if p.dead:
                continue
            self._ensure_player_explored(p)
            explored_grid = p.explored[self.depth]
            p_visible = self.player_visible[i]
            for y in range(MAP_HEIGHT):
                for x in range(MAP_WIDTH):
                    if p_visible[y][x]:
                        explored_grid[y][x] = True
        # Maintain combined explored for curses rendering
        if not hasattr(self, '_combined_explored') or self._combined_explored is None:
            self._combined_explored = [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                if self.visible[y][x]:
                    self._combined_explored[y][x] = True

    def msg(self, text, color=COLOR_WHITE):
        self.message_log.append((text, color))
        if len(self.message_log) > MAX_MSGS:
            self.message_log.pop(0)

    def is_passable(self, x, y):
        if x < 0 or x >= MAP_WIDTH or y < 0 or y >= MAP_HEIGHT:
            return False
        tile = self.dungeon[y][x]
        if tile == TILE_WALL:
            return False
        return True

    def get_enemy_at(self, x, y):
        for e in self.enemies:
            if e["x"] == x and e["y"] == y and e["hp"] > 0:
                return e
        return None

    def get_item_at(self, x, y):
        for i, item in enumerate(self.items):
            if item["x"] == x and item["y"] == y:
                return i, item
        return None, None

    def do_attack(self, attacker_name, attacker_atk, defender_name, defender_def, damage_variance=2):
        damage = max(1, attacker_atk - defender_def + random.randint(-damage_variance, damage_variance))
        return damage

    def queue_player_action(self, player_idx, action):
        if self.game_over or self.game_win:
            return
        self.players[player_idx].queued_action = action

    def execute_player_action(self, player_idx):
        player = self.players[player_idx]
        action = player.queued_action
        player.queued_action = None
        if action is None:
            return
        action_type = action["type"]
        if action_type == "move":
            self._do_move(player, action["dx"], action["dy"])
        elif action_type == "grab":
            self._do_grab_item(player)
            player.next_tick = self.tick + TICK_MOVE
        elif action_type == "stairs_down":
            self._do_go_down_stairs(player)
            for p in self.players:
                p.next_tick = self.tick + TICK_MOVE
        elif action_type == "stairs_up":
            self._do_go_up_stairs(player)
            for p in self.players:
                p.next_tick = self.tick + TICK_MOVE
        elif action_type == "rest":
            self._do_rest(player)
            player.rest_end_tick = self.tick + TICK_PLAYER_REST
            player.rest_progress_shown = 0
            player.next_tick = player.rest_end_tick

    def _do_move(self, player, dx, dy):
        nx, ny = player.x + dx, player.y + dy
        if not self.is_passable(nx, ny):
            player.next_tick = self.tick + TICK_WAIT
            return
        enemy = self.get_enemy_at(nx, ny)
        if enemy:
            self._do_combat_attack(player, enemy)
            player.next_tick = self.tick + TICK_ATTACK
        else:
            player.x, player.y = nx, ny
            self.consecutive_waits = 0
            player.next_tick = self.tick + TICK_PLAYER_MOVE

    def _do_combat_attack(self, player, enemy):
        self.consecutive_waits = 0
        damage = self.do_attack(
            player.name, player.attack_total(),
            enemy["name"], enemy["defense"])
        enemy["hp"] -= damage
        self.msg(f"{player.name} hits the {enemy['name']} for {damage} damage!", COLOR_WHITE)
        if enemy["hp"] <= 0:
            self.msg(f"The {enemy['name']} dies!", COLOR_RED)
            player.xp += enemy["xp"]
            self._check_level_up(player)

    def _check_level_up(self, player):
        while player.xp >= player.next_level_xp:
            player.xp -= player.next_level_xp
            player.level += 1
            player.max_hp += 5
            player.hp = min(player.hp + 5, player.max_hp)
            player.attack += 1
            player.defense += 1
            player.next_level_xp = int(player.next_level_xp * 1.5)
            self.msg(f"{player.name} is now level {player.level}!", COLOR_YELLOW)

    def _process_tick(self):
        if self.game_over or self.game_win:
            return
        any_action = False
        for i, player in enumerate(self.players):
            if player.dead:
                continue
            if self.tick >= player.next_tick:
                if player.queued_action is not None:
                    self.execute_player_action(i)
                    any_action = True
                else:
                    player.next_tick = self.tick + 1
        for enemy in self.enemies:
            if enemy["hp"] <= 0:
                continue
            if self.tick >= enemy["next_tick"]:
                self._process_enemy_action(enemy)
        if not any_action:
            self._update_visibility()
            self._update_explored()
        else:
            self._update_visibility()
            self._update_explored()

    def _get_nearest_player(self, ex, ey):
        best = None
        best_dist = float('inf')
        for p in self.players:
            if p.dead:
                continue
            dist = abs(p.x - ex) + abs(p.y - ey)
            if dist < best_dist:
                best = p
                best_dist = dist
        return best, best_dist

    def _process_enemy_action(self, enemy):
        ex, ey = enemy["x"], enemy["y"]
        target, dist = self._get_nearest_player(ex, ey)
        if target is None:
            moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            random.shuffle(moves)
            for wdx, wdy in moves:
                wx, wy = ex + wdx, ey + wdy
                if self.is_passable(wx, wy) and not self.get_enemy_at(wx, wy):
                    enemy["x"], enemy["y"] = wx, wy
                    break
            enemy["next_tick"] = self.tick + TICK_MOVE
            return
        can_see = self.visible[enemy["y"]][enemy["x"]] and dist <= FOV_RADIUS + 2

        if dist == 1:
            damage = self.do_attack(
                enemy["name"], enemy["attack"],
                target.name, target.defense_total(), 1)
            target.hp -= damage
            self.msg(f"The {enemy['name']} hits {target.name} for {damage} damage!", enemy["color"])
            enemy["next_tick"] = self.tick + TICK_ATTACK
            if target.hp <= 0:
                target.hp = 0
                target.dead = True
                self.msg(f"{target.name} has died!", COLOR_RED)
                alive = any(p and not p.dead for p in self.players)
                if not alive:
                    self.game_over = True
                    return
        elif can_see:
            dx = 0
            dy = 0
            if abs(target.x - ex) > abs(target.y - ey):
                dx = 1 if target.x > ex else -1
            else:
                dy = 1 if target.y > ey else -1
            nx, ny = ex + dx, ey + dy
            if self.is_passable(nx, ny) and not self.get_enemy_at(nx, ny) and (nx != target.x or ny != target.y):
                enemy["x"], enemy["y"] = nx, ny
                enemy["next_tick"] = self.tick + TICK_MOVE
            else:
                moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
                random.shuffle(moves)
                for wdx, wdy in moves:
                    wx, wy = ex + wdx, ey + wdy
                    if self.is_passable(wx, wy) and not self.get_enemy_at(wx, wy):
                        enemy["x"], enemy["y"] = wx, wy
                        break
                enemy["next_tick"] = self.tick + TICK_MOVE
        else:
            moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            random.shuffle(moves)
            for wdx, wdy in moves:
                wx, wy = ex + wdx, ey + wdy
                if self.is_passable(wx, wy) and not self.get_enemy_at(wx, wy):
                    enemy["x"], enemy["y"] = wx, wy
                    break
            enemy["next_tick"] = self.tick + TICK_MOVE

    def _do_go_down_stairs(self, player):
        self.consecutive_waits = 0
        if self.dungeon[player.y][player.x] == TILE_STAIRS_DOWN:
            self._save_current_level()
            self.depth += 1
            if self.depth >= MAX_DEPTH:
                self.msg("You have conquered the dungeon!", COLOR_YELLOW)
                self.game_win = True
                return
            self.new_dungeon()
        else:
            self.msg(f"{player.name}: no stairs here.", COLOR_CYAN)

    def _do_go_up_stairs(self, player):
        self.consecutive_waits = 0
        if self.dungeon[player.y][player.x] == TILE_STAIRS_UP:
            if self.depth > 0:
                self._save_current_level()
                self.depth -= 1
                self.new_dungeon(from_stairs_up=True)
            else:
                self.msg(f"{player.name}: can't go up further.", COLOR_CYAN)
        else:
            self.msg(f"{player.name}: no stairs here.", COLOR_CYAN)

    def _do_grab_item(self, player):
        self.consecutive_waits = 0
        idx, item = self.get_item_at(player.x, player.y)
        if item is None:
            self.msg(f"{player.name}: nothing to grab here.", COLOR_CYAN)
            return
        kind = item["kind"]
        if kind == ITEM_POTION:
            heal = random.randint(5, 10)
            player.hp = min(player.hp + heal, player.max_hp)
            self.msg(f"{player.name} drinks a potion. Recovered {heal} HP.", COLOR_RED)
        elif kind == ITEM_SWORD:
            player.weapon_bonus += item["bonus"]
            self.msg(f"{player.name} equips a sword (+{item['bonus']} attack).", COLOR_WHITE)
        elif kind == ITEM_SHIELD:
            player.armor_bonus += item["bonus"]
            self.msg(f"{player.name} equips a shield (+{item['bonus']} defense).", COLOR_CYAN)
        elif kind == ITEM_GOLD:
            player.gold += item["value"]
            self.msg(f"{player.name} picks up {item['value']} gold.", COLOR_YELLOW)
        self.items.pop(idx)

    def _do_rest(self, player):
        self.consecutive_waits += 1
        if player.hp < player.max_hp:
            player.hp += 1
            self.msg(f"{player.name} rests for a moment. (+1 HP)", COLOR_GREEN)
        else:
            self.msg(f"{player.name} rests for a moment.", COLOR_GREEN)
        chance = 0.05 * self.consecutive_waits + 0.02 * self.depth
        chance = min(chance, 0.7)
        if random.random() < chance:
            self._spawn_nearby_enemy()

    def _spawn_nearby_enemy(self):
        """Spawn a random enemy near the first player."""
        p = self.players[0]
        for _ in range(10):
            sx = p.x + random.randint(-5, 5)
            sy = p.y + random.randint(-5, 5)
            if sx == p.x and sy == p.y:
                continue
            if not (0 <= sx < MAP_WIDTH and 0 <= sy < MAP_HEIGHT):
                continue
            if not self.is_passable(sx, sy):
                continue
            if self.get_enemy_at(sx, sy):
                continue
            dist = abs(sx - p.x) + abs(sy - p.y)
            if dist < 4:
                continue
            etypes = list(ENEMY_PROPS.keys())
            etype = random.choice(etypes)
            prop = ENEMY_PROPS[etype]
            scale = 1 + self.depth * 0.15
            enemy = {
                "x": sx, "y": sy,
                "kind": etype,
                "name": prop["name"],
                "char": prop["char"],
                "color": prop["color"],
                "hp": int(prop["hp"] * scale),
                "max_hp": int(prop["hp"] * scale),
                "attack": int(prop["attack"] * scale),
                "defense": int(prop["defense"] * scale),
                "xp": int(prop["xp"] * scale),
                "next_tick": self.tick + random.randint(0, 99),
            }
            self.enemies.append(enemy)
            self.msg(f"A {prop['name']} appears!", COLOR_RED)
            return

    def get_char_at(self, mx, my, player_idx=0):
        """Return the character to display at map position (mx, my)."""
        if mx < 0 or mx >= MAP_WIDTH or my < 0 or my >= MAP_HEIGHT:
            return ' '
        player = self.players[player_idx] if 0 <= player_idx < len(self.players) else None
        if player is None:
            return ' '
        explored_grid = player.explored.get(self.depth, [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)])
        p_visible = self.player_visible[player_idx] if 0 <= player_idx < len(self.player_visible) else [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
        is_explored = explored_grid[my][mx]
        is_visible = p_visible[my][mx]
        if not is_explored:
            return ' '
        enemy = self.get_enemy_at(mx, my)
        if enemy and is_visible:
            return enemy["char"]
        for p in self.players:
            if mx == p.x and my == p.y and not p.dead and is_visible:
                return p.char
        _, item = self.get_item_at(mx, my)
        if item and is_visible:
            return ITEM_PROPS[item["kind"]]["char"]
        tile = self.dungeon[my][mx]
        return TILE_CHAR.get(tile, '?')

    def print_text_map(self):
        """Print the map as plain text (no curses)."""
        view_h = MAX_SCREEN_Y - 4
        view_w = MAX_SCREEN_X
        p = self.players[0] if self.players else None
        if p is None:
            print("No players")
            return
        start_x = max(0, min(p.x - view_w // 2, MAP_WIDTH - view_w))
        start_y = max(0, min(p.y - view_h // 2, MAP_HEIGHT - view_h))

        print(f"{'=' * view_w}")
        for pl in self.players:
            bar = (f"{pl.name} | Lv{pl.level} | HP {pl.hp}/{pl.max_hp} | "
                   f"ATK {pl.attack_total()} | DEF {pl.defense_total()} | "
                   f"XP {pl.xp}/{pl.next_level_xp} | Gold {pl.gold} {'[DEAD]' if pl.dead else ''}")
            print(bar.ljust(view_w))
        print(f"Depth {self.depth + 1}/{MAX_DEPTH}")

        for sy in range(view_h):
            row = []
            for sx in range(view_w):
                mx = sx + start_x
                my = sy + start_y
                row.append(self.get_char_at(mx, my))
            print(''.join(row))

        for msg_text, _ in self.message_log[-3:]:
            print(msg_text[:view_w])
        print("P1:Arrows  P2:WASD  >:Down  <:Up  g/G:Grab  /*:Rest  q:Quit")
        print(f"{'=' * view_w}")

def run_text_mode():
    """Run a single frame in text mode for debugging."""
    depth = 0
    dungeon, rooms = create_dungeon(depth)
    px, py, enemies, items = place_entities(rooms, dungeon, depth)
    players = [
        Player("Hero1", "@", px, py, COLOR_YELLOW),
        Player("Hero2", "@", px + 1, py, COLOR_GREEN),
    ]
    visible = [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
    for p in players:
        fov = compute_fov(dungeon, p.x, p.y, FOV_RADIUS)
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                if fov[y][x]:
                    visible[y][x] = True
    explored = [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            if visible[y][x]:
                explored[y][x] = True

    view_h = MAX_SCREEN_Y - 4
    view_w = MAX_SCREEN_X
    start_x = max(0, min(px - view_w // 2, MAP_WIDTH - view_w))
    start_y = max(0, min(py - view_h // 2, MAP_HEIGHT - view_h))

    print(f"{'=' * view_w}")
    print(f"P1@({players[0].x},{players[0].y}) P2@({players[1].x},{players[1].y}), Rooms: {len(rooms)}")
    for e in enemies:
        print(f"  Enemy: {e['name']} at ({e['x']}, {e['y']})")
    for it in items:
        print(f"  Item: {it['kind']} at ({it['x']}, {it['y']})")

    for sy in range(view_h):
        row = []
        for sx in range(view_w):
            mx = sx + start_x
            my = sy + start_y
            if mx < 0 or mx >= MAP_WIDTH or my < 0 or my >= MAP_HEIGHT:
                row.append(' ')
                continue
            if not explored[my][mx]:
                row.append(' ')
                continue
            if mx == players[0].x and my == players[0].y:
                row.append('A')
            elif mx == players[1].x and my == players[1].y:
                row.append('B')
            elif visible[my][mx]:
                for e in enemies:
                    if e['x'] == mx and e['y'] == my and e['hp'] > 0:
                        row.append(e['char'])
                        break
                else:
                    for it in items:
                        if it['x'] == mx and it['y'] == my:
                            row.append(ITEM_PROPS[it["kind"]]["char"])
                            break
                    else:
                        row.append(TILE_CHAR.get(dungeon[my][mx], '?'))
            else:
                row.append(TILE_CHAR.get(dungeon[my][mx], '?'))
        print(''.join(row))
    print(f"{'=' * view_w}")


if __name__ == "__main__":
    run_text_mode()
