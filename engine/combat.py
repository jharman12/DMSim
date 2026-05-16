"""
Combat resolution: turn AI, weapon attacks, spell casting, damage, reactions.
No Qt imports — fully testable.
"""
import re
from dataclasses import dataclass
from typing import Optional

from engine.utils import safe_log
from engine.dice import rollDice, rollSave, rollDeathSave, printDeathSaves
from engine.targeting import (
    drawLine, coordWithinReach, moveWithingReach,
    bestSphere, bestLine2, bestSquare, bestCone,
)
from engine.persistent import (
    create_persistent_spell, end_concentration, concentration_save,
)


@dataclass
class myAction:
    name: str
    type: str
    mod: float
    numHit: int
    currCoord: tuple
    moveCoord: tuple
    targets: list
    castCoord: Optional[tuple] = None
    area_coords: list = None  # all hex coords in the spell area (including empty hexes)


def removeDeadActors(map_obj, sortedInitList):
    totalList = map_obj.party + map_obj.enemy
    deadActors = [actor for actor in totalList if not actor.alive]
    for deadActor in deadActors:
        print(deadActor.name, 'is dead')
        if deadActor in map_obj.party:
            map_obj.party.remove(deadActor)
        else:
            map_obj.enemy.remove(deadActor)
        actorCoord = [
            coord for coord in list(map_obj.arrayCenters)
            if map_obj.arrayCenters[coord] == deadActor
        ][0]
        map_obj.arrayCenters[actorCoord] = ''
        del sortedInitList[deadActor]
    return deadActors


