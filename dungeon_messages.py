#!/usr/bin/env python3
"""
Dungeon Crawler - Message strings and templates.

All player-facing message strings live here for easy localization
and content changes without touching game logic.

Placeholders:
  {name}     -- resolved to 'You' (subject player) or actual name (others)
  {damage}   -- numeric damage value
  {heal}     -- numeric HP recovered
  {level}    -- numeric player level
  {depth}    -- numeric dungeon depth
  {bonus}    -- numeric equipment bonus
  {gold}     -- numeric gold amount
  {enemy}    -- enemy display name
  {killer}   -- name of creature that killed a player
  {corpse}   -- name of dead player
  {corpse_level} -- level of dead player
"""

# ---------------------------------------------------------------------------
# Enemy movement ambient sounds (one list per monster name)
# ---------------------------------------------------------------------------
ENEMY_SOUNDS = {
    "Rat": [
        "You hear faint scratching in the darkness.",
        "Something small scurries across the stone floor.",
        "A faint squeak echoes from somewhere nearby.",
    ],
    "Bat": [
        "You hear the flutter of leathery wings nearby.",
        "A faint squeaking sound comes from the shadows.",
        "Something flutters past in the darkness.",
    ],
    "Spider": [
        "You hear a faint skittering against the stone.",
        "Something crawls across the ceiling above.",
        "A soft clicking sound echoes from the darkness.",
    ],
    "Snake": [
        "You hear a faint hiss in the darkness.",
        "Something slithers across the stone floor.",
        "A dry rustling sound comes from somewhere nearby.",
    ],
    "Kobold": [
        "You hear faint chittering nearby.",
        "Something small and quick scampers in the dark.",
        "A distant giggle echoes through the corridor.",
    ],
    "Goblin": [
        "You hear a faint cackle in the distance.",
        "Something shuffles nearby with clanking metal.",
        "A guttural mutter echoes through the darkness.",
    ],
    "Imp": [
        "You hear a faint cackle echoing nearby.",
        "Something small and swift darts through the shadows.",
        "A sizzling sound comes from somewhere in the dark.",
    ],
    "Skeleton": [
        "You hear bones clattering in the darkness.",
        "Something rattles as it moves nearby.",
        "A dry clicking echoes through the corridor.",
    ],
    "Zombie": [
        "You hear a slow shuffle in the darkness.",
        "Something drags heavily across the stone.",
        "A low groan echoes from somewhere nearby.",
    ],
    "Wolf": [
        "You hear a low growl in the distance.",
        "Something prowls through the shadows nearby.",
        "A sharp snarl echoes through the corridor.",
    ],
    "Hydra": [
        "You hear multiple heads hissing in the darkness.",
        "Something massive shifts nearby with a wet slither.",
        "A deep gurgling roar echoes through the dungeon.",
    ],
    "Mummy": [
        "You hear bandages rustling in the darkness.",
        "Something shuffles slowly with a dry whisper.",
        "Ancient mumbling echoes from somewhere nearby.",
    ],
    "Wraith": [
        "You hear a chilling whisper in the darkness.",
        "Something ethereal drifts through the shadows.",
        "A cold moan echoes from somewhere nearby.",
    ],
    "Troll": [
        "You hear heavy thudding footsteps nearby.",
        "Something massive grunts in the darkness.",
        "A crude club drags across the stone floor.",
    ],
    "Minotaur": [
        "You hear heavy hooves pounding in the distance.",
        "Something massive snorts in the darkness.",
        "A horn scrapes against stone nearby.",
    ],
    "Medusa": [
        "You hear a faint hissing, like many snakes at once.",
        "Something moves with an uncanny stillness nearby.",
        "A cold whisper echoes from the shadows.",
    ],
    "Owlbear": [
        "You hear a guttural hoot in the darkness.",
        "Something heavy scratches at the stone.",
        "Talons scrape across the floor nearby.",
    ],
    "Hook Horror": [
        "You hear metal clanking in the darkness.",
        "Something drags heavy hooks across the stone.",
        "A rhythmic scraping echoes from somewhere nearby.",
    ],
    "Phase Spider": [
        "You hear a faint shimmering in the air.",
        "Something skitters through the walls nearby.",
        "A dimensional ripple echoes from the shadows.",
    ],
    "Basilisk": [
        "You hear a heavy slithering in the darkness.",
        "Something hisses with a stony resonance.",
        "A cold clicking echoes from somewhere nearby.",
    ],
    "Wyvern": [
        "You hear heavy wings beating in the distance.",
        "Something scaly scrapes against the stone.",
        "A deep roar echoes through the dungeon.",
    ],
    "Phoenix": [
        "You hear crackling flames in the darkness.",
        "Something melodic cries from somewhere nearby.",
        "Wings beat with the sound of rushing fire.",
    ],
    "Grue": [
        "You hear whispers from the darkness itself.",
        "Something shifts in the shadows nearby.",
        "A cold presence stirs in the distance.",
    ],
    "Gelatinous Cube": [
        "You hear a wet squelching in the darkness.",
        "Something drips and oozes across the floor.",
        "A gurgling sound echoes from somewhere nearby.",
    ],
    "Remorhaz": [
        "You hear the ground tremble with heavy footsteps.",
        "Something burrows through the stone nearby.",
        "A deep rumble echoes with crackling heat.",
    ],
    "Ice Devil": [
        "You hear a freezing wind in the darkness.",
        "Something heavy moves with crackling frost.",
        "A chilling laugh echoes from somewhere nearby.",
    ],
    "Lich": [
        "You hear a faint chanting in the darkness.",
        "Something moves with an aura of cold magic.",
        "A crackling energy echoes from somewhere nearby.",
    ],
    "Beholder": [
        "You hear a wet squelching and clicking nearby.",
        "Something floats through the darkness with a hum.",
        "Multiple eyes track you from somewhere in the shadows.",
    ],
    "Balor": [
        "You hear fire crackling with immense heat.",
        "Something massive moves with devastating power.",
        "A deep roar shakes the very walls nearby.",
    ],
    "Orc": [
        "You hear heavy footsteps and grunting nearby.",
        "Something swings a weapon in the darkness.",
        "A guttural shout echoes through the corridor.",
    ],
    "Golem": [
        "You hear heavy stone grinding nearby.",
        "Something massive thuds across the floor.",
        "Metallic clanking echoes from somewhere in the dark.",
    ],
    "Demon": [
        "You hear a deep roar from the darkness.",
        "Something moves with crackling hellfire.",
        "Sulfurous heat radiates from somewhere nearby.",
    ],
    "Dragon": [
        "You hear massive wings beating in the distance.",
        "Something enormous shifts with a deep rumble.",
        "A roar echoes through the dungeon with terrifying force.",
    ],
    "Water Mite": [
        "You hear a faint splashing in the water.",
        "Something small ripples across the pool nearby.",
        "A tiny splash echoes from the dark water.",
    ],
    "Water Snake": [
        "You hear a faint hiss from the water.",
        "Something slithers beneath the surface nearby.",
        "A ripple disturbs the still water in the distance.",
    ],
    "Deep One": [
        "You hear gurgling speech from the water.",
        "Something large moves beneath the dark surface.",
        "A wet gurgling sound comes from the pool nearby.",
    ],
    "Water Elemental": [
        "You hear water churning and splashing nearby.",
        "The pool bubbles and swirls with unseen force.",
        "A rushing sound of water echoes from the darkness.",
    ],
    "Kraken": [
        "You hear massive splashing and gurgling nearby.",
        "The water trembles as something enormous shifts beneath.",
        "A deep rumbling roar emanates from the dark depths.",
    ],
}

