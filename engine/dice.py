"""
Pure dice-rolling and math utilities.
No dependencies on map, actors, or any other engine module.
"""
import random as r
import math
import numpy as np

from engine.utils import safe_log


def rollDice(n, diceType, map_obj=None):
    """Roll n dice of diceType sides. Returns list of results."""
    rolls = [r.randint(1, diceType) for _ in range(n)]
    if map_obj is not None:
        string = f'\t{n}d{diceType}: ' + ', '.join(str(x) for x in rolls)
        safe_log(string, map_obj)
    return rolls


def rollSave(actor, abilityType, dc, map_obj=None):
    """
    Roll a saving throw. Returns True if failed (roll < dc), False if passed.
    """
    roll = r.randint(1, 20)
    mod = down_round((actor.modDict[abilityType] - 10) / 2)
    safe_log(
        f'\t{actor.name} {abilityType} save: \n\t\t{roll} + {mod} = {roll + mod}',
        map_obj
    )
    return (roll + mod) < dc


def rollDeathSave(actor, map_obj=None):
    """Roll a death saving throw and update actor state."""
    safe_log(f'\t{actor.name} is rolling death saves!', map_obj)
    roll = rollDice(1, 20, map_obj)[0]

    if roll <= 10:
        safe_log(f'\t{actor.name} failed death save with {roll}', map_obj)
        if roll == 1:
            actor.deathSaves['fail'].append(2)
        else:
            actor.deathSaves['fail'].append(1)
    else:
        if roll == 20:
            safe_log(f'{actor.name} is getting up with a Natural 20!', map_obj)
            actor.deathSaves['pass'].append(3)
            actor.health = 1
            actor.status.remove('deathSaves')
            actor.deathSaves = {'pass': [], 'fail': []}
            return
        actor.deathSaves['pass'].append(1)
        safe_log(f'{actor.name} passed death save with {roll}', map_obj)

    fails = sum(actor.deathSaves['fail'])
    passes = sum(actor.deathSaves['pass'])

    if fails >= 3:
        actor.alive = 0

    if passes >= 3 and roll != 20:
        actor.health = 1
        actor.status.append('unconscious')
        actor.status.remove('deathSaves')
        actor.deathSaves = {'pass': [], 'fail': []}
        safe_log(f'\t{actor.name} has passed death saves', map_obj)

    printDeathSaves(actor.deathSaves, map_obj)


def printDeathSaves(deathSaves, map_obj=None):
    safe_log('\t\tPasses: ' + str(deathSaves['pass']), map_obj)
    safe_log('\t\tFails: ' + str(deathSaves['fail']), map_obj)


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