def takeTurn(actor, map_obj, interactive=False, gViewer=None):
    """
    AI turn decision function.
    Loops through every weapon and spell, decides best move/cast to maximise damage/healing.
    Returns [actor, map_obj, turnChoices, turnChoice] in interactive mode, else executes action.
    """
    print(gViewer)
    healDownedTeammate = []

    if not actor.is_player:
        actor.legActions = actor.maxLegActions
    else:
        if 'deathSaves' in actor.status:
            rollDeathSave(actor, map_obj)
            if 'deathSaves' in actor.status or 'unconscious' in actor.status:
                print(actor.name, 'turn is skipped, in deathSaves or unconscious', actor.status)
                safe_log(
                    '\t' + actor.name + ' turn is skipped, in deathSaves or unconscious '
                    + str(actor.status), map_obj
                )
                return
        if 'unconscious' in actor.status:
            return
        if actor in map_obj.party:
            for mate in map_obj.party:
                if mate.alive and 'deathSaves' in mate.status:
                    print('Teammate', mate.name, 'is down at',
                          [x for x in list(map_obj.arrayCenters) if map_obj.arrayCenters[x] == mate][0])
                    healDownedTeammate.append(
                        [x for x in list(map_obj.arrayCenters) if map_obj.arrayCenters[x] == mate][0]
                    )

    actor.reaction = 1

    # --- Restrained: speed is 0 this turn ---
    is_restrained = bool(getattr(actor, 'restrained', []))
    effective_speed = 0 if is_restrained else actor.speed

    if actor in map_obj.enemy:
        aTargets = 'party'
        hTargets = 'enemy'
        enemyList = [
            list(map_obj.arrayCenters).index(i)
            for i in map_obj.arrayCenters.keys()
            if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.enemy
        ]
        partyList = [
            list(map_obj.arrayCenters).index(i)
            for i in map_obj.arrayCenters.keys()
            if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.party
        ]

    if actor in map_obj.party:
        enemyList = [
            list(map_obj.arrayCenters).index(i)
            for i in map_obj.arrayCenters.keys()
            if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.party
        ]
        partyList = [
            list(map_obj.arrayCenters).index(i)
            for i in map_obj.arrayCenters.keys()
            if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.enemy
        ]
        hTargets = 'party'
        aTargets = 'enemy'

    myIndex = [
        list(map_obj.arrayCenters).index(i)
        for i in map_obj.arrayCenters.keys()
        if map_obj.arrayCenters[i] == actor
    ][0]
    closest = 999
    distance = []
    for index in enemyList:
        dist = map_obj.distanceCalc(myIndex, index)
        distance.append(dist)
        if dist <= closest:
            closest = dist
            toAttack = map_obj.arrayCenters[list(map_obj.arrayCenters)[index]]

    minDist = min(distance)
    closestGuy = map_obj.arrayCenters[list(map_obj.arrayCenters)[enemyList[distance.index(minDist)]]]
    closestCoord = [coord for coord in list(map_obj.arrayCenters) if map_obj.arrayCenters[coord] == closestGuy][0]
    closestIndex = list(map_obj.arrayCenters).index(closestCoord)
    distanceMatrix = [
        (map_obj.distanceCalc(myIndex, index), map_obj.distanceCalc(closestIndex, index))
        for index in range(len(list(map_obj.arrayCenters)))
        if map_obj.arrayCenters[list(map_obj.arrayCenters)[index]] == ''
    ]
    moveMatrix = [
        index for index in range(len(list(map_obj.arrayCenters)))
        if map_obj.distanceCalc(index, myIndex) <= effective_speed / 5
        and (map_obj.arrayCenters[list(map_obj.arrayCenters)[index]] == ''
             or map_obj.arrayCenters[list(map_obj.arrayCenters)[index]] == actor)
    ]

    turnChoices = []
    myCoord = list(map_obj.arrayCenters)[myIndex]

    # --- Weapon choices ---
    for weap in actor.weaponList:
        avgDmg = 0
        if int(minDist) > int((int(weap.range) + int(effective_speed)) / 5):
            turnChoices.append(myAction(
                name=weap.name, type='Wdmg', mod=0, numHit=0,
                currCoord=list(map_obj.arrayCenters)[myIndex],
                moveCoord=list(map_obj.arrayCenters)[myIndex], targets=[]
            ))
            continue

        anyOpenSpot = [x for x in distanceMatrix if x[0] <= effective_speed / 5 and x[1] <= int(weap.range) / 5]
        if len(anyOpenSpot) == 0:
            turnChoices.append(myAction(
                name=weap.name, type='Wdmg', mod=0, numHit=0,
                currCoord=list(map_obj.arrayCenters)[myIndex],
                moveCoord=list(map_obj.arrayCenters)[myIndex], targets=[]
            ))
            continue

        line = drawLine(myCoord, closestCoord, map_obj)
        if weap.range / 5 >= actor.optRange:
            if minDist >= actor.optRange + effective_speed / 5:
                options = [
                    x for x in line
                    if map_obj.distanceCalc(
                        list(map_obj.arrayCenters).index(myCoord),
                        list(map_obj.arrayCenters).index(x)
                    ) <= effective_speed / 5
                ]
                if map_obj.arrayCenters[options[-1]] != '' and map_obj.arrayCenters[options[-1]] != actor:
                    newCoord = map_obj.nearestFreeHex(
                        list(map_obj.arrayCenters).index(myCoord),
                        list(map_obj.arrayCenters).index(options[-1])
                    )
                else:
                    newCoord = options[-1]
            else:
                reach = weap.range
                hexLimit = reach / 5
                dist = map_obj.distanceCalc(
                    list(map_obj.arrayCenters).index(closestCoord),
                    list(map_obj.arrayCenters).index(myCoord)
                )
                if dist <= hexLimit:
                    newCoord = [
                        coord for coord in line
                        if map_obj.distanceCalc(
                            list(map_obj.arrayCenters).index(myCoord),
                            list(map_obj.arrayCenters).index(coord)
                        ) <= effective_speed / 5
                    ][-1]
                else:
                    moveTo = [
                        coord for coord in line
                        if map_obj.distanceCalc(
                            list(map_obj.arrayCenters).index(closestCoord),
                            list(map_obj.arrayCenters).index(coord)
                        ) <= hexLimit
                    ][0]
                    if map_obj.arrayCenters[moveTo] != '':
                        moveToIndex = list(map_obj.arrayCenters).index(moveTo)
                        newCoord = map_obj.nearestFreeHex(myIndex, moveToIndex)
                    else:
                        newCoord = moveTo
        else:
            reach = weap.range
            hexLimit = reach / 5
            dist = map_obj.distanceCalc(
                list(map_obj.arrayCenters).index(closestCoord),
                list(map_obj.arrayCenters).index(myCoord)
            )
            if dist <= hexLimit:
                newCoord = myCoord
            moveTo = [
                coord for coord in line
                if map_obj.distanceCalc(
                    list(map_obj.arrayCenters).index(closestCoord),
                    list(map_obj.arrayCenters).index(coord)
                ) <= hexLimit
            ][0]
            if map_obj.arrayCenters[moveTo] != '':
                newCoord = map_obj.nearestFreeHex(myIndex, closestIndex)
            else:
                newCoord = moveTo

        if not actor.is_player:
            if weap.name in actor.multiAttack.keys():
                attackTimes = actor.multiAttack[weap.name]
            else:
                attackTimes = 1
            for di in weap.diceType:
                diceCount = weap.diceCount[weap.diceType.index(di)]
                avgDmg += attackTimes * (0.5 + weap.dmgMod + diceCount * di / 2)
        else:
            attackTimes = 1 + actor.twoAttacks
            if isinstance(weap.diceType, list):
                dice = int(re.findall(r'\d+', weap.diceType[0])[0]) if weap.diceType else 0
            else:
                dice = int(re.findall(r'\d+', weap.diceType)[0])
            diceCount = weap.diceCount
            avgDmg += attackTimes * (0.5 + weap.dmgMod + diceCount * dice / 2)

        turnChoices.append(myAction(
            name=weap.name, type='Wdmg', mod=avgDmg, numHit=1,
            currCoord=list(map_obj.arrayCenters)[myIndex],
            moveCoord=newCoord, targets=[closestCoord]
        ))

    # --- Spell choices ---
    conditionsList = [
        'Blinded', 'Charmed', 'Deafened', 'Frightened', 'Grappled', 'Incapacitated',
        'Invisible', 'Paralyzed', 'Petrified', 'Poisoned', 'Prone', 'Restrained',
        'Stunned', 'Unconscious', 'Exhausted',
    ]
    dmgTypes = [
        'Acid', 'Bludgeoning', 'Cold', 'Fire', 'Force', 'Lightning', 'Necrotic',
        'Piercing', 'Poison', 'Psychic', 'Radiant', 'Slashing', 'Thunder',
    ]

    for spell in actor.spells.keys():
        if not actor.is_player:
            if actor.spells[spell][1]['combat'] == 'n' or actor.spells[spell][0] <= 0:
                continue
            myArea = actor.spells[spell][1]['area']
            myEffect = actor.spells[spell][1]['effect']
            myDice = actor.spells[spell][1]['dice']
            myRange = actor.spells[spell][1]['range']
        else:
            if (actor.spells[spell]['combat'] == 'n'
                    or 0 >= actor.spellSlots[str(actor.spells[spell]['lvl'])]
                    or actor.spells[spell]['time'] != "1 Action"):
                continue
            myArea = actor.spells[spell]['area']
            myEffect = actor.spells[spell]['effect']
            myDice = actor.spells[spell]['dice']
            myRange = actor.spells[spell]['range']

        avgDmg = 0

        if myEffect == 'Healing':
            if myArea != '':
                pass  # area healing not yet implemented
            else:
                hexLimit = (int(re.findall(r'\d+', myRange)[0]) / 5) + actor.speed / 5
                anyOpenSpot = [
                    x for x in distanceMatrix
                    if x[0] <= actor.speed / 5 and x[1] <= int(re.findall(r'\d+', myRange)[0]) / 5
                ]
                if len(anyOpenSpot) == 0:
                    turnChoices.append(myAction(
                        name=spell, type='heal', mod=0, numHit=0,
                        currCoord=list(map_obj.arrayCenters)[myIndex],
                        moveCoord=list(map_obj.arrayCenters)[myIndex], targets=[]
                    ))
                    continue
                dice = myDice
                if dice == ['']:
                    continue
                for di in dice:
                    if 'd' not in di:
                        avgDmg = int(re.findall(r'\d+', di)[0])
                        continue
                    diceCount = int(re.findall(r'\d+', di)[0])
                    diceDmg = int(re.findall(r'\d+', di)[1])
                    avgDmg += 0.5 + diceCount * diceDmg / 2

                lowestMissingHealth = [0, [myCoord]]
                for index in partyList:
                    if map_obj.distanceCalc(myIndex, index) <= hexLimit:
                        person = map_obj.arrayCenters[list(map_obj.arrayCenters)[index]]
                        mostHeal = min(avgDmg, person.maxHealth - person.health)
                        if mostHeal > lowestMissingHealth[0]:
                            lowestMissingHealth = [
                                mostHeal,
                                [i for i in map_obj.arrayCenters if map_obj.arrayCenters[i] == person]
                            ]

                reachLimit = int(re.findall(r'\d+', myRange)[0]) / 5
                if lowestMissingHealth[1][0] != myCoord:
                    moveToCoord = coordWithinReach(myCoord, lowestMissingHealth[1][0], reachLimit, map_obj)
                else:
                    moveToCoord = myCoord

                turnChoices.append(myAction(
                    name=spell, type='heal', mod=lowestMissingHealth[0], numHit=1,
                    currCoord=list(map_obj.arrayCenters)[myIndex],
                    moveCoord=moveToCoord, targets=lowestMissingHealth[1]
                ))

        if myArea != '':
            match myArea:
                case str(x) if 'sphere' in x:
                    numToHit = bestSphere(
                        actor, map_obj,
                        int(re.findall(r'\d+', myArea)[0]),
                        int(re.findall(r'\d+', myRange)[0]),
                        targets=aTargets
                    )
                case str(x) if 'cone' in x:
                    numToHit = bestCone(
                        actor, map_obj,
                        int(re.findall(r'\d+', myArea)[0]),
                        int(re.findall(r'\d+', myRange)[0])
                    )
                case str(x) if 'line' in x:
                    numToHit = bestLine2(
                        actor, map_obj,
                        int(re.findall(r'\d+', myArea)[0]),
                        int(re.findall(r'\d+', myRange)[0])
                    )
                case str(x) if 'square' in x:
                    numToHit = bestSquare(
                        actor, map_obj,
                        int(re.findall(r'\d+', myArea)[0]),
                        int(re.findall(r'\d+', myRange)[0])
                    )

            if myEffect in dmgTypes:
                dice = myDice
                for di in dice:
                    diceCount = int(re.findall(r'\d+', di)[0])
                    diceDmg = int(re.findall(r'\d+', di)[1])
                    avgDmg += 0.5 + diceCount * diceDmg / 2

                if len(numToHit) == 2:
                    turnChoices.append(myAction(
                        name=spell, type='Sdmg', mod=0, numHit=0,
                        currCoord=list(map_obj.arrayCenters)[myIndex],
                        moveCoord=list(map_obj.arrayCenters)[myIndex], targets=[]
                    ))
                else:
                    reachLimit = int(re.findall(r'\d+', myRange)[0]) / 5
                    moveToCoord = coordWithinReach(myCoord, numToHit[2], reachLimit, map_obj)
                    turnChoices.append(myAction(
                        name=spell, type='Sdmg', mod=numToHit[0] * avgDmg, numHit=numToHit[0],
                        currCoord=list(map_obj.arrayCenters)[myIndex],
                        moveCoord=moveToCoord, castCoord=numToHit[2], targets=numToHit[3]
                    ))

            elif myEffect in conditionsList:
                if len(numToHit) == 2:
                    turnChoices.append(myAction(
                        name=spell, type='cc', mod=0, numHit=0,
                        currCoord=list(map_obj.arrayCenters)[myIndex],
                        moveCoord=list(map_obj.arrayCenters)[myIndex], targets=[]
                    ))
                else:
                    reachLimit = int(re.findall(r'\d+', myRange)[0]) / 5
                    moveToCoord = coordWithinReach(myCoord, numToHit[2], reachLimit, map_obj)
                    turnChoices.append(myAction(
                        name=spell, type='cc', mod=numToHit[0] * avgDmg * 20, numHit=numToHit[0],
                        currCoord=list(map_obj.arrayCenters)[myIndex],
                        moveCoord=moveToCoord, castCoord=numToHit[2], targets=numToHit[3]
                    ))
        else:
            hexLimit = (int(re.findall(r'\d+', myRange)[0]) / 5) + actor.speed / 5
            distance_hits = [index for index in enemyList if map_obj.distanceCalc(myIndex, index) <= hexLimit]
            anyOpenSpot = [
                x for x in distanceMatrix
                if x[0] <= actor.speed / 5 and x[1] <= int(re.findall(r'\d+', myRange)[0]) / 5
            ]
            if len(anyOpenSpot) == 0:
                turnChoices.append(myAction(
                    name=spell, type='Sdmg', mod=0, numHit=0,
                    currCoord=list(map_obj.arrayCenters)[myIndex],
                    moveCoord=list(map_obj.arrayCenters)[myIndex], targets=[]
                ))
                continue
            if len(distance_hits) == 0:
                turnChoices.append(myAction(
                    name=spell, type='Sdmg', mod=0, numHit=0,
                    currCoord=list(map_obj.arrayCenters)[myIndex],
                    moveCoord=list(map_obj.arrayCenters)[myIndex], targets=[]
                ))
            elif myEffect in dmgTypes:
                dice = myDice
                for di in dice:
                    diceCount = int(re.findall(r'\d+', di)[0])
                    diceDmg = int(re.findall(r'\d+', di)[1])
                    avgDmg += 0.5 + diceCount * diceDmg / 2

                reachLimit = int(re.findall(r'\d+', myRange)[0]) / 5
                if reachLimit >= actor.optRange:
                    moveToCoord = coordWithinReach(myCoord, closestCoord, actor.optRange, map_obj)
                    if map_obj.distanceCalc(
                        list(map_obj.arrayCenters).index(moveToCoord),
                        list(map_obj.arrayCenters).index(myCoord)
                    ) > actor.speed / 5:
                        moveToCoord = coordWithinReach(myCoord, closestCoord, reachLimit, map_obj)
                else:
                    moveToCoord = coordWithinReach(myCoord, closestCoord, reachLimit, map_obj)

                turnChoices.append(myAction(
                    name=spell, type='Sdmg', mod=avgDmg, numHit=1,
                    currCoord=list(map_obj.arrayCenters)[myIndex],
                    moveCoord=moveToCoord, targets=[closestCoord]
                ))
            elif myEffect in conditionsList:
                reachLimit = int(re.findall(r'\d+', myRange)[0]) / 5
                if reachLimit >= actor.optRange:
                    moveToCoord = coordWithinReach(myCoord, closestCoord, actor.optRange, map_obj)
                    if map_obj.distanceCalc(
                        list(map_obj.arrayCenters).index(moveToCoord),
                        list(map_obj.arrayCenters).index(myCoord)
                    ) > actor.speed / 5:
                        moveToCoord = coordWithinReach(myCoord, closestCoord, reachLimit, map_obj)
                else:
                    moveToCoord = coordWithinReach(myCoord, closestCoord, reachLimit, map_obj)

                turnChoices.append(myAction(
                    name=spell, type='cc', mod=1, numHit=1,
                    currCoord=list(map_obj.arrayCenters)[myIndex],
                    moveCoord=moveToCoord, targets=[closestCoord]
                ))

    # --- Break Free (Restrained) ---
    # If the actor is Restrained they can spend their action trying to escape.
    # The AI will choose this if they can't meaningfully act from their current position
    # (best current action mod == 0) OR if breaking free is estimated to be more valuable.
    if is_restrained:
        save_type, break_dc = actor.restrained[0], actor.restrained[1]
        # Estimate average weapon damage the actor could deal if free (with full movement).
        best_current = max((float(c.mod) for c in turnChoices), default=0)
        avg_weapon_dmg = 0
        for weap in actor.weaponList:
            for di in weap.diceType:
                dc = weap.diceCount[weap.diceType.index(di)]
                avg_weapon_dmg = max(avg_weapon_dmg, dc * di / 2 + weap.dmgMod)
        if not actor.is_player:
            attacks = actor.multiAttack.get(actor.weaponList[0].name, 1) if actor.weaponList else 1
            avg_weapon_dmg *= attacks
        # Rough break-free value: expected damage if freed (discounted by ~50% chance to fail save)
        break_free_mod = avg_weapon_dmg * 0.6 if avg_weapon_dmg > 0 else 0.5
        # Only add if meaningful OR if no current options
        if best_current == 0 or break_free_mod > best_current * 0.8:
            turnChoices.append(myAction(
                name=f'Break Free (DC {break_dc} {save_type})',
                type='break_free', mod=break_free_mod, numHit=0,
                currCoord=myCoord, moveCoord=myCoord, targets=[]
            ))

    # Pick best action
    turnChoices.append(myAction(
        name='dash', type='dash', mod=0, numHit=0,
        currCoord=myCoord, moveCoord=closestCoord, targets=closestCoord
    ))
    best = 0
    turnChoice = myAction(
        name='dash', type='dash', mod=0, numHit=0,
        currCoord=myCoord, moveCoord=closestCoord, targets=closestCoord
    )
    for choice in turnChoices:
        if float(choice.mod) >= float(best):
            best = choice.mod
            turnChoice = choice

    # Override: prioritise healing a downed teammate
    if len(healDownedTeammate) != 0:
        mostHealing = 0
        for choice in turnChoices:
            if (choice.type == 'heal'
                    and float(choice.mod) >= float(mostHealing)
                    and float(choice.mod) != 0
                    and any(x in healDownedTeammate for x in choice.targets)):
                print('Prioritizing healing downed teammate!')
                mostHealing = choice.mod
                turnChoice = choice

    print(turnChoice, "before interactive check")

    if not interactive:
        doAction(actor, map_obj, turnChoice)
    else:
        map_obj.graphicsViewer.setCurMoveCoords(moveMatrix)
        return [actor, map_obj, turnChoices, turnChoice]


