CHARGE_MOVES = frozenset(
    {
        "solarbeam",
        "solarblade",
        "skyattack",
        "meteorbeam",
        "electroshot",
        "dig",
        "dive",
        "fly",
        "bounce",
        "phantomforce",
        "shadowforce",
        "skullbash",
        "razorwind",
        "iceburn",
        "freezeshock",
    }
)

RECHARGE_MOVES = frozenset(
    {
        "hyperbeam",
        "gigaimpact",
        "blastburn",
        "frenzyplant",
        "hydrocannon",
        "rockwrecker",
        "roaroftime",
        "prismaticlaser",
        "eternabeam",
    }
)

SUICIDE_MOVES = frozenset(
    {
        "explosion",
        "selfdestruct",
        "mistyexplosion",
        "steelbeam",
        "mindblown",
    }
)

CONDITIONAL_MOVES = frozenset(
    {
        "dreameater",
        "belch",
        "lastrespects",
        "steelroller",
        "focuspunch",
        "avalanche",
        "revenge",
        "payback",
        "retaliate",
        "acrobatics",
        "hex",
        "venoshock",
        "brine",
        "assurance",
        "wakeupslap",
        "smellingsalts",
        "weatherball",
        "terrainpulse",
        "expandingforce",
        "risingvoltage",
        "grassyglide",
        "waterspout",
        "eruption",
        "reversal",
        "flail",
    }
)

SETUP_MOVES = frozenset(
    {
        "swordsdance",
        "dragondance",
        "nastyplot",
        "bulkup",
        "calmmind",
        "irondefense",
        "amnesia",
        "agility",
        "rockpolish",
        "coil",
        "curse",
        "growth",
        "workup",
        "tailglow",
        "shellsmash",
        "quiverdance",
        "shiftgear",
        "honeclaws",
        "geomancy",
    }
)

WEATHER_MOVES = frozenset(
    {
        "sunnyday",
        "raindance",
        "sandstorm",
        "hail",
        "snowscape",
    }
)

TERRAIN_MOVES = frozenset(
    {
        "electricterrain",
        "grassyterrain",
        "mistyterrain",
        "psychicterrain",
    }
)

HAZARD_MOVES = frozenset(
    {
        "stealthrock",
        "spikes",
        "toxicspikes",
        "stickyweb",
    }
)

RECOVERY_MOVES = frozenset(
    {
        "recover",
        "softboiled",
        "roost",
        "slackoff",
        "healorder",
        "milkdrink",
        "moonlight",
        "morningsun",
        "synthesis",
        "shoreup",
        "strengthsap",
    }
)

FORCE_SWITCH_MOVES = frozenset(
    {
        "roar",
        "whirlwind",
        "dragontail",
        "circlethrow",
    }
)

SPECIAL_MOVES = frozenset(
    {
        "metronome",
        "assist",
        "copycat",
        "mirrormove",
        "mefirst",
        "sleeptalk",
        "naturepower",
        "celebrate",
        "holdhands",
        "happyhour",
        "futuresight",
        "waterspout",
        "roaroftime",
        "gigaimpact",
        "dragonascent",
        "psychoboost",
    }
)

EXCLUDED_MOVES = (
    CHARGE_MOVES
    | RECHARGE_MOVES
    | SUICIDE_MOVES
    | CONDITIONAL_MOVES
    | SETUP_MOVES
    | WEATHER_MOVES
    | TERRAIN_MOVES
    | HAZARD_MOVES
    | RECOVERY_MOVES
    | FORCE_SWITCH_MOVES
    | SPECIAL_MOVES
)

PENALIZED_MOVES: dict[str, int] = {
    "dracometeor": 20,
    "leafstorm": 20,
    "overheat": 20,
    "psychoboost": 20,
    "closecombat": 15,
    "superpower": 15,
    "headlongrush": 15,
    "bravebird": 10,
    "flareblitz": 10,
    "woodhammer": 10,
    "doubleedge": 10,
    "volttackle": 10,
    "wavecrash": 10,
}
