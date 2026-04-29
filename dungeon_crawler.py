#!/usr/bin/env python3
"""
Dungeon Crawler - A terminal roguelike game.
Use arrow keys or WASD to move. Bump into enemies to attack.
Press > or . to go down stairs. g to grab items.
"""

import curses
import random
import copy
import math
import sys

# --- Constants ---
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
    TILE_WALL: curses.COLOR_BLUE,
    TILE_FLOOR: curses.COLOR_BLUE,
    TILE_DOOR: curses.COLOR_YELLOW,
    TILE_STAIRS_DOWN: curses.COLOR_YELLOW,
    TILE_STAIRS_UP: curses.COLOR_YELLOW,
}

# Entity types
ENEMY_ORC = "orc"
ENEMY_GOLEM = "golem"
ENEMY_SNAKE = "snake"
ENEMY_DEMON = "demon"
ENEMY_DRAGON = "dragon"

ENEMY_PROPS = {
    ENEMY_ORC: {"char": "o", "color": curses.COLOR_GREEN, "name": "Orc", "hp": 10, "attack": 3, "defense": 1, "xp": 5},
    ENEMY_GOLEM: {"char": "G", "color": curses.COLOR_CYAN, "name": "Golem", "hp": 20, "attack": 5, "defense": 4, "xp": 15},
    ENEMY_SNAKE: {"char": "s", "color": curses.COLOR_RED, "name": "Snake", "hp": 5, "attack": 2, "defense": 0, "xp": 3},
    ENEMY_DEMON: {"char": "D", "color": curses.COLOR_RED, "name": "Demon", "hp": 30, "attack": 8, "defense": 3, "xp": 30},
    ENEMY_DRAGON: {"char": "D", "color": curses.COLOR_RED, "name": "Dragon", "hp": 50, "attack": 12, "defense": 5, "xp": 50},
}

ITEM_POTION = "potion"
ITEM_SWORD = "sword"
ITEM_SHIELD = "shield"
ITEM_GOLD = "gold"