def chooseAction(actor, map_obj, turnChoices, turnChoice):
    """CLI fallback for interactive CLI play (not GUI)."""
    from engine.utils import stringToTuple

    for action in turnChoices:
        print(
            '\t', action.mod, ':', action.name, 'will do',
            'hitting', action.numHit, 'enemies if you move from',
            action.currCoord, 'to', action.moveCoord
        )
    user_action = input("Choose action\n")
    choice = False
    for action in turnChoices:
        if action.name.lower() == user_action.lower():
            choice = action

    if not choice:
        print("Your choice does not match a possible action. Try again.")
        chooseAction(actor, map_obj, turnChoices, turnChoice)
        return

    override_Target = input(
        "Would you like to override the target of action? (yes, no). Current Target = "
        + str(choice.targets) + '\n'
    )
    if override_Target == 'yes':
        for coord in map_obj.arrayCenters:
            if map_obj.arrayCenters[coord] != '':
                print('\t', map_obj.arrayCenters[coord].name, " at ", coord)
        newTarget = stringToTuple(input("New coords of target?\n"))
        choice.targets = [newTarget]

    override_Move = input("Would you like to override moveCoords? (yes or no)\n")
    if override_Move == 'yes':
        newMove = stringToTuple(input("New coords to move to?"))
        choice.moveCoord = newMove

    doAction(actor, map_obj, choice)