ENEMY_SOUNDS_DEFAULT = [
    "You hear a faint scuttling in the darkness.",
    "Something shifts in the shadows nearby.",
    "You hear a low growl in the distance.",
]

# ---------------------------------------------------------------------------
# Enemy hit broadcast messages (one list per monster name)
# ---------------------------------------------------------------------------
ENEMY_HIT_MESSAGES = {
    "Rat": [
        "The Rat bites {name} for {damage} damage!",
        "The Rat gnaws at {name} for {damage} damage!",
        "The Rat scratches at {name} for {damage} damage!",
    ],
    "Bat": [
        "The Bat pecks at {name} for {damage} damage!",
        "The Bat claws at {name} for {damage} damage!",
        "The Bat dives and strikes {name} for {damage} damage!",
    ],
    "Spider": [
        "The Spider bites {name} for {damage} damage!",
        "The Spider injects venom into {name} for {damage} damage!",
        "The Spider wraps {name} in web and bites for {damage} damage!",
    ],
    "Snake": [
        "The Snake strikes {name} for {damage} damage!",
        "The Snake bites {name} and injects venom for {damage} damage!",
        "The Snake coils tight and strikes {name} for {damage} damage!",
    ],
    "Kobold": [
        "The Kobold stabs {name} with a rusty dagger for {damage} damage!",
        "The Kobold strikes {name} with a crude club for {damage} damage!",
        "The Kobold lunges and scratches {name} for {damage} damage!",
    ],
    "Goblin": [
        "The Goblin hits {name} with a wooden club for {damage} damage!",
        "The Goblin slashes {name} with a jagged blade for {damage} damage!",
        "The Goblin strikes {name} with surprising speed for {damage} damage!",
    ],
    "Imp": [
        "The Imp claws at {name} for {damage} damage!",
        "The Imp bites {name} with sharp fangs for {damage} damage!",
        "The Imp zaps {name} with a burst of hellfire for {damage} damage!",
    ],
    "Skeleton": [
        "The Skeleton strikes {name} with bony fists for {damage} damage!",
        "The Skeleton clubs {name} with a rusty sword for {damage} damage!",
        "The Skeleton slashes {name} with skeletal hands for {damage} damage!",
    ],
    "Zombie": [
        "The Zombie grabs {name} and bites for {damage} damage!",
        "The Zombie slams into {name} for {damage} damage!",
        "The Zombie strikes {name} with rotting hands for {damage} damage!",
    ],
    "Wolf": [
        "The Wolf lunges and bites {name} for {damage} damage!",
        "The Wolf claws at {name} for {damage} damage!",
        "The Wolf tackles {name} for {damage} damage!",
    ],
    "Hydra": [
        "The Hydra bites {name} with multiple heads for {damage} damage!",
        "The Hydra wraps around {name} and bites for {damage} damage!",
        "The Hydra lashes out with its tails for {damage} damage!",
    ],
    "Mummy": [
        "The Mummy strikes {name} with bandaged fists for {damage} damage!",
        "The Mummy wraps {name} in ancient bandages for {damage} damage!",
        "The Mummy delivers a withering blow to {name} for {damage} damage!",
    ],
    "Wraith": [
        "The Wraith drains life force from {name} for {damage} damage!",
        "The Wraith strikes {name} with spectral claws for {damage} damage!",
        "The Wraith delivers a chilling touch to {name} for {damage} damage!",
    ],
    "Troll": [
        "The Troll swings a massive club at {name} for {damage} damage!",
        "The Troll slams {name} with huge fists for {damage} damage!",
        "The Troll delivers a crushing blow to {name} for {damage} damage!",
    ],
    "Minotaur": [
        "The Minotaur charges and strikes {name} for {damage} damage!",
        "The Minotaur swings a massive axe at {name} for {damage} damage!",
        "The Minotaur delivers a powerful blow to {name} for {damage} damage!",
    ],
    "Medusa": [
        "The Medusa strikes {name} with a serpent's hiss for {damage} damage!",
        (
            "The Medusa delivers a paralyzing touch to {name} "
            "for {damage} damage!"
        ),
        "The Medusa lashes out with writhing snake hair for {damage} damage!",
    ],
    "Owlbear": [
        "The Owlbear claws deeply into {name} for {damage} damage!",
        "The Owlbear strikes {name} with massive talons for {damage} damage!",
        "The Owlbear delivers a crushing blow to {name} for {damage} damage!",
    ],
    "Hook Horror": [
        "The Hook Horror slashes {name} with razor hooks for {damage} damage!",
        "The Hook Horror drags its hooks across {name} for {damage} damage!",
        (
            "The Hook Horror strikes {name} with metal appendages "
            "for {damage} damage!"
        ),
    ],
    "Phase Spider": [
        (
            "The Phase Spider phases through the wall and bites "
            "{name} for {damage} damage!"
        ),
        (
            "The Phase Spider materializes and strikes {name} "
            "for {damage} damage!"
        ),
        "The Phase Spider injects venom into {name} for {damage} damage!",
    ],
    "Basilisk": [
        (
            "The Basilisk strikes {name} with a petrifying gaze "
            "for {damage} damage!"
        ),
        "The Basilisk delivers a venomous bite to {name} for {damage} damage!",
        "The Basilisk lashes {name} with its stony tail for {damage} damage!",
    ],
    "Wyvern": [
        "The Wyvern breathes acid onto {name} for {damage} damage!",
        "The Wyvern strikes {name} with massive claws for {damage} damage!",
        "The Wyvern delivers a poisonous bite to {name} for {damage} damage!",
    ],
    "Phoenix": [
        "The Phoenix scorches {name} with blazing flames for {damage} damage!",
        "The Phoenix strikes {name} with fiery wings for {damage} damage!",
        "The Phoenix delivers a searing blow to {name} for {damage} damage!",
    ],
    "Grue": [
        (
            "The Grue emerges from the darkness and strikes "
            "{name} for {damage} damage!"
        ),
        "The Grue delivers a chilling touch to {name} for {damage} damage!",
        "The Grue strikes {name} with shadowy claws for {damage} damage!",
    ],
    "Gelatinous Cube": [
        (
            "The Gelatinous Cube partially engulfs {name} "
            "and dissolves for {damage} damage!"
        ),
        (
            "The Gelatinous Cube delivers a squelching blow to {name} "
            "for {damage} damage!"
        ),
        (
            "The Gelatinous Cube oozes corrosive slime onto {name} "
            "for {damage} damage!"
        ),
    ],
    "Remorhaz": [
        "The Remorhaz burrows up and strikes {name} for {damage} damage!",
        "The Remorhaz breathes intense heat onto {name} for {damage} damage!",
        (
            "The Remorhaz delivers a devastating blow to {name} "
            "for {damage} damage!"
        ),
    ],
    "Ice Devil": [
        "The Ice Devil strikes {name} with razor frost for {damage} damage!",
        (
            "The Ice Devil delivers a freezing blow to {name} "
            "for {damage} damage!"
        ),
        "The Ice Devil scorches {name} with cold fire for {damage} damage!",
    ],
    "Lich": [
        "The Lich zaps {name} with necrotic energy for {damage} damage!",
        "The Lich strikes {name} with a skeletal hand for {damage} damage!",
        "The Lich delivers a withering curse to {name} for {damage} damage!",
    ],
    "Beholder": [
        "The Beholder fires a ray at {name} for {damage} damage!",
        (
            "The Beholder strikes {name} with writhing eyestalks "
            "for {damage} damage!"
        ),
        (
            "The Beholder blasts {name} with a debilitating ray "
            "for {damage} damage!"
        ),
    ],
    "Balor": [
        "The Balor strikes {name} with a flaming sword for {damage} damage!",
        "The Balor breathes hellfire onto {name} for {damage} damage!",
        "The Balor delivers a devastating blow to {name} for {damage} damage!",
    ],
    "Orc": [
        "The Orc strikes {name} with a heavy axe for {damage} damage!",
        "The Orc hits {name} with a spiked club for {damage} damage!",
        "The Orc slashes {name} with a crude blade for {damage} damage!",
    ],
    "Golem": [
        "The Golem slams {name} with stone fists for {damage} damage!",
        "The Golem delivers a crushing blow to {name} for {damage} damage!",
        "The Golem strikes {name} with metallic arms for {damage} damage!",
    ],
    "Demon": [
        (
            "The Demon strikes {name} with crackling hellfire "
            "for {damage} damage!"
        ),
        "The Demon claws at {name} with demonic strength for {damage} damage!",
        "The Demon delivers a devastating blow to {name} for {damage} damage!",
    ],
    "Dragon": [
        "The Dragon breathes searing fire onto {name} for {damage} damage!",
        "The Dragon strikes {name} with massive claws for {damage} damage!",
        (
            "The Dragon delivers a devastating bite to {name} "
            "for {damage} damage!"
        ),
    ],
    "Water Mite": [
        "A Water Mite bursts from the water and bites {name} for {damage} damage!",
        "Something small and fast strikes {name} from the water for {damage} damage!",
        "A Water Mite leaps from the pool and stings {name} for {damage} damage!",
    ],
    "Water Snake": [
        "A Water Snake lunges from the water and bites {name} for {damage} damage!",
        "Cold water erupts as a Water Snake strikes {name} for {damage} damage!",
        "A Water Snake coils around {name} and bites for {damage} damage!",
    ],
    "Deep One": [
        "A Deep One rises from the water and claws {name} for {damage} damage!",
        "Something large emerges from the depths and strikes {name} for {damage} damage!",
        "A Deep One grabs {name} from the water and slashes for {damage} damage!",
    ],
    "Water Elemental": [
        "A Water Elemental surges from the pool and slams {name} for {damage} damage!",
        "The water boils as a Water Elemental strikes {name} for {damage} damage!",
        "A torrent of water crashes into {name} for {damage} damage!",
    ],
    "Kraken": [
        "A Kraken tentacle lashes {name} from the water for {damage} damage!",
        "The water explodes as a Kraken emerges and strikes {name} for {damage} damage!",
        "A massive Kraken grabs {name} and slams them for {damage} damage!",
    ],
}

