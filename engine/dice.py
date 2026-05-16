"""
Pure dice-rolling and math utilities.
No dependencies on map, actors, or any other engine module.
"""
import random as r
import math
import numpy as np

from engine.utils import safe_log


# ---------------------------------------------------------------------------
# Optional manual roll provider
# Signature:  provider(n, sides, context, actor_name=None) -> list[int] | None
# - actor_name: the name of the actor whose dice these are (None = unknown/attacker)
# - Returning None falls back to random.
# ---------------------------------------------------------------------------
_roll_provider = None


def set_roll_provider(fn):
    """Install a callable that overrides dice randomness (e.g. for manual rolls)."""
    global _roll_provider
    _roll_provider = fn


def clear_roll_provider():
    """Remove the roll provider and restore fully random rolls."""
    global _roll_provider
    _roll_provider = None


def _format_roll_log(n, diceType, rolls):
    """Format a roll result for logging.
    d20 rolls (attack/save checks) show individual values so advantage/disadvantage is visible.
    All other rolls (damage, healing, etc.) show the total only.
    """
    if diceType == 20:
        return f"\t{n}d{diceType}: " + ", ".join(str(x) for x in rolls)
    total = sum(rolls)
    if n == 1:
        return f"\t{n}d{diceType}: {total}"
    return f"\t{n}d{diceType}: {total} ({', '.join(str(x) for x in rolls)})"


def rollDice(n, diceType, map_obj=None, context="", actor_name=None):
    """Roll n dice of diceType sides. Returns list of results."""
    if _roll_provider is not None:
        rolls = _roll_provider(n, diceType, context or f"{n}d{diceType}", actor_name)
        if rolls is not None:
            if map_obj is not None:
                safe_log(_format_roll_log(n, diceType, rolls), map_obj)
            return rolls
    rolls = [r.randint(1, diceType) for _ in range(n)]
    if map_obj is not None:
        safe_log(_format_roll_log(n, diceType, rolls), map_obj)
    return rolls


def rollSave(actor, abilityType, dc, map_obj=None):
    """
    Roll a saving throw. Returns True if failed (roll < dc), False if passed.
    Passes actor.name to the provider so it can decide per-save whether to
    show a manual-roll dialog for that specific actor.
    """
    if _roll_provider is not None:
        result = _roll_provider(
            1, 20,
            f"{actor.name} {abilityType} save (DC {dc})",
            actor.name,
        )
        roll = result[0] if result else r.randint(1, 20)
    else:
        roll = r.randint(1, 20)
    mod = down_round((actor.modDict[abilityType] - 10) / 2)
    safe_log(
        f"\t{actor.name} {abilityType} save: \n\t\t{roll} + {mod} = {roll + mod}",
        map_obj,
    )
    return (roll + mod) < dc


def rollDeathSave(actor, map_obj=None):
    """Roll a death saving throw and update actor state."""
    safe_log(f"\t{actor.name} is rolling death saves!", map_obj)
    if _roll_provider is not None:
        result = _roll_provider(1, 20, f"{actor.name} death saving throw", actor.name)
        roll = result[0] if result else r.randint(1, 20)
    else:
        roll = rollDice(1, 20, map_obj)[0]

    if roll <= 10:
        safe_log(f"\t{actor.name} failed death save with {roll}", map_obj)
        if roll == 1:
            actor.deathSaves["fail"].append(2)
        else:
            actor.deathSaves["fail"].append(1)
    else:
        if roll == 20:
            safe_log(f"{actor.name} is getting up with a Natural 20!", map_obj)
            actor.deathSaves["pass"].append(3)
            actor.health = 1
            actor.status.remove("deathSaves")
            actor.deathSaves = {"pass": [], "fail": []}
            return
        actor.deathSaves["pass"].append(1)
        safe_log(f"{actor.name} passed death save with {roll}", map_obj)

    fails = sum(actor.deathSaves["fail"])
    passes = sum(actor.deathSaves["pass"])

    if fails >= 3:
        actor.alive = 0

    if passes >= 3 and roll != 20:
        actor.health = 1
        actor.status.append("unconscious")
        actor.status.remove("deathSaves")
        actor.deathSaves = {"pass": [], "fail": []}
        safe_log(f"\t{actor.name} has passed death saves", map_obj)

    printDeathSaves(actor.deathSaves, map_obj)


def printDeathSaves(deathSaves, map_obj=None):
    safe_log("\t\tPasses: " + str(deathSaves["pass"]), map_obj)
    safe_log("\t\tFails: " + str(deathSaves["fail"]), map_obj)


def weibull(h):
    x = 1
    y = 0
    z = 0.7
    pk = 1 - np.exp(-x * (h - y) ** z)
    return pk


def col_round(x):
    frac = x - math.floor(x)
    if frac <= 0.5:
        return math.floor(x)
    return math.ceil(x)


def down_round(x):
    frac = x - math.floor(x)
    if frac <= 0.5:
        return math.floor(x)
    return math.ceil(x)


def cone(x):
    area = sum([i for i in range(2, int((x / 5) + 2))]) * 5
    return area