def _doBreakFree(actor, map_obj, turnChoice):
    """Actor spends their action trying to break free from the Restrained condition."""
    save_type, dc = actor.restrained[0], actor.restrained[1]
    safe_log(f'\t{actor.name} attempts to break free! ({save_type} DC {dc})', map_obj)
    failed = rollSave(actor, save_type, dc, map_obj)
    if not failed:
        actor.restrained = []
        safe_log(f'\t{actor.name} breaks free from Restrained!', map_obj)
    else:
        safe_log(f'\t{actor.name} fails to break free and remains Restrained.', map_obj)


def doAction(actor, map_obj, turnChoice):
    safe_log('\tAction: ' + turnChoice.name, map_obj)

    if turnChoice.type == 'dash':
        map_obj.dashActor(actor, turnChoice.moveCoord)
        return

    if turnChoice.type == 'break_free':
        _doBreakFree(actor, map_obj, turnChoice)
        return

    print(actor.name, 'is taking action', turnChoice.type, 'with', turnChoice.name)

    if turnChoice.type == 'Wdmg':
        weaponChoice = [x for x in actor.weaponList if x.name == turnChoice.name][0]
        if map_obj.arrayCenters[turnChoice.moveCoord] != '' and map_obj.arrayCenters[turnChoice.moveCoord] != actor:
            map_obj.moveToNearest(actor, turnChoice.moveCoord)
        elif map_obj.arrayCenters[turnChoice.moveCoord] != actor:
            map_obj.moveActor(actor, turnChoice.moveCoord)
        target = map_obj.arrayCenters[turnChoice.targets[0]]
        weaponAttack(actor, target, weaponChoice, map_obj)

    elif turnChoice.type in ('Sdmg', 'cc'):
        castSpellTurn(actor, turnChoice, map_obj)

    elif turnChoice.type == 'heal':
        healSpellTurn(actor, turnChoice, map_obj)