ENEMY_HIT_DEFAULT = "The {enemy} hits {name} for {damage} damage!"

# ---------------------------------------------------------------------------
# Generic ambient sounds (not tied to a specific monster)
# ---------------------------------------------------------------------------
PLAYER_MOVE_AMBIENT = [
    "You hear faint footsteps nearby.",
    "A faint sound of movement echoes through the dungeon.",
    "You hear something moving in the distance.",
]

COMBAT_CLASH_AMBIENT = [
    "You hear the sharp clash of steel nearby.",
    "A sudden clash echoes through the dungeon.",
    "You hear something being struck in the distance.",
]

ENEMY_DEATH_AMBIENT = [
    "You hear something collapse in the distance.",
    "A dying groan echoes nearby.",
    "You hear a wet thud from somewhere nearby.",
]

PLAYER_DEATH_AMBIENT = [
    "You hear someone cry out in agony nearby.",
    "A terrible scream echoes through the dungeon.",
    "You hear a body collapse in the distance.",
]

STAIRS_DOWN_AMBIENT = [
    "You hear footsteps descending the stairs.",
    "The sound of boots echoing down the staircase.",
    "Footsteps fade into the depths below.",
]

STAIRS_DOWN_DEPTH_AMBIENT = [
    "You hear footsteps descending from above.",
    "Boots echo down the staircase.",
    "Footsteps approach from the stairs above.",
]

