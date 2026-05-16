"""
DEPRECATED — modelMethods.py is no longer the source of truth.

All logic has been moved to:
  engine/utils.py      — safe_log, singleton, text2int, etc.
  engine/dice.py       — rollDice, rollSave, rollDeathSave, weibull, etc.
  engine/targeting.py  — drawLine, calcMoveHexes, bestSphere, etc.
  engine/combat.py     — takeTurn, doAction, weaponAttack, takeDmg, etc.
  model/weapon.py      — WeaponNew dataclass
  model/actor.py       — Actor base class

This file re-exports everything for backward compatibility only.
Update your imports and then delete this file.
"""
# ruff: noqa: F401
from engine.utils import (
    singleton, safe_log, stringToTuple,
    text2int, numberAfterString, numberBeforeString,
)
from engine.dice import (
    rollDice, rollSave, rollDeathSave, printDeathSaves,
    weibull, col_round, down_round, cone,
)
from engine.targeting import (
    drawLine, calcMoveHexes, coordWithinReach, moveWithingReach,
    bestSphere, bestLine2, bestSquare, bestCone,
)
from engine.combat import (
    myAction, removeDeadActors, takeTurn, chooseAction, doAction,
    healSpellTurn, takeHealing, castSpellTurn, weaponAttack,
    takeDmg, takeReaction,
)
from model.weapon import WeaponNew