def healSpellTurn(actor, turnChoice, map_obj):
    moveCoord = turnChoice.moveCoord
    if map_obj.arrayCenters[moveCoord] != '' and map_obj.arrayCenters[moveCoord] != actor:
        map_obj.moveToNearest(actor, moveCoord)
    elif map_obj.arrayCenters[moveCoord] != actor:
        map_obj.moveActor(actor, moveCoord)

    peopleTargeted = [map_obj.arrayCenters[x] for x in turnChoice.targets if map_obj.arrayCenters[x] != '']
    spell = actor.spells[turnChoice.name]

    if not actor.is_player:
        actor.spells[turnChoice.name][0] -= 1
        spell = actor.spells[turnChoice.name][1]
    else:
        actor.spellSlots[str(actor.spells[turnChoice.name]['lvl'])] -= 1

    dice = spell['dice']
    dmg = 0
    if dice[0] != '':
        for di in dice:
            if 'd' not in di:
                dmg = int(di)
                continue
            diceCount = int(re.findall(r'\d+', di)[0])
            diceDmg = int(re.findall(r'\d+', di)[1])
            dmg += sum(rollDice(diceCount, diceDmg, map_obj))

    if dmg > 0:
        for person in peopleTargeted:
            takeHealing(actor, person, dmg, map_obj)