STAIRS_UP_AMBIENT = [
    "You hear footsteps ascending the stairs.",
    "The sound of boots echoing up the staircase.",
    "Footsteps fade upward into the darkness.",
]

STAIRS_UP_DEPTH_AMBIENT = [
    "You hear footsteps ascending from below.",
    "Boots echo up the staircase.",
    "Footsteps approach from the stairs below.",
]

ENEMY_SPAWN_AMBIENT = [
    "You hear a sudden growl in the distance.",
    "Something stirs in the darkness nearby.",
    "A cold chill runs down your spine.",
]

# ---------------------------------------------------------------------------
# Broadcast messages (visible to all players who can see the event)
# ---------------------------------------------------------------------------
MSG_PLAYER_HIT_ENEMY = {
    0: [
        "{name}'s attack glanced off the {enemy}!",
        "{name} struck the {enemy} but did no damage.",
        "{name} swung at the {enemy} and missed entirely.",
    ],
    1: [
        "{name} scratched the {enemy} for {damage} damage.",
        "{name} tapped the {enemy} for {damage} damage.",
        "{name} grazed the {enemy} for {damage} damage.",
    ],
    2: [
        "{name} landed a light blow on the {enemy} for {damage} damage.",
        "{name} struck the {enemy} for {damage} damage.",
        "{name} hit the {enemy} for {damage} damage.",
    ],
    3: [
        "{name} landed a solid hit on the {enemy} for {damage} damage.",
        "{name} struck the {enemy} hard for {damage} damage.",
        "{name} connected with the {enemy} for {damage} damage.",
    ],
    5: [
        "{name} smashed into the {enemy} for {damage} damage!",
        "{name} landed a heavy blow on the {enemy} for {damage} damage!",
        "{name} struck the {enemy} powerfully for {damage} damage!",
    ],
    8: [
        "{name} devastated the {enemy} for {damage} damage!",
        "{name} wrecked the {enemy} for {damage} damage!",
        "{name} brutally struck the {enemy} for {damage} damage!",
    ],
    12: [
        "{name} utterly obliterated the {enemy} for {damage} damage!",
        "{name} annihilated the {enemy} for {damage} damage!",
        "{name} absolutely demolished the {enemy} for {damage} damage!",
    ],
}
MSG_ENEMY_DIES = "The {enemy} dies!"
MSG_LEVEL_UP = "{name} is now level {level}!"
MSG_PLAYER_DIED = "{name} has died!"
MSG_CONQUERED = "{name} has conquered the dungeon!"
MSG_DESCENDED = "{name} descended deeper. (Depth: {depth})"
MSG_ASCENDED = "{name} went back up. (Depth: {depth})"
MSG_DRANK_POTION = "{name} drank a potion. Recovered {heal} HP."
MSG_EQUIPPED_WEAPON = "{name} equipped a {weapon}."
MSG_EQUIPPED_SHIELD = "{name} equipped a {shield}."
MSG_DROPPED_WEAPON = "{name} dropped a {weapon}."
MSG_DROPPED_SHIELD = "{name} dropped a {shield}."
MSG_PICKED_UP_GOLD = "{name} picked up {gold} gold."
MSG_REST_HEAL = "{name} waited for a moment. (+3 HP)"
MSG_REST_NO_HEAL = "{name} waited for a moment."
MSG_ENEMY_APPEARS = "A {enemy} appears!"

