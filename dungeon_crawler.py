#!/usr/bin/env python3
"""Core game logic: dungeon generation, FOV, combat, entities, items, corpses,
ambient sounds, player state, and a text-mode renderer for debugging."""

import random

from dungeon_messages import (
    ENEMY_SOUNDS,
    ENEMY_SOUNDS_DEFAULT,
    ENEMY_HIT_MESSAGES,
    ENEMY_HIT_DEFAULT,
    PLAYER_MOVE_AMBIENT,
    COMBAT_CLASH_AMBIENT,
    ENEMY_DEATH_AMBIENT,
    PLAYER_DEATH_AMBIENT,
    STAIRS_DOWN_AMBIENT,
    STAIRS_DOWN_DEPTH_AMBIENT,
    STAIRS_UP_AMBIENT,
    STAIRS_UP_DEPTH_AMBIENT,
    MSG_PLAYER_HIT_ENEMY,
    MSG_ENEMY_DIES,
    MSG_LEVEL_UP,
    MSG_PLAYER_DIED,
    MSG_CONQUERED,
    MSG_DESCENDED,
    MSG_ASCENDED,
    MSG_DRANK_POTION,
    MSG_EQUIPPED_SWORD,
    MSG_EQUIPPED_SHIELD,
    MSG_PICKED_UP_GOLD,
    MSG_REST_HEAL,
    MSG_REST_NO_HEAL,
    MSG_ENEMY_INTO_VIEW,
    MSG_GENERATOR_INTO_VIEW,
    MSG_GENERATOR_SPAWNS,
    MSG_HIT_GENERATOR,
    MSG_GENERATOR_DESTROYED,
    MSG_GENERATOR_RESPAWN,
    MSG_NO_STAIRS_DOWN,
    MSG_CANNOT_GO_UP,
    MSG_NO_STAIRS_UP,
    MSG_NOTHING_TO_GRAB,
    MSG_SEE_ITEM,
    MSG_SEE_CORPSE,
    MSG_SEE_STAIRS_DOWN,
    MSG_SEE_STAIRS_UP,
    MSG_SEE_PLAYER,
    MSG_OPEN_DOOR,
    MSG_SEE_DOOR_OPEN,
)

# --- Constants ---
# Color constants (match curses.COLOR_* values for compatibility)
COLOR_RED = 1
COLOR_GREEN = 2
COLOR_YELLOW = 3
COLOR_BLUE = 4
COLOR_MAGENTA = 5
COLOR_CYAN = 6
COLOR_WHITE = 7

MAX_SCREEN_X = 80
MAX_SCREEN_Y = 24
MAP_WIDTH = 60
MAP_HEIGHT = 60
MAX_ROOMS = 30
MIN_ROOM_SIZE = 4
MAX_ROOM_SIZE = 12
MAX_ENEMIES_PER_ROOM = 3
MAX_MSGS = 6
MAX_DEPTH = 10
FOV_RADIUS = 7
TICKS_PER_SECOND = 100
TICK_MOVE = 20
TICK_ATTACK = 50
TICK_WAIT = 20
TICK_PLAYER_MOVE = 10
AMBIENT_COOLDOWN = 200  # 2 seconds at 100 ticks/sec
GENERATOR_SPAWN_MIN = 200
GENERATOR_SPAWN_MAX = 200
GENERATORS_PER_LEVEL = 3
GENERATOR_RESPAWN_TIME = 6000  # 60 seconds to respawn after destruction
MAX_ENEMIES_BASE = 10
MAX_ENEMIES_PER_DEPTH = 3


def max_enemies_for_depth(depth):
    """Return the maximum number of living enemies allowed at a given depth."""
    return MAX_ENEMIES_BASE + depth * MAX_ENEMIES_PER_DEPTH

# Tile types
TILE_WALL = 0
TILE_FLOOR = 1
TILE_DOOR_CLOSED = 2
TILE_STAIRS_DOWN = 3
TILE_STAIRS_UP = 4
TILE_DOOR_OPEN = 5
TILE_GENERATOR = 6

# Tile rendering
TILE_CHAR = {
    TILE_WALL: "#",
    TILE_FLOOR: ".",
    TILE_DOOR_CLOSED: "+",
    TILE_STAIRS_DOWN: ">",
    TILE_STAIRS_UP: "<",
    TILE_DOOR_OPEN: "-",
    TILE_GENERATOR: "~",
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
    ENEMY_RAT: {
        "char": "r", "color": COLOR_YELLOW, "name": "Rat",
        "hp": 3, "attack": 1, "defense": 0, "xp": 1,
    },
    ENEMY_BAT: {
        "char": "b", "color": COLOR_YELLOW, "name": "Bat",
        "hp": 2, "attack": 1, "defense": 0, "xp": 1,
    },
    ENEMY_SPIDER: {
        "char": "S", "color": COLOR_YELLOW, "name": "Spider",
        "hp": 4, "attack": 2, "defense": 0, "xp": 2,
    },
    ENEMY_KOBOLD: {
        "char": "k", "color": COLOR_YELLOW, "name": "Kobold",
        "hp": 5, "attack": 2, "defense": 0, "xp": 2,
    },
    ENEMY_GNOME: {
        "char": "g", "color": COLOR_YELLOW, "name": "Goblin",
        "hp": 7, "attack": 2, "defense": 0, "xp": 2,
    },
    # Tier 2 - common threats
    ENEMY_IMP: {
        "char": "i", "color": COLOR_RED, "name": "Imp",
        "hp": 6, "attack": 3, "defense": 0, "xp": 4,
    },
    ENEMY_SKELETON: {
        "char": "s", "color": COLOR_WHITE, "name": "Skeleton",
        "hp": 8, "attack": 3, "defense": 1, "xp": 4,
    },
    ENEMY_ZOMBIE: {
        "char": "Z", "color": COLOR_GREEN, "name": "Zombie",
        "hp": 12, "attack": 2, "defense": 0, "xp": 3,
    },
    ENEMY_WOLF: {
        "char": "W", "color": COLOR_WHITE, "name": "Wolf",
        "hp": 8, "attack": 4, "defense": 0, "xp": 3,
    },
    # Tier 3 - undead/horrors
    ENEMY_HYDRA: {
        "char": "H", "color": COLOR_GREEN, "name": "Hydra",
        "hp": 35, "attack": 8, "defense": 3, "xp": 30,
    },
    ENEMY_MUMMY: {
        "char": "M", "color": COLOR_YELLOW, "name": "Mummy",
        "hp": 18, "attack": 4, "defense": 2, "xp": 10,
    },
    ENEMY_WRAITH: {
        "char": "W", "color": COLOR_CYAN, "name": "Wraith",
        "hp": 15, "attack": 5, "defense": 2, "xp": 12,
    },
    ENEMY_TROLL: {
        "char": "T", "color": COLOR_GREEN, "name": "Troll",
        "hp": 25, "attack": 6, "defense": 2, "xp": 20,
    },
    # Tier 4 - formidable beasts
    ENEMY_MINOTAUR: {
        "char": "N", "color": COLOR_YELLOW, "name": "Minotaur",
        "hp": 25, "attack": 7, "defense": 2, "xp": 20,
    },
    ENEMY_MEDUSA: {
        "char": "m", "color": COLOR_GREEN, "name": "Medusa",
        "hp": 24, "attack": 6, "defense": 2, "xp": 20,
    },
    ENEMY_OWLBEAR: {
        "char": "O", "color": COLOR_YELLOW, "name": "Owlbear",
        "hp": 22, "attack": 6, "defense": 1, "xp": 15,
    },
    ENEMY_HOOK_HORROR: {
        "char": "h", "color": COLOR_YELLOW, "name": "Hook Horror",
        "hp": 26, "attack": 7, "defense": 2, "xp": 20,
    },
    # Tier 5 - exotic threats
    ENEMY_PHASE_SPIDER: {
        "char": "P", "color": COLOR_RED, "name": "Phase Spider",
        "hp": 18, "attack": 5, "defense": 1, "xp": 12,
    },
    ENEMY_BASILISK: {
        "char": "B", "color": COLOR_GREEN, "name": "Basilisk",
        "hp": 20, "attack": 6, "defense": 3, "xp": 18,
    },
    ENEMY_WYVERN: {
        "char": "Y", "color": COLOR_GREEN, "name": "Wyvern",
        "hp": 32, "attack": 9, "defense": 3, "xp": 25,
    },
    # Tier 6 - powerful creatures
    ENEMY_PHOENIX: {
        "char": "F", "color": COLOR_RED, "name": "Phoenix",
        "hp": 28, "attack": 8, "defense": 2, "xp": 22,
    },
    ENEMY_GRUE: {
        "char": "X", "color": COLOR_MAGENTA, "name": "Grue",
        "hp": 15, "attack": 5, "defense": 1, "xp": 12,
    },
    ENEMY_GELATINOUS_CUBE: {
        "char": "C", "color": COLOR_CYAN,
        "name": "Gelatinous Cube",
        "hp": 28, "attack": 4, "defense": 1, "xp": 15,
    },
    ENEMY_REMORHAZ: {
        "char": "R", "color": COLOR_RED, "name": "Remorhaz",
        "hp": 40, "attack": 10, "defense": 4, "xp": 35,
    },
    ENEMY_ICE_DEVIL: {
        "char": "I", "color": COLOR_CYAN, "name": "Ice Devil",
        "hp": 35, "attack": 9, "defense": 3, "xp": 30,
    },
    # Tier 7 - legendary threats
    ENEMY_LICH: {
        "char": "L", "color": COLOR_WHITE, "name": "Lich",
        "hp": 45, "attack": 10, "defense": 4, "xp": 45,
    },
    ENEMY_BEHOLDER: {
        "char": "E", "color": COLOR_YELLOW, "name": "Beholder",
        "hp": 40, "attack": 9, "defense": 4, "xp": 40,
    },
    # Tier 8 - ultimate bosses
    ENEMY_BALOR: {
        "char": "B", "color": COLOR_RED, "name": "Balor",
        "hp": 60, "attack": 14, "defense": 5, "xp": 60,
    },
    # Keep old enemies for compatibility
    ENEMY_ORC: {
        "char": "o", "color": COLOR_GREEN, "name": "Orc",
        "hp": 10, "attack": 3, "defense": 1, "xp": 5,
    },
    ENEMY_GOLEM: {
        "char": "G", "color": COLOR_CYAN, "name": "Golem",
        "hp": 20, "attack": 5, "defense": 4, "xp": 15,
    },
    ENEMY_SNAKE: {
        "char": "n", "color": COLOR_RED, "name": "Snake",
        "hp": 5, "attack": 2, "defense": 0, "xp": 3,
    },
    ENEMY_DEMON: {
        "char": "D", "color": COLOR_RED, "name": "Demon",
        "hp": 30, "attack": 8, "defense": 3, "xp": 30,
    },
    ENEMY_DRAGON: {
        "char": "d", "color": COLOR_RED, "name": "Dragon",
        "hp": 50, "attack": 12, "defense": 5, "xp": 50,
    },
}


