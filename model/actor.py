"""
Actor base class shared by Player and Monster.
Provides common attributes and the is_player sentinel used throughout the engine.
"""


class Actor:
    """
    Base class for all combatants.
    Subclasses must set the attributes listed below either in __init__ or as class-level defaults.
    """

    # Subclasses override this to identify themselves without fragile isinstance string checks.
    is_player: bool = False

    # --- Identity ---
    name: str

    # --- Vitals ---
    health: int
    maxHealth: int
    ac: int
    alive: int  # 1 = alive, 0 = dead
    status: list
    deathSaves: dict

    # --- Movement ---
    speed: int
    maxSpeed: int

    # --- Ability scores ---
    modDict: dict

    # --- Actions ---
    weaponList: list
    spells: dict
    reaction: int
    twoAttacks: int

    # --- Initiative ---
    initMod: int

    # --- Spellcasting ---
    spellAttackMod: int
    spellDC: int

    # --- Legendary mechanics ---
    legRes: int
    maxLegRes: int
    legActions: int
    maxLegActions: int
    legActionWeapon: object

    # --- Conditions ---
    cc: list

    # --- Tactical ---
    optRange: int  # preferred engagement distance in hexes
    size: str
