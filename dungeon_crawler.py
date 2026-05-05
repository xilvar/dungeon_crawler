#!/usr/bin/env python3
"""
Dungeon Crawler - A terminal roguelike game.
Use arrow keys or WASD to move. Bump into enemies to attack.
Press > or . to go down stairs. g to grab items.
"""

import random

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
TICK_MOVE = 20
TICK_ATTACK = 100
TICK_WAIT = 50
TICK_PLAYER_MOVE = 10
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
        self.rest_end_tick = None
        self.rest_progress_shown = 0
        self.dead = False
        self.game_win = False
        self.messages = []
        # Per-depth explored grids: {depth: 2D boolean grid}
        self.explored = {}

    def attack_total(self):
        return self.attack + self.weapon_bonus

    def defense_total(self):
        return self.defense + self.armor_bonus


# --- Game State ---
class Game:
    def __init__(self):
        self.game_over = False
        self.players = []
        self.levels = {}
        self.tick = 0

        self._init_level(0)

    def _get_dungeon(self, depth):
        return self.levels[depth]["dungeon"]

    def _get_enemies(self, depth):
        return self.levels[depth]["enemies"]

    def _get_items(self, depth):
        return self.levels[depth]["items"]

    def _get_stairs_down(self, depth):
        return self.levels[depth]["stairs_down_x"], self.levels[depth]["stairs_down_y"]

    def _get_stairs_up(self, depth):
        return self.levels[depth]["stairs_up_x"], self.levels[depth]["stairs_up_y"]

    def _ensure_level(self, depth):
        """Ensure a level exists at the given depth, creating it if needed."""
        if depth not in self.levels:
            self._init_level(depth)

    def _init_level(self, depth):
        """Generate a new dungeon level at the given depth."""
        dungeon, rooms = create_dungeon(depth)
        px, py, enemies, items = place_entities(rooms, dungeon, depth)

        start_room = rooms[0]
        end_room = rooms[-1]

        stairs_down_x, stairs_down_y = end_room.center_x, end_room.center_y

        stairs_up_x = start_room.center_x
        stairs_up_y = start_room.center_y
        while stairs_up_x == px and stairs_up_y == py:
            stairs_up_y += 1

        if depth > 0:
            dungeon[stairs_up_y][stairs_up_x] = TILE_STAIRS_UP

        self.levels[depth] = {
            "dungeon": dungeon,
            "enemies": enemies,
            "items": items,
            "corpses": [],
            "stairs_down_x": stairs_down_x,
            "stairs_down_y": stairs_down_y,
            "stairs_up_x": stairs_up_x,
            "stairs_up_y": stairs_up_y,
            "spawn_x": px,
            "spawn_y": py,
        }

        for e in enemies:
            e["next_tick"] = self.tick + random.randint(0, 99)

    def _ensure_player_explored(self, player):
        """Ensure a player has an explored grid for their current depth."""
        if player.depth not in player.explored:
            player.explored[player.depth] = [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]

    def _update_visibility(self):
        old_visible = self.player_visible if hasattr(self, 'player_visible') else []
        self.player_visible = []
        for i, p in enumerate(self.players):
            if not p.dead:
                dungeon = self._get_dungeon(p.depth)
                fov = compute_fov(dungeon, p.x, p.y, FOV_RADIUS)
                self.player_visible.append(fov)
            else:
                self.player_visible.append([[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)])

        # Detect enemies that just came into view
        for i, p in enumerate(self.players):
            if p.dead:
                continue
            old_fov = old_visible[i] if i < len(old_visible) else [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
            new_fov = self.player_visible[i]
            for e in self._get_enemies(p.depth):
                if e["hp"] <= 0:
                    continue
                if new_fov[e["y"]][e["x"]] and not old_fov[e["y"]][e["x"]]:
                    self._tell(p, f"A {e['name']} comes into view.", e["color"])

    def _update_explored(self):
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

    def _tell(self, player, text, color=COLOR_WHITE):
        """Send a message to a specific player, resolving {name} to 'You'."""
        resolved = text.replace("{name}", "You")
        player.messages.append((resolved, color))
        if len(player.messages) > MAX_MSGS:
            player.messages.pop(0)

    def _broadcast(self, x, y, depth, text, color=COLOR_WHITE, subject=None):
        """Send a message to all alive players on the same depth who can see (x, y).
        Resolves {name} to 'You' for the subject player, actual name for others."""
        dungeon = self._get_dungeon(depth)
        for p in self.players:
            if p.dead or p.depth != depth:
                continue
            fov = compute_fov(dungeon, p.x, p.y, FOV_RADIUS)
            if fov[y][x]:
                if subject and p is subject:
                    resolved = text.replace("{name}", "You")
                else:
                    resolved = text.replace("{name}", subject.name if subject else "")
                p.messages.append((resolved, color))
                if len(p.messages) > MAX_MSGS:
                    p.messages.pop(0)

    def _ambient_sound(self, x, y, depth, messages, color, source=None, chance=0.35, skip_visible=False):
        """Send a random ambient message to nearby players on the same depth,
        with probability decreasing by distance. Skips the source player.
        When skip_visible is True, also skips players who can see the source."""
        dungeon = self._get_dungeon(depth)
        for p in self.players:
            if p.dead or p.depth != depth or p is source:
                continue
            dist = abs(p.x - x) + abs(p.y - y)
            if dist < 2 or dist > 25:
                continue
            if skip_visible and source:
                fov = compute_fov(dungeon, p.x, p.y, FOV_RADIUS)
                if fov[y][x]:
                    continue
            prob = max(0, chance * (1 - dist / 25))
            if random.random() < prob:
                self._tell(p, random.choice(messages), color)

    def _ambient_depth(self, depth, messages, color, source=None, chance=0.5, skip_visible=False):
        """Send a random ambient message to all alive players on a depth,
        regardless of distance. Skips the source player.
        When skip_visible is True, also skips players who can see the source."""
        dungeon = self._get_dungeon(depth)
        for p in self.players:
            if p.dead or p.depth != depth or p is source:
                continue
            if skip_visible and source:
                fov = compute_fov(dungeon, p.x, p.y, FOV_RADIUS)
                if fov[source.y][source.x]:
                    continue
            if random.random() < chance:
                self._tell(p, random.choice(messages), color)

    def is_passable(self, x, y, depth):
        if x < 0 or x >= MAP_WIDTH or y < 0 or y >= MAP_HEIGHT:
            return False
        tile = self._get_dungeon(depth)[y][x]
        if tile == TILE_WALL:
            return False
        return True

    def get_enemy_at(self, x, y, depth):
        for e in self._get_enemies(depth):
            if e["x"] == x and e["y"] == y and e["hp"] > 0:
                return e
        return None

    def get_item_at(self, x, y, depth):
        items = self._get_items(depth)
        for i, item in enumerate(items):
            if item["x"] == x and item["y"] == y:
                return i, item
        return None, None

    def _get_corpses(self, depth):
        return self.levels[depth]["corpses"]

    def get_corpse_at(self, x, y, depth):
        for c in self._get_corpses(depth):
            if c["x"] == x and c["y"] == y:
                return c
        return None

    def do_attack(self, attacker_name, attacker_atk, defender_name, defender_def, damage_variance=2):
        damage = max(1, attacker_atk - defender_def + random.randint(-damage_variance, damage_variance))
        return damage

    def queue_player_action(self, player_idx, action):
        if self.game_over:
            return
        player = self.players[player_idx]
        if player.game_win:
            return
        player.queued_action = action

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
            player.next_tick = self.tick + TICK_MOVE
        elif action_type == "stairs_up":
            self._do_go_up_stairs(player)
            player.next_tick = self.tick + TICK_MOVE
        elif action_type == "rest":
            self._do_rest(player)
            player.rest_end_tick = self.tick + TICK_PLAYER_REST
            player.rest_progress_shown = 0
            player.next_tick = player.rest_end_tick

    def _do_move(self, player, dx, dy):
        nx, ny = player.x + dx, player.y + dy
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
            self._ambient_sound(nx, ny, player.depth, [
                "You hear faint footsteps nearby.",
                "A faint sound of movement echoes through the dungeon.",
                "You hear something moving in the distance.",
            ], COLOR_WHITE, source=player, chance=0.25, skip_visible=True)
            corpse = self.get_corpse_at(nx, ny, player.depth)
            if corpse:
                self._tell(player,
                    f"You see the corpse of {corpse['name']} (lv {corpse['level']}). Looks like they were killed by a {corpse['killer']}.",
                    COLOR_RED)

    def _do_combat_attack(self, player, enemy):
        damage = self.do_attack(
            player.name, player.attack_total(),
            enemy["name"], enemy["defense"])
        enemy["hp"] -= damage
        self._broadcast(enemy["x"], enemy["y"], player.depth,
                        f"{{name}} hit the {enemy['name']} for {damage} damage!", COLOR_WHITE, subject=player)
        self._ambient_sound(enemy["x"], enemy["y"], player.depth, [
            "You hear the sharp clash of steel nearby.",
            "A sudden clash echoes through the dungeon.",
            "You hear something being struck in the distance.",
        ], COLOR_WHITE, source=player)
        if enemy["hp"] <= 0:
            self._broadcast(enemy["x"], enemy["y"], player.depth,
                            f"The {enemy['name']} dies!", COLOR_RED)
            self._ambient_sound(enemy["x"], enemy["y"], player.depth, [
                "You hear something collapse in the distance.",
                "A dying groan echoes nearby.",
                "You hear a wet thud from somewhere nearby.",
            ], COLOR_RED, source=player)
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
            self._broadcast(player.x, player.y, player.depth,
                            f"{{name}} is now level {player.level}!", COLOR_YELLOW, subject=player)

    def _process_tick(self):
        if self.game_over:
            return
        for i, player in enumerate(self.players):
            if player.dead or player.game_win:
                continue
            if self.tick >= player.next_tick:
                if player.queued_action is not None:
                    self.execute_player_action(i)
                else:
                    player.next_tick = self.tick + 1
        for depth in list(self.levels.keys()):
            for enemy in self._get_enemies(depth):
                if enemy["hp"] <= 0:
                    continue
                if self.tick >= enemy["next_tick"]:
                    self._process_enemy_action(enemy, depth)
        self._update_visibility()
        self._update_explored()

    def _get_nearest_player(self, ex, ey, depth):
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

    def _process_enemy_action(self, enemy, depth):
        ex, ey = enemy["x"], enemy["y"]
        target, dist = self._get_nearest_player(ex, ey, depth)
        if target is None:
            moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            random.shuffle(moves)
            moved = False
            for wdx, wdy in moves:
                wx, wy = ex + wdx, ey + wdy
                if self.is_passable(wx, wy, depth) and not self.get_enemy_at(wx, wy, depth):
                    enemy["x"], enemy["y"] = wx, wy
                    moved = True
                    break
            if moved:
                self._ambient_sound(enemy["x"], enemy["y"], depth, [
                    "You hear a faint scuttling in the darkness.",
                    "Something shifts in the shadows nearby.",
                    "You hear a low growl in the distance.",
                ], COLOR_WHITE, chance=0.09)
            enemy["next_tick"] = self.tick + TICK_MOVE
            return
        dungeon = self._get_dungeon(depth)
        player_on_depth = [p for p in self.players if p.depth == depth and not p.dead]
        combined_visible = [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
        for p in player_on_depth:
            fov = compute_fov(dungeon, p.x, p.y, FOV_RADIUS)
            for y in range(MAP_HEIGHT):
                for x in range(MAP_WIDTH):
                    if fov[y][x]:
                        combined_visible[y][x] = True
        can_see = combined_visible[enemy["y"]][enemy["x"]] and dist <= FOV_RADIUS + 2

        if dist == 1:
            damage = self.do_attack(
                enemy["name"], enemy["attack"],
                target.name, target.defense_total(), 1)
            target.hp -= damage
            self._broadcast(target.x, target.y, depth,
                            f"The {enemy['name']} hit {{name}} for {damage} damage!", enemy["color"], subject=target)
            self._ambient_sound(target.x, target.y, depth, [
                "You hear the sharp clash of steel nearby.",
                "A cry of pain echoes through the dungeon.",
                "You hear something being struck in the distance.",
            ], COLOR_WHITE)
            enemy["next_tick"] = self.tick + TICK_ATTACK
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
                                "{name} has died!", COLOR_RED, subject=target)
                self._ambient_sound(target.x, target.y, depth, [
                    "You hear someone cry out in agony nearby.",
                    "A terrible scream echoes through the dungeon.",
                    "You hear a body collapse in the distance.",
                ], COLOR_RED)
                alive = any(p and not p.dead and not p.game_win for p in self.players)
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
            if self.is_passable(nx, ny, depth) and not self.get_enemy_at(nx, ny, depth) and (nx != target.x or ny != target.y):
                enemy["x"], enemy["y"] = nx, ny
                moved = True
            else:
                moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
                random.shuffle(moves)
                for wdx, wdy in moves:
                    wx, wy = ex + wdx, ey + wdy
                    if self.is_passable(wx, wy, depth) and not self.get_enemy_at(wx, wy, depth):
                        enemy["x"], enemy["y"] = wx, wy
                        moved = True
                        break
            if moved:
                self._ambient_sound(enemy["x"], enemy["y"], depth, [
                    "You hear something heavy moving nearby.",
                    "A low growl echoes from somewhere in the dark.",
                    "You hear claws scraping against stone.",
                ], COLOR_WHITE, chance=0.09)
            enemy["next_tick"] = self.tick + TICK_MOVE
        else:
            moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            random.shuffle(moves)
            moved = False
            for wdx, wdy in moves:
                wx, wy = ex + wdx, ey + wdy
                if self.is_passable(wx, wy, depth) and not self.get_enemy_at(wx, wy, depth):
                    enemy["x"], enemy["y"] = wx, wy
                    moved = True
                    break
            if moved:
                self._ambient_sound(enemy["x"], enemy["y"], depth, [
                    "You hear a faint scuttling in the darkness.",
                    "Something shifts in the shadows nearby.",
                    "You hear a low growl in the distance.",
                ], COLOR_WHITE, chance=0.09)
            enemy["next_tick"] = self.tick + TICK_MOVE

    def _do_go_down_stairs(self, player):
        dungeon = self._get_dungeon(player.depth)
        if dungeon[player.y][player.x] == TILE_STAIRS_DOWN:
            new_depth = player.depth + 1
            if new_depth >= MAX_DEPTH:
                self._broadcast(player.x, player.y, player.depth,
                                "{name} has conquered the dungeon!", COLOR_YELLOW, subject=player)
                player.game_win = True
                return
            self._ensure_level(new_depth)
            stairs_up_x, stairs_up_y = self._get_stairs_up(new_depth)
            old_x, old_y, old_depth = player.x, player.y, player.depth
            player.depth = new_depth
            player.x, player.y = stairs_up_x, stairs_up_y
            self._ensure_player_explored(player)
            self._ambient_sound(old_x, old_y, old_depth, [
                "You hear footsteps descending the stairs.",
                "The sound of boots echoing down the staircase.",
                "Footsteps fade into the depths below.",
            ], COLOR_CYAN, source=player, chance=0.7, skip_visible=True)
            self._ambient_depth(new_depth, [
                "You hear footsteps ascending from below.",
                "Boots echo up the staircase.",
                "Footsteps approach from the stairs below.",
            ], COLOR_CYAN, source=player, skip_visible=True)
            self._broadcast(old_x, old_y, old_depth,
                            f"{{name}} descended deeper. (Depth: {new_depth + 1})", COLOR_CYAN, subject=player)
        else:
            self._tell(player, "{name}: no stairs down here.", COLOR_CYAN)

    def _do_go_up_stairs(self, player):
        dungeon = self._get_dungeon(player.depth)
        if dungeon[player.y][player.x] == TILE_STAIRS_UP:
            if player.depth > 0:
                new_depth = player.depth - 1
                self._ensure_level(new_depth)
                stairs_down_x, stairs_down_y = self._get_stairs_down(new_depth)
                old_x, old_y, old_depth = player.x, player.y, player.depth
                player.depth = new_depth
                player.x, player.y = stairs_down_x, stairs_down_y
                self._ensure_player_explored(player)
                self._ambient_sound(old_x, old_y, old_depth, [
                    "You hear footsteps ascending the stairs.",
                    "The sound of boots echoing up the staircase.",
                    "Footsteps fade upward into the darkness.",
                ], COLOR_CYAN, source=player, chance=0.7, skip_visible=True)
                self._ambient_depth(new_depth, [
                    "You hear footsteps ascending from below.",
                    "Boots echo up the staircase.",
                    "Footsteps approach from the stairs below.",
                ], COLOR_CYAN, source=player, skip_visible=True)
                self._broadcast(old_x, old_y, old_depth,
                                f"{{name}} went back up. (Depth: {new_depth + 1})", COLOR_CYAN, subject=player)
            else:
                self._tell(player, "{name}: can't go up further.", COLOR_CYAN)
        else:
            self._tell(player, "{name}: no stairs up here.", COLOR_CYAN)

    def _do_grab_item(self, player):
        idx, item = self.get_item_at(player.x, player.y, player.depth)
        if item is None:
            self._tell(player, "{name}: nothing to grab here.", COLOR_CYAN)
            return
        kind = item["kind"]
        if kind == ITEM_POTION:
            heal = random.randint(5, 10)
            player.hp = min(player.hp + heal, player.max_hp)
            self._broadcast(player.x, player.y, player.depth,
                            f"{{name}} drank a potion. Recovered {heal} HP.", COLOR_RED, subject=player)
        elif kind == ITEM_SWORD:
            player.weapon_bonus += item["bonus"]
            self._broadcast(player.x, player.y, player.depth,
                            f"{{name}} equipped a sword (+{item['bonus']} attack).", COLOR_WHITE, subject=player)
        elif kind == ITEM_SHIELD:
            player.armor_bonus += item["bonus"]
            self._broadcast(player.x, player.y, player.depth,
                            f"{{name}} equipped a shield (+{item['bonus']} defense).", COLOR_CYAN, subject=player)
        elif kind == ITEM_GOLD:
            player.gold += item["value"]
            self._broadcast(player.x, player.y, player.depth,
                            f"{{name}} picked up {item['value']} gold.", COLOR_YELLOW, subject=player)
        self._get_items(player.depth).pop(idx)

    def _do_rest(self, player):
        if not hasattr(player, '_consecutive_waits'):
            player._consecutive_waits = 0
        player._consecutive_waits += 1
        if player.hp < player.max_hp:
            player.hp += 1
            self._broadcast(player.x, player.y, player.depth,
                            "{name} rested for a moment. (+1 HP)", COLOR_GREEN, subject=player)
        else:
            self._broadcast(player.x, player.y, player.depth,
                            "{name} rested for a moment.", COLOR_GREEN, subject=player)
        chance = 0.05 * player._consecutive_waits + 0.02 * player.depth
        chance = min(chance, 0.7)
        if random.random() < chance:
            self._spawn_nearby_enemy(player)

    def _spawn_nearby_enemy(self, player):
        """Spawn a random enemy near the given player on their level."""
        depth = player.depth
        for _ in range(10):
            sx = player.x + random.randint(-5, 5)
            sy = player.y + random.randint(-5, 5)
            if sx == player.x and sy == player.y:
                continue
            if not (0 <= sx < MAP_WIDTH and 0 <= sy < MAP_HEIGHT):
                continue
            if not self.is_passable(sx, sy, depth):
                continue
            if self.get_enemy_at(sx, sy, depth):
                continue
            dist = abs(sx - player.x) + abs(sy - player.y)
            if dist < 4:
                continue
            etypes = list(ENEMY_PROPS.keys())
            etype = random.choice(etypes)
            prop = ENEMY_PROPS[etype]
            scale = 1 + depth * 0.15
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
            self._get_enemies(depth).append(enemy)
            self._broadcast(sx, sy, depth, f"A {prop['name']} appears!", COLOR_RED)
            self._ambient_sound(sx, sy, depth, [
                "You hear a sudden growl in the distance.",
                "Something stirs in the darkness nearby.",
                "A cold chill runs down your spine.",
            ], COLOR_RED, chance=0.09)
            return

    def get_char_at(self, mx, my, player_idx=0):
        """Return the character to display at map position (mx, my)."""
        if mx < 0 or mx >= MAP_WIDTH or my < 0 or my >= MAP_HEIGHT:
            return ' '
        player = self.players[player_idx] if 0 <= player_idx < len(self.players) else None
        if player is None:
            return ' '
        depth = player.depth
        explored_grid = player.explored.get(depth, [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)])
        p_visible = self.player_visible[player_idx] if 0 <= player_idx < len(self.player_visible) else [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
        is_explored = explored_grid[my][mx]
        is_visible = p_visible[my][mx]
        if not is_explored:
            return ' '
        enemy = self.get_enemy_at(mx, my, depth)
        if enemy and is_visible:
            return enemy["char"]
        for p in self.players:
            if p.depth == depth and mx == p.x and my == p.y and not p.dead and is_visible:
                return p.char
        _, item = self.get_item_at(mx, my, depth)
        if item and is_visible:
            return ITEM_PROPS[item["kind"]]["char"]
        corpse = self.get_corpse_at(mx, my, depth)
        if corpse and is_explored:
            return "_"
        tile = self._get_dungeon(depth)[my][mx]
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
            bar = (f"{pl.name} | D{pl.depth + 1} | Lv{pl.level} | HP {pl.hp}/{pl.max_hp} | "
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

        for msg_text, _ in self.players[0].messages[-3:]:
            print(msg_text[:view_w])
        print("P1:Arrows  P2:WASD  >:Down  <:Up  g/G:Grab  /*:Rest  q:Quit")
        print(f"{'=' * view_w}")


def run_text_mode():
    """Run a single frame in text mode for debugging."""
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