# ---------------------------------------------------------------------------
# Combat result messages
# ---------------------------------------------------------------------------
MSG_CRITICAL_HIT = [
    "{name} lands a crushing blow on the {enemy} for {damage} damage!",
    "{name} strikes the {enemy} vitally for {damage} damage!",
    "{name} devastates the {enemy} with a critical strike for {damage} damage!",
]
MSG_GLANCING_HIT = [
    "{name}'s attack glanced off the {enemy} for {damage} damage.",
    "{name} barely scratched the {enemy} for {damage} damage.",
    "{name}'s blow skimmed the {enemy} for {damage} damage.",
]
MSG_ENEMY_DODGE = [
    "The {enemy} dodges {name}'s attack!",
    "The {enemy} evades {name}'s strike!",
    "{name}'s attack passes harmlessly by the {enemy}!",
]
MSG_SHIELD_BLOCK = [
    "{name}'s shield absorbs the blow!",
    "{name}'s shield takes the hit!",
    "{name} blocks the attack with their shield!",
]
MSG_SHIELD_BLOCK_PARTIAL = [
    "{name}'s shield absorbs some of the blow! ({absorbed} absorbed)",
    "{name}'s shield takes the hit! ({absorbed} absorbed)",
    "{name} blocks with their shield! ({absorbed} absorbed)",
]

