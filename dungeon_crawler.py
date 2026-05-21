#!/usr/bin/env python3
"""Core game logic: dungeon generation, FOV, combat, entities, items, corpses,
ambient sounds, player state, and a text-mode renderer for debugging."""

import random
from collections import deque

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
    MSG_EQUIPPED_WEAPON,
    MSG_EQUIPPED_SHIELD,
    MSG_DROPPED_WEAPON,
    MSG_DROPPED_SHIELD,
    MSG_PICKED_UP_GOLD,
    MSG_REST_HEAL,
    MSG_REST_NO_HEAL,
    MSG_CRITICAL_HIT,
    MSG_GLANCING_HIT,
    MSG_ENEMY_DODGE,
    MSG_SHIELD_BLOCK,
    MSG_SHIELD_BLOCK_PARTIAL,
    MSG_STATUS_POISON_APPLY,
    MSG_STATUS_BURN_APPLY,
    MSG_STATUS_BLEED_APPLY,
    MSG_STATUS_CHILL_APPLY,
    MSG_STATUS_PARALYSIS_APPLY,
    MSG_STATUS_DO_TICK,
    MSG_STATUS_PARALYSIS_TICK,
    MSG_STATUS_WEAR_OFF,

    MSG_ENEMY_INTO_VIEW,
    MSG_PLAYER_INTO_VIEW,
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
    MSG_WALK_WALL,
    MSG_ENTER_WATER,
    MSG_LEAVE_WATER,
    MSG_STEP_TRAP,
    MSG_ENTRANCE_ROOMS,
    MSG_ENTRANCE_CAVES,
    MSG_ENTRANCE_LABYRINTH,
    MSG_ENTRANCE_TOWER,
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
MAX_ENEMIES_BASE = 15
MAX_ENEMIES_PER_DEPTH = 5

# Dungeon type strings
DUNGEON_TYPE_ROOMS = "rooms"
DUNGEON_TYPE_CAVES = "caves"
DUNGEON_TYPE_LABYRINTH = "labyrinth"
DUNGEON_TYPE_TOWER = "tower"
DUNGEON_TYPES = [DUNGEON_TYPE_ROOMS, DUNGEON_TYPE_CAVES, DUNGEON_TYPE_LABYRINTH, DUNGEON_TYPE_TOWER]

# Dungeon type depth thresholds
DUNGEON_FORCE_TOWER_DEPTH = MAX_DEPTH - 1
DUNGEON_FORCE_LABYRINTH_DEPTH = 8
DUNGEON_DEEP_MIX_MIN_DEPTH = 6
DUNGEON_MIX_MIN_DEPTH = 4
DUNGEON_CAVES_MIN_DEPTH = 2

# Action type strings
ACTION_MOVE = "move"
ACTION_WAIT = "wait"
ACTION_GRAB = "grab"
ACTION_STAIRS_DOWN = "stairs_down"
ACTION_STAIRS_UP = "stairs_up"

# Combat thresholds
PERCENTILE_ROLL_MIN = 1
PERCENTILE_ROLL_MAX = 100
ENEMY_ATTACK_VARIANCE_MIN = -1
ENEMY_ATTACK_VARIANCE_MAX = 1
ENEMY_ATTACK_RANGE = 1
ENEMYCHASE_FOV_EXTENSION = 2
WATER_ENEMY_ADJACENT_VISIBLE_RANGE = 1

# Trap values
TRAP_DAMAGE_BASE = 3
TRAP_DAMAGE_PER_DEPTH = 2
TRAP_CHANCE_PER_DEPTH = 0.006

# Player level-up
LEVEL_UP_HP_GAIN = 5
LEVEL_UP_XP_SCALE_FACTOR = 1.5

# Status effect DoT damage
POISON_DOT_DAMAGE_MIN = 1
POISON_DOT_DAMAGE_MAX = 2
BURN_DOT_DAMAGE_BASE = 1
BURN_DOT_DEPTH_DIVISOR = 2
BLEED_DOT_ATTACK_DIVISOR = 3
STATUS_DOT_DAMAGE_FALLBACK = 1

# Item spawn chances (room-based dungeons)
ITEM_POTION_SPAWN_CHANCE = 0.5
ITEM_GOLD_SPAWN_CHANCE = 0.3
ITEM_WEAPON_SPAWN_CHANCE = 0.22
ITEM_SHIELD_SPAWN_CHANCE = 0.15
GOLD_VALUE_MIN = 5
GOLD_VALUE_MAX = 15
START_ROOM_POTIONS_MIN = 1
START_ROOM_POTIONS_MAX = 3

# Item spawn chances (cave/labyrinth/tower dungeons)
CAVE_ITEMS_BASE_COUNT = 2
CAVE_ITEMS_DEPTH_DIVISOR = 2
CAVE_ITEM_POTION_THRESHOLD = 0.25
CAVE_ITEM_WEAPON_THRESHOLD = 0.55
CAVE_ITEM_SHIELD_THRESHOLD = 0.77
CAVE_GOLD_VALUE_MIN = 5
CAVE_GOLD_VALUE_MAX = 20
CAVE_GOLD_VALUE_PER_DEPTH = 5

# Cave enemy limits
CAVE_MAX_ENEMIES_BASE = 16
CAVE_MAX_ENEMIES_PER_DEPTH = 6
CAVE_MAX_ENEMIES_CAP = 60
CAVE_WATER_ENEMIES_BASE = 2
CAVE_WATER_ENEMIES_CAP = 10

# Enemy stat scaling per depth
ENEMY_HP_SCALE_PER_DEPTH = 2
ENEMY_ATTACK_SCALE_PER_DEPTH = 1
ENEMY_DEFENSE_DEPTH_DIVISOR = 2
ENEMY_XP_SCALE_PER_DEPTH = 5

# Generator stats
GENERATOR_HP_MULTIPLIER = 5
GENERATOR_HP_PER_DEPTH = 10
GENERATOR_DEFENSE_MAX = 6

# Room-based dungeon enemy scaling
ENEMY_STATS_BASE_SCALE = 1
ENEMY_STATS_DEPTH_SCALE_FACTOR = 0.15

# Dungeon generation
DUNGEON_MIN_ROOMS_REQUIRED = 5
DUNGEON_MIN_ROOMS_VALID = 2
DUNGEON_MIN_WALL_FRACTION_DIVISOR = 10
CAVE_OPEN_TILE_MIN_FLOOR_NEIGHBORS = 3
LABYRINTH_OPEN_TILE_MIN_FLOOR_NEIGHBORS = 2
LABYRINTH_DEAD_END_FLOOR_NEIGHBORS = 1
TOWER_MIN_RING_WIDTH = 3
TOWER_MIN_RINGS_BASE = 3
TOWER_RINGS_DEPTH_DIVISOR = 3
TOWER_MAX_RINGS = 5

# Potion healing
POTION_HEAL_MIN = 5
POTION_HEAL_MAX = 10

# Rest healing
REST_HEAL_CHANCE = 0.1
REST_HEAL_AMOUNT = 3

# Water movement
WATER_MOVE_SPEED_PENALTY = 2

# Game tick intervals
PARALYSIS_STATUS_MSG_INTERVAL = 20
IDLE_LEVEL_TICK_INTERVAL = 10
MAX_TICK_ADVANCE_PLAYER_COUNT = 4

# Player initial tick
PLAYER_INITIAL_TICK_RANGE_MIN = 0
PLAYER_INITIAL_TICK_RANGE_MAX = 99

# Ambient sound defaults
AMBIENT_SOUND_DEFAULT_CHANCE = 0.35
AMBIENT_SOUND_DEFAULT_RANGE = 25
AMBIENT_DEPTH_DEFAULT_CHANCE = 0.5
AMBIENT_SOUND_MIN_DIST = 2
PLAYER_MOVE_AMBIENT_CHANCE = 0.08
PLAYER_MOVE_AMBIENT_RANGE = 38
COMBAT_CLASH_AMBIENT_CHANCE = 0.5
COMBAT_AMBIENT_RANGE = 38
ENEMY_DEATH_AMBIENT_CHANCE = 1.0
ENEMY_DEATH_AMBIENT_RANGE = 38
STAIRS_AMBIENT_RANGE = 38
ENEMY_MOVE_AMBIENT_CHANCE = 0.09
ENEMY_MOVE_AMBIENT_RANGE = 37

# Text-mode renderer
TEXT_MAP_STATUS_LINES = 4
TEXT_MAP_DISPLAY_MSG_COUNT = 3


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
TILE_WATER = 7
TILE_TRAP = 8