ITEM_PROPS = {
    ITEM_POTION: {"char": "!", "color": curses.COLOR_RED, "name": "Health Potion"},
    ITEM_SWORD: {"char": "/", "color": curses.COLOR_WHITE, "name": "Sword"},
    ITEM_SHIELD: {"char": ")", "color": curses.COLOR_CYAN, "name": "Shield"},
    ITEM_GOLD: {"char": ",", "color": curses.COLOR_YELLOW, "name": "Gold"},
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
            if (new_room.x1 <= other.x2 and new_room.x2 >= other.x1 and
                new_room.y1 <= other.y2 and new_room.y2 >= other.y1):
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
                    if ((y - 1 >= 0 and dungeon[y-1][x] == TILE_WALL and y + 1 < MAP_HEIGHT and dungeon[y+1][x] == TILE_WALL) or
                        (x - 1 >= 0 and dungeon[y][x-1] == TILE_WALL and x + 1 < MAP_WIDTH and dungeon[y][x+1] == TILE_WALL)):
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
        0: [ENEMY_SNAKE, ENEMY_SNAKE, ENEMY_ORC],
        1: [ENEMY_SNAKE, ENEMY_ORC, ENEMY_ORC],
        2: [ENEMY_ORC, ENEMY_ORC, ENEMY_GOLEM],
        3: [ENEMY_ORC, ENEMY_GOLEM, ENEMY_GOLEM],
        4: [ENEMY_GOLEM, ENEMY_DEMON],
        5: [ENEMY_GOLEM, ENEMY_DEMON, ENEMY_DEMON],
        6: [ENEMY_DEMON, ENEMY_DEMON, ENEMY_DRAGON],
        7: [ENEMY_DEMON, ENEMY_DRAGON],
        8: [ENEMY_DRAGON, ENEMY_DRAGON],
        9: [ENEMY_DRAGON, ENEMY_DRAGON],
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


# --- Game State ---
class Game:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.depth = 0
        self.messages = []
        self.game_over = False
        self.game_win = False
        self.message_log = []

        # Player stats
        self.player_hp = 30
        self.player_max_hp = 30
        self.player_attack = 5
        self.player_defense = 1
        self.player_level = 1
        self.player_xp = 0
        self.player_next_level_xp = 10
        self.player_weapon_bonus = 0
        self.player_armor_bonus = 0
        self.player_gold = 0
        self.player_name = "Hero"

        self._init_curses()
        self.new_dungeon()

    def _init_curses(self):
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        for i in range(16):
            curses.init_pair(i + 1, i, -1)
        self.stdscr.nodelay(False)
        self.stdscr.keypad(True)

    def new_dungeon(self, from_stairs_up=False):
        self.dungeon, rooms = create_dungeon(self.depth)
        self.explored = [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
        self.player_x, self.player_y, self.enemies, self.items = place_entities(rooms, self.dungeon, self.depth)
        self.visible = compute_fov(self.dungeon, self.player_x, self.player_y, FOV_RADIUS)
        self._update_explored()
        if not from_stairs_up:
            self.msg(f"You descend into the dungeon. (Depth: {self.depth + 1})")
        else:
            self.msg(f"You go back up. (Depth: {self.depth + 1})")

    def _update_explored(self):
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                if self.visible[y][x]:
                    self.explored[y][x] = True

    def msg(self, text, color=curses.COLOR_WHITE):
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

    def player_attack_total(self):
        return self.player_attack + self.player_weapon_bonus

    def player_defense_total(self):
        return self.player_defense + self.player_armor_bonus

    def do_attack(self, attacker_name, attacker_atk, defender_name, defender_def, damage_variance=2):
        damage = max(1, attacker_atk - defender_def + random.randint(-damage_variance, damage_variance))
        return damage

    def move_player(self, dx, dy):
        if self.game_over or self.game_win:
            return
        nx, ny = self.player_x + dx, self.player_y + dy
        if not self.is_passable(nx, ny):
            return

        enemy = self.get_enemy_at(nx, ny)
        if enemy:
            self.combat_attack(enemy)
        else:
            self.player_x, self.player_y = nx, ny

        self.visible = compute_fov(self.dungeon, self.player_x, self.player_y, FOV_RADIUS)
        self._update_explored()
        self._enemy_turn()

    def combat_attack(self, enemy):
        damage = self.do_attack(self.player_name, self.player_attack_total(),
                                 enemy["name"], enemy["defense"])
        enemy["hp"] -= damage
        self.msg(f"You hit the {enemy['name']} for {damage} damage!", curses.COLOR_WHITE)
        if enemy["hp"] <= 0:
            self.msg(f"The {enemy['name']} dies!", curses.COLOR_RED)
            self.player_xp += enemy["xp"]
            self._check_level_up()

    def _check_level_up(self):
        while self.player_xp >= self.player_next_level_xp:
            self.player_xp -= self.player_next_level_xp
            self.player_level += 1
            self.player_max_hp += 5
            self.player_hp = min(self.player_hp + 5, self.player_max_hp)
            self.player_attack += 1
            self.player_defense += 1
            self.player_next_level_xp = int(self.player_next_level_xp * 1.5)
            self.msg(f"Congratulations! You are now level {self.player_level}!", curses.COLOR_YELLOW)

    def _enemy_turn(self):
        for enemy in self.enemies:
            if enemy["hp"] <= 0:
                continue
            if not self.visible[enemy["y"]][enemy["x"]]:
                continue  # Only act if visible to player (simple AI)

            ex, ey = enemy["x"], enemy["y"]
            px, py = self.player_x, self.player_y
            dist = abs(px - ex) + abs(py - ey)

            if dist > FOV_RADIUS + 2:
                continue

            if dist == 1:
                # Adjacent - attack player
                damage = self.do_attack(enemy["name"], enemy["attack"],
                                         self.player_name, self.player_defense_total(), 1)
                self.player_hp -= damage
                self.msg(f"The {enemy['name']} hits you for {damage} damage!", enemy["color"])
                if self.player_hp <= 0:
                    self.player_hp = 0
                    self.msg("You have died!", curses.COLOR_RED)
                    self.game_over = True
                    return
            else:
                # Move toward player (simple chase)
                dx = 0
                dy = 0
                if abs(px - ex) > abs(py - ey):
                    dx = 1 if px > ex else -1
                else:
                    dy = 1 if py > ey else -1

                nx, ny = ex + dx, ey + dy
                if self.is_passable(nx, ny) and not self.get_enemy_at(nx, ny) and (nx != px or ny != py):
                    enemy["x"], enemy["y"] = nx, ny

    def go_down_stairs(self):
        if self.dungeon[self.player_y][self.player_x] == TILE_STAIRS_DOWN:
            self.depth += 1
            if self.depth >= MAX_DEPTH:
                self.msg("You have conquered the dungeon!", curses.COLOR_YELLOW)
                self.game_win = True
                return
            self.new_dungeon()
        else:
            self.msg("No stairs here.", curses.COLOR_CYAN)

    def go_up_stairs(self):
        if self.dungeon[self.player_y][self.player_x] == TILE_STAIRS_UP and self.depth > 0:
            self.depth -= 1
            self.new_dungeon(from_stairs_up=True)
        elif self.depth > 0:
            self.depth -= 1
            self.new_dungeon(from_stairs_up=True)
        else:
            self.msg("Can't go up further.", curses.COLOR_CYAN)

    def grab_item(self):
        idx, item = self.get_item_at(self.player_x, self.player_y)
        if item is None:
            self.msg("Nothing to grab here.", curses.COLOR_CYAN)
            return

        kind = item["kind"]
        if kind == ITEM_POTION:
            heal = random.randint(5, 10)
            self.player_hp = min(self.player_hp + heal, self.player_max_hp)
            self.msg(f"You drink a potion. Recovered {heal} HP.", curses.COLOR_RED)
        elif kind == ITEM_SWORD:
            old = self.player_weapon_bonus
            self.player_weapon_bonus += item["bonus"]
            self.msg(f"You equip a sword (+{item['bonus']} attack).", curses.COLOR_WHITE)
        elif kind == ITEM_SHIELD:
            old = self.player_armor_bonus
            self.player_armor_bonus += item["bonus"]
            self.msg(f"You equip a shield (+{item['bonus']} defense).", curses.COLOR_CYAN)
        elif kind == ITEM_GOLD:
            self.player_gold += item["value"]
            self.msg(f"You pick up {item['value']} gold.", curses.COLOR_YELLOW)

        self.items.pop(idx)

    def wait_turn(self):
        """Wait a turn (rest). Heal 1 HP."""
        if self.player_hp < self.player_max_hp:
            self.player_hp += 1
            self.msg("You rest for a moment. (+1 HP)", curses.COLOR_GREEN)
        self._enemy_turn()

    def handle_input(self, key):
        if self.game_over or self.game_win:
            if key in (ord('q'), ord('Q'), 27):  # q or Escape
                sys.exit(0)
            return

        actions = {
            ord('h'): (-1, 0), ord('j'): (0, 1), ord('k'): (0, -1), ord('l'): (1, 0),
            ord('y'): (-1, -1), ord('u'): (1, -1), ord('b'): (-1, 1), ord('n'): (1, 1),
            curses.KEY_LEFT: (-1, 0), curses.KEY_DOWN: (0, 1), curses.KEY_UP: (0, -1),
            curses.KEY_RIGHT: (1, 0),
            ord('a'): (-1, 0), ord('s'): (0, 1), ord('w'): (0, -1), ord('d'): (1, 0),
        }

        if key in actions:
            self.move_player(*actions[key])
        elif key in (ord('>'), ord('=')):
            self.go_down_stairs()
        elif key in (ord('<'), ord('-')):
            self.go_up_stairs()
        elif key in (ord('g'),):
            self.grab_item()
        elif key in (ord('/'),):
            self.wait_turn()
        elif key in (ord('q'), ord('Q'), 27):
            sys.exit(0)

    def get_char_at(self, mx, my):
        """Return the character to display at map position (mx, my)."""
        if mx < 0 or mx >= MAP_WIDTH or my < 0 or my >= MAP_HEIGHT:
            return ' '
        is_explored = self.explored[my][mx]
        is_visible = self.visible[my][mx]
        if not is_explored:
            return ' '
        enemy = self.get_enemy_at(mx, my)
        if enemy and is_visible:
            return enemy["char"]
        if mx == self.player_x and my == self.player_y:
            return '@'
        _, item = self.get_item_at(mx, my)
        if item and is_visible:
            return ITEM_PROPS[item["kind"]]["char"]
        tile = self.dungeon[my][mx]
        return TILE_CHAR.get(tile, '?')

    def print_text_map(self):
        """Print the map as plain text (no curses)."""
        view_h = MAX_SCREEN_Y - 4
        view_w = MAX_SCREEN_X
        start_x = max(0, min(self.player_x - view_w // 2, MAP_WIDTH - view_w))
        start_y = max(0, min(self.player_y - view_h // 2, MAP_HEIGHT - view_h))

        print(f"{'=' * view_w}")
        bar = (f"{self.player_name} | Lv{self.player_level} | "
               f"HP {self.player_hp}/{self.player_max_hp} | "
               f"ATK {self.player_attack_total()} | DEF {self.player_defense_total()} | "
               f"XP {self.player_xp}/{self.player_next_level_xp} | "
               f"Gold {self.player_gold} | Depth {self.depth + 1}/{MAX_DEPTH}")
        print(bar.ljust(view_w))

        for sy in range(view_h):
            row = []
            for sx in range(view_w):
                mx = sx + start_x
                my = sy + start_y
                row.append(self.get_char_at(mx, my))
            print(''.join(row))

        for msg_text, _ in self.message_log[-3:]:
            print(msg_text[:view_w])
        print(f"WASD/HJKL:Move  >:Down  <:Up  g:Grab  /:Wait  q:Quit")
        print(f"{'=' * view_w}")

    def render(self):
        self.stdscr.erase()

        view_h = MAX_SCREEN_Y - 4
        view_w = MAX_SCREEN_X
        start_x = max(0, min(self.player_x - view_w // 2, MAP_WIDTH - view_w))
        start_y = max(0, min(self.player_y - view_h // 2, MAP_HEIGHT - view_h))

        for sy in range(view_h):
            row_chars = []
            for sx in range(view_w):
                mx = sx + start_x
                my = sy + start_y
                ch = self.get_char_at(mx, my)
                row_chars.append(ch)
                enemy = self.get_enemy_at(mx, my)
                if enemy and self.visible[my][mx]:
                    color = enemy["color"]
                    attr = curses.color_pair(color + 1) | curses.A_BOLD
                    try:
                        self.stdscr.addch(sy, sx, ord(ch), attr)
                    except curses.error:
                        pass
                else:
                    try:
                        self.stdscr.addch(sy, sx, ch)
                    except curses.error:
                        pass

        bar = (f"{self.player_name} | Lv{self.player_level} | "
               f"HP {self.player_hp}/{self.player_max_hp} | "
               f"ATK {self.player_attack_total()} | DEF {self.player_defense_total()} | "
               f"XP {self.player_xp}/{self.player_next_level_xp} | "
               f"Gold {self.player_gold} | Depth {self.depth + 1}/{MAX_DEPTH}")
        try:
            self.stdscr.addstr(view_h, 0, bar.ljust(view_w))
        except curses.error:
            pass

        for i, (msg_text, _) in enumerate(self.message_log[-2:]):
            try:
                self.stdscr.addstr(view_h + 1 + i, 0, msg_text.ljust(view_w))
            except curses.error:
                pass

        help_text = "WASD/HJKL:Move  >:Down  <:Up  g:Grab  /:Wait  q:Quit"
        try:
            self.stdscr.addstr(MAX_SCREEN_Y - 1, 0, help_text.ljust(view_w))
        except curses.error:
            pass

        if self.game_over:
            self._show_overlay("YOU HAVE DIED", "Press q to quit.", curses.COLOR_RED)
        elif self.game_win:
            self._show_overlay("YOU CONQUERED THE DUNGEON!", f"Final: Lv{self.player_level}, Gold:{self.player_gold}. Press q to quit.",
                                curses.COLOR_GREEN)

        self.stdscr.refresh()

    def _show_overlay(self, title, subtitle, color):
        try:
            self.stdscr.addstr(10, 25, title, curses.color_pair(color + 1) | curses.A_BOLD)
            self.stdscr.addstr(12, 20, subtitle, curses.color_pair(curses.COLOR_WHITE + 1))
        except curses.error:
            pass

    def run(self):
        while True:
            self.render()
            key = self.stdscr.getch()
            self.handle_input(key)


def main(stdscr):
    game = Game(stdscr)
    game.run()


def run_text_mode():
    """Run a single frame in text mode for debugging."""
    depth = 0
    dungeon, rooms = create_dungeon(depth)
    player_x, player_y, enemies, items = place_entities(rooms, dungeon, depth)
    visible = compute_fov(dungeon, player_x, player_y, FOV_RADIUS)
    explored = [[False] * MAP_WIDTH for _ in range(MAP_HEIGHT)]
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            if visible[y][x]:
                explored[y][x] = True

    view_h = MAX_SCREEN_Y - 4
    view_w = MAX_SCREEN_X
    start_x = max(0, min(player_x - view_w // 2, MAP_WIDTH - view_w))
    start_y = max(0, min(player_y - view_h // 2, MAP_HEIGHT - view_h))

    print(f"{'=' * view_w}")
    print(f"Player at ({player_x}, {player_y}), Rooms: {len(rooms)}")
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
            if mx == player_x and my == player_y:
                row.append('@')
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
    if '--text' in sys.argv:
        run_text_mode()
    else:
        curses.wrapper(main)