# ---------------------------------------------------------------------------
# Status effect messages
# ---------------------------------------------------------------------------
MSG_STATUS_POISON_APPLY = [
    "{name} is poisoned by the {enemy}!",
    "Venom courses through {name}'s veins!",
    "{name} feels poisoned!",
]
MSG_STATUS_BURN_APPLY = [
    "{name} is burned by the {enemy}!",
    "Flames sear {name}'s flesh!",
    "{name} catches fire!",
]
MSG_STATUS_BLEED_APPLY = [
    "{name} starts bleeding from the {enemy}'s attack!",
    "Blood pours from {name}'s wounds!",
    "{name} is cut deeply!",
]
MSG_STATUS_CHILL_APPLY = [
    "{name} is frozen by the {enemy}'s touch!",
    "An icy chill slows {name} down!",
    "{name} shivers as frost covers their body!",
]
MSG_STATUS_PARALYSIS_APPLY = [
    "{name} is paralyzed by the {enemy}!",
    "{name} can't move, frozen in place!",
    "Paralysis locks {name}'s muscles!",
]
MSG_STATUS_DO_TICK = "{name} takes {damage} damage from {effect}."
MSG_STATUS_PARALYSIS_TICK = "{name} is paralyzed and cannot move!"
MSG_STATUS_WEAR_OFF = "{name}'s {effect} wears off."