# Tile rendering
TILE_CHAR = {
    TILE_WALL: "#",
    TILE_FLOOR: ".",
    TILE_DOOR_CLOSED: "+",
    TILE_STAIRS_DOWN: ">",
    TILE_STAIRS_UP: "<",
    TILE_DOOR_OPEN: "-",
    TILE_GENERATOR: "*",
    TILE_WATER: "~",
    TILE_TRAP: ",",
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
ENEMY_WATER_MITE = "water_mite"
ENEMY_WATER_SNAKE = "water_snake"
ENEMY_DEEP_ONE = "deep_one"
ENEMY_WATER_ELEMENTAL = "water_elemental"
ENEMY_KRAKEN = "kraken"

# Status effect definitions (must be before ENEMY_PROPS which references them)
STATUS_POISON = "poison"
STATUS_BURN = "burn"
STATUS_BLEED = "bleed"
STATUS_CHILL = "chill"
STATUS_PARALYSIS = "paralysis"

STATUS_EFFECT_DURATION = 200  # 2 seconds at 100 ticks/sec
STATUS_EFFECT_TICK_INTERVAL = 20  # apply DoT every 20 ticks
STATUS_EFFECT_CHANCE = 30  # 30% chance per hit

ENEMY_PROPS = {
    # Tier 1 - vermin/scavengers
    ENEMY_RAT: {
        "char": "r", "color": COLOR_YELLOW, "name": "Rat",
        "hp": 3, "attack": 1, "defense": 0, "xp": 1,
        "dodge": 3,
    },
    ENEMY_BAT: {
        "char": "b", "color": COLOR_YELLOW, "name": "Bat",
        "hp": 2, "attack": 1, "defense": 0, "xp": 1,
        "dodge": 5,
    },
    ENEMY_SPIDER: {
        "char": "S", "color": COLOR_YELLOW, "name": "Spider",
        "hp": 4, "attack": 2, "defense": 0, "xp": 2,
        "dodge": 3, "status_effect": STATUS_POISON,
    },
    ENEMY_KOBOLD: {
        "char": "k", "color": COLOR_YELLOW, "name": "Kobold",
        "hp": 5, "attack": 2, "defense": 0, "xp": 2,
        "dodge": 3,
    },
    ENEMY_GNOME: {
        "char": "g", "color": COLOR_YELLOW, "name": "Goblin",
        "hp": 7, "attack": 2, "defense": 0, "xp": 2,
        "dodge": 3,
    },
    # Tier 2 - common threats
    ENEMY_IMP: {
        "char": "i", "color": COLOR_RED, "name": "Imp",
        "hp": 6, "attack": 3, "defense": 0, "xp": 4,
        "dodge": 5,
    },
    ENEMY_SKELETON: {
        "char": "s", "color": COLOR_WHITE, "name": "Skeleton",
        "hp": 8, "attack": 3, "defense": 1, "xp": 4,
        "dodge": 5,
    },
    ENEMY_ZOMBIE: {
        "char": "Z", "color": COLOR_GREEN, "name": "Zombie",
        "hp": 12, "attack": 2, "defense": 0, "xp": 3,
        "dodge": 3,
    },
    ENEMY_WOLF: {
        "char": "W", "color": COLOR_WHITE, "name": "Wolf",
        "hp": 8, "attack": 4, "defense": 0, "xp": 3,
        "dodge": 5,
    },
    # Tier 3 - undead/horrors
    ENEMY_HYDRA: {
        "char": "H", "color": COLOR_GREEN, "name": "Hydra",
        "hp": 35, "attack": 8, "defense": 3, "xp": 30,
        "dodge": 5, "status_effect": STATUS_POISON,
    },
    ENEMY_MUMMY: {
        "char": "M", "color": COLOR_YELLOW, "name": "Mummy",
        "hp": 18, "attack": 4, "defense": 2, "xp": 10,
        "dodge": 5,
    },
    ENEMY_WRAITH: {
        "char": "W", "color": COLOR_CYAN, "name": "Wraith",
        "hp": 15, "attack": 5, "defense": 2, "xp": 12,
        "dodge": 7, "status_effect": STATUS_CHILL,
    },
    ENEMY_TROLL: {
        "char": "T", "color": COLOR_GREEN, "name": "Troll",
        "hp": 25, "attack": 6, "defense": 2, "xp": 20,
        "dodge": 5, "status_effect": STATUS_BLEED,
    },
    # Tier 4 - formidable beasts
    ENEMY_MINOTAUR: {
        "char": "N", "color": COLOR_YELLOW, "name": "Minotaur",
        "hp": 25, "attack": 7, "defense": 2, "xp": 20,
        "dodge": 5, "status_effect": STATUS_BLEED,
    },
    ENEMY_MEDUSA: {
        "char": "m", "color": COLOR_GREEN, "name": "Medusa",
        "hp": 24, "attack": 6, "defense": 2, "xp": 20,
        "dodge": 7, "status_effect": STATUS_PARALYSIS,
    },
    ENEMY_OWLBEAR: {
        "char": "O", "color": COLOR_YELLOW, "name": "Owlbear",
        "hp": 22, "attack": 6, "defense": 1, "xp": 15,
        "dodge": 5, "status_effect": STATUS_BLEED,
    },
    ENEMY_HOOK_HORROR: {
        "char": "h", "color": COLOR_YELLOW, "name": "Hook Horror",
        "hp": 26, "attack": 7, "defense": 2, "xp": 20,
        "dodge": 7, "status_effect": STATUS_BLEED,
    },
    # Tier 5 - exotic threats
    ENEMY_PHASE_SPIDER: {
        "char": "P", "color": COLOR_RED, "name": "Phase Spider",
        "hp": 18, "attack": 5, "defense": 1, "xp": 12,
        "dodge": 10, "status_effect": STATUS_POISON,
    },
    ENEMY_BASILISK: {
        "char": "B", "color": COLOR_GREEN, "name": "Basilisk",
        "hp": 20, "attack": 6, "defense": 3, "xp": 18,
        "dodge": 8, "status_effect": STATUS_PARALYSIS,
    },
    ENEMY_WYVERN: {
        "char": "Y", "color": COLOR_GREEN, "name": "Wyvern",
        "hp": 32, "attack": 9, "defense": 3, "xp": 25,
        "dodge": 8, "status_effect": STATUS_BURN,
    },
    # Tier 6 - powerful creatures
    ENEMY_PHOENIX: {
        "char": "F", "color": COLOR_RED, "name": "Phoenix",
        "hp": 28, "attack": 8, "defense": 2, "xp": 22,
        "dodge": 10, "status_effect": STATUS_BURN,
    },
    ENEMY_GRUE: {
        "char": "X", "color": COLOR_MAGENTA, "name": "Grue",
        "hp": 15, "attack": 5, "defense": 1, "xp": 12,
        "dodge": 10,
    },
    ENEMY_GELATINOUS_CUBE: {
        "char": "C", "color": COLOR_CYAN,
        "name": "Gelatinous Cube",
        "hp": 28, "attack": 4, "defense": 1, "xp": 15,
        "dodge": 8,
    },
    ENEMY_REMORHAZ: {
        "char": "R", "color": COLOR_RED, "name": "Remorhaz",
        "hp": 40, "attack": 10, "defense": 4, "xp": 35,
        "dodge": 10, "status_effect": STATUS_BURN,
    },
    ENEMY_ICE_DEVIL: {
        "char": "I", "color": COLOR_CYAN, "name": "Ice Devil",
        "hp": 35, "attack": 9, "defense": 3, "xp": 30,
        "dodge": 12, "status_effect": STATUS_CHILL,
    },
    # Tier 7 - legendary threats
    ENEMY_LICH: {
        "char": "L", "color": COLOR_WHITE, "name": "Lich",
        "hp": 45, "attack": 10, "defense": 4, "xp": 45,
        "dodge": 12, "status_effect": STATUS_POISON,
    },
    ENEMY_BEHOLDER: {
        "char": "E", "color": COLOR_YELLOW, "name": "Beholder",
        "hp": 40, "attack": 9, "defense": 4, "xp": 40,
        "dodge": 12, "status_effect": STATUS_PARALYSIS,
    },
    # Tier 8 - ultimate bosses
    ENEMY_BALOR: {
        "char": "B", "color": COLOR_RED, "name": "Balor",
        "hp": 60, "attack": 14, "defense": 5, "xp": 60,
        "dodge": 15, "status_effect": STATUS_BURN,
    },
    # Keep old enemies for compatibility
    ENEMY_ORC: {
        "char": "o", "color": COLOR_GREEN, "name": "Orc",
        "hp": 10, "attack": 3, "defense": 1, "xp": 5,
        "dodge": 5,
    },
    ENEMY_GOLEM: {
        "char": "G", "color": COLOR_CYAN, "name": "Golem",
        "hp": 20, "attack": 5, "defense": 4, "xp": 15,
        "dodge": 3,
    },
    ENEMY_SNAKE: {
        "char": "n", "color": COLOR_RED, "name": "Snake",
        "hp": 5, "attack": 2, "defense": 0, "xp": 3,
        "dodge": 5, "status_effect": STATUS_POISON,
    },
    ENEMY_DEMON: {
        "char": "D", "color": COLOR_RED, "name": "Demon",
        "hp": 30, "attack": 8, "defense": 3, "xp": 30,
        "dodge": 10,
    },
    ENEMY_DRAGON: {
        "char": "d", "color": COLOR_RED, "name": "Dragon",
        "hp": 50, "attack": 12, "defense": 5, "xp": 50,
        "dodge": 12, "status_effect": STATUS_BURN,
    },
    # Water enemies - hidden in water, cannot leave water
    ENEMY_WATER_MITE: {
        "char": ".", "color": COLOR_BLUE, "name": "Water Mite",
        "hp": 4, "attack": 2, "defense": 0, "xp": 2,
        "dodge": 5,
        "water": True,
    },
    ENEMY_WATER_SNAKE: {
        "char": "N", "color": COLOR_CYAN, "name": "Water Snake",
        "hp": 10, "attack": 4, "defense": 1, "xp": 6,
        "dodge": 7, "status_effect": STATUS_POISON,
        "water": True,
    },
    ENEMY_DEEP_ONE: {
        "char": "D", "color": COLOR_CYAN, "name": "Deep One",
        "hp": 30, "attack": 7, "defense": 3, "xp": 25,
        "dodge": 10,
        "water": True,
    },
    ENEMY_WATER_ELEMENTAL: {
        "char": "W", "color": COLOR_BLUE, "name": "Water Elemental",
        "hp": 40, "attack": 9, "defense": 3, "xp": 35,
        "dodge": 12, "status_effect": STATUS_CHILL,
        "water": True,
    },
    ENEMY_KRAKEN: {
        "char": "K", "color": COLOR_MAGENTA, "name": "Kraken",
        "hp": 55, "attack": 12, "defense": 4, "xp": 55,
        "dodge": 12, "status_effect": STATUS_BLEED,
        "water": True,
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

# Weapon definitions: dice string, crit chance (%), crit multiplier, name, depth range
WEAPON_FISTS = "fists"
WEAPON_DAGGER = "dagger"
WEAPON_SHORT_SWORD = "short_sword"
WEAPON_LONG_SWORD = "long_sword"
WEAPON_WAR_AXE = "war_axe"
WEAPON_GREAT_SWORD = "great_sword"
WEAPON_VORPAL_BLADE = "vorpal_blade"

WEAPON_PROPS = {
    WEAPON_FISTS: {"dice": "1d2", "crit": 0, "crit_mult": 1, "name": "Fists", "depth_range": (0, 9)},
    WEAPON_DAGGER: {"dice": "1d4", "crit": 0, "crit_mult": 1, "name": "Dagger", "depth_range": (0, 3)},
    WEAPON_SHORT_SWORD: {"dice": "1d6", "crit": 0, "crit_mult": 1, "name": "Short Sword", "depth_range": (1, 4)},
    WEAPON_LONG_SWORD: {"dice": "1d8", "crit": 5, "crit_mult": 2, "name": "Long Sword", "depth_range": (3, 6)},
    WEAPON_WAR_AXE: {"dice": "1d10", "crit": 5, "crit_mult": 2, "name": "War Axe", "depth_range": (4, 7)},
    WEAPON_GREAT_SWORD: {"dice": "2d6", "crit": 8, "crit_mult": 2, "name": "Great Sword", "depth_range": (6, 8)},
    WEAPON_VORPAL_BLADE: {"dice": "2d8", "crit": 15, "crit_mult": 2.5, "name": "Vorpal Blade", "depth_range": (8, 9)},
}

# Shield definitions: block chance (%), absorption amount, name, depth range
SHIELD_NONE = "none"
SHIELD_LEATHER = "leather_shield"
SHIELD_WOOD = "wood_shield"
SHIELD_IRON = "iron_shield"
SHIELD_TOWER = "tower_shield"

SHIELD_PROPS = {
    SHIELD_NONE: {"block": 0, "absorb": 0, "name": "None", "depth_range": (0, 9)},
    SHIELD_LEATHER: {"block": 10, "absorb": 2, "name": "Leather Shield", "depth_range": (0, 3)},
    SHIELD_WOOD: {"block": 15, "absorb": 3, "name": "Wood Shield", "depth_range": (1, 4)},
    SHIELD_IRON: {"block": 20, "absorb": 5, "name": "Iron Shield", "depth_range": (3, 6)},
    SHIELD_TOWER: {"block": 30, "absorb": 7, "name": "Tower Shield", "depth_range": (6, 9)},
}

# Weapon descriptors: name variants with stat modifier ranges
# Each descriptor has a display name and ranges for dice_faces_delta, crit_delta, flat_bonus
WEAPON_DESCRIPTORS = [
    {"name": "Rusty",       "dice_delta": (-1, 0),    "crit_delta": (-2, 0), "flat_delta": (-1, 0)},
    {"name": "Dull",        "dice_delta": (-1, 0),    "crit_delta": (-1, 0), "flat_delta": (0, 0)},
    {"name": "Worn",        "dice_delta": (0, 0),     "crit_delta": (-1, 1), "flat_delta": (-1, 0)},
    {"name": "Cracked",     "dice_delta": (-1, 1),    "crit_delta": (-2, 1), "flat_delta": (-1, 1)},
    {"name": "",            "dice_delta": (-1, 1),    "crit_delta": (-1, 1), "flat_delta": (-1, 1)},
    {"name": "Well-made",   "dice_delta": (0, 1),     "crit_delta": (0, 2), "flat_delta": (0, 1)},
    {"name": "Sharp",       "dice_delta": (0, 1),     "crit_delta": (1, 2), "flat_delta": (0, 1)},
    {"name": "Battle-hardened", "dice_delta": (0, 2), "crit_delta": (0, 1), "flat_delta": (0, 2)},
    {"name": "Keen",        "dice_delta": (1, 1),     "crit_delta": (2, 3), "flat_delta": (0, 1)},
]

SHIELD_DESCRIPTORS = [
    {"name": "Damaged",     "block_delta": (-4, -1), "absorb_delta": (-1, 0)},
    {"name": "Splintered",  "block_delta": (-3, -1), "absorb_delta": (-1, 0)},
    {"name": "Worn",        "block_delta": (-2, 0),  "absorb_delta": (0, 0)},
    {"name": "Scuffed",     "block_delta": (-2, 1),  "absorb_delta": (-1, 1)},
    {"name": "",            "block_delta": (-2, 2),  "absorb_delta": (-1, 1)},
    {"name": "Sturdy",      "block_delta": (1, 2),   "absorb_delta": (0, 1)},
    {"name": "Reinforced",  "block_delta": (2, 4),   "absorb_delta": (1, 2)},
    {"name": "Solid",       "block_delta": (2, 3),   "absorb_delta": (1, 1)},
    {"name": "Fortified",   "block_delta": (3, 5),   "absorb_delta": (1, 2)},
]


def _parse_dice(dice_str):
    """Parse a dice string like '2d8' into (count, sides)."""
    if 'd' in dice_str:
        parts = dice_str.split('d')
        return int(parts[0]), int(parts[1])
    return 1, int(dice_str)


def generate_weapon_variant(weapon_type):
    """Generate a weapon variant with a descriptor and modified stats.

    Returns a dict: {weapon, dice, crit, crit_mult, flat_bonus, name}
    """
    if weapon_type == WEAPON_FISTS:
        return {
            "weapon": WEAPON_FISTS,
            "dice": WEAPON_PROPS[WEAPON_FISTS]["dice"],
            "crit": 0,
            "crit_mult": 1,
            "flat_bonus": 0,
            "name": "Fists",
        }

    props = WEAPON_PROPS[weapon_type]
    desc = random.choice(WEAPON_DESCRIPTORS)
    count, sides = _parse_dice(props["dice"])

    dice_delta = random.randint(desc["dice_delta"][0], desc["dice_delta"][1])
    crit_delta = random.randint(desc["crit_delta"][0], desc["crit_delta"][1])
    flat_delta = random.randint(desc["flat_delta"][0], desc["flat_delta"][1])

    new_sides = max(2, sides + dice_delta)
    new_crit = max(0, props["crit"] + crit_delta)
    new_flat = flat_delta

    desc_name = desc["name"]
    full_name = f"{desc_name} {props['name']}" if desc_name else props["name"]

    return {
        "weapon": weapon_type,
        "dice": f"{count}d{new_sides}",
        "crit": new_crit,
        "crit_mult": props["crit_mult"],
        "flat_bonus": new_flat,
        "name": full_name,
    }


def generate_shield_variant(shield_type):
    """Generate a shield variant with a descriptor and modified stats.

    Returns a dict: {shield, block, absorb, name}
    """
    if shield_type == SHIELD_NONE:
        return {
            "shield": SHIELD_NONE,
            "block": 0,
            "absorb": 0,
            "name": "None",
        }

    props = SHIELD_PROPS[shield_type]
    desc = random.choice(SHIELD_DESCRIPTORS)

    block_delta = random.randint(desc["block_delta"][0], desc["block_delta"][1])
    absorb_delta = random.randint(desc["absorb_delta"][0], desc["absorb_delta"][1])

    new_block = max(0, props["block"] + block_delta)
    new_absorb = max(0, props["absorb"] + absorb_delta)

    desc_name = desc["name"]
    full_name = f"{desc_name} {props['name']}" if desc_name else props["name"]

    return {
        "shield": shield_type,
        "block": new_block,
        "absorb": new_absorb,
        "name": full_name,
    }


def pick_weapon_for_depth(depth):
    """Pick a random weapon variant appropriate for the given depth."""
    candidates = [
        wtype for wtype, props in WEAPON_PROPS.items()
        if wtype != WEAPON_FISTS and props["depth_range"][0] <= depth <= props["depth_range"][1]
    ]
    if not candidates:
        return generate_weapon_variant(WEAPON_DAGGER)
    return generate_weapon_variant(random.choice(candidates))


def pick_shield_for_depth(depth):
    """Pick a random shield variant appropriate for the given depth."""
    candidates = [
        stype for stype, props in SHIELD_PROPS.items()
        if stype != SHIELD_NONE and props["depth_range"][0] <= depth <= props["depth_range"][1]
    ]
    if not candidates:
        return generate_shield_variant(SHIELD_LEATHER)
    return generate_shield_variant(random.choice(candidates))


# Status effect properties (constants defined above in ENEMY_PROPS section)
STATUS_EFFECT_PROPS = {
    STATUS_POISON: {
        "name": "poison", "color": COLOR_GREEN,
        "apply_msg": MSG_STATUS_POISON_APPLY,
    },
    STATUS_BURN: {
        "name": "burn", "color": COLOR_RED,
        "apply_msg": MSG_STATUS_BURN_APPLY,
    },
    STATUS_BLEED: {
        "name": "bleed", "color": COLOR_RED,
        "apply_msg": MSG_STATUS_BLEED_APPLY,
    },
    STATUS_CHILL: {
        "name": "chill", "color": COLOR_CYAN,
        "apply_msg": MSG_STATUS_CHILL_APPLY,
    },
    STATUS_PARALYSIS: {
        "name": "paralysis", "color": COLOR_MAGENTA,
        "apply_msg": MSG_STATUS_PARALYSIS_APPLY,
    },
}


def roll_dice(dice_str):
    """Roll dice from a string like '2d6'. Returns total."""
    parts = dice_str.lower().split("d")
    count = int(parts[0])
    sides = int(parts[1])
    return sum(random.randint(1, sides) for _ in range(count))


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

        if len(rooms) >= DUNGEON_MIN_ROOMS_REQUIRED:
            break

    if len(rooms) < DUNGEON_MIN_ROOMS_VALID:
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


DUNGEON_TYPES = ["rooms", "caves", "labyrinth", "tower"]
CAVE_FILL = 0.47
CAVE_WALL_THRESHOLD = 4
CAVE_SMOOTH_PASSES = 6
CAVE_MIN_OPEN = 400


def create_cave_dungeon(depth):
    """Generate an organic cave dungeon using cellular automata.

    Retries until a valid cave is produced.
    Returns (grid, open_areas, water_areas) where open_areas is a list of
    (x, y) floor tiles and water_areas is a list of (x, y) water tiles.
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

        _add_water_to_cave(cave)

        open_areas = []
        water_areas = []
        for py in range(1, MAP_HEIGHT - 1):
            for px in range(1, MAP_WIDTH - 1):
                if cave[py][px] == TILE_FLOOR:
                    neighbors = sum(1 for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                                   if cave[py + dy][px + dx] == TILE_FLOOR)
                    if neighbors >= CAVE_OPEN_TILE_MIN_FLOOR_NEIGHBORS:
                        open_areas.append((px, py))
                elif cave[py][px] == TILE_WATER:
                    water_areas.append((px, py))

        if len(open_areas) >= CAVE_MIN_OPEN:
            # Reject if cave is too open (not enough walls)
            wall_count = sum(1 for y in range(MAP_HEIGHT)
                             for x in range(MAP_WIDTH)
                             if cave[y][x] == TILE_WALL)
            if wall_count >= MAP_WIDTH * MAP_HEIGHT // DUNGEON_MIN_WALL_FRACTION_DIVISOR:
                return cave, open_areas, water_areas


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


def _find_reachable_from(dungeon, sx, sy):
    """Flood fill from (sx, sy) returning set of all reachable passable tiles.

    Passable tiles are anything that is not a wall or closed door.
    """
    height = len(dungeon)
    width = len(dungeon[0])
    reachable = set()
    queue = deque([(sx, sy)])
    reachable.add((sx, sy))
    while queue:
        x, y = queue.popleft()
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if (0 <= nx < width and 0 <= ny < height
                    and (nx, ny) not in reachable):
                tile = dungeon[ny][nx]
                if tile not in (TILE_WALL, TILE_DOOR_CLOSED):
                    reachable.add((nx, ny))
                    queue.append((nx, ny))
    return reachable


CAVE_WATER_DEPTH = 4


def _add_water_to_cave(cave):
    """Convert floor tiles deep inside open areas to water.

    Uses BFS distance transform from walls. Tiles far from any wall
    become water, creating natural pools in the center of large caves.
    """
    height = len(cave)
    width = len(cave[0])

    distance = [[-1] * width for _ in range(height)]
    queue = deque()

    for y in range(height):
        for x in range(width):
            if cave[y][x] == TILE_WALL:
                distance[y][x] = 0
                queue.append((x, y))

    while queue:
        x, y = queue.popleft()
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and distance[ny][nx] == -1:
                distance[ny][nx] = distance[y][x] + 1
                queue.append((nx, ny))

    for y in range(height):
        for x in range(width):
            if cave[y][x] == TILE_FLOOR and distance[y][x] >= CAVE_WATER_DEPTH:
                cave[y][x] = TILE_WATER


LABYRINTH_LOOP_CHANCE = 0.20
LABYRINTH_TRAP_CHANCE = 0.15
TRAP_CHANCE = 0.003


def _scatter_traps(dungeon, exclude, chance=TRAP_CHANCE):
    """Randomly place traps on floor tiles, excluding certain positions."""
    for y in range(1, MAP_HEIGHT - 1):
        for x in range(1, MAP_WIDTH - 1):
            if dungeon[y][x] == TILE_FLOOR and (x, y) not in exclude:
                if random.random() < chance:
                    dungeon[y][x] = TILE_TRAP


def create_labyrinth_dungeon(depth):
    """Generate a maze-like labyrinth with tight corridors and dead ends.

    Uses recursive backtracking to create a perfect maze, then removes
    some walls to create loops. Places traps in dead-end corridors.
    Returns (grid, open_areas).
    """
    while True:
        maze = [[TILE_WALL] * MAP_WIDTH for _ in range(MAP_HEIGHT)]

        # Maze cells are at odd coordinates, walls at even
        cell_w = MAP_WIDTH // 2
        cell_h = MAP_HEIGHT // 2

        # Recursive backtracking maze generation
        visited = [[False] * cell_w for _ in range(cell_h)]
        stack = []
        sx, sy = 0, 0
        visited[sy][sx] = True
        maze[2 * sy + 1][2 * sx + 1] = TILE_FLOOR

        while True:
            cx, cy = 2 * sx + 1, 2 * sy + 1
            neighbors = []
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = sx + dx, sy + dy
                if 0 <= nx < cell_w and 0 <= ny < cell_h and not visited[ny][nx]:
                    neighbors.append((nx, ny, dx, dy))
            if neighbors:
                nx, ny, dx, dy = random.choice(neighbors)
                maze[cy + dy][cx + dx] = TILE_FLOOR
                maze[2 * ny + 1][2 * nx + 1] = TILE_FLOOR
                visited[ny][nx] = True
                stack.append((sx, sy))
                sx, sy = nx, ny
            elif stack:
                sx, sy = stack.pop()
            else:
                break

        # Remove random internal walls to create loops
        removed = 0
        target = int(cell_w * cell_h * LABYRINTH_LOOP_CHANCE)
        candidates = []
        for y in range(2, MAP_HEIGHT - 2, 2):
            for x in range(2, MAP_WIDTH - 2, 2):
                if maze[y][x] == TILE_WALL:
                    candidates.append((x, y))
        random.shuffle(candidates)
        for x, y in candidates:
            if removed >= target:
                break
            # Only remove if both adjacent cells are floor (internal wall)
            if (maze[y - 1][x] == TILE_FLOOR and maze[y + 1][x] == TILE_FLOOR) or \
               (maze[y][x - 1] == TILE_FLOOR and maze[y][x + 1] == TILE_FLOOR):
                maze[y][x] = TILE_FLOOR
                removed += 1

         # Find dead ends (floor tiles with only 1 floor neighbor) for traps
        open_areas = []
        for py in range(1, MAP_HEIGHT - 1):
            for px in range(1, MAP_WIDTH - 1):
                if maze[py][px] != TILE_FLOOR:
                    continue
                floor_neighbors = sum(
                    1 for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    if maze[py + dy][px + dx] == TILE_FLOOR)
                if floor_neighbors >= LABYRINTH_OPEN_TILE_MIN_FLOOR_NEIGHBORS:
                    open_areas.append((px, py))
                elif floor_neighbors == LABYRINTH_DEAD_END_FLOOR_NEIGHBORS:
                    # Dead end - place a trap with some probability
                    if random.random() < LABYRINTH_TRAP_CHANCE:
                        maze[py][px] = TILE_TRAP
                    else:
                        open_areas.append((px, py))

        if len(open_areas) >= CAVE_MIN_OPEN:
            # Reject if labyrinth is too open (not enough walls)
            wall_count = sum(1 for y in range(MAP_HEIGHT)
                             for x in range(MAP_WIDTH)
                             if maze[y][x] == TILE_WALL)
            if wall_count >= MAP_WIDTH * MAP_HEIGHT // DUNGEON_MIN_WALL_FRACTION_DIVISOR:
                return maze, open_areas


TOWER_MIN_ROOMS = 3
TOWER_MAX_ROOMS = 6


def create_tower_dungeon(depth):
    """Generate a tower level with concentric rings and chambers.

    Creates 3-5 concentric rectangular rings connected by passages,
    with chambers carved into each ring. The innermost ring is a
    boss arena.
    Returns (grid, open_areas).
    """
    while True:
        tower = [[TILE_WALL] * MAP_WIDTH for _ in range(MAP_HEIGHT)]

        cx, cy = MAP_WIDTH // 2, MAP_HEIGHT // 2
        num_rings = min(TOWER_MIN_RINGS_BASE + depth // TOWER_RINGS_DEPTH_DIVISOR, TOWER_MAX_RINGS)
        ring_width = min(MAP_WIDTH, MAP_HEIGHT) // (2 * num_rings + 2)
        if ring_width < TOWER_MIN_RING_WIDTH:
            ring_width = TOWER_MIN_RING_WIDTH

        all_open = []

        for ring in range(num_rings, 0, -1):
            rx = cx - ring * ring_width
            ry = cy - ring * ring_width
            rw = 2 * ring * ring_width
            rh = 2 * ring * ring_width

            # Carve the ring (hollow rectangle)
            thickness = max(2, ring_width // 2)
            for y in range(ry, ry + thickness):
                for x in range(rx, rx + rw):
                    if 0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT:
                        tower[y][x] = TILE_FLOOR
            for y in range(ry + rh - thickness, ry + rh):
                for x in range(rx, rx + rw):
                    if 0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT:
                        tower[y][x] = TILE_FLOOR
            for y in range(ry + thickness, ry + rh - thickness):
                for x in range(rx, rx + thickness):
                    if 0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT:
                        tower[y][x] = TILE_FLOOR
                for x in range(rx + rw - thickness, rx + rw):
                    if 0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT:
                        tower[y][x] = TILE_FLOOR

            # Carve chambers into the ring
            num_rooms = random.randint(TOWER_MIN_ROOMS, TOWER_MAX_ROOMS)
            for _ in range(num_rooms):
                # Pick a side of the ring to carve a chamber
                side = random.randint(0, 3)
                if side == 0:  # top
                    room_x = random.randint(rx + 2, rx + rw - 4)
                    room_y = ry + thickness
                elif side == 1:  # bottom
                    room_x = random.randint(rx + 2, rx + rw - 4)
                    room_y = ry + rh - thickness - 3
                elif side == 2:  # left
                    room_x = rx + thickness
                    room_y = random.randint(ry + 2, ry + rh - 4)
                else:  # right
                    room_x = rx + rw - thickness - 3
                    room_y = random.randint(ry + 2, ry + rh - 4)
                room_w = random.randint(3, 5)
                room_h = random.randint(3, 5)
                for dy in range(room_h):
                    for dx in range(room_w):
                        ny, nx = room_y + dy, room_x + dx
                        if 0 < nx < MAP_WIDTH - 1 and 0 < ny < MAP_HEIGHT - 1:
                            tower[ny][nx] = TILE_FLOOR

            # Connect to inner ring with passages
            if ring > 1:
                num_passages = random.randint(2, 4)
                for _ in range(num_passages):
                    side = random.randint(0, 3)
                    if side == 0:  # top
                        px = random.randint(rx + 2, rx + rw - 3)
                        py = ry + thickness - 1
                    elif side == 1:  # bottom
                        px = random.randint(rx + 2, rx + rw - 3)
                        py = ry + rh - thickness
                    elif side == 2:  # left
                        px = rx + thickness - 1
                        py = random.randint(ry + 2, ry + rh - 3)
                    else:  # right
                        px = rx + rw - thickness
                        py = random.randint(ry + 2, ry + rh - 3)
                    # Carve a narrow passage inward
                    for step in range(thickness):
                        ny, nx = py, px
                        if 0 < nx < MAP_WIDTH - 1 and 0 < ny < MAP_HEIGHT - 1:
                            tower[ny][nx] = TILE_FLOOR
                        if side == 0:
                            ny += 1
                        elif side == 1:
                            ny -= 1
                        elif side == 2:
                            nx += 1
                        else:
                            nx -= 1

        # Innermost ring is a boss arena - clear the center
        arena_r = ring_width
        for y in range(cy - arena_r, cy + arena_r + 1):
            for x in range(cx - arena_r, cx + arena_r + 1):
                if 0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT:
                    tower[y][x] = TILE_FLOOR

        # Collect open areas
        open_areas = []
        for py in range(1, MAP_HEIGHT - 1):
            for px in range(1, MAP_WIDTH - 1):
                if tower[py][px] != TILE_FLOOR:
                    continue
                neighbors = sum(
                    1 for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    if tower[py + dy][px + dx] == TILE_FLOOR)
                if neighbors >= 2:
                    open_areas.append((px, py))

        if len(open_areas) >= CAVE_MIN_OPEN:
            # Reject if tower is too open (not enough walls)
            wall_count = sum(1 for y in range(MAP_HEIGHT)
                             for x in range(MAP_WIDTH)
                             if tower[y][x] == TILE_WALL)
            if wall_count >= MAP_WIDTH * MAP_HEIGHT // DUNGEON_MIN_WALL_FRACTION_DIVISOR:
                return tower, open_areas


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
                for _ in range(random.randint(START_ROOM_POTIONS_MIN, START_ROOM_POTIONS_MAX)):
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
            scale = ENEMY_STATS_BASE_SCALE + depth * ENEMY_STATS_DEPTH_SCALE_FACTOR
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
        if random.random() < ITEM_POTION_SPAWN_CHANCE:
            ix = random.randint(room.x1 + 1, room.x2 - 1)
            iy = random.randint(room.y1 + 1, room.y2 - 1)
            items.append({"x": ix, "y": iy, "kind": ITEM_POTION})
        if random.random() < ITEM_GOLD_SPAWN_CHANCE:
            ix = random.randint(room.x1 + 1, room.x2 - 1)
            iy = random.randint(room.y1 + 1, room.y2 - 1)
            items.append({
                "x": ix, "y": iy, "kind": ITEM_GOLD,
                "value": random.randint(GOLD_VALUE_MIN, GOLD_VALUE_MAX) * (depth + 1)})
        if random.random() < ITEM_WEAPON_SPAWN_CHANCE:
            ix = random.randint(room.x1 + 1, room.x2 - 1)
            iy = random.randint(room.y1 + 1, room.y2 - 1)
            items.append({
                "x": ix, "y": iy, "kind": ITEM_SWORD,
                "weapon": pick_weapon_for_depth(depth),
            })
        if random.random() < ITEM_SHIELD_SPAWN_CHANCE:
            ix = random.randint(room.x1 + 1, room.x2 - 1)
            iy = random.randint(room.y1 + 1, room.y2 - 1)
            items.append({
                "x": ix, "y": iy, "kind": ITEM_SHIELD,
                "shield": pick_shield_for_depth(depth),
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
        self.equipped_weapon = WEAPON_FISTS
        self.equipped_shield = SHIELD_NONE
        self.gold = 0
        self.next_tick = random.randint(PLAYER_INITIAL_TICK_RANGE_MIN, PLAYER_INITIAL_TICK_RANGE_MAX)
        self.queued_action = None
        self.consecutive_waits = 0
        self.dead = False
        self.game_win = False
        self.messages = []
        self._last_ambient_tick = 0
        # Per-depth explored grids: {depth: 2D boolean grid}
        self.explored = {}
        # Per-depth discovered trap locations: {depth: set of (x, y)}
        self.discovered_traps = {}
        # Depths for which the entrance message has already been shown
        self._entrance_shown = set()
        # Active status effects: {effect_name: remaining_ticks}
        self.status_effects = {}

    def weapon_damage(self):
        """Roll weapon dice + flat bonus. Returns total damage."""
        if isinstance(self.equipped_weapon, dict):
            return roll_dice(self.equipped_weapon["dice"]) + self.equipped_weapon.get("flat_bonus", 0)
        props = WEAPON_PROPS[self.equipped_weapon]
        return roll_dice(props["dice"])

    def crit_info(self):
        """Return (crit_chance, crit_multiplier) for the equipped weapon."""
        if isinstance(self.equipped_weapon, dict):
            return self.equipped_weapon["crit"], self.equipped_weapon["crit_mult"]
        props = WEAPON_PROPS[self.equipped_weapon]
        return props["crit"], props["crit_mult"]

    def shield_info(self):
        """Return (block_chance, absorb) for the equipped shield."""
        if isinstance(self.equipped_shield, dict):
            return self.equipped_shield["block"], self.equipped_shield["absorb"]
        props = SHIELD_PROPS[self.equipped_shield]
        return props["block"], props["absorb"]

    def defense_total(self):
        """Return total defense (base only, shields handle block separately)."""
        return self.defense

    def weapon_name(self):
        """Return display name of equipped weapon."""
        if isinstance(self.equipped_weapon, dict):
            return self.equipped_weapon["name"]
        return WEAPON_PROPS[self.equipped_weapon]["name"]

    def shield_name(self):
        """Return display name of equipped shield."""
        if isinstance(self.equipped_shield, dict):
            return self.equipped_shield["name"]
        return SHIELD_PROPS[self.equipped_shield]["name"]

    def _weapon_display(self):
        """Return formatted weapon display string with dice and flat bonus."""
        if isinstance(self.equipped_weapon, dict):
            w = self.equipped_weapon
            dice = w['dice']
            bonus = w.get('flat_bonus', 0)
            bonus_str = f"{bonus:+d}" if bonus else ""
            return f"{w['name']}({dice}{bonus_str})"
        props = WEAPON_PROPS[self.equipped_weapon]
        return f"{props['name']}({props['dice']})"

    def _shield_display(self):
        """Return formatted shield display string with block% and absorb."""
        if isinstance(self.equipped_shield, dict):
            s = self.equipped_shield
            return f"{s['name']}({s['block']}%/{s['absorb']}dmg)"
        props = SHIELD_PROPS[self.equipped_shield]
        return f"{props['name']}({props['block']}%/{props['absorb']}dmg)"


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

    def _place_entities_cave(self, open_areas, water_areas, dungeon, depth):
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
        max_enemies = min(CAVE_MAX_ENEMIES_BASE + depth * CAVE_MAX_ENEMIES_PER_DEPTH, CAVE_MAX_ENEMIES_CAP)

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
                "hp": props["hp"] + depth * ENEMY_HP_SCALE_PER_DEPTH,
                "max_hp": props["hp"] + depth * ENEMY_HP_SCALE_PER_DEPTH,
                "attack": props["attack"] + depth * ENEMY_ATTACK_SCALE_PER_DEPTH,
                "defense": props["defense"] + depth // ENEMY_DEFENSE_DEPTH_DIVISOR,
                "xp": props["xp"] + depth * ENEMY_XP_SCALE_PER_DEPTH,
                "depth": depth,
            }
            enemies.append(e)

        # Place water enemies on water tiles
        water_enemy_by_depth = {
            0: [ENEMY_WATER_MITE],
            1: [ENEMY_WATER_MITE],
            2: [ENEMY_WATER_MITE, ENEMY_WATER_SNAKE],
            3: [ENEMY_WATER_SNAKE],
            4: [ENEMY_WATER_SNAKE, ENEMY_DEEP_ONE],
            5: [ENEMY_DEEP_ONE],
            6: [ENEMY_DEEP_ONE, ENEMY_WATER_ELEMENTAL],
            7: [ENEMY_WATER_ELEMENTAL],
            8: [ENEMY_WATER_ELEMENTAL, ENEMY_KRAKEN],
            9: [ENEMY_KRAKEN],
        }
        water_pool = water_enemy_by_depth.get(enemy_tier, [ENEMY_WATER_MITE])
        max_water_enemies = min(CAVE_WATER_ENEMIES_BASE + depth, CAVE_WATER_ENEMIES_CAP)

        for _ in range(max_water_enemies):
            spot = self._pick_open_spot(water_areas, used)
            if spot is None:
                break
            ex, ey = spot
            used.add(spot)
            etype = random.choice(water_pool)
            props = ENEMY_PROPS[etype]
            e = {
                "name": props["name"],
                "char": props["char"],
                "color": props["color"],
                "x": ex, "y": ey,
                "hp": props["hp"] + depth * ENEMY_HP_SCALE_PER_DEPTH,
                "max_hp": props["hp"] + depth * ENEMY_HP_SCALE_PER_DEPTH,
                "attack": props["attack"] + depth * ENEMY_ATTACK_SCALE_PER_DEPTH,
                "defense": props["defense"] + depth // ENEMY_DEFENSE_DEPTH_DIVISOR,
                "xp": props["xp"] + depth * ENEMY_XP_SCALE_PER_DEPTH,
                "depth": depth,
                "water": True,
            }
            enemies.append(e)

        # Items (reduced for caves)
        for _ in range(CAVE_ITEMS_BASE_COUNT + depth // CAVE_ITEMS_DEPTH_DIVISOR):
            spot = self._pick_open_spot(open_areas, used)
            if spot is None:
                break
            used.add(spot)
            roll = random.random()
            if roll < CAVE_ITEM_POTION_THRESHOLD:
                kind = ITEM_POTION
            elif roll < CAVE_ITEM_WEAPON_THRESHOLD:
                kind = ITEM_SWORD
            elif roll < CAVE_ITEM_SHIELD_THRESHOLD:
                kind = ITEM_SHIELD
            else:
                kind = ITEM_GOLD
            item = {
                "kind": kind,
                "x": spot[0], "y": spot[1],
                "depth": depth,
            }
            if kind == ITEM_GOLD:
                item["value"] = random.randint(CAVE_GOLD_VALUE_MIN, CAVE_GOLD_VALUE_MAX) + depth * CAVE_GOLD_VALUE_PER_DEPTH
            elif kind == ITEM_SWORD:
                item["weapon"] = pick_weapon_for_depth(depth)
            elif kind == ITEM_SHIELD:
                item["shield"] = pick_shield_for_depth(depth)
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
                "hp": ENEMY_PROPS[etype]["hp"] * GENERATOR_HP_MULTIPLIER + depth * GENERATOR_HP_PER_DEPTH,
                "max_hp": ENEMY_PROPS[etype]["hp"] * GENERATOR_HP_MULTIPLIER + depth * GENERATOR_HP_PER_DEPTH,
                "defense": min(GENERATOR_DEFENSE_MAX, (depth * 3) // 4),
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
        if depth == DUNGEON_FORCE_TOWER_DEPTH:
            dungeon_type = DUNGEON_TYPE_TOWER
        elif depth == DUNGEON_FORCE_LABYRINTH_DEPTH:
            dungeon_type = DUNGEON_TYPE_LABYRINTH
        elif depth >= DUNGEON_DEEP_MIX_MIN_DEPTH:
            dungeon_type = random.choice([DUNGEON_TYPE_CAVES, DUNGEON_TYPE_LABYRINTH])
        elif depth >= DUNGEON_MIX_MIN_DEPTH:
            dungeon_type = random.choice([DUNGEON_TYPE_ROOMS, DUNGEON_TYPE_CAVES, DUNGEON_TYPE_LABYRINTH])
        elif depth >= DUNGEON_CAVES_MIN_DEPTH:
            dungeon_type = random.choice([DUNGEON_TYPE_ROOMS, DUNGEON_TYPE_CAVES])
        else:
            dungeon_type = DUNGEON_TYPE_ROOMS
        if dungeon_type == DUNGEON_TYPE_CAVES:
            dungeon, open_areas, water_areas = create_cave_dungeon(depth)
            px, py, enemies, items = self._place_entities_cave(
                open_areas, water_areas, dungeon, depth)
            reachable = _find_reachable_from(dungeon, px, py)
            reachable_open = [(x, y) for x, y in open_areas
                              if (x, y) in reachable]
            stairs_down_x, stairs_down_y = self._pick_cave_spot(
                reachable_open, px, py)
            stairs_up_x, stairs_up_y = self._pick_cave_spot(
                reachable_open, px, py,
                exclude=(stairs_down_x, stairs_down_y))
        elif dungeon_type == DUNGEON_TYPE_LABYRINTH:
            dungeon, open_areas = create_labyrinth_dungeon(depth)
            px, py, enemies, items = self._place_entities_cave(
                open_areas, [], dungeon, depth)
            reachable = _find_reachable_from(dungeon, px, py)
            reachable_open = [(x, y) for x, y in open_areas
                              if (x, y) in reachable]
            stairs_down_x, stairs_down_y = self._pick_cave_spot(
                reachable_open, px, py)
            stairs_up_x, stairs_up_y = self._pick_cave_spot(
                reachable_open, px, py,
                exclude=(stairs_down_x, stairs_down_y))
        elif dungeon_type == DUNGEON_TYPE_TOWER:
            dungeon, open_areas = create_tower_dungeon(depth)
            px, py, enemies, items = self._place_entities_cave(
                open_areas, [], dungeon, depth)
            reachable = _find_reachable_from(dungeon, px, py)
            reachable_open = [(x, y) for x, y in open_areas
                              if (x, y) in reachable]
            stairs_down_x, stairs_down_y = self._pick_cave_spot(
                reachable_open, px, py)
            stairs_up_x, stairs_up_y = self._pick_cave_spot(
                reachable_open, px, py,
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

        # Scatter traps across the level
        exclude = {(px, py), (stairs_down_x, stairs_down_y), (stairs_up_x, stairs_up_y)}
        _scatter_traps(dungeon, exclude, TRAP_CHANCE + depth * TRAP_CHANCE_PER_DEPTH)

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
            "dungeon_type": dungeon_type,
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

    def _show_entrance(self, player):
        """Show a dungeon-type entrance message on first entry to a level."""
        depth = player.depth
        if depth in player._entrance_shown:
            return
        player._entrance_shown.add(depth)
        dungeon_type = self.levels[depth].get("dungeon_type", "rooms")
        messages = {
            DUNGEON_TYPE_ROOMS: MSG_ENTRANCE_ROOMS,
            DUNGEON_TYPE_CAVES: MSG_ENTRANCE_CAVES,
            DUNGEON_TYPE_LABYRINTH: MSG_ENTRANCE_LABYRINTH,
            DUNGEON_TYPE_TOWER: MSG_ENTRANCE_TOWER,
        }.get(dungeon_type, MSG_ENTRANCE_ROOMS)
        colors = {
            DUNGEON_TYPE_ROOMS: COLOR_WHITE,
            DUNGEON_TYPE_CAVES: COLOR_BLUE,
            DUNGEON_TYPE_LABYRINTH: COLOR_YELLOW,
            DUNGEON_TYPE_TOWER: COLOR_MAGENTA,
        }.get(dungeon_type, COLOR_WHITE)
        self._tell(player, random.choice(messages), colors)

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
            # Detect other players that just came into view
            for other in self.players:
                if other is p or other.dead:
                    continue
                if other.depth != p.depth:
                    continue
                if (new_fov[other.y][other.x]
                        and not old_fov[other.y][other.x]):
                    self._tell(
                        p, random.choice(MSG_PLAYER_INTO_VIEW),
                        other.color,
                        ctx={"player": other.name},
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
        source=None, chance=AMBIENT_SOUND_DEFAULT_CHANCE,
        skip_visible=False, range=AMBIENT_SOUND_DEFAULT_RANGE, flat=False,
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
            if dist < AMBIENT_SOUND_MIN_DIST or dist > range:
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
        source=None, chance=AMBIENT_DEPTH_DEFAULT_CHANCE, skip_visible=False,
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

    def _find_nearby_free_tile(self, x, y, depth, exclude_positions):
        """Find a passable tile near (x, y) not occupied by enemies, items,
        players, corpses, or positions in exclude_positions. Searches in
        expanding rings up to 4 tiles away. Returns (fx, fy) or None."""
        if 0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT:
            tile = self._get_dungeon(depth)[y][x]
            if (tile not in (TILE_WALL, TILE_DOOR_CLOSED)
                    and (x, y) not in exclude_positions
                    and not self.get_enemy_at(x, y, depth)
                    and not self.get_item_at(x, y, depth)[1]
                    and not self.get_corpse_at(x, y, depth)
                    and not any(
                        p.depth == depth and p.x == x and p.y == y
                        and not p.dead for p in self.players)):
                return (x, y)
        for radius in range(1, 5):
            candidates = []
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) != radius and abs(dy) != radius:
                        continue
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < MAP_WIDTH and 0 <= ny < MAP_HEIGHT):
                        continue
                    tile = self._get_dungeon(depth)[ny][nx]
                    if (tile not in (TILE_WALL, TILE_DOOR_CLOSED)
                            and (nx, ny) not in exclude_positions
                            and not self.get_enemy_at(nx, ny, depth)
                            and not self.get_item_at(nx, ny, depth)[1]
                            and not self.get_corpse_at(nx, ny, depth)
                            and not any(
                                p.depth == depth and p.x == nx and p.y == ny
                                and not p.dead for p in self.players)):
                        candidates.append((nx, ny))
            if candidates:
                return random.choice(candidates)
        return None

    def _drop_player_items(self, player, depth):
        """Drop the player's equipped weapon, shield, and gold as items
        near their death position. Items are placed on separate free tiles
        that do not overlap with the corpse, each other, or existing entities."""
        items = self._get_items(depth)
        occupied = {(player.x, player.y)}

        # Drop weapon if not fists
        if player.equipped_weapon != WEAPON_FISTS:
            weapon = player.equipped_weapon
            player.equipped_weapon = WEAPON_FISTS
            spot = self._find_nearby_free_tile(
                player.x, player.y, depth, occupied)
            if spot:
                occupied.add(spot)
                items.append({
                    "x": spot[0], "y": spot[1],
                    "kind": ITEM_SWORD, "weapon": weapon,
                })

        # Drop shield if not none
        if player.equipped_shield != SHIELD_NONE:
            shield = player.equipped_shield
            player.equipped_shield = SHIELD_NONE
            spot = self._find_nearby_free_tile(
                player.x, player.y, depth, occupied)
            if spot:
                occupied.add(spot)
                items.append({
                    "x": spot[0], "y": spot[1],
                    "kind": ITEM_SHIELD, "shield": shield,
                })

        # Drop gold if any
        if player.gold > 0:
            gold_value = player.gold
            player.gold = 0
            spot = self._find_nearby_free_tile(
                player.x, player.y, depth, occupied)
            if spot:
                items.append({
                    "x": spot[0], "y": spot[1],
                    "kind": ITEM_GOLD, "value": gold_value,
                })

    def _get_player_at(self, x, y, depth, exclude):
        """Return another player at (x, y) on the given depth, or None."""
        for p in self.players:
            if p is exclude:
                continue
            if not p.dead and p.depth == depth and p.x == x and p.y == y:
                return p
        return None

    def resolve_attack(self, player, enemy, is_player_attacking):
        """Resolve a full attack: dodge → dice → crit → shield → defense → status.

        Returns a dict with: damage, dodged, critical, shield_blocked, shield_absorbed,
        status_applied, message, message_color, message_ctx.
        """
        result = {
            "damage": 0, "dodged": False, "critical": False,
            "shield_blocked": False, "shield_absorbed": 0,
            "status_applied": None,
        }

        if is_player_attacking:
            # Player attacking enemy
            dodge_chance = enemy.get("dodge", 0)
            if dodge_chance and random.randint(PERCENTILE_ROLL_MIN, PERCENTILE_ROLL_MAX) <= dodge_chance:
                result["dodged"] = True
                result["message"] = random.choice(MSG_ENEMY_DODGE)
                result["message_color"] = COLOR_WHITE
                result["message_ctx"] = {"enemy": enemy["name"]}
                return result

            # Roll weapon dice + level
            damage = player.weapon_damage()

            # Crit check
            crit_chance, crit_mult = player.crit_info()
            if crit_chance and random.randint(PERCENTILE_ROLL_MIN, PERCENTILE_ROLL_MAX) <= crit_chance:
                damage = int(damage * crit_mult)
                result["critical"] = True

            # No shield block for enemies, no status effects
            result["damage"] = max(1, damage - enemy.get("defense", 0))
            result["message"] = (
                random.choice(MSG_CRITICAL_HIT) if result["critical"]
                else None  # use tier-based message later
            )
            result["message_color"] = COLOR_YELLOW if result["critical"] else COLOR_WHITE
            result["message_ctx"] = {"enemy": enemy["name"]}
            return result
        else:
            # Enemy attacking player
            damage = max(
                1, enemy["attack"] - player.defense_total()
                + random.randint(ENEMY_ATTACK_VARIANCE_MIN, ENEMY_ATTACK_VARIANCE_MAX),
            )

            # Shield block check
            block_chance, absorb = player.shield_info()
            if block_chance and random.randint(PERCENTILE_ROLL_MIN, PERCENTILE_ROLL_MAX) <= block_chance:
                result["shield_blocked"] = True
                absorbed = min(damage, absorb)
                result["shield_absorbed"] = absorbed
                damage = damage - absorbed
                if damage <= 0:
                    result["message"] = random.choice(MSG_SHIELD_BLOCK)
                    result["message_color"] = COLOR_CYAN
                    result["message_ctx"] = {}
                    result["damage"] = 0
                    return result
                else:
                    result["message"] = random.choice(MSG_SHIELD_BLOCK_PARTIAL)
                    result["message_color"] = COLOR_CYAN
                    result["message_ctx"] = {"absorbed": absorbed}

            # Status effect check
            status_effect = enemy.get("status_effect")
            if (status_effect and status_effect in STATUS_EFFECT_PROPS
                    and random.randint(PERCENTILE_ROLL_MIN, PERCENTILE_ROLL_MAX) <= STATUS_EFFECT_CHANCE):
                result["status_applied"] = status_effect

            result["damage"] = max(1, damage)
            if not result["shield_blocked"]:
                result["message"] = None  # use enemy hit message
                result["message_color"] = enemy["color"]
            return result

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
        if action_type != ACTION_WAIT:
            player.consecutive_waits = 0
        if action_type == ACTION_MOVE:
            self._do_move(player, action["dx"], action["dy"])
        elif action_type == ACTION_GRAB:
            self._do_grab_item(player)
            player.next_tick = self.tick + TICK_MOVE
        elif action_type == ACTION_STAIRS_DOWN:
            self._do_go_down_stairs(player)
            player.next_tick = self.tick + TICK_MOVE
        elif action_type == ACTION_STAIRS_UP:
            self._do_go_up_stairs(player)
            player.next_tick = self.tick + TICK_MOVE
        elif action_type == ACTION_WAIT:
            self._do_wait(player)
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
                damage = max(1, player.weapon_damage() - gen["defense"])
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
                COLOR_WHITE, source=player, chance=PLAYER_MOVE_AMBIENT_CHANCE,
                skip_visible=True, range=PLAYER_MOVE_AMBIENT_RANGE, flat=True,
            )
            return
        if not self.is_passable(nx, ny, player.depth):
            player.next_tick = self.tick + TICK_WAIT
            self._tell(player, random.choice(MSG_WALK_WALL), COLOR_WHITE)
            return
        enemy = self.get_enemy_at(nx, ny, player.depth)
        if enemy:
            self._do_combat_attack(player, enemy)
            player.next_tick = self.tick + TICK_ATTACK
        else:
            current_tile = dungeon[player.y][player.x]
            in_water = target_tile == TILE_WATER
            was_in_water = current_tile == TILE_WATER
            player.x, player.y = nx, ny
            if in_water:
                player.next_tick = self.tick + TICK_PLAYER_MOVE * WATER_MOVE_SPEED_PENALTY
            else:
                player.next_tick = self.tick + TICK_PLAYER_MOVE
            if in_water and not was_in_water:
                self._tell(player, random.choice(MSG_ENTER_WATER), COLOR_BLUE)
            elif was_in_water and not in_water:
                self._tell(player, random.choice(MSG_LEAVE_WATER), COLOR_BLUE)
            if target_tile == TILE_TRAP:
                # Reveal trap to the triggering player
                depth = player.depth
                if depth not in player.discovered_traps:
                    player.discovered_traps[depth] = set()
                player.discovered_traps[depth].add((nx, ny))

                # Reveal trap to other players who can see it
                for other in self.players:
                    if other is player or other.dead or other.depth != depth:
                        continue
                    fov = compute_fov(dungeon, other.x, other.y, FOV_RADIUS)
                    if fov[ny][nx]:
                        if depth not in other.discovered_traps:
                            other.discovered_traps[depth] = set()
                        other.discovered_traps[depth].add((nx, ny))

                trap_damage = TRAP_DAMAGE_BASE + player.depth * TRAP_DAMAGE_PER_DEPTH
                player.hp -= trap_damage
                self._tell(
                    player, random.choice(MSG_STEP_TRAP),
                    COLOR_RED, ctx={"damage": trap_damage})
                if player.hp <= 0:
                    player.hp = 0
                    player.dead = True
                    self._drop_player_items(player, player.depth)
                    self.levels[player.depth]["corpses"].append({
                        "x": player.x,
                        "y": player.y,
                        "name": player.name,
                        "level": player.level,
                        "killer": "trap",
                    })
                    self._broadcast(
                        player.x, player.y, player.depth,
                        MSG_PLAYER_DIED, COLOR_RED, subject=player)
            self._ambient_sound(
                nx, ny, player.depth, PLAYER_MOVE_AMBIENT,
                COLOR_WHITE, source=player, chance=PLAYER_MOVE_AMBIENT_CHANCE,
                skip_visible=True, range=PLAYER_MOVE_AMBIENT_RANGE, flat=True,
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
            if item["kind"] == ITEM_SWORD and "weapon" in item:
                w = item["weapon"]
                item_name = (w["name"] if isinstance(w, dict) else WEAPON_PROPS[w]["name"]).lower()
            elif item["kind"] == ITEM_SHIELD and "shield" in item:
                s = item["shield"]
                item_name = (s["name"] if isinstance(s, dict) else SHIELD_PROPS[s]["name"]).lower()
            else:
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
        if enemy.get("water"):
            enemy["visible"] = True
        result = self.resolve_attack(player, enemy, is_player_attacking=True)

        if result["dodged"]:
            self._broadcast(
                enemy["x"], enemy["y"], player.depth,
                result["message"], result["message_color"],
                subject=player, ctx=result["message_ctx"],
            )
            return

        enemy["hp"] -= result["damage"]

        if result["critical"]:
            hit_msg = result["message"]
            msg_color = result["message_color"]
        else:
            tier_keys = sorted(MSG_PLAYER_HIT_ENEMY.keys())
            tier = tier_keys[0]
            for tk in tier_keys:
                if result["damage"] >= tk:
                    tier = tk
            hit_msg = random.choice(MSG_PLAYER_HIT_ENEMY[tier])
            msg_color = COLOR_WHITE

        self._broadcast(
            enemy["x"], enemy["y"], player.depth,
            hit_msg, msg_color,
            subject=player,
            ctx={"enemy": enemy["name"], "damage": result["damage"]},
        )
        self._ambient_sound(
            enemy["x"], enemy["y"], player.depth,
            COMBAT_CLASH_AMBIENT,
            COLOR_WHITE, source=player, chance=COMBAT_CLASH_AMBIENT_CHANCE,
            range=COMBAT_AMBIENT_RANGE, flat=True,
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
                COLOR_RED, source=player, chance=ENEMY_DEATH_AMBIENT_CHANCE,
                range=ENEMY_DEATH_AMBIENT_RANGE, flat=True)
            player.xp += enemy["xp"]
            self._check_level_up(player)

    def _check_level_up(self, player):
        """Process level-ups while the player has enough XP."""
        while player.xp >= player.next_level_xp:
            player.xp -= player.next_level_xp
            player.level += 1
            player.max_hp += LEVEL_UP_HP_GAIN
            player.hp = min(player.hp + LEVEL_UP_HP_GAIN, player.max_hp)
            player.next_level_xp = int(player.next_level_xp * LEVEL_UP_XP_SCALE_FACTOR)
            self._broadcast(
                player.x, player.y, player.depth,
                MSG_LEVEL_UP, COLOR_YELLOW,
                subject=player, ctx={"level": player.level},
            )

    def _process_status_effects(self, player):
        """Process status effect tick-down and DoT damage."""
        to_remove = []
        for effect_name, remaining in player.status_effects.items():
            if remaining <= 0:
                to_remove.append(effect_name)
                continue
            # Apply DoT damage at interval
            if effect_name != STATUS_PARALYSIS:
                if remaining % STATUS_EFFECT_TICK_INTERVAL == 0:
                    dot_damage = self._calculate_dot_damage(player, effect_name)
                    player.hp -= dot_damage
                    self._tell(
                        player, MSG_STATUS_DO_TICK,
                        STATUS_EFFECT_PROPS[effect_name]["color"],
                        ctx={"damage": dot_damage,
                             "effect": STATUS_EFFECT_PROPS[effect_name]["name"]},
                    )
                    if player.hp <= 0:
                        player.hp = 0
                        player.dead = True
                        killer_name = STATUS_EFFECT_PROPS[effect_name]["name"]
                        self._drop_player_items(player, player.depth)
                        self.levels[player.depth]["corpses"].append({
                            "x": player.x,
                            "y": player.y,
                            "name": player.name,
                            "level": player.level,
                            "killer": killer_name,
                        })
                        self._broadcast(
                            player.x, player.y, player.depth,
                            MSG_PLAYER_DIED, COLOR_RED, subject=player)
            player.status_effects[effect_name] = remaining - 1

        for effect_name in to_remove:
            del player.status_effects[effect_name]
            self._tell(
                player, MSG_STATUS_WEAR_OFF,
                STATUS_EFFECT_PROPS[effect_name]["color"],
                ctx={"effect": STATUS_EFFECT_PROPS[effect_name]["name"]},
            )

    def _calculate_dot_damage(self, player, effect_name):
        """Calculate DoT damage per tick for the given effect."""
        if effect_name == STATUS_POISON:
            return random.randint(POISON_DOT_DAMAGE_MIN, POISON_DOT_DAMAGE_MAX)
        elif effect_name == STATUS_BURN:
            return BURN_DOT_DAMAGE_BASE + player.depth // BURN_DOT_DEPTH_DIVISOR
        elif effect_name == STATUS_BLEED:
            return max(STATUS_DOT_DAMAGE_FALLBACK, player.attack // BLEED_DOT_ATTACK_DIVISOR)
        return STATUS_DOT_DAMAGE_FALLBACK

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
            # Process status effects each tick
            self._process_status_effects(player)
            if self.tick >= player.next_tick:
                # Check paralysis - skip action, advance time
                if STATUS_PARALYSIS in player.status_effects:
                    player.next_tick = self.tick + TICK_MOVE
                    if player.depth in self.levels:
                        self.levels[player.depth]["tick"] += TICK_MOVE
                    if self.tick % PARALYSIS_STATUS_MSG_INTERVAL == 0:
                        self._tell(player, random.choice(MSG_STATUS_PARALYSIS_TICK),
                                   STATUS_EFFECT_PROPS[STATUS_PARALYSIS]["color"])
                    player.queued_action = None
                    continue
                if player.queued_action is not None:
                    self.execute_player_action(i)
                    # Advance level tick by action cost
                    action_cost = player.next_tick - self.tick
                    if action_cost > 0 and player.depth in self.levels:
                        self.levels[player.depth]["tick"] += action_cost
                else:
                    player.next_tick = self.tick + 1
          # Slow idle progression: advance level ticks by 1 every IDLE_LEVEL_TICK_INTERVAL wall-clock ticks
        if self.tick % IDLE_LEVEL_TICK_INTERVAL == 0:
            for depth in list(self.levels.keys()):
                if any(p.depth == depth and not p.dead for p in self.players):
                    self.levels[depth]["tick"] += 1
        # Cap level tick advancement to max MAX_TICK_ADVANCE_PLAYER_COUNT players worth per wall-clock tick
        _max_tick_advance = MAX_TICK_ADVANCE_PLAYER_COUNT * TICK_ATTACK
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

    def _can_enemy_move_to(self, enemy, x, y, depth):
        """Check if an enemy can move to (x, y).

        Water enemies can only move to water tiles.
        """
        if not self.is_passable(x, y, depth):
            return False
        if self.get_enemy_at(x, y, depth):
            return False
        if enemy.get("water"):
            dungeon = self._get_dungeon(depth)
            if not (0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT):
                return False
            return dungeon[y][x] == TILE_WATER
        return True

    def _process_enemy_action(self, enemy, depth, level_tick):
        """Process one action for an enemy: attack, chase, or wander."""
        ex, ey = enemy["x"], enemy["y"]
        target, dist = self._get_nearest_player(ex, ey, depth)
        is_water = enemy.get("water", False)
        # Water enemies are only visible when adjacent to a player
        if is_water:
            enemy["visible"] = dist <= WATER_ENEMY_ADJACENT_VISIBLE_RANGE
        if target is None:
            moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            random.shuffle(moves)
            moved = False
            for wdx, wdy in moves:
                wx, wy = ex + wdx, ey + wdy
                if self._can_enemy_move_to(enemy, wx, wy, depth):
                    enemy["x"], enemy["y"] = wx, wy
                    moved = True
                    break
            if moved:
                self._ambient_sound(
                    enemy["x"], enemy["y"], depth,
                    ENEMY_SOUNDS.get(enemy["name"],
                                     ENEMY_SOUNDS_DEFAULT),
                    COLOR_WHITE, chance=ENEMY_MOVE_AMBIENT_CHANCE, range=ENEMY_MOVE_AMBIENT_RANGE)
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
                   and dist <= FOV_RADIUS + ENEMYCHASE_FOV_EXTENSION)

        if dist == ENEMY_ATTACK_RANGE:
            result = self.resolve_attack(target, enemy, is_player_attacking=False)
            target.hp -= result["damage"]

            # Shield block message
            if result["shield_blocked"]:
                self._broadcast(
                    target.x, target.y, depth,
                    result["message"], result["message_color"],
                    subject=target, ctx=result["message_ctx"],
                )

            # Hit message
            hit_template = random.choice(
                ENEMY_HIT_MESSAGES.get(enemy["name"],
                                       [ENEMY_HIT_DEFAULT]))
            hit_ctx = {"damage": result["damage"]}
            absorb_suffix = ""
            if result["shield_blocked"]:
                absorb_suffix = f" (shield absorbed {result['shield_absorbed']})"
            self._broadcast(
                target.x, target.y, depth,
                hit_template + absorb_suffix, enemy["color"],
                subject=target, ctx=hit_ctx,
            )

            # Status effect application
            if result["status_applied"]:
                status_name = result["status_applied"]
                props = STATUS_EFFECT_PROPS[status_name]
                # Refresh or set duration (paralysis doesn't stack, refresh on hit)
                if status_name == STATUS_PARALYSIS:
                    # Paralysis: apply immediately, set duration
                    target.status_effects[status_name] = STATUS_EFFECT_DURATION
                else:
                    # DoT effects: set or refresh duration
                    target.status_effects[status_name] = STATUS_EFFECT_DURATION
                self._broadcast(
                    target.x, target.y, depth,
                    random.choice(props["apply_msg"]),
                    props["color"],
                    subject=target,
                    ctx={"enemy": enemy["name"]},
                )

            self._ambient_sound(
                target.x, target.y, depth, COMBAT_CLASH_AMBIENT,
                COLOR_WHITE, chance=COMBAT_CLASH_AMBIENT_CHANCE, range=COMBAT_AMBIENT_RANGE, flat=True)
            enemy["next_tick"] = level_tick + TICK_ATTACK
            if target.hp <= 0:
                target.hp = 0
                target.dead = True
                self._drop_player_items(target, depth)
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
                    COLOR_RED, chance=ENEMY_DEATH_AMBIENT_CHANCE, range=ENEMY_DEATH_AMBIENT_RANGE, flat=True,
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
            if (self._can_enemy_move_to(enemy, nx, ny, depth)
                    and (nx != target.x or ny != target.y)):
                enemy["x"], enemy["y"] = nx, ny
                moved = True
            else:
                moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
                random.shuffle(moves)
                for wdx, wdy in moves:
                    wx, wy = ex + wdx, ey + wdy
                    if self._can_enemy_move_to(enemy, wx, wy, depth):
                        enemy["x"], enemy["y"] = wx, wy
                        moved = True
                        break
            if moved:
                self._ambient_sound(
                    enemy["x"], enemy["y"], depth,
                    ENEMY_SOUNDS.get(enemy["name"], ENEMY_SOUNDS_DEFAULT),
                    COLOR_WHITE, chance=ENEMY_MOVE_AMBIENT_CHANCE, range=ENEMY_MOVE_AMBIENT_RANGE,
                )
            enemy["next_tick"] = level_tick + TICK_MOVE
        else:
            moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            random.shuffle(moves)
            moved = False
            for wdx, wdy in moves:
                wx, wy = ex + wdx, ey + wdy
                if self._can_enemy_move_to(enemy, wx, wy, depth):
                    enemy["x"], enemy["y"] = wx, wy
                    moved = True
                    break
            if moved:
                self._ambient_sound(
                    enemy["x"], enemy["y"], depth,
                    ENEMY_SOUNDS.get(enemy["name"],
                                     ENEMY_SOUNDS_DEFAULT),
                    COLOR_WHITE, chance=ENEMY_MOVE_AMBIENT_CHANCE, range=ENEMY_MOVE_AMBIENT_RANGE)
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
            self._show_entrance(player)
            self._ambient_sound(
                old_x, old_y, old_depth, STAIRS_DOWN_AMBIENT,
                COLOR_CYAN, source=player, chance=ENEMY_DEATH_AMBIENT_CHANCE,
                skip_visible=True, range=STAIRS_AMBIENT_RANGE, flat=True,
            )
            self._ambient_depth(
                new_depth, STAIRS_DOWN_DEPTH_AMBIENT,
                COLOR_CYAN, source=player,
                chance=ENEMY_DEATH_AMBIENT_CHANCE, skip_visible=True,
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
                self._show_entrance(player)
                self._ambient_sound(
                    old_x, old_y, old_depth, STAIRS_UP_AMBIENT,
                    COLOR_CYAN, source=player, chance=ENEMY_DEATH_AMBIENT_CHANCE,
                    skip_visible=True, range=STAIRS_AMBIENT_RANGE, flat=True,
                )
                self._ambient_depth(
                    new_depth, STAIRS_UP_DEPTH_AMBIENT,
                    COLOR_CYAN, source=player,
                    chance=ENEMY_DEATH_AMBIENT_CHANCE, skip_visible=True,
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
            heal = random.randint(POTION_HEAL_MIN, POTION_HEAL_MAX)
            player.hp = min(player.hp + heal, player.max_hp)
            self._broadcast(
                player.x, player.y, player.depth,
                MSG_DRANK_POTION, COLOR_RED,
                subject=player, ctx={"heal": heal},
            )
        elif kind == ITEM_SWORD:
            new_weapon = item["weapon"]
            # Drop old weapon if not fists
            if player.equipped_weapon != WEAPON_FISTS:
                old_weapon = player.equipped_weapon
                self._get_items(player.depth).append({
                    "x": player.x, "y": player.y,
                    "kind": ITEM_SWORD, "weapon": old_weapon,
                })
                old_name = old_weapon["name"] if isinstance(old_weapon, dict) else WEAPON_PROPS[old_weapon]["name"]
                self._broadcast(
                    player.x, player.y, player.depth,
                    MSG_DROPPED_WEAPON, COLOR_WHITE,
                    subject=player,
                    ctx={"weapon": old_name.lower()},
                )
            player.equipped_weapon = new_weapon
            new_name = new_weapon["name"] if isinstance(new_weapon, dict) else WEAPON_PROPS[new_weapon]["name"]
            self._broadcast(
                player.x, player.y, player.depth,
                MSG_EQUIPPED_WEAPON, COLOR_WHITE,
                subject=player,
                ctx={"weapon": new_name.lower()},
            )
        elif kind == ITEM_SHIELD:
            new_shield = item["shield"]
            # Drop old shield if not none
            if player.equipped_shield != SHIELD_NONE:
                old_shield = player.equipped_shield
                self._get_items(player.depth).append({
                    "x": player.x, "y": player.y,
                    "kind": ITEM_SHIELD, "shield": old_shield,
                })
                old_name = old_shield["name"] if isinstance(old_shield, dict) else SHIELD_PROPS[old_shield]["name"]
                self._broadcast(
                    player.x, player.y, player.depth,
                    MSG_DROPPED_SHIELD, COLOR_CYAN,
                    subject=player,
                    ctx={"shield": old_name.lower()},
                )
            player.equipped_shield = new_shield
            new_name = new_shield["name"] if isinstance(new_shield, dict) else SHIELD_PROPS[new_shield]["name"]
            self._broadcast(
                player.x, player.y, player.depth,
                MSG_EQUIPPED_SHIELD, COLOR_CYAN,
                subject=player,
                ctx={"shield": new_name.lower()},
            )
        elif kind == ITEM_GOLD:
            player.gold += item["value"]
            self._broadcast(
                player.x, player.y, player.depth,
                MSG_PICKED_UP_GOLD, COLOR_YELLOW,
                subject=player, ctx={"gold": item["value"]},
            )
        self._get_items(player.depth).pop(idx)

    def _do_wait(self, player):
        """Wait for a moment.

        Build up chance to heal 3HP with each contiguous wait.
        """
        if player.hp >= player.max_hp:
            player.consecutive_waits = 0
            self._broadcast(player.x, player.y, player.depth,
                            MSG_REST_NO_HEAL, COLOR_GREEN, subject=player)
            return
        player.consecutive_waits += 1
        if random.random() < REST_HEAL_CHANCE:
            player.hp = min(player.hp + REST_HEAL_AMOUNT, player.max_hp)
            player.consecutive_waits = 0
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
        if tile == TILE_TRAP:
            discovered = player.discovered_traps.get(depth, set())
            if (mx, my) in discovered:
                return TILE_CHAR[TILE_TRAP]
            return TILE_CHAR[TILE_FLOOR]
        return TILE_CHAR.get(tile, '?')

    def print_text_map(self):
        """Print the current map view as plain text for debugging."""
        view_h = MAX_SCREEN_Y - TEXT_MAP_STATUS_LINES
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

        for msg_text, _, _ in self.players[0].messages[-TEXT_MAP_DISPLAY_MSG_COUNT:]:
            print(msg_text[:view_w])
        print("P1:Arrows  P2:WASD  >:Down  <:Up  g/G:Grab  .:Wait  q:Quit")
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
