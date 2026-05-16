from dataclasses import dataclass


@dataclass
class WeaponNew:
    name: str
    attackType: str
    range: int
    attackMod: int
    diceType: list
    diceCount: list
    dmgMod: int