# ---------------------------------------------------------------------------
# Direct player messages (_tell)
# ---------------------------------------------------------------------------
MSG_ENEMY_INTO_VIEW = "A {enemy} comes into view."
MSG_GENERATOR_INTO_VIEW = [
    "You notice a pulsing portal shimmering in the shadows.",
    "A faintly glowing pool catches your eye.",
    "Something eerie glimmers ahead.",
    "You see a swirling rift in the air.",
]
MSG_PLAYER_INTO_VIEW = [
    "You spot {player} lurking in the shadows.",
    "A faint glimmer reveals {player} ahead.",
    "You catch sight of {player} in the distance.",
    "Something moves — it's {player}.",
]
MSG_GENERATOR_SPAWNS = [
    "A {enemy} emerges from a swirling portal!",
    "A {enemy} materializes from a glowing pool!",
    "A {enemy} crawls out of a dark rift!",
    "Reality tears open and a {enemy} steps through!",
]
MSG_HIT_GENERATOR = "{name} strikes the portal for {damage} damage!"
MSG_GENERATOR_DESTROYED = "The portal collapses in a flash of light!"
MSG_GENERATOR_RESPAWN = "A new portal begins to form in the distance."
MSG_CORPSE_INFO = (
    "You see the corpse of {corpse} (lv {corpse_level}). "
    "Looks like they were killed by a {killer}."
)
MSG_NO_STAIRS_DOWN = "{name}: no stairs down here."
MSG_CANNOT_GO_UP = "{name}: can't go up further."
MSG_NO_STAIRS_UP = "{name}: no stairs up here."
MSG_NOTHING_TO_GRAB = "{name}: nothing to grab here."

# ---------------------------------------------------------------------------
# Walk-over messages (shown when player steps onto a tile with an entity)
# ---------------------------------------------------------------------------
MSG_SEE_ITEM = [
    "You see a {item} here.",
    "A {item} lies on the ground.",
    "There's a {item} here.",
]
MSG_SEE_CORPSE = [
    "You see the corpse of {corpse} (lv {corpse_level}). "
    "Looks like they were killed by a {killer}.",
    "The remains of {corpse} (lv {corpse_level}) lie here. "
    "A {killer} was responsible.",
    "You step near {corpse}'s corpse (lv {corpse_level}). "
    "Killed by a {killer}.",
]
MSG_SEE_STAIRS_DOWN = [
    "You see stairs leading down.",
    "Stairs descend into darkness.",
    "There are stairs heading deeper.",
]
MSG_SEE_STAIRS_UP = [
    "You see stairs leading up.",
    "Stairs ascend towards light.",
    "There are stairs heading up.",
]
MSG_SEE_PLAYER = [
    "You bump into {player}.",
    "You step right up to {player}.",
    "You walk alongside {player}.",
]
MSG_OPEN_DOOR = [
    "You push the door open with a creak.",
    "You open the door.",
    "The door swings open as you push it.",
]
MSG_SEE_DOOR_OPEN = [
    "You step through the open doorway.",
    "You walk across the open door.",
    "You pass through the doorway.",
]
MSG_WALK_WALL = [
    "You bump into the wall.",
    "The wall stops you in your tracks.",
    "You press against the stone wall.",
    "The wall is solid.",
]
MSG_ENTER_WATER = [
    "You wade into the water.",
    "You step into the pool.",
    "Cold water rises around your legs.",
    "You splash into the water.",
]
MSG_LEAVE_WATER = [
    "You step out of the water.",
    "You wade out of the pool.",
    "Water drips from your clothes as you exit.",
    "You emerge from the water.",
]
MSG_STEP_TRAP = [
    "You step on a hidden trap and take {damage} damage!",
    "A trap snaps shut under your foot for {damage} damage!",
    "You trigger a concealed pit trap for {damage} damage!",
    "Sharpened spikes erupt from the floor dealing {damage} damage!",
]

# ---------------------------------------------------------------------------
# Dungeon entrance messages (shown once per level on first entry)
# ---------------------------------------------------------------------------
MSG_ENTRANCE_ROOMS = [
    "You step into a network of chambers and corridors.",
    "Stone rooms stretch before you, connected by narrow passages.",
    "You find yourself in a dungeon of rooms and hallways.",
]
MSG_ENTRANCE_CAVES = [
    "You descend into a sprawling cave system.",
    "Natural caverns open before you, their walls slick with moisture.",
    "You find yourself in a vast underground cave network.",
]
MSG_ENTRANCE_LABYRINTH = [
    "You enter a maze of twisting corridors and dead ends.",
    "A labyrinth of tight passages stretches in every direction.",
    "You find yourself in a maze of narrow hallways.",
]
MSG_ENTRANCE_TOWER = [
    "You step into a circular chamber within a dark tower.",
    "Concentric rings of chambers surround a central arena.",
    "You find yourself inside an ancient tower, its rooms spiraling inward.",
]