def takeHealing(actor, people, dmg, map_obj):
    print(actor.name, 'is healing', people.name, 'for', dmg)
    safe_log('\t' + actor.name + ' is healing ' + people.name + ' for ' + str(dmg), map_obj)
    if people.is_player:
        if any(x in people.status for x in ['deathSaves', 'unconscious']):
            people.health = 0
            people.status = []
            people.deathSaves = {'pass': [], 'fail': []}
    people.health += dmg


def castSpellTurn(actor, turnChoice, map_obj):
    moveCoord = turnChoice.moveCoord
    if map_obj.arrayCenters[moveCoord] != '' and map_obj.arrayCenters[moveCoord] != actor:
        map_obj.moveToNearest(actor, moveCoord)
    elif map_obj.arrayCenters[moveCoord] != actor:
        map_obj.moveActor(actor, moveCoord)

    peopleTargeted = [map_obj.arrayCenters[x] for x in turnChoice.targets if map_obj.arrayCenters[x] != '']
    spell = actor.spells[turnChoice.name]

    if not actor.is_player:
        actor.spells[turnChoice.name][0] -= 1
        spell = actor.spells[turnChoice.name][1]
    else:
        actor.spellSlots[str(actor.spells[turnChoice.name]['lvl'])] -= 1

    # If this is a concentration spell, end any existing concentration first.
    is_concentration = str(spell.get('concentration', '')).strip().upper() == 'Y'
    if is_concentration:
        end_concentration(actor, map_obj)

    peopleWhoPassedSave = []
    save = spell['save'].split()
    if spell['attack'] == '' and save:
        peopleHit = [x for x in peopleTargeted if rollSave(x, save[0], actor.spellDC, map_obj)]
        peopleWhoPassedSave = [x for x in peopleTargeted if x not in peopleHit]
    else:
        hitRoll = rollDice(1, 20, map_obj)[0] + int(actor.spellAttackMod)
        peopleHit = [x for x in peopleTargeted if hitRoll >= x.ac]

    dice = spell['dice']
    dmg = 0
    if dice[0] != '':
        for di in dice:
            diceCount = int(re.findall(r'\d+', di)[0])
            diceDmg = int(re.findall(r'\d+', di)[1])
            dmg += sum(rollDice(diceCount, diceDmg, map_obj))

    # Persistent (concentration + area) spells: create zone, skip immediate damage.
    # Instantaneous AoE spells deal damage normally.
    if is_concentration and spell.get('area', '') != '':
        coords = list(map_obj.arrayCenters)
        # Use area_coords (all hexes in the area) if the GUI set them;
        # fall back to targets only (AI path or legacy calls).
        zone_coords = list(getattr(turnChoice, 'area_coords', None) or turnChoice.targets)
        hex_indices = [coords.index(c) for c in zone_coords if c in coords]
        ps = create_persistent_spell(
            actor, turnChoice.name, spell,
            hex_indices=hex_indices,
            map_coords=zone_coords,
        )
        actor.concentration_spell = ps
        map_obj.persistent_spells.append(ps)
        safe_log(
            f'\t{actor.name} creates a {turnChoice.name} zone '
            f'({ps.rounds_remaining} rounds).',
            map_obj,
        )
        # Apply immediate entrance damage to anyone currently in the zone.
        if dmg > 0:
            for person in peopleTargeted:
                failed = person in peopleHit
                takeDmg(actor, person, dmg if failed else dmg // 2, map_obj)
        return

    if spell['area'] != '' and dmg > 0:
        for person in peopleTargeted:
            if person in peopleHit:
                takeDmg(actor, person, dmg, map_obj)
            else:
                takeDmg(actor, person, round(dmg / 2, 0), map_obj)
    elif dmg > 0:
        for person in peopleHit:
            takeDmg(actor, person, dmg, map_obj)
        for person in peopleWhoPassedSave:
            takeDmg(actor, person, int(dmg / 2), map_obj)

    if turnChoice.type == 'cc':
        for person in peopleHit:
            person.cc = [spell['lvl'], save, actor.spellDC]


def weaponAttack(actor, target, weap, map_obj):
    myIndex = [
        list(map_obj.arrayCenters).index(i)
        for i in map_obj.arrayCenters.keys()
        if map_obj.arrayCenters[i] == actor
    ][0]
    targetIndex = [
        list(map_obj.arrayCenters).index(i)
        for i in map_obj.arrayCenters.keys()
        if map_obj.arrayCenters[i] == target
    ][0]
    targDistance = map_obj.distanceCalc(myIndex, targetIndex)

    if targDistance > weap.range / 5:
        print(actor.name, 'out of range to hit', target.name, 'with', weap.name, '...', targDistance, '..', weap.range / 5)
        safe_log(
            '\t' + actor.name + ' out of range to hit ' + target.name + ' with ' + weap.name
            + ' ... ' + str(targDistance) + ' .. ' + str(weap.range / 5), map_obj
        )
        return

    if not actor.is_player:
        numAttack = int(actor.multiAttack[weap.name]) if weap.name in actor.multiAttack else 1
        prof = 0
    else:
        numAttack = actor.twoAttacks + 1
        prof = actor.proficiency

    rollToHit = [x + int(weap.attackMod) + int(prof) for x in rollDice(numAttack, 20, map_obj)]
    hits = []
    for roll in rollToHit:
        safe_log(
            '\tRolling to Hit against ' + target.name + '\n\t\tRoll: '
            + str(roll - int(weap.attackMod) - int(prof)) + ' + ' + str(int(weap.attackMod) + prof),
            map_obj
        )
        if roll >= int(target.ac):
            safe_log('\t\t' + str(roll) + ' hits against ' + str(target.ac), map_obj)
            hits.append(2 if roll == 20 + int(prof) + int(weap.attackMod) else 1)

    dmg = 0
    for hit in hits:
        if not actor.is_player:
            dmg = sum(rollDice(int(weap.diceCount[0]), int(weap.diceType[0]), map_obj)) + int(weap.dmgMod)
            if hit == 2:
                dmg = sum(rollDice(int(weap.diceCount[0]), int(weap.diceType[0]), map_obj))
        else:
            dmg += rollDice(int(weap.diceCount), int(re.findall(r'\d+', weap.diceType)[0]), map_obj)[0] + int(weap.dmgMod)
            if hit == 2:
                dmg += rollDice(int(weap.diceCount), int(re.findall(r'\d+', weap.diceType)[0]), map_obj)[0]

    if actor.is_player:
        dmg += actor.classMeleeDmg(hits, dmg)

    takeDmg(actor, target, dmg, map_obj)


def takeDmg(actor, target, dmg, map_obj):
    print(actor.name, 'is doing', dmg, 'to', target.name)
    safe_log('\t' + actor.name + ' is doing ' + str(dmg) + ' to ' + target.name, map_obj)

    if not target.is_player:
        target.health -= dmg
        if target.health <= 0:
            target.alive = 0
            print(target.name + ' is dead')
    else:
        if 'deathSaves' in target.status:
            target.deathSaves['fail'].append(1)
            safe_log('\t\tActor: ' + target.name + ' is in deathSaves', map_obj)
            printDeathSaves(target.deathSaves, map_obj)
            if sum(target.deathSaves['fail']) >= 3:
                target.alive = 0
        else:
            target.health -= dmg
            if target.health <= 0:
                if 'deathSaves' not in target.status:
                    target.status.append('deathSaves')
                    target.cc = []

    # Only trigger a concentration save if the target actually took damage.
    if dmg > 0:
        concentration_save(target, int(dmg), map_obj)


def takeReaction(actor, map_obj, target):
    myIndex = [
        list(map_obj.arrayCenters).index(i)
        for i in map_obj.arrayCenters.keys()
        if map_obj.arrayCenters[i] == actor
    ][0]
    targetIndex = [
        list(map_obj.arrayCenters).index(i)
        for i in map_obj.arrayCenters.keys()
        if map_obj.arrayCenters[i] == target
    ][0]
    minDist = map_obj.distanceCalc(myIndex, targetIndex)

    maxDmg = 0
    attackWith = actor.weaponList[0]
    attackTimes = 1
    prof = 0

    for weap in actor.weaponList:
        avgDmg = 0
        if int(minDist) > int(weap.range) / 5:
            continue
        if not actor.is_player:
            for di in weap.diceType:
                diceCount = weap.diceCount[weap.diceType.index(di)]
                avgDmg += attackTimes * (0.5 + weap.dmgMod + diceCount * di / 2)
            prof = 0
        else:
            if isinstance(weap.diceType, list):
                dice = int(re.findall(r'\d+', weap.diceType[0])[0]) if weap.diceType else 0
            else:
                dice = int(re.findall(r'\d+', weap.diceType)[0])
            diceCount = weap.diceCount
            avgDmg += attackTimes * (0.5 + weap.dmgMod + diceCount * dice / 2)
            prof = actor.proficiency

        if avgDmg > maxDmg:
            maxDmg = avgDmg
            attackWith = weap

    if maxDmg == 0:
        return

    rollToHit = [x + int(attackWith.attackMod) + int(prof) for x in rollDice(attackTimes, 20, map_obj)]
    hits = []
    for roll in rollToHit:
        if roll >= int(target.ac):
            hits.append(2 if roll == 20 + int(attackWith.attackMod) else 1)

    dmg = 0
    safe_log('\t' + actor.name + ' is taking a reaction against ' + target.name, map_obj)
    for hit in hits:
        if not actor.is_player:
            dmg = sum(rollDice(int(attackWith.diceCount[0]), int(attackWith.diceType[0]), map_obj)) + int(attackWith.dmgMod)
            if hit == 2:
                dmg = sum(rollDice(int(attackWith.diceCount[0]), int(attackWith.diceType[0]), map_obj))
        else:
            dmg += rollDice(int(attackWith.diceCount), int(re.findall(r'\d+', attackWith.diceType)[0]), map_obj)[0] + int(attackWith.dmgMod)
            if hit == 2:
                dmg += rollDice(int(attackWith.diceCount), int(re.findall(r'\d+', attackWith.diceType)[0]), map_obj)[0]

    if actor.is_player:
        dmg += actor.classMeleeDmg(hits, dmg)

    takeDmg(actor, target, dmg, map_obj)
    actor.reaction = 0
