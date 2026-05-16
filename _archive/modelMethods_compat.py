"""
Backward-compatibility shim.

All symbols have been moved to engine/ and model/weapon.py.
This module re-exports them so existing code continues to work during transition.
It will be DELETED once all import sites have been updated.

DO NOT add new code here.
"""
# ruff: noqa
# pylint: disable=wildcard-import

from engine.utils import singleton, safe_log, stringToTuple, text2int, numberAfterString, numberBeforeString
from engine.dice import rollDice, rollSave, rollDeathSave, printDeathSaves, weibull, col_round, down_round, cone
from engine.targeting import drawLine, calcMoveHexes, coordWithinReach, moveWithingReach, bestSphere, bestLine2, bestSquare, bestCone
from engine.combat import myAction, removeDeadActors, takeTurn, chooseAction, doAction, healSpellTurn, takeHealing, castSpellTurn, weaponAttack, takeDmg, takeReaction
from model.weapon import WeaponNew

__all__ = [
    'singleton', 'safe_log', 'stringToTuple', 'text2int', 'numberAfterString', 'numberBeforeString',
    'rollDice', 'rollSave', 'rollDeathSave', 'printDeathSaves', 'weibull', 'col_round', 'down_round', 'cone',
    'drawLine', 'calcMoveHexes', 'coordWithinReach', 'moveWithingReach', 'bestSphere', 'bestLine2', 'bestSquare', 'bestCone',
    'myAction', 'removeDeadActors', 'takeTurn', 'chooseAction', 'doAction',
    'healSpellTurn', 'takeHealing', 'castSpellTurn', 'weaponAttack', 'takeDmg', 'takeReaction',
    'WeaponNew',
]