ITEM_POTION = "potion"
ITEM_SWORD = "sword"
ITEM_SHIELD = "shield"
ITEM_GOLD = "gold"

ITEM_PROPS = {
    ITEM_POTION: {"char": "!", "color": COLOR_RED, "name": "Health Potion"},
    ITEM_SWORD: {"char": "/", "color": COLOR_WHITE, "name": "Sword"},
    ITEM_SHIELD: {"char": ")", "color": COLOR_CYAN, "name": "Shield"},
    ITEM_GOLD: {"char": "$", "color": COLOR_YELLOW, "name": "Pile of Gold"},
}


class Room:
    """Represents a rectangular room in a dungeon."""
    def __init__(self, x1, y1, x2, y2):
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2
        self.center_x = (x1 + x2) // 2
        self.center_y = (y1 + y2) // 2


def create_dungeon(depth):
    """Generate a random dungeon with rooms, corridors, and doors.

    Returns (grid, rooms).
    """
    dungeon = [[TILE_WALL for _ in range(MAP_WIDTH)]
               for _ in range(MAP_HEIGHT)]
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

    # Place doors flush with room walls at corridor-room boundaries.
    # A door goes on the corridor tile adjacent to a room tile.
    def in_room(rx, ry):
        for r in rooms:
            if r.x1 <= rx <= r.x2 and r.y1 <= ry <= r.y2:
                return True
        return False

    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            if dungeon[y][x] != TILE_FLOOR:
                continue
            if in_room(x, y):
                continue
            # This is a corridor tile — check if adjacent to a room
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if (0 <= nx < MAP_WIDTH and 0 <= ny < MAP_HEIGHT
                        and in_room(nx, ny)
                        and dungeon[ny][nx] == TILE_FLOOR):
                    if random.random() < 0.5:
                        dungeon[y][x] = TILE_DOOR_CLOSED
                        break

    return dungeon, rooms


DUNGEON_TYPES = ["rooms", "caves"]
CAVE_FILL = 0.47
CAVE_WALL_THRESHOLD = 4
CAVE_SMOOTH_PASSES = 6
CAVE_MIN_OPEN = 400


def create_cave_dungeon(depth):
    """Generate an organic cave dungeon using cellular automata.

    Retries until a valid cave is produced.
    Returns (grid, open_areas) where open_areas is a list of (x, y) floor tiles.
    """
    while True:
        cave = [[TILE_WALL if random.random() < CAVE_FILL else TILE_FLOOR
                 for _ in range(MAP_WIDTH)]
                for _ in range(MAP_HEIGHT)]

        for y in range(MAP_HEIGHT):
            cave[y][0] = TILE_WALL
            cave[y][MAP_WIDTH - 1] = TILE_WALL
        for x in range(MAP_WIDTH):
            cave[0][x] = TILE_WALL
            cave[MAP_HEIGHT - 1][x] = TILE_WALL

        for _ in range(CAVE_SMOOTH_PASSES):
            new_cave = [[TILE_WALL] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
            for y in range(1, MAP_HEIGHT - 1):
                for x in range(1, MAP_WIDTH - 1):
                    wall_count = 0
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if cave[y + dy][x + dx] == TILE_WALL:
                                wall_count += 1
                    if wall_count > CAVE_WALL_THRESHOLD:
                        new_cave[y][x] = TILE_WALL
                    elif wall_count < CAVE_WALL_THRESHOLD:
                        new_cave[y][x] = TILE_FLOOR
                    else:
                        new_cave[y][x] = cave[y][x]
            cave = new_cave

        visited = [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
        components = []
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                if cave[y][x] == TILE_FLOOR and not visited[y][x]:
                    component = _flood_fill(cave, visited, x, y)
                    components.append(component)

        if not components:
            continue

        largest = max(components, key=len)
        largest_set = set((px, py) for px, py in largest)
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                if (x, y) not in largest_set:
                    cave[y][x] = TILE_WALL

        open_areas = []
        for py in range(1, MAP_HEIGHT - 1):
            for px in range(1, MAP_WIDTH - 1):
                if cave[py][px] != TILE_FLOOR:
                    continue
                neighbors = sum(1 for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                               if cave[py + dy][px + dx] == TILE_FLOOR)
                if neighbors >= 3:
                    open_areas.append((px, py))

        if len(open_areas) >= CAVE_MIN_OPEN:
            return cave, open_areas


def _flood_fill(grid, visited, sx, sy):
    """BFS flood fill returning list of connected floor tiles."""
    component = []
    queue = [(sx, sy)]
    visited[sy][sx] = True
    while queue:
        x, y = queue.pop(0)
        component.append((x, y))
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if (0 <= nx < MAP_WIDTH and 0 <= ny < MAP_HEIGHT
                    and not visited[ny][nx] and grid[ny][nx] == TILE_FLOOR):
                visited[ny][nx] = True
                queue.append((nx, ny))
    return component


def place_entities(rooms, dungeon, depth):
    """Place enemies and items in rooms.

    Returns (spawn_x, spawn_y, enemies, items).
    """
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
        2: [
            ENEMY_KOBOLD, ENEMY_GNOME, ENEMY_IMP,
            ENEMY_SKELETON, ENEMY_ZOMBIE, ENEMY_WOLF,
        ],
        3: [
            ENEMY_GNOME, ENEMY_SKELETON, ENEMY_ZOMBIE,
            ENEMY_WOLF, ENEMY_MUMMY, ENEMY_WRAITH,
        ],
        4: [
            ENEMY_SKELETON, ENEMY_WOLF, ENEMY_MUMMY,
            ENEMY_TROLL, ENEMY_MINOTAUR, ENEMY_MEDUSA,
        ],
        5: [
            ENEMY_MUMMY, ENEMY_TROLL, ENEMY_MINOTAUR,
            ENEMY_OWLBEAR, ENEMY_HOOK_HORROR, ENEMY_PHASE_SPIDER,
        ],
        6: [
            ENEMY_TROLL, ENEMY_MEDUSA, ENEMY_BASILISK,
            ENEMY_WYVERN, ENEMY_GELATINOUS_CUBE, ENEMY_REMORHAZ,
        ],
        7: [
            ENEMY_MINOTAUR, ENEMY_WYVERN, ENEMY_PHOENIX,
            ENEMY_ICE_DEVIL, ENEMY_LICH, ENEMY_BEHOLDER,
        ],
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
            items.append({
                "x": ix, "y": iy, "kind": ITEM_GOLD,
                "value": random.randint(5, 15) * (depth + 1)})
        if random.random() < 0.15:
            ix = random.randint(room.x1 + 1, room.x2 - 1)
            iy = random.randint(room.y1 + 1, room.y2 - 1)
            items.append({
                "x": ix, "y": iy, "kind": ITEM_SWORD,
                "bonus": random.randint(1, 3),
            })
        if random.random() < 0.1:
            ix = random.randint(room.x1 + 1, room.x2 - 1)
            iy = random.randint(room.y1 + 1, room.y2 - 1)
            items.append({
                "x": ix, "y": iy, "kind": ITEM_SHIELD,
                "bonus": random.randint(1, 2),
            })

    return player_x, player_y, enemies, items


# --- Field of View (raycasting) ---
def compute_fov(map_grid, px, py, radius):
    """Return a 2D boolean grid of tiles visible from (px, py).

    Visibility is computed within the given radius.
    """
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
    """Bresenham line-of-sight check between two points on the map grid."""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    x, y = x0, y0
    while True:
        if (x, y) == (x1, y1):
            return True
        if map_grid[y][x] in (TILE_WALL, TILE_DOOR_CLOSED) and (x, y) != (x0, y0):
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
    """Represents a player character with stats, position, and inventory."""
    def __init__(self, name, char, x, y, color=COLOR_WHITE, depth=0):
        self.name = name
        self.char = char
        self.color = color
        self.x = x
        self.y = y
        self.depth = depth
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
        self.consecutive_rests = 0
        self.dead = False
        self.game_win = False
        self.messages = []
        self._last_ambient_tick = 0
        # Per-depth explored grids: {depth: 2D boolean grid}
        self.explored = {}

    def attack_total(self):
        """Return total attack including weapon bonus."""
        return self.attack + self.weapon_bonus

    def defense_total(self):
        """Return total defense including armor bonus."""
        return self.defense + self.armor_bonus


# --- Game State ---
class Game:
    """Manages the full game state.

    Handles levels, players, enemies, ticks, and messaging.
    """
    def __init__(self):
        """Create a new game with level 0 pre-generated."""
        self.game_over = False
        self.players = []
        self.levels = {}
        self.tick = 0

        self._init_level(0)

    def _get_dungeon(self, depth):
        """Return the dungeon grid for the given depth."""
        return self.levels[depth]["dungeon"]

    def _get_enemies(self, depth):
        """Return the enemy list for the given depth."""
        return self.levels[depth]["enemies"]

    def _get_items(self, depth):
        """Return the item list for the given depth."""
        return self.levels[depth]["items"]

    def _get_stairs_down(self, depth):
        """Return (x, y) of the stairs-down tile at the given depth."""
        sd = self.levels[depth]
        return sd["stairs_down_x"], sd["stairs_down_y"]

    def _get_stairs_up(self, depth):
        """Return (x, y) of the stairs-up tile at the given depth."""
        su = self.levels[depth]
        return su["stairs_up_x"], su["stairs_up_y"]

    def _pick_cave_spot(self, open_areas, px, py, exclude=None):
        """Pick a random spot from open areas, avoiding given coordinates.

        If exclude is set, prefers spots far from it.
        """
        candidates = [(x, y) for x, y in open_areas
                      if (x, y) != (px, py) and (x, y) != exclude]
        if not candidates:
            candidates = list(open_areas)
        if not exclude:
            return random.choice(candidates)
        # Weight by distance from exclude to prefer far spots
        distances = [abs(x - exclude[0]) + abs(y - exclude[1])
                     for x, y in candidates]
        max_dist = max(distances) if distances else 1
        weights = [(d + 1) ** 2 for d in distances]  # quadratic weighting
        return random.choices(candidates, weights=weights, k=1)[0]

    def _place_entities_cave(self, open_areas, dungeon, depth):
        """Place player, enemies, and items in a cave dungeon."""
        if not open_areas:
            return 0, 0, [], []

        # Player spawns at a random open area
        px, py = random.choice(open_areas)
        spawn = (px, py)

        enemies = []
        items = []
        used = {spawn}

        enemy_types_by_depth = {
            0: [ENEMY_RAT, ENEMY_RAT, ENEMY_BAT, ENEMY_SPIDER, ENEMY_SNAKE],
            1: [ENEMY_RAT, ENEMY_SPIDER, ENEMY_KOBOLD, ENEMY_GNOME, ENEMY_SNAKE],
            2: [ENEMY_KOBOLD, ENEMY_GNOME, ENEMY_IMP,
                ENEMY_SKELETON, ENEMY_ZOMBIE, ENEMY_WOLF],
            3: [ENEMY_GNOME, ENEMY_SKELETON, ENEMY_ZOMBIE,
                ENEMY_WOLF, ENEMY_MUMMY, ENEMY_WRAITH],
            4: [ENEMY_SKELETON, ENEMY_WOLF, ENEMY_MUMMY,
                ENEMY_TROLL, ENEMY_MINOTAUR, ENEMY_MEDUSA],
            5: [ENEMY_MUMMY, ENEMY_TROLL, ENEMY_MINOTAUR,
                ENEMY_OWLBEAR, ENEMY_HOOK_HORROR, ENEMY_PHASE_SPIDER],
            6: [ENEMY_TROLL, ENEMY_MEDUSA, ENEMY_BASILISK,
                ENEMY_WYVERN, ENEMY_GELATINOUS_CUBE, ENEMY_REMORHAZ],
            7: [ENEMY_MINOTAUR, ENEMY_OWLBEAR, ENEMY_WYVERN,
                ENEMY_ICE_DEVIL, ENEMY_LICH, ENEMY_BEHOLDER],
            8: [ENEMY_LICH, ENEMY_BEHOLDER, ENEMY_BALOR, ENEMY_HYDRA],
            9: [ENEMY_LICH, ENEMY_BEHOLDER, ENEMY_BALOR, ENEMY_DRAGON],
        }
        enemy_tier = max(0, min(depth - 1, 9))
        enemy_pool = enemy_types_by_depth[enemy_tier]
        max_enemies = min(16 + depth * 6, 60)

        for _ in range(max_enemies):
            spot = self._pick_open_spot(open_areas, used)
            if spot is None:
                break
            ex, ey = spot
            used.add(spot)
            etype = random.choice(enemy_pool)
            props = ENEMY_PROPS[etype]
            e = {
                "name": props["name"],
                "char": props["char"],
                "color": props["color"],
                "x": ex, "y": ey,
                "hp": props["hp"] + depth * 2,
                "max_hp": props["hp"] + depth * 2,
                "attack": props["attack"] + depth,
                "defense": props["defense"] + depth // 2,
                "xp": props["xp"] + depth * 5,
                "depth": depth,
            }
            enemies.append(e)

        # Items (reduced for caves)
        for _ in range(2 + depth // 2):
            spot = self._pick_open_spot(open_areas, used)
            if spot is None:
                break
            used.add(spot)
            roll = random.random()
            if roll < 0.4:
                kind = ITEM_POTION
            elif roll < 0.6:
                kind = ITEM_SWORD
            elif roll < 0.75:
                kind = ITEM_SHIELD
            else:
                kind = ITEM_GOLD
            item = {
                "kind": kind,
                "x": spot[0], "y": spot[1],
                "depth": depth,
            }
            if kind == ITEM_GOLD:
                item["value"] = random.randint(5, 20) + depth * 5
            elif kind == ITEM_SWORD:
                item["bonus"] = random.randint(1, 2) + depth // 2
            elif kind == ITEM_SHIELD:
                item["bonus"] = random.randint(1, 2) + depth // 3
            items.append(item)

        return px, py, enemies, items

    def _pick_open_spot(self, open_areas, used):
        """Pick a random open area not in used set."""
        available = [s for s in open_areas if s not in used]
        if not available:
            return None
        return random.choice(available)

    def _place_generators(self, dungeon, depth, occupied, level_tick):
        """Place monster generators on floor tiles not in occupied set.

        Returns list of generator dicts with spawn timer and enemy type.
        """
        enemy_types_by_depth = {
            0: [ENEMY_RAT, ENEMY_BAT, ENEMY_SPIDER],
            1: [ENEMY_RAT, ENEMY_SPIDER, ENEMY_KOBOLD],
            2: [ENEMY_KOBOLD, ENEMY_SKELETON, ENEMY_ZOMBIE],
            3: [ENEMY_SKELETON, ENEMY_ZOMBIE, ENEMY_WOLF],
            4: [ENEMY_WOLF, ENEMY_MUMMY, ENEMY_TROLL],
            5: [ENEMY_TROLL, ENEMY_MINOTAUR, ENEMY_OWLBEAR],
            6: [ENEMY_MINOTAUR, ENEMY_WYVERN, ENEMY_REMORHAZ],
            7: [ENEMY_WYVERN, ENEMY_ICE_DEVIL, ENEMY_LICH],
            8: [ENEMY_LICH, ENEMY_BEHOLDER, ENEMY_BALOR],
            9: [ENEMY_BEHOLDER, ENEMY_BALOR, ENEMY_DRAGON],
        }
        enemy_pool = enemy_types_by_depth[min(depth, 9)]

        # Collect all floor tiles
        floor_tiles = []
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                if dungeon[y][x] == TILE_FLOOR and (x, y) not in occupied:
                    floor_tiles.append((x, y))

        if not floor_tiles:
            return []

        generators = []
        used = set()
        for _ in range(GENERATORS_PER_LEVEL):
            spot = self._pick_open_spot(floor_tiles, used | occupied)
            if spot is None:
                break
            used.add(spot)
            etype = random.choice(enemy_pool)
            generators.append({
                "x": spot[0], "y": spot[1],
                "enemy_type": etype,
                "spawn_tick": level_tick + random.randint(
                    GENERATOR_SPAWN_MIN, GENERATOR_SPAWN_MAX),
                "hp": ENEMY_PROPS[etype]["hp"] * 5 + depth * 10,
                "max_hp": ENEMY_PROPS[etype]["hp"] * 5 + depth * 10,
                "defense": 2 + depth // 2,
                "destroyed": False,
                "respawn_tick": 0,
            })
            dungeon[spot[1]][spot[0]] = TILE_GENERATOR

        return generators

    def _ensure_level(self, depth):
        """Ensure a level exists at the given depth, creating it if needed."""
        if depth not in self.levels:
            self._init_level(depth)

    def _init_level(self, depth):
        """Generate a new dungeon level at the given depth.

        Populates enemies, items, and stairs.
        """
        dungeon_type = random.choice(DUNGEON_TYPES)
        if dungeon_type == "caves":
            dungeon, open_areas = create_cave_dungeon(depth)
            px, py, enemies, items = self._place_entities_cave(open_areas, dungeon, depth)
            stairs_down_x, stairs_down_y = self._pick_cave_spot(open_areas, px, py)
            stairs_up_x, stairs_up_y = self._pick_cave_spot(open_areas, px, py,
                                                             exclude=(stairs_down_x, stairs_down_y))
        else:
            dungeon, rooms = create_dungeon(depth)
            px, py, enemies, items = place_entities(rooms, dungeon, depth)
            start_room = rooms[0]
            end_room = rooms[-1]
            stairs_down_x, stairs_down_y = end_room.center_x, end_room.center_y
            stairs_up_x = start_room.center_x
            stairs_up_y = start_room.center_y
            while stairs_up_x == px and stairs_up_y == py:
                stairs_up_y += 1

        dungeon[stairs_down_y][stairs_down_x] = TILE_STAIRS_DOWN
        if depth > 0:
            dungeon[stairs_up_y][stairs_up_x] = TILE_STAIRS_UP

        # Place monster generators
        generators = self._place_generators(dungeon, depth,
                                            {(px, py), (stairs_down_x, stairs_down_y),
                                             (stairs_up_x, stairs_up_y)}, 0)

        self.levels[depth] = {
            "dungeon": dungeon,
            "enemies": enemies,
            "items": items,
            "corpses": [],
            "generators": generators,
            "tick": 0,
            "stairs_down_x": stairs_down_x,
            "stairs_down_y": stairs_down_y,
            "stairs_up_x": stairs_up_x,
            "stairs_up_y": stairs_up_y,
            "spawn_x": px,
            "spawn_y": py,
        }

        for e in enemies:
            e["next_tick"] = 0

    def _ensure_player_explored(self, player):
        """Ensure the player has an explored grid for their current depth."""
        if player.depth not in player.explored:
            player.explored[player.depth] = (
                [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
            )

    def _update_visibility(self):
        """Recompute FOV for all players and announce newly visible enemies."""
        old_visible = (self.player_visible
                       if hasattr(self, 'player_visible') else [])
        self.player_visible = []
        for i, p in enumerate(self.players):
            if not p.dead:
                dungeon = self._get_dungeon(p.depth)
                fov = compute_fov(dungeon, p.x, p.y, FOV_RADIUS)
                self.player_visible.append(fov)
            else:
                self.player_visible.append(
                    [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)])

        # Detect enemies that just came into view
        for i, p in enumerate(self.players):
            if p.dead:
                continue
            old_fov = (
                old_visible[i] if i < len(old_visible)
                else [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
            )
            new_fov = self.player_visible[i]
            for e in self._get_enemies(p.depth):
                if e["hp"] <= 0:
                    continue
                if (new_fov[e["y"]][e["x"]]
                        and not old_fov[e["y"]][e["x"]]):
                    self._tell(
                        p, MSG_ENEMY_INTO_VIEW, e["color"],
                        ctx={"enemy": e["name"]},
                    )
            # Detect generators that just came into view
            for gen in self.levels.get(p.depth, {}).get("generators", []):
                if gen["destroyed"]:
                    continue
                if (new_fov[gen["y"]][gen["x"]]
                        and not old_fov[gen["y"]][gen["x"]]):
                    self._tell(
                        p, random.choice(MSG_GENERATOR_INTO_VIEW),
                        COLOR_MAGENTA,
                    )

    def _update_explored(self):
        """Mark newly visible tiles as explored for each player."""
        for i, p in enumerate(self.players):
            if p.dead:
                continue
            self._ensure_player_explored(p)
            explored_grid = p.explored[p.depth]
            p_visible = self.player_visible[i]
            for y in range(MAP_HEIGHT):
                for x in range(MAP_WIDTH):
                    if p_visible[y][x]:
                        explored_grid[y][x] = True

    def _tell(self, player, text, color=COLOR_WHITE, ctx=None):
        """Send a message to a specific player, resolving {name} to 'You'."""
        resolved = text.replace("{name}", "You")
        if ctx:
            resolved = resolved.format(**ctx)
        player.messages.append((resolved, color, self.tick))
        if len(player.messages) > MAX_MSGS:
            player.messages.pop(0)

    def _broadcast(
        self, x, y, depth, text,
        color=COLOR_WHITE, subject=None, ctx=None,
    ):
        """Send a message to all alive players on the same depth.

        Only players who can see (x, y) receive it.
        """
        dungeon = self._get_dungeon(depth)
        for p in self.players:
            if p.dead or p.depth != depth:
                continue
            fov = compute_fov(dungeon, p.x, p.y, FOV_RADIUS)
            if fov[y][x]:
                if subject and p is subject:
                    resolved = text.replace("{name}", "You")
                else:
                    resolved = text.replace(
                        "{name}", subject.name if subject else "",
                    )
                if ctx:
                    resolved = resolved.format(**ctx)
                p.messages.append((resolved, color, self.tick))
                if len(p.messages) > MAX_MSGS:
                    p.messages.pop(0)

    def _ambient_sound(
        self, x, y, depth, messages, color,
        source=None, chance=0.35,
        skip_visible=False, range=25, flat=False,
    ):
        """Send a random ambient message to nearby players on the same depth,
        with probability decreasing by distance. Skips the source player.
        When skip_visible is True, also skips players who can see the source.
        When flat is True, uses a flat chance regardless of distance."""
        dungeon = self._get_dungeon(depth)
        for p in self.players:
            if p.dead or p.depth != depth or p is source:
                continue
            dist = abs(p.x - x) + abs(p.y - y)
            if dist < 2 or dist > range:
                continue
            if skip_visible and source:
                fov = compute_fov(dungeon, p.x, p.y, FOV_RADIUS)
                if fov[y][x]:
                    continue
            prob = chance if flat else max(0, chance * (1 - dist / range))
            if random.random() < prob:
                if self.tick - p._last_ambient_tick < AMBIENT_COOLDOWN:
                    continue
                p._last_ambient_tick = self.tick
                self._tell(p, random.choice(messages), color)

    def _ambient_depth(
        self, depth, messages, color,
        source=None, chance=0.5, skip_visible=False,
    ):
        """Send a random ambient message to all alive players on a depth,
        regardless of distance. Skips the source player.
        When skip_visible is True, also skips players who
        can see the source."""
        dungeon = self._get_dungeon(depth)
        for p in self.players:
            if p.dead or p.depth != depth or p is source:
                continue
            if skip_visible and source:
                fov = compute_fov(dungeon, p.x, p.y, FOV_RADIUS)
                if fov[source.y][source.x]:
                    continue
            if random.random() < chance:
                if self.tick - p._last_ambient_tick < AMBIENT_COOLDOWN:
                    continue
                p._last_ambient_tick = self.tick
                self._tell(p, random.choice(messages), color)

    def _find_open_spawn(self, x, y, depth, exclude_player=None):
        """Find the nearest open tile to (x, y) that doesn't overlap with
        other players or enemies. Prefers cardinal directions over diagonals.
        Only searches within 2 tiles of the intended position."""
        if self._is_tile_free(x, y, depth, exclude_player):
            return x, y
        for dx, dy in [
            (0, -1), (0, 1), (-1, 0), (1, 0),
            (-1, -1), (1, -1), (-1, 1), (1, 1),
            (0, -2), (0, 2), (-2, 0), (2, 0),
        ]:
            nx, ny = x + dx, y + dy
            if self._is_tile_free(nx, ny, depth, exclude_player):
                return nx, ny
        return x, y

    def _is_tile_free(self, x, y, depth, exclude_player=None):
        """Check if a tile is passable.

        Returns False if occupied by another player or enemy.
        """
        if not self.is_passable(x, y, depth):
            return False
        if self.get_enemy_at(x, y, depth):
            return False
        for p in self.players:
            if p is exclude_player:
                continue
            if not p.dead and p.depth == depth and p.x == x and p.y == y:
                return False
        return True

    def is_passable(self, x, y, depth):
        """Return True if (x, y) is within bounds and passable.

        Walls and closed doors block movement.
        """
        if x < 0 or x >= MAP_WIDTH or y < 0 or y >= MAP_HEIGHT:
            return False
        tile = self._get_dungeon(depth)[y][x]
        return tile not in (TILE_WALL, TILE_DOOR_CLOSED)

    def _get_generator_at(self, x, y, depth):
        """Return the generator at (x, y) on the given depth, or None."""
        for gen in self.levels.get(depth, {}).get("generators", []):
            if gen["x"] == x and gen["y"] == y:
                return gen
        return None

    def get_enemy_at(self, x, y, depth):
        """Return the living enemy at (x, y) on the given depth, or None."""
        for e in self._get_enemies(depth):
            if e["x"] == x and e["y"] == y and e["hp"] > 0:
                return e
        return None

    def get_item_at(self, x, y, depth):
        """Return (index, item) for the item at (x, y), or (None, None)."""
        items = self._get_items(depth)
        for i, item in enumerate(items):
            if item["x"] == x and item["y"] == y:
                return i, item
        return None, None

    def _get_corpses(self, depth):
        """Return the corpse list for the given depth."""
        return self.levels[depth]["corpses"]

    def get_corpse_at(self, x, y, depth):
        """Return the corpse at (x, y) on the given depth, or None."""
        for c in self._get_corpses(depth):
            if c["x"] == x and c["y"] == y:
                return c
        return None

    def _get_player_at(self, x, y, depth, exclude):
        """Return another player at (x, y) on the given depth, or None."""
        for p in self.players:
            if p is exclude:
                continue
            if not p.dead and p.depth == depth and p.x == x and p.y == y:
                return p
        return None

    def do_attack(
        self, attacker_name, attacker_atk,
        defender_name, defender_def,
        damage_variance=2,
    ):
        """Calculate damage: (atk - def) +/- random variance, minimum 1."""
        damage = max(
            1, attacker_atk - defender_def
            + random.randint(-damage_variance, damage_variance),
        )
        return damage

    def queue_player_action(self, player_idx, action):
        """Queue an action for the given player.

        The action executes on their next tick.
        """
        if self.game_over:
            return
        player = self.players[player_idx]
        if player.game_win:
            return
        player.queued_action = action

    def execute_player_action(self, player_idx):
        """Execute the queued action for the given player."""
        player = self.players[player_idx]
        action = player.queued_action
        player.queued_action = None
        if action is None:
            return
        action_type = action["type"]
        if action_type != "rest":
            player.consecutive_rests = 0
        if action_type == "move":
            self._do_move(player, action["dx"], action["dy"])
        elif action_type == "grab":
            self._do_grab_item(player)
            player.next_tick = self.tick + TICK_MOVE
        elif action_type == "stairs_down":
            self._do_go_down_stairs(player)
            player.next_tick = self.tick + TICK_MOVE
        elif action_type == "stairs_up":
            self._do_go_up_stairs(player)
            player.next_tick = self.tick + TICK_MOVE
        elif action_type == "rest":
            self._do_rest(player)
            player.next_tick = self.tick + TICK_MOVE

    def _do_move(self, player, dx, dy):
        """Move the player by (dx, dy). Rejects diagonal movement."""
        if dx != 0 and dy != 0:
            player.next_tick = self.tick + TICK_WAIT
            return
        nx, ny = player.x + dx, player.y + dy
        dungeon = self._get_dungeon(player.depth)
        in_bounds = (0 <= nx < MAP_WIDTH and 0 <= ny < MAP_HEIGHT)
        target_tile = dungeon[ny][nx] if in_bounds else TILE_WALL
        if target_tile == TILE_DOOR_CLOSED:
            dungeon[ny][nx] = TILE_DOOR_OPEN
            player.next_tick = self.tick + TICK_PLAYER_MOVE
            self._tell(player, random.choice(MSG_OPEN_DOOR), COLOR_WHITE)
            return
        if target_tile == TILE_GENERATOR:
            enemy = self.get_enemy_at(nx, ny, player.depth)
            if enemy:
                self._do_combat_attack(player, enemy)
                player.next_tick = self.tick + TICK_ATTACK
                return
            gen = self._get_generator_at(nx, ny, player.depth)
            if gen and not gen["destroyed"]:
                damage = self.do_attack(
                    player.name, player.attack_total(),
                    "portal", gen["defense"])
                gen["hp"] -= damage
                self._broadcast(
                    nx, ny, player.depth,
                    MSG_HIT_GENERATOR, COLOR_MAGENTA,
                    subject=player,
                    ctx={"damage": damage},
                )
                player.next_tick = self.tick + TICK_ATTACK
                if gen["hp"] <= 0:
                    gen["destroyed"] = True
                    gen["respawn_tick"] = self.levels[player.depth]["tick"] + GENERATOR_RESPAWN_TIME
                    dungeon[ny][nx] = TILE_FLOOR
                    self._broadcast(
                        nx, ny, player.depth,
                        MSG_GENERATOR_DESTROYED, COLOR_MAGENTA,
                        subject=player,
                    )
                return
        if target_tile == TILE_DOOR_OPEN:
            enemy = self.get_enemy_at(nx, ny, player.depth)
            if enemy:
                self._do_combat_attack(player, enemy)
                player.next_tick = self.tick + TICK_ATTACK
                return
            player.x, player.y = nx, ny
            player.next_tick = self.tick + TICK_PLAYER_MOVE
            self._tell(player, random.choice(MSG_SEE_DOOR_OPEN), COLOR_WHITE)
            self._ambient_sound(
                nx, ny, player.depth, PLAYER_MOVE_AMBIENT,
                COLOR_WHITE, source=player, chance=0.08,
                skip_visible=True, range=38, flat=True,
            )
            return
        if not self.is_passable(nx, ny, player.depth):
            player.next_tick = self.tick + TICK_WAIT
            return
        enemy = self.get_enemy_at(nx, ny, player.depth)
        if enemy:
            self._do_combat_attack(player, enemy)
            player.next_tick = self.tick + TICK_ATTACK
        else:
            player.x, player.y = nx, ny
            player.next_tick = self.tick + TICK_PLAYER_MOVE
            self._ambient_sound(
                nx, ny, player.depth, PLAYER_MOVE_AMBIENT,
                COLOR_WHITE, source=player, chance=0.08,
                skip_visible=True, range=38, flat=True,
            )
            self._show_walk_over_messages(player, nx, ny)

    def _show_walk_over_messages(self, player, x, y):
        """Show a message when the player walks over an entity."""
        depth = player.depth
        other = self._get_player_at(x, y, depth, player)
        if other:
            self._tell(player, random.choice(MSG_SEE_PLAYER),
                       COLOR_GREEN, ctx={"player": other.name})
            return
        corpse = self.get_corpse_at(x, y, depth)
        if corpse:
            self._tell(player, random.choice(MSG_SEE_CORPSE), COLOR_RED,
                       ctx={
                           "corpse": corpse["name"],
                           "corpse_level": corpse["level"],
                           "killer": corpse["killer"],
                       })
            return
        _, item = self.get_item_at(x, y, depth)
        if item:
            item_name = ITEM_PROPS[item["kind"]]["name"].lower()
            self._tell(player, random.choice(MSG_SEE_ITEM),
                       COLOR_WHITE, ctx={"item": item_name})
            return
        dungeon = self._get_dungeon(depth)
        tile = dungeon[y][x]
        if tile == TILE_STAIRS_DOWN:
            self._tell(player, random.choice(MSG_SEE_STAIRS_DOWN),
                       COLOR_CYAN)
        elif tile == TILE_STAIRS_UP:
            self._tell(player, random.choice(MSG_SEE_STAIRS_UP),
                       COLOR_CYAN)

    def _do_combat_attack(self, player, enemy):
        """Resolve a player attacking an adjacent enemy."""
        damage = self.do_attack(
            player.name, player.attack_total(),
            enemy["name"], enemy["defense"])
        enemy["hp"] -= damage
        tier_keys = sorted(MSG_PLAYER_HIT_ENEMY.keys())
        tier = tier_keys[0]
        for tk in tier_keys:
            if damage >= tk:
                tier = tk
        hit_msg = random.choice(MSG_PLAYER_HIT_ENEMY[tier])
        self._broadcast(
            enemy["x"], enemy["y"], player.depth,
            hit_msg, COLOR_WHITE,
            subject=player,
            ctx={"enemy": enemy["name"], "damage": damage},
        )
        self._ambient_sound(
            enemy["x"], enemy["y"], player.depth,
            COMBAT_CLASH_AMBIENT,
            COLOR_WHITE, source=player, chance=0.5,
            range=38, flat=True,
        )
        if enemy["hp"] <= 0:
            self._broadcast(
                enemy["x"], enemy["y"], player.depth,
                MSG_ENEMY_DIES, COLOR_RED,
                ctx={"enemy": enemy["name"]},
            )
            self._ambient_sound(
                enemy["x"], enemy["y"], player.depth,
                ENEMY_DEATH_AMBIENT,
                COLOR_RED, source=player, chance=1.0,
                range=38, flat=True)
            player.xp += enemy["xp"]
            self._check_level_up(player)

    def _check_level_up(self, player):
        """Process level-ups while the player has enough XP."""
        while player.xp >= player.next_level_xp:
            player.xp -= player.next_level_xp
            player.level += 1
            player.max_hp += 5
            player.hp = min(player.hp + 5, player.max_hp)
            player.attack += 1
            player.next_level_xp = int(player.next_level_xp * 1.5)
            self._broadcast(
                player.x, player.y, player.depth,
                MSG_LEVEL_UP, COLOR_YELLOW,
                subject=player, ctx={"level": player.level},
            )

    def _process_tick(self):
        """Advance the game by one tick.

        Process player actions, enemy AI, and visibility.
        """
        if self.game_over:
            return
        # Snapshot level ticks to cap advancement per wall-clock tick
        _prev_level_ticks = {d: self.levels[d]["tick"] for d in self.levels}
        for i, player in enumerate(self.players):
            if player.dead or player.game_win:
                continue
            if self.tick >= player.next_tick:
                if player.queued_action is not None:
                    self.execute_player_action(i)
                    # Advance level tick by action cost
                    action_cost = player.next_tick - self.tick
                    if action_cost > 0 and player.depth in self.levels:
                        self.levels[player.depth]["tick"] += action_cost
                else:
                    player.next_tick = self.tick + 1
          # Slow idle progression: advance level ticks by 1 every 10 wall-clock ticks
        if self.tick % 10 == 0:
            for depth in list(self.levels.keys()):
                if any(p.depth == depth and not p.dead for p in self.players):
                    self.levels[depth]["tick"] += 1
        # Cap level tick advancement to max 4 players worth per wall-clock tick
        _max_tick_advance = 4 * TICK_ATTACK
        for depth in list(self.levels.keys()):
            prev = _prev_level_ticks.get(depth, 0)
            advanced = self.levels[depth]["tick"] - prev
            if advanced > _max_tick_advance:
                self.levels[depth]["tick"] = prev + _max_tick_advance
        # Process enemies per level using level tick
        for depth in list(self.levels.keys()):
            level_tick = self.levels[depth]["tick"]
            for enemy in self._get_enemies(depth):
                if enemy["hp"] <= 0:
                    continue
                if level_tick >= enemy["next_tick"]:
                    self._process_enemy_action(enemy, depth, level_tick)
        # Process monster generators (only if players are on that depth)
        for depth in list(self.levels.keys()):
            depth_players = [p for p in self.players
                             if not p.dead and p.depth == depth]
            if not depth_players:
                continue
            lvl = self.levels[depth]
            level_tick = lvl["tick"]
            # Respawn destroyed generators
            for gen in lvl.get("generators", []):
                if gen["destroyed"] and level_tick >= gen["respawn_tick"]:
                    self._respawn_generator(gen, depth, level_tick)
            # Spawn from active generators when their spawn timer expires
            for gen in lvl.get("generators", []):
                if not gen["destroyed"] and level_tick >= gen["spawn_tick"]:
                    self._spawn_from_generator(gen, depth, level_tick)
        self._update_visibility()
        self._update_explored()

    def _spawn_from_generator(self, gen, depth, level_tick):
        """Spawn an enemy from a monster generator."""
        gx, gy = gen["x"], gen["y"]
        dungeon = self._get_dungeon(depth)
        enemies = self._get_enemies(depth)

        # Check monster limit for this depth
        living = sum(1 for e in enemies if e["hp"] > 0)
        if living >= max_enemies_for_depth(depth):
            return

        # Check if there's already an enemy on the generator
        for e in enemies:
            if e["x"] == gx and e["y"] == gy and e["hp"] > 0:
                return  # blocked, don't spawn

        # Check adjacent tiles for a free spot
        adj = [(gx + dx, gy + dy) for dx, dy in
               [(-1, 0), (1, 0), (0, -1), (0, 1)]]
        random.shuffle(adj)
        spawn_x, spawn_y = gx, gy  # default: spawn on generator itself
        for sx, sy in adj:
            if self._is_tile_free(sx, sy, depth):
                spawn_x, spawn_y = sx, sy
                break

        etype = gen["enemy_type"]
        props = ENEMY_PROPS[etype]
        enemy = {
            "name": props["name"],
            "char": props["char"],
            "color": props["color"],
            "x": spawn_x, "y": spawn_y,
            "hp": props["hp"] + depth * 2,
            "max_hp": props["hp"] + depth * 2,
            "attack": props["attack"] + depth,
            "defense": props["defense"] + depth // 2,
            "xp": props["xp"] + depth * 5,
            "depth": depth,
            "next_tick": level_tick,
        }
        enemies.append(enemy)

        # Reschedule next spawn
        gen["spawn_tick"] = level_tick + random.randint(
            GENERATOR_SPAWN_MIN, GENERATOR_SPAWN_MAX)

        # Notify nearby players
        for p in self.players:
            if p.dead or p.depth != depth:
                continue
            dist = abs(p.x - gx) + abs(p.y - gy)
            if dist <= FOV_RADIUS:
                self._tell(p, random.choice(MSG_GENERATOR_SPAWNS),
                           COLOR_MAGENTA, ctx={"enemy": props["name"]})

    def _respawn_generator(self, gen, depth, level_tick):
        """Respawn a destroyed generator at a new random location."""
        dungeon = self._get_dungeon(depth)

        # Find all floor tiles that are free
        floor_tiles = []
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                if dungeon[y][x] == TILE_FLOOR:
                    # Check no enemy, item, player, or other generator here
                    if (not self.get_enemy_at(x, y, depth)
                            and not self.get_item_at(x, y, depth)[1]
                            and not any(p.depth == depth and p.x == x and p.y == y
                                       for p in self.players if not p.dead)):
                        floor_tiles.append((x, y))

        if not floor_tiles:
            return

        # Pick a new spot
        spot = random.choice(floor_tiles)
        gen["x"] = spot[0]
        gen["y"] = spot[1]
        gen["destroyed"] = False
        gen["hp"] = gen["max_hp"]
        gen["spawn_tick"] = level_tick + random.randint(
            GENERATOR_SPAWN_MIN, GENERATOR_SPAWN_MAX)
        dungeon[spot[1]][spot[0]] = TILE_GENERATOR

        # Notify nearby players
        for p in self.players:
            if p.dead or p.depth != depth:
                continue
            dist = abs(p.x - spot[0]) + abs(p.y - spot[1])
            if dist <= FOV_RADIUS:
                self._tell(p, random.choice(MSG_GENERATOR_RESPAWN),
                           COLOR_MAGENTA)

    def _get_nearest_player(self, ex, ey, depth):
        """Return (player, distance) of the nearest alive player.

        Only considers players on the given depth.
        """
        best = None
        best_dist = float('inf')
        for p in self.players:
            if p.dead or p.depth != depth:
                continue
            dist = abs(p.x - ex) + abs(p.y - ey)
            if dist < best_dist:
                best = p
                best_dist = dist
        return best, best_dist

    def _process_enemy_action(self, enemy, depth, level_tick):
        """Process one action for an enemy: attack, chase, or wander."""
        ex, ey = enemy["x"], enemy["y"]
        target, dist = self._get_nearest_player(ex, ey, depth)
        if target is None:
            moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            random.shuffle(moves)
            moved = False
            for wdx, wdy in moves:
                wx, wy = ex + wdx, ey + wdy
                if (self.is_passable(wx, wy, depth)
                        and not self.get_enemy_at(wx, wy, depth)):
                    enemy["x"], enemy["y"] = wx, wy
                    moved = True
                    break
            if moved:
                self._ambient_sound(
                    enemy["x"], enemy["y"], depth,
                    ENEMY_SOUNDS.get(enemy["name"],
                                     ENEMY_SOUNDS_DEFAULT),
                    COLOR_WHITE, chance=0.09, range=37)
            enemy["next_tick"] = level_tick + TICK_MOVE
            return
        dungeon = self._get_dungeon(depth)
        player_on_depth = [
            p for p in self.players
            if p.depth == depth and not p.dead]
        combined_visible = [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
        for p in player_on_depth:
            fov = compute_fov(dungeon, p.x, p.y, FOV_RADIUS)
            for y in range(MAP_HEIGHT):
                for x in range(MAP_WIDTH):
                    if fov[y][x]:
                        combined_visible[y][x] = True
        can_see = (combined_visible[enemy["y"]][enemy["x"]]
                   and dist <= FOV_RADIUS + 2)

        if dist == 1:
            damage = self.do_attack(
                enemy["name"], enemy["attack"],
                target.name, target.defense_total(), 1)
            target.hp -= damage
            hit_template = random.choice(
                ENEMY_HIT_MESSAGES.get(enemy["name"],
                                       [ENEMY_HIT_DEFAULT]))
            self._broadcast(
                target.x, target.y, depth,
                hit_template, enemy["color"],
                subject=target, ctx={"damage": damage},
            )
            self._ambient_sound(
                target.x, target.y, depth, COMBAT_CLASH_AMBIENT,
                COLOR_WHITE, chance=0.5, range=38, flat=True)
            enemy["next_tick"] = level_tick + TICK_ATTACK
            if target.hp <= 0:
                target.hp = 0
                target.dead = True
                self.levels[depth]["corpses"].append({
                    "x": target.x,
                    "y": target.y,
                    "name": target.name,
                    "level": target.level,
                    "killer": enemy["name"],
                })
                self._broadcast(target.x, target.y, depth,
                                MSG_PLAYER_DIED, COLOR_RED, subject=target)
                self._ambient_sound(
                    target.x, target.y, depth, PLAYER_DEATH_AMBIENT,
                    COLOR_RED, chance=1.0, range=38, flat=True,
                )
                alive = any(
                    p and not p.dead and not p.game_win
                    for p in self.players)
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
            moved = False
            if (self.is_passable(nx, ny, depth)
                    and not self.get_enemy_at(nx, ny, depth)
                    and (nx != target.x or ny != target.y)):
                enemy["x"], enemy["y"] = nx, ny
                moved = True
            else:
                moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
                random.shuffle(moves)
                for wdx, wdy in moves:
                    wx, wy = ex + wdx, ey + wdy
                    if (self.is_passable(wx, wy, depth)
                            and not self.get_enemy_at(wx, wy, depth)):
                        enemy["x"], enemy["y"] = wx, wy
                        moved = True
                        break
            if moved:
                self._ambient_sound(
                    enemy["x"], enemy["y"], depth,
                    ENEMY_SOUNDS.get(enemy["name"], ENEMY_SOUNDS_DEFAULT),
                    COLOR_WHITE, chance=0.09, range=37,
                )
            enemy["next_tick"] = level_tick + TICK_MOVE
        else:
            moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            random.shuffle(moves)
            moved = False
            for wdx, wdy in moves:
                wx, wy = ex + wdx, ey + wdy
                if (self.is_passable(wx, wy, depth)
                        and not self.get_enemy_at(wx, wy, depth)):
                    enemy["x"], enemy["y"] = wx, wy
                    moved = True
                    break
            if moved:
                self._ambient_sound(
                    enemy["x"], enemy["y"], depth,
                    ENEMY_SOUNDS.get(enemy["name"],
                                     ENEMY_SOUNDS_DEFAULT),
                    COLOR_WHITE, chance=0.09, range=37)
            enemy["next_tick"] = level_tick + TICK_MOVE

    def _do_go_down_stairs(self, player):
        """Move the player down one level via stairs-down tile."""
        dungeon = self._get_dungeon(player.depth)
        if dungeon[player.y][player.x] == TILE_STAIRS_DOWN:
            new_depth = player.depth + 1
            if new_depth >= MAX_DEPTH:
                self._broadcast(player.x, player.y, player.depth,
                                MSG_CONQUERED, COLOR_YELLOW, subject=player)
                player.game_win = True
                return
            self._ensure_level(new_depth)
            stairs_up_x, stairs_up_y = self._get_stairs_up(new_depth)
            old_x, old_y, old_depth = player.x, player.y, player.depth
            player.depth = new_depth
            player.x, player.y = self._find_open_spawn(
                stairs_up_x, stairs_up_y, new_depth,
                exclude_player=player)
            self._ensure_player_explored(player)
            self._ambient_sound(
                old_x, old_y, old_depth, STAIRS_DOWN_AMBIENT,
                COLOR_CYAN, source=player, chance=1.0,
                skip_visible=True, range=38, flat=True,
            )
            self._ambient_depth(
                new_depth, STAIRS_DOWN_DEPTH_AMBIENT,
                COLOR_CYAN, source=player,
                chance=1.0, skip_visible=True,
            )
            self._broadcast(
                old_x, old_y, old_depth,
                MSG_DESCENDED, COLOR_CYAN,
                subject=player,
                ctx={"depth": new_depth + 1},
            )
        else:
            self._tell(player, MSG_NO_STAIRS_DOWN, COLOR_CYAN)

    def _do_go_up_stairs(self, player):
        """Move the player up one level via stairs-up tile."""
        dungeon = self._get_dungeon(player.depth)
        if dungeon[player.y][player.x] == TILE_STAIRS_UP:
            if player.depth > 0:
                new_depth = player.depth - 1
                self._ensure_level(new_depth)
                stairs_down_x, stairs_down_y = self._get_stairs_down(new_depth)
                old_x, old_y, old_depth = player.x, player.y, player.depth
                player.depth = new_depth
                player.x, player.y = self._find_open_spawn(
                    stairs_down_x, stairs_down_y, new_depth,
                    exclude_player=player)
                self._ensure_player_explored(player)
                self._ambient_sound(
                    old_x, old_y, old_depth, STAIRS_UP_AMBIENT,
                    COLOR_CYAN, source=player, chance=1.0,
                    skip_visible=True, range=38, flat=True,
                )
                self._ambient_depth(
                    new_depth, STAIRS_UP_DEPTH_AMBIENT,
                    COLOR_CYAN, source=player,
                    chance=1.0, skip_visible=True,
                )
                self._broadcast(
                    old_x, old_y, old_depth,
                    MSG_ASCENDED, COLOR_CYAN,
                    subject=player,
                    ctx={"depth": new_depth + 1},
                )
            else:
                self._tell(player, MSG_CANNOT_GO_UP, COLOR_CYAN)
        else:
            self._tell(player, MSG_NO_STAIRS_UP, COLOR_CYAN)

    def _do_grab_item(self, player):
        """Pick up and apply the item at the player's position."""
        idx, item = self.get_item_at(player.x, player.y, player.depth)
        if item is None:
            self._tell(player, MSG_NOTHING_TO_GRAB, COLOR_CYAN)
            return
        kind = item["kind"]
        if kind == ITEM_POTION:
            heal = random.randint(5, 10)
            player.hp = min(player.hp + heal, player.max_hp)
            self._broadcast(
                player.x, player.y, player.depth,
                MSG_DRANK_POTION, COLOR_RED,
                subject=player, ctx={"heal": heal},
            )
        elif kind == ITEM_SWORD:
            player.weapon_bonus += item["bonus"]
            self._broadcast(
                player.x, player.y, player.depth,
                MSG_EQUIPPED_SWORD, COLOR_WHITE,
                subject=player, ctx={"bonus": item["bonus"]},
            )
        elif kind == ITEM_SHIELD:
            player.armor_bonus += item["bonus"]
            self._broadcast(
                player.x, player.y, player.depth,
                MSG_EQUIPPED_SHIELD, COLOR_CYAN,
                subject=player, ctx={"bonus": item["bonus"]},
            )
        elif kind == ITEM_GOLD:
            player.gold += item["value"]
            self._broadcast(
                player.x, player.y, player.depth,
                MSG_PICKED_UP_GOLD, COLOR_YELLOW,
                subject=player, ctx={"gold": item["value"]},
            )
        self._get_items(player.depth).pop(idx)

    def _do_rest(self, player):
        """Rest for a moment.

        Build up chance to heal 3HP with each contiguous rest.
        """
        if player.hp >= player.max_hp:
            player.consecutive_rests = 0
            self._broadcast(player.x, player.y, player.depth,
                            MSG_REST_NO_HEAL, COLOR_GREEN, subject=player)
            return
        player.consecutive_rests += 1
        if random.random() < 0.1:
            player.hp = min(player.hp + 3, player.max_hp)
            player.consecutive_rests = 0
            self._broadcast(player.x, player.y, player.depth,
                            MSG_REST_HEAL, COLOR_GREEN, subject=player)
        else:
            self._broadcast(player.x, player.y, player.depth,
                            MSG_REST_NO_HEAL, COLOR_GREEN, subject=player)

    def get_char_at(self, mx, my, player_idx=0):
        """Return the display character at (mx, my).

        Respects explored/visible state.
        """
        if mx < 0 or mx >= MAP_WIDTH or my < 0 or my >= MAP_HEIGHT:
            return ' '
        player = (self.players[player_idx]
                  if 0 <= player_idx < len(self.players) else None)
        if player is None:
            return ' '
        depth = player.depth
        explored_grid = player.explored.get(
            depth, [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)])
        if not explored_grid[my][mx]:
            return ' '
        tile = self._get_dungeon(depth)[my][mx]
        return TILE_CHAR.get(tile, '?')

    def print_text_map(self):
        """Print the current map view as plain text for debugging."""
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
            bar = (
                f"{pl.name} | D{pl.depth + 1} | Lv{pl.level} | "
                f"HP {pl.hp}/{pl.max_hp} | "
                f"ATK {pl.attack_total()} | DEF {pl.defense_total()} | "
                f"XP {pl.xp}/{pl.next_level_xp} | Gold {pl.gold} "
                f"{'[WIN]' if pl.game_win else '[DEAD]' if pl.dead else ''}")
            print(bar.ljust(view_w))

        for sy in range(view_h):
            row = []
            for sx in range(view_w):
                mx = sx + start_x
                my = sy + start_y
                row.append(self.get_char_at(mx, my))
            print(''.join(row))

        for msg_text, _, _ in self.players[0].messages[-3:]:
            print(msg_text[:view_w])
        print("P1:Arrows  P2:WASD  >:Down  <:Up  g/G:Grab  /*:Rest  q:Quit")
        print(f"{'=' * view_w}")


def run_text_mode():
    """Create a game with two test players.

    Render one frame as plain text.
    """
    game = Game()
    game._init_level(0)
    spawn_x, spawn_y = game.levels[0]["spawn_x"], game.levels[0]["spawn_y"]
    game.players = [
        Player("Hero1", "@", spawn_x, spawn_y, COLOR_YELLOW, 0),
        Player("Hero2", "@", spawn_x + 1, spawn_y, COLOR_GREEN, 0),
    ]
    game._update_visibility()
    game._update_explored()
    game.print_text_map()


if __name__ == "__main__":
    run_text_mode()
