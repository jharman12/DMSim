import random as r
from dataclasses import dataclass
import re
import math
import numpy as np
import json
import sys
import time
import operator
from scipy import spatial
import array


def removeDeadActors(map, sortedInitList):
    totalList = map.party + map.enemy
    deadActors = [actor for actor in totalList if not actor.alive]
    if len(deadActors) >= 1:
        for deadActor in deadActors:
            print(deadActor.name, 'is dead')
            if deadActor in map.party:
                map.party.remove(deadActor)
            else:
                map.enemy.remove(deadActor)
            actorCoord = [coord for coord in list(map.arrayCenters) if map.arrayCenters[coord] == deadActor][0]
            map.arrayCenters[actorCoord] = ''
            del sortedInitList[deadActor]
    return deadActors

def takeTurn(actor, m, interactive = False):
    '''
    Turn decidider function... take enemyList and decide what to do for the turn
        based on actor.turnFactors
    '''
    global map
    map = m
    player = 1
    healDownedTeammate = 0
    if str(type(actor)) == "<class 'monster.Monster'>":
        player = 0
        actor.legActions = actor.maxLegActions # if monster reset legendary actions
    else:
        if 'deathSaves' in actor.status:
            rollDeathSave(actor)
            # skip your turn if youre still in death saves or succeeded but still unconscious
            if 'deathSaves' in actor.status or 'unconscious' in actor.status: 
                print(actor.name, 'turn is skipped, in deathSaves or unconscious', actor.status)
                return
            # if you get passed the above check, you should have rolled a nat 20
        if 'unconscious' in actor.status: # skip turn
            return
        if actor in map.party:
            for mate in map.party:
                if mate.alive and 'deathSaves' in mate.status:
                    healDownedTeammate = 1
        
        
    


    actor.reaction = 1
    if actor in map.enemy:
        aTargets = 'party'
        hTargets = 'enemy'
        enemyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.enemy]
        partyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.party]
    
    if actor in map.party:
        enemyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.party]
        partyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.enemy]
        hTargets = 'party'
        aTargets = 'enemy'
    myIndex = [list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] == actor][0]
    closest = 999
    distance = []
    for index in enemyList:
        dist = map.distanceCalc(myIndex, index)
        distance.append(dist)
        if dist <= closest:
            closest = dist
            toAttack = map.arrayCenters[list(map.arrayCenters)[index]]
    minDist = min(distance)
    closestGuy = map.arrayCenters[list(map.arrayCenters)[enemyList[distance.index(minDist)]]]
    closestCoord = [coord for coord in list(map.arrayCenters) if map.arrayCenters[coord] == closestGuy]
    closestIndex = list(map.arrayCenters).index(closestCoord[0])
    distanceMatrix = [(map.distanceCalc(myIndex, index), map.distanceCalc(closestIndex, index)) for index in range(len(list(map.arrayCenters))) if map.arrayCenters[list(map.arrayCenters)[index]] == '']
    
    turnChoices = []
    for weap in actor.weaponList:
        avgDmg = 0
        if int(minDist) > int((int(weap.range) + int(actor.speed))/5): # if you cant get within range, dmg = 0
            
            turnChoices.append([weap.name, 'Wdmg', avgDmg])
            continue
        anyOpenSpot = [x for x in distanceMatrix if x[0] <= actor.speed/5 and x[1] <= int(weap.range)/5] 
        if len(anyOpenSpot) == 0: # if no where to move to, dmg = 0
            turnChoices.append([weap.name, 'Wdmg', avgDmg])
            continue
        
        if not player: # if monster
            if weap.name in actor.multiAttack.keys():
                attackTimes = actor.multiAttack[weap.name]
            else:
                attackTimes = 1
            dice = weap.diceType
            diceCount = weap.diceCount
            for di in dice:
                diceCount = weap.diceCount[weap.diceType.index(di)]
                ##print(diceCount)
                avgDmg +=  attackTimes * (0.5 + weap.dmgMod + diceCount * di / 2 )
                turnChoices.append([weap.name, 'Wdmg', avgDmg, minDist, closestCoord])
        else: # your a player
            attackTimes = 1 + actor.twoAttacks
            dice = int(re.findall(r'\d+',weap.diceType)[0])
            diceCount = weap.diceCount
            
            avgDmg +=  attackTimes * (0.5 + weap.dmgMod + diceCount * dice / 2 )
            turnChoices.append([weap.name, 'Wdmg', avgDmg, minDist, closestCoord])
        #####
    
    conditionsList = ['Blinded','Charmed','Deafened', 'Frightened','Grappled','Incapacitated','Invisible','Paralyzed','Petrified','Poisoned','Prone','Restrained', 'Stunned','Unconscious','Exhausted']
    dmgTypes = ['Acid', 'Bludgeoning', 'Cold', 'Fire', 'Force', 'Lightning', 'Necrotic', 'Piercing', 'Poison', 'Psychic', 'Radiant', 'Slashing', 'Thunder']
    
    for spell in actor.spells.keys():
        if not player:
            if actor.spells[spell][1]['combat'] == 'n' or actor.spells[spell][0] <= 0:
                continue
            myArea = actor.spells[spell][1]['area']
            myEffect = actor.spells[spell][1]['effect']
            myDice = actor.spells[spell][1]['dice']
            #print('setting myDice to ', myDice, 'for spell', spell)
            myRange = actor.spells[spell][1]['range']
        else:
            if actor.spells[spell]['combat'] == 'n' or 0 >= actor.spellSlots[str(actor.spells[spell]['lvl'])] or actor.spells[spell]['time'] != "1 Action":
                continue
            myArea = actor.spells[spell]['area']
            myEffect = actor.spells[spell]['effect']
            myDice = actor.spells[spell]['dice']
            myRange = actor.spells[spell]['range']
            
            
            
        #######
        
        avgDmg = 0
        if myEffect == 'Healing':
            if myArea != '':
                
                #numToHit = bestSphere(actor, map, int(re.findall(r'\d+', myArea)[0]), int(re.findall(r'\d+', myRange)[0]), targets = 'party')
                thing = 1 # area not working properly for healing
            else:
                #print(spell)
                hexLimit = (int(re.findall(r'\d+', myRange)[0])/5) +actor.speed/5
                anyOpenSpot = [x for x in distanceMatrix if x[0] <= actor.speed/5 and x[1] <= int(re.findall(r'\d+', myRange)[0])/5] 
                
                if len(anyOpenSpot) == 0:
                    turnChoices.append([spell, 'heal', 0,(0,0)])
                dice = myDice
                #print(dice)
                if dice == [""]:
                    #print('skip')
                    continue
                for di in dice:
                    if not 'd' in di:
                        avgDmg = int(re.findall(r'\d+', di)[0])
                        #print(avgDmg)
                        continue
                    diceCount = int(re.findall(r'\d+', di)[0])
                    diceDmg = int(re.findall(r'\d+', di)[1])
                    avgDmg += 0.5 + diceCount * diceDmg / 2
                lowestMissingHealth = [0, 0]
                for index in partyList:
                    if map.distanceCalc(myIndex, index) <= hexLimit:
                        person = map.arrayCenters[list(map.arrayCenters)[index]]
                        mostHeal = min(avgDmg, person.maxHealth - person.health)
                        if mostHeal > lowestMissingHealth[0]:
                            
                            lowestMissingHealth= [mostHeal, [i for i in map.arrayCenters if map.arrayCenters[i] == person]]
                
                turnChoices.append([spell, 'heal', lowestMissingHealth[0], (1,list(map.arrayCenters)[myIndex], list(map.arrayCenters)[myIndex], lowestMissingHealth[1])])
                #print(turnChoices)
        if myArea != '':
            match myArea:
                case str(x) if 'sphere' in x:
                    numToHit = bestSphere(actor, map, int(re.findall(r'\d+', myArea)[0]), int(re.findall(r'\d+', myRange)[0]), targets = aTargets)
                    
                case str(x) if 'cone' in x:
                    numToHit = bestCone(actor, map, int(re.findall(r'\d+', myArea)[0]), int(re.findall(r'\d+', myRange)[0]))

                case str(x) if 'line' in x:
                    numToHit = bestLine2(actor, map, int(re.findall(r'\d+', myArea)[0]), int(re.findall(r'\d+', myRange)[0]))
                case str(x) if 'square' in x:
                    numToHit = bestSquare(actor, map, int(re.findall(r'\d+', myArea)[0]), int(re.findall(r'\d+', myRange)[0]))
            if myEffect in dmgTypes:
                dice = myDice
                for di in dice:
                    diceCount = int(re.findall(r'\d+', di)[0])
                    diceDmg = int(re.findall(r'\d+', di)[1])
                    avgDmg += 0.5 + diceCount * diceDmg / 2
                turnChoices.append([spell, 'Sdmg', avgDmg*numToHit[0], numToHit])
            elif myEffect in conditionsList:
                turnChoices.append([spell, 'cc', numToHit[0]*20, numToHit])
        else:
            hexLimit = (int(re.findall(r'\d+', myRange)[0])/5) +actor.speed/5
            distance = [index for index in enemyList if map.distanceCalc(myIndex, index) <= hexLimit]
            anyOpenSpot = [x for x in distanceMatrix if x[0] <= actor.speed/5 and x[1] <= int(re.findall(r'\d+', myRange)[0])/5] 
            ##print(anyOpenSpot)
            if len(anyOpenSpot) == 0:
                turnChoices.append([spell, 'Sdmg', 0,(0,0)])
                ##print('zero for', spell)
                #sys.exit()
                continue
            ##print(spell, len(distance))
            if len(distance) == 0:
                ##print('no one in range for spell', spell)
                turnChoices.append([spell, 'Sdmg', 0,(0,0)])
            elif myEffect in dmgTypes:
                dice = myDice
                for di in dice:
                    diceCount = int(re.findall(r'\d+', di)[0])
                    diceDmg = int(re.findall(r'\d+', di)[1])
                    avgDmg += 0.5 + diceCount * diceDmg / 2
                ##print(spell, numToHit)
                turnChoices.append([spell, 'Sdmg', avgDmg, (1,list(map.arrayCenters)[myIndex], list(map.arrayCenters)[myIndex], closestCoord)])
            elif myEffect in conditionsList:
                turnChoices.append([spell, 'cc', 1, 
                                    (1,list(map.arrayCenters)[myIndex], list(map.arrayCenters)[myIndex], closestCoord)])
    best = 0
    for choice in turnChoices:
        
        if float(choice[2]) >= float(best):
            best = choice[2]
            turnChoice = choice

    print(best)
    if healDownedTeammate: # if ally is down, override turnchoice to pick up
        mostHealing = 0
        for choice in turnChoices:
            if choice[1] =='heal' and float(choice[2]) >= float(mostHealing) and float(choice[2]) != 0:
                mostHealing = choice[2]
                turnChoice = choice
    print(turnChoice)
    if not interactive:
        doAction(actor, map, turnChoice, closestGuy, best)
    else:
        chooseAction(actor, map, turnChoices, turnChoice, closestGuy, best)

@dataclass
class myAction:
    name: str
    type: str
    mod: float # dmg or healing
    numHit: int
    currCoord: tuple
    moveCoord: tuple
    targets: list

def chooseAction(actor, map, turnChoices, turnChoice, closestGuy, best):


    for action in turnChoices:
        print(action[0], "will do", action[2], "hitting", action[3][0], "enemies if you move from", action[3][1], "to", action[3][2])

    user_action = input("Choose action")
    choice = False
    for action in turnChoice:
        if action[0].lower() == user_action.lower():
            choice = action
    if not choice: # failed to match
        print("Your choice does not match a possible action. Try again.")
        chooseAction(actor, map, turnChoices, turnChoice, closestGuy, best)
    override_Target = input("Would you like to override the target of action? (yes, no). Current Target = ", choice[3][3])
    if override_Target == "yes":
        newTarget = input("New coords of target?")
    override_Move = input("Would you like to override moveCoords")
    
def doAction(actor, map, turnChoice, closestGuy, best):
    
    # need closestGuy, closestCoord, minDIst

    
    if best == 0:
        map.dashActor(actor, closestGuy)
        
        return
    else:
        print(actor.name, 'is taking action', turnChoice[1], 'with',turnChoice[0])
    if turnChoice[1] == 'Wdmg':
        minDist = turnChoice[3]
        closestCoord = turnChoice[4]
        weaponChoice = [x for x in actor.weaponList if x.name == turnChoice[0]][0]
        if weaponChoice.range/5 >= actor.optRange:
            if minDist >= actor.optRange + actor.speed/5:
                actorCoord = [x for x in map.arrayCenters.keys() if map.arrayCenters[x] == actor][0]
                line = drawLine(actorCoord, closestCoord[0])
                options = [x for x in line if map.distanceCalc(list(map.arrayCenters).index(actorCoord), list(map.arrayCenters).index(x)) <= actor.speed/5]
                distance = map.distanceCalc(list(map.arrayCenters).index(actorCoord), list(map.arrayCenters).index(options[-1]))
                if map.arrayCenters[options[-1]] != '' and map.arrayCenters[options[-1]] != actor:
                    newCoord = map.moveToNearest(actor, map.arrayCenters[options[-1]])
                else:
                    map.moveActor(actor, options[-1])
            else:
                moveWithingReach(actor, closestGuy, actor.optRange*5, map)
        else:
            moveWithingReach(actor, closestGuy, weaponChoice.range, map)
        weaponAttack(actor, closestGuy, weaponChoice, map)
    elif turnChoice[1] == 'Sdmg' or turnChoice[1] == 'cc':
        castSpellTurn(actor, turnChoice, map)
    elif turnChoice[1] == 'heal':
        healSpellTurn(actor, turnChoice, map)

def healSpellTurn(actor, turnChoice, map):
    actorCoord = [x for x in map.arrayCenters.keys() if map.arrayCenters[x] == actor][0]
    player = 1
    if str(type(actor)) == "<class 'monster.Monster'>":
        player = 0

    if map.arrayCenters[turnChoice[3][1]] != '' and map.arrayCenters[turnChoice[3][1]] != actor:
        
        newCoord = map.moveToNearest(actor, turnChoice[3][1])
        map.moveActor(actor, newCoord)
    elif map.arrayCenters[turnChoice[3][1]] != actor:
        
        map.moveActor(actor, turnChoice[3][1])
    peopleTargeted = [map.arrayCenters[x] for x in turnChoice[3][3] if map.arrayCenters[x] != '']

    spell = actor.spells[turnChoice[0]]
    if not player:
        actor.spells[turnChoice[0]][0] -= 1
        spell = actor.spells[turnChoice[0]][1]
        
    else:
        actor.spellSlots[str(actor.spells[turnChoice[0]]['lvl'])] -= 1

    dice = spell['dice']
    dmg = 0
    if dice[0] != '':
        for di in dice:
            if not 'd' in di:
                dmg = int(di)
                continue
            diceCount = int(re.findall(r'\d+', di)[0])
            
            diceDmg = int(re.findall(r'\d+', di)[1])
            dmg += sum(rollDice(diceCount, diceDmg))
    if dmg > 0:
        for people in peopleTargeted:
            takeHealing(actor, people, dmg, map)

def takeHealing(actor, people, dmg, map):
    print(actor.name, 'is healing', people.name, 'for',dmg)
    player = 1
    if str(type(actor)) == "<class 'monster.Monster'>":
        player = 0
    if player:
        if any([x in people.status for x in ['deathSaves','unconscious']]):
            people.health = 0
            people.status = []
    people.health += dmg

def castSpellTurn(actor, turnChoice, map):
    actorCoord = [x for x in map.arrayCenters.keys() if map.arrayCenters[x] == actor][0]
    player = 1
    if str(type(actor)) == "<class 'monster.Monster'>":
        player = 0
    
    if map.arrayCenters[turnChoice[3][1]] != '' and map.arrayCenters[turnChoice[3][1]] != actor:
        
        newCoord = map.moveToNearest(actor, turnChoice[3][1])
        map.moveActor(actor, newCoord)
    elif map.arrayCenters[turnChoice[3][1]] != actor:
        
        map.moveActor(actor, turnChoice[3][1])
    peopleTargeted = [map.arrayCenters[x] for x in turnChoice[3][3] if map.arrayCenters[x] != '']
    spell = actor.spells[turnChoice[0]]
    if not player:
        actor.spells[turnChoice[0]][0] -= 1
        spell = actor.spells[turnChoice[0]][1]
        
    else:
        actor.spellSlots[str(actor.spells[turnChoice[0]]['lvl'])] -= 1
    
    #actor.spellSlots[str(actor.spells[turnChoice[0]]['lvl'])] -= 1
    save = spell['save'].split()
    if spell['attack'] == '' and save != []: # youre a save effect
        peopleHit = [x for x in peopleTargeted if rollSave(x, save[0], actor.spellDC)]
    else: # spell attack
        reachLimit = (int(re.findall(r'\d+', spell['range'])[0])) 
        if reachLimit >= actor.optRange:
            moveWithingReach(actor, peopleTargeted[0], actor.optRange, map)
        else:
            moveWithingReach(actor, peopleTargeted[0], reachLimit, map)
        hitRoll = rollDice(1,20)[0] + int(actor.spellAttackMod)
        peopleHit = [x for x in peopleTargeted if hitRoll >= x.ac]
    
    dice = spell['dice']
    dmg = 0
    if dice[0] != '':
        for di in dice:
            diceCount = int(re.findall(r'\d+', di)[0])
            
            diceDmg = int(re.findall(r'\d+', di)[1])
            dmg += sum(rollDice(diceCount, diceDmg))

    if spell['area'] != '' and dmg > 0:
        for people in peopleTargeted:
            if people in peopleHit:
                #people.health -= dmg
                takeDmg(actor, people, dmg, map)
            else:
                people.health -= col_round(dmg/2)
    elif dmg > 0 :
        for people in peopleHit:
            #people.health -= dmg
            takeDmg(actor, people, dmg, map)
    
    if turnChoice[1] == 'cc':
        for people in peopleHit:
            people.cc = [spell["lvl"], save, actor.spellDC]

def weaponAttack(actor, target, weap, map):

        player = 1
        if str(type(actor)) == "<class 'monster.Monster'>":
            player = 0
        myIndex = [list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] == actor][0]
        targetIndex = [list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] == target][0]
        targDistance = map.distanceCalc(myIndex, targetIndex)
        if targDistance > weap.range/5:
            print(actor.name,'out of range to hit',target.name,'with',weap.name,'...',targDistance,'..',weap.range/5)
            raise SystemExit('Crashed in weaponAttack')
        
        
        if not player: 
            if weap.name in actor.multiAttack.keys():
                numAttack = int(actor.multiAttack[weap.name])
            else:
                numAttack = 1
            prof = 0
        else:
            numAttack = actor.twoAttacks + 1
            prof = actor.proficiency
        
        #numAttack = actor.twoAttacks + 1
        rollToHit = [x + int(weap.attackMod) + int(prof) for x in rollDice(numAttack, 20) ]
        hits = []
        for roll in rollToHit:
            if roll >= int(target.ac):
                if roll == 20 + int(prof) + int(weap.attackMod):
                    hits.append(2)
                else:
                    hits.append(1)
        dmg = 0
        for hit in hits:
            if not player:
                dmg = sum([rollDice(int(weap.diceCount[i]), int(weap.diceType[i])) for i in range(len(weap.diceType))][0]) + int(weap.dmgMod)
                if hit == 2:
                    dmg = sum([rollDice(int(weap.diceCount[i]), int(weap.diceType[i])) for i in range(len(weap.diceType))][0]) 
            else:
                dmg += rollDice(int(weap.diceCount), int(int(re.findall(r'\d+', weap.diceType)[0])))[0] + int(weap.dmgMod)
                if hit == 2:
                    dmg += rollDice(int(weap.diceCount), int(int(re.findall(r'\d+', weap.diceType)[0])))[0] 
        if player:
            dmg += actor.classMeleeDmg(hits, dmg)
        #target.health -= dmg
        takeDmg(actor, target, dmg, map)

def bestSphere(actor, map, radius, reach, targets = 'enemy'):
    reachLimit = reach/5
    setRatio = 4
    hexLimit = radius/5
    #print(hexLimit)
    actorCoord = [x for x in map.arrayCenters.keys() if map.arrayCenters[x] == actor][0]
    if targets == 'party':
        enemyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.enemy]
        partyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.party]
    if targets == 'enemy':
        enemyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.party]
        partyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.enemy]

    
    distances = {}
    distances['Enemy'] = [[map.distanceCalc(coord1, list(map.arrayCenters).index(coord2)) for coord1 in enemyList] for coord2 in list(map.arrayCenters)]
    distances['Ally'] = [[map.distanceCalc(coord1, list(map.arrayCenters).index(coord2)) for coord1 in partyList] for coord2 in list(map.arrayCenters)]
    desired = len(enemyList)
    goalAchieved = 0
    
    while goalAchieved == 0:
        for i in range(len(distances['Ally'])):
            
            sumEnemies = sum([1 for dist in distances['Enemy'][i] if dist <= hexLimit])
            if sumEnemies == 0:
                continue
            sumAllies = sum([1 for dist in distances['Ally'][i] if dist <= hexLimit])
            #print(sumAllies, sumEnemies)

            if sumAllies == 0 and sumEnemies == desired: # simple case
                enemiesHit = [list(map.arrayCenters)[coord] for coord in enemyList if map.distanceCalc(coord, i)<= hexLimit]
                partyHit = [list(map.arrayCenters)[coord] for coord in partyList if map.distanceCalc(coord, i)<= hexLimit]
                totalHit = enemiesHit + partyHit
                
                return (desired, actorCoord, list(map.arrayCenters)[i], totalHit)
            if sumAllies == 0 and sumEnemies < desired:
                continue
            if sumAllies != 0 and sumEnemies/sumAllies >= setRatio:
                enemiesHit = [list(map.arrayCenters)[coord] for coord in enemyList if map.distanceCalc(coord, i) <= hexLimit]
                partyHit = [list(map.arrayCenters)[coord] for coord in partyList if map.distanceCalc(coord, i) <= hexLimit]
                totalHit = enemiesHit + partyHit
                return (sumEnemies, actorCoord, list(map.arrayCenters)[i], totalHit)

        desired -= 1
        if desired == 0:
            return (0,0)

def bestLine(actor, map, length, reach):
    ##print('bestLine')
    setRatio = 4
    
    mapKeys = map.arrayCenters.keys()
    actorCoord = [x for x in map.arrayCenters.keys() if map.arrayCenters[x] == actor][0]
    ##print(reach)
    moveLimit =  reach + actor.speed/5
    myIndex = list(map.arrayCenters).index(actorCoord)
    movementCoords = [ coord for coord in map.arrayCenters.keys() if map.distanceCalc(myIndex, list(map.arrayCenters).index(coord)) <= moveLimit and map.arrayCenters[coord] == '']
    hexLimit = int(length/5)
    
    if actor in map.enemy:
        enemyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.enemy]
        partyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.party]
    if actor in map.party:
        enemyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.party]
        partyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.enemy]

    distances = {}
    distances['Enemy'] = [[map.distanceCalc(coord1, list(map.arrayCenters).index(coord2)) for coord1 in enemyList] for coord2 in movementCoords]
    distances['Ally'] = [[map.distanceCalc(coord1, list(map.arrayCenters).index(coord2)) for coord1 in partyList] for coord2 in movementCoords]
    desired = len(enemyList)
    distances =  [[coord2 for coord1 in enemyList if map.distanceCalc(coord1, list(map.arrayCenters).index(coord2)) <= hexLimit] for coord2 in movementCoords]
    flat = list(set([x for xs in distances for x in xs]))
    ##print(len(flat), len(movementCoords))
    people = [x for x in map.arrayCenters.keys() if map.arrayCenters[x] != '' and map.arrayCenters[x] != 'c']
    #ep = [x for x in people if map.arrayCenters[x].name == 'Ephraim'][0]

    maxX = max([coord[0] for coord in list(map.arrayCenters)])
    maxY = max([coord[1] for coord in list(map.arrayCenters)])
    
    
    mapRing =  [coord for coord in list(map.arrayCenters) if coord[1] in (0,1, maxY-1, maxY) or coord[0] in (0,maxX)]
    
    
    goalAchieved = 0
    finalList = []
    start = time.time()
    for moveCoord in flat:

        dist = [list(map.arrayCenters)[ind] for ind in range(len(list(map.arrayCenters))) if map.distanceCalc(list(map.arrayCenters).index(moveCoord), ind) == hexLimit]

        

        for coord in mapRing:
            if map.distanceCalc(list(map.arrayCenters).index(coord), list(map.arrayCenters).index(moveCoord)) <= hexLimit:
                dist.append(coord)
        # handle case where range larger than map
        if len(dist) == 0:
            ##print('dis was empty creating new one')
            dist = mapRing
        maxHit =0
        for coord in dist:
            
            if coord == moveCoord:
                continue
            line = drawLine(coord, moveCoord, map)
            sumEnemies =  sum([1 for badGuy in enemyList if list(map.arrayCenters)[badGuy] in line])
            if sumEnemies >> maxHit:
                maxHit = sumEnemies
        finalList.append((moveCoord,maxHit))
    ##print(finalList)
    maxEnemies = max([x[1] for x in finalList])
    end = time.time()
    #print('For loop', end - start)
    return maxEnemies
    
def bestLine2(actor, map, length, reach):
    startTime = time.time()
    
    actorCoord = [x for x in map.arrayCenters.keys() if map.arrayCenters[x] == actor][0]
    moveLimit =  reach + actor.speed/5
    myIndex = list(map.arrayCenters).index(actorCoord)
    movementCoords = [ coord for coord in map.arrayCenters.keys() if map.distanceCalc(myIndex, list(map.arrayCenters).index(coord)) <= moveLimit and map.arrayCenters[coord] == '']
    hexLimit = int(length/5)
    
    if actor in map.enemy:
        enemyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.enemy]
    if actor in map.party:
        enemyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.party]
    if len(enemyList) == 1:
        enemyDist = map.distanceCalc(myIndex, enemyList[0])
        if enemyDist > moveLimit + hexLimit:
            return(0,0)
        targetCoord = list(map.arrayCenters)[enemyList[0]]
        line = drawLine(actorCoord,targetCoord, map)
        moveTo = [coord for coord in line if map.distanceCalc(list(map.arrayCenters).index(targetCoord), list(map.arrayCenters).index(coord)) <= hexLimit and map.arrayCenters[coord] == ''][0] # closest inside reach
        return(1, moveTo, moveTo, [targetCoord])
    
        
    test = []
    for enemy in enemyList:
        for e2 in enemyList:
            e2Dist = map.distanceCalc(myIndex, e2)
            enemyDist = map.distanceCalc(myIndex, enemy)
            if e2 == enemy or enemyDist > moveLimit + hexLimit or e2Dist > moveLimit + hexLimit:
                continue
            enemyCoord = list(map.arrayCenters)[enemy]
            e2Coord = list(map.arrayCenters)[e2]
            line = drawLine(enemyCoord, e2Coord, map)
            sumEnemies =  sum([1 for badGuy in enemyList if list(map.arrayCenters)[badGuy] in line])
            test.append([(sumEnemies, 0), enemyCoord, e2Coord])
    test = list({tuple(sorted(i)): i for i in test}.values())
    test.sort()
    test.reverse()
    maxX = max([coord[0] for coord in list(map.arrayCenters)])
    maxY = max([coord[1] for coord in list(map.arrayCenters)])
    
    test = np.asarray(test)
    testRing = np.asarray([coord for coord in list(map.arrayCenters) if coord[1] in (0,1, maxY-1, maxY) or coord[0] in (0,maxX)])
    
    possibleCoords = []
    for targets in test:

        possibleCoords.clear()
        firstCoord = tuple(targets[1])
        secondCoord = tuple(targets[2])
        
        maX = max(firstCoord[0], secondCoord[0])
        maY = max(firstCoord[1], secondCoord[1])
        miX = min(firstCoord[0], secondCoord[0])
        miY = min(firstCoord[1], secondCoord[1])
        for coord in testRing:
            coord = tuple(coord)
            
            
            if (maX, maY) in [firstCoord, secondCoord]:
                if coord[0] < maX or coord[1] < maY :
                    continue
            elif coord[0] > miX or coord[1] < maY:
                continue
            if coord[0] > miX and coord[0] < maX or coord[1] > miY and coord[1] < maY:
                continue
            guys = targets[0][0]
            if firstCoord != coord:
                line = drawLine(coord, firstCoord, map)
                
                inBetweenCoords = [x for x in line  if x[0] >= miX and x[0] <= maX and x[1]>= miY and x[1] <=maY]
                sumEnemies =  sum([1 for badGuy in enemyList if list(map.arrayCenters)[badGuy] in inBetweenCoords])
                if secondCoord in line and sumEnemies == guys:
                    possibleCoords +=  [coord for coord in line if coord not in inBetweenCoords]
                    '''for c in line:
                        map.arrayCenters[c] = 'c'''
            if secondCoord != coord:
                line2 = drawLine(coord, secondCoord, map)
                inBetweenCoords = [x for x in line2  if x[0] >= miX and x[0] <= maX and x[1]>= miY and x[1] <=maY]
                sumEnemies =  sum([1 for badGuy in enemyList if list(map.arrayCenters)[badGuy] in inBetweenCoords])
                if firstCoord in line2 and sumEnemies == guys:
                    possibleCoords +=  [coord for coord in line2 if coord not in inBetweenCoords]
                    '''for c in line2:
                        map.arrayCenters[c] = 'c'''
            moveTo = [x for x in possibleCoords if x in movementCoords]
            if len(moveTo) != 0:
                badGuys =  [ list(map.arrayCenters)[badGuy]for badGuy in enemyList if list(map.arrayCenters)[badGuy] in inBetweenCoords]
                finalCoord = [guys, moveTo[0], moveTo[0], badGuys]
                EndTime = time.time()
                
                return finalCoord
            
        return(0,0)        
    
def drawLine( coord1, coord2, map):

    dist = int(map.distanceCalc(list(map.arrayCenters).index(coord1), list(map.arrayCenters).index(coord2)))

    x1, y1 = coord1
    x2, y2 = coord2

    xDiff = x2 -x1
    yDiff = y2-y1
    
    
    pts = np.array(list(map.arrayCenters))
    
    lineCoord = np.array([(0.0,0.0) for i in range(dist +1)]) 
    for i in range(int(dist)+1):
        lineCoord[i] = [coord1[0] + i*xDiff/dist, coord1[1] + i*yDiff/dist-0.01]
    snapCoord = [tuple(pts[spatial.KDTree(pts).query(coord)[1]]) for coord in lineCoord]
    
    return snapCoord

def bestSquare(actor, map, length, reach):
    setRatio = 4
    actorCoord = [x for x in map.arrayCenters.keys() if map.arrayCenters[x] == actor][0]
    moveLimit =  reach/5 + actor.speed/5
    #print(reach)
    myIndex = list(map.arrayCenters).index(actorCoord)
    movementCoords = [ coord for coord in map.arrayCenters.keys() if map.distanceCalc(myIndex, list(map.arrayCenters).index(coord)) <= moveLimit and map.arrayCenters[coord] == '']
    hexLimit = int(length/5)
    ##print(hexLimit)

    if actor in map.enemy:
        enemyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.enemy]
        partyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.party]
    if actor in map.party:
        enemyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.party]
        partyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.enemy]
    desired = len(enemyList)
    distances =  [[coord2 for coord1 in enemyList if map.distanceCalc(coord1, list(map.arrayCenters).index(coord2)) <= hexLimit] for coord2 in movementCoords]
    flat = list(set([x for xs in distances for x in xs]))
    
    # create square

    #operations2 = [[[operator.sub, 1], [operator.add, 1], [operator.sub, 1], [operator.sub, 1]]]
    operations = [[operator.sub,1, operator.add, 1,operator.add,0,operator.sub,0], 
                    [operator.sub, 1, operator.sub, 1,operator.add,0,operator.sub,0],
                    [operator.add,1, operator.add, 1,operator.add,0,operator.sub,0], 
                    [operator.add, 1, operator.sub, 1,operator.add,0,operator.sub,0],
                    [operator.sub, 1, operator.add, 2,operator.add,1,operator.sub,5],
                    [operator.add, 1, operator.sub, 2,operator.sub,1,operator.add,5],
                    [operator.add, 1, operator.sub, 2,operator.sub,1,operator.sub,5],
                    [operator.sub, 1, operator.add, 2,operator.add,1,operator.add,5]]
    if len(flat) == 0:
        return (0,0)
    finalList = []
    for moveCoord in flat:
        maxHit =0
        for op in operations:
            startCoord = (op[0](moveCoord[0], op[1]), op[2](moveCoord[1], op[3]))
            squareCoords = []
            ##print(op)
            for k in range(hexLimit):
                for l in range(hexLimit):
                    x = op[4](op[0](startCoord[0], k),op[5])
                    if op[2] == operator.add:
                        y= op[6](operator.sub(startCoord[1], 2*l),op[7])
                    else:
                        y= op[6](operator.add(startCoord[1], 2*l),op[7])
                    if x % 2 != y % 2 :
                        y = op[2](y, 1)
                    squareCoords.append((x,y))
            
            sumEnemies = sum([1 for ind in enemyList if list(map.arrayCenters)[ind] in squareCoords])
            
            if sumEnemies == 0:
                continue
            sumAllies = sum([1 for ind in partyList if list(map.arrayCenters)[ind] in squareCoords])
            if sumEnemies >> maxHit:
                maxHit = sumEnemies
                enemiesHit = [list(map.arrayCenters)[ind] for ind in enemyList if list(map.arrayCenters)[ind] in squareCoords]
                partyHit = [list(map.arrayCenters)[ind] for ind in partyList if list(map.arrayCenters)[ind] in squareCoords]
                totalHit = enemiesHit + partyHit
            if sumAllies == 0 and sumEnemies == desired: # simple case
                enemiesHit = [list(map.arrayCenters)[ind] for ind in enemyList if list(map.arrayCenters)[ind] in squareCoords]
                partyHit = [list(map.arrayCenters)[ind] for ind in partyList if list(map.arrayCenters)[ind] in squareCoords]
                totalHit = enemiesHit + partyHit
                line = drawLine(actorCoord, moveCoord, map)
                ##print(line)
                options = [x for x in line if map.distanceCalc(list(map.arrayCenters).index(x), list(map.arrayCenters).index(actorCoord)) <= actor.speed/5 and
                        map.distanceCalc(list(map.arrayCenters).index(x), list(map.arrayCenters).index(moveCoord)) <= reach/5]
                ##print(options)
                return (desired, options[0], moveCoord, totalHit)
            if sumAllies == 0 and sumEnemies < desired:
                continue
            if sumAllies != 0 and sumEnemies/sumAllies >= setRatio:
                enemiesHit = [list(map.arrayCenters)[ind] for ind in enemyList if list(map.arrayCenters)[ind] in squareCoords]
                partyHit = [list(map.arrayCenters)[ind] for ind in partyList if list(map.arrayCenters)[ind] in squareCoords]
                totalHit = enemiesHit + partyHit
                line = drawLine(actorCoord, moveCoord, map)
                ##print(line)
                options = [x for x in line if map.distanceCalc(list(map.arrayCenters).index(x), list(map.arrayCenters).index(actorCoord)) <= actor.speed/5 and 
                        map.distanceCalc(list(map.arrayCenters).index(x), list(map.arrayCenters).index(moveCoord)) <= reach/5]
                ##print(options)
                return (sumEnemies, options[0], moveCoord, totalHit)
        finalList.append((moveCoord,maxHit, totalHit))
    ##print(finalList)
    onlyHits = [x[1] for x in finalList]
    maxEnemies = max(onlyHits)
    max_index = onlyHits.index(maxEnemies)
    ##print(finalList[max_index])
    line = drawLine(actorCoord, finalList[max_index][0], map)
    options = [x for x in line if map.distanceCalc(list(map.arrayCenters).index(x), list(map.arrayCenters).index(actorCoord)) <= actor.speed/5 and 
                map.distanceCalc(list(map.arrayCenters).index(x), list(map.arrayCenters).index(finalList[max_index][0])) <= reach/5]
    return (maxEnemies, options[0], finalList[max_index][0], finalList[max_index][2])
    

def bestCone(actor, map, length, reach):
    '''
    step 1 make a cone at all coming from actor
    '''
    ##print('bestCone')
    setRatio = 4
    mapKeys = map.arrayCenters.keys()
    actorCoord = [x for x in map.arrayCenters.keys() if map.arrayCenters[x] == actor][0]
    moveLimit = actor.speed/5
    myIndex = list(map.arrayCenters).index(actorCoord)
    movementCoords = [ coord for coord in map.arrayCenters.keys() if map.distanceCalc(myIndex, list(map.arrayCenters).index(coord)) <= moveLimit and map.arrayCenters[coord] == '']
    hexLimit = int(length/5)
    
    if actor in map.enemy:
        enemyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.enemy]
        partyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.party]
    if actor in map.party:
        enemyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.party]
        partyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.enemy]

    distances = {}
    distances['Enemy'] = [[map.distanceCalc(coord1, list(map.arrayCenters).index(coord2)) for coord1 in enemyList] for coord2 in movementCoords]
    distances['Ally'] = [[map.distanceCalc(coord1, list(map.arrayCenters).index(coord2)) for coord1 in partyList] for coord2 in movementCoords]
    desired = len(enemyList)
    ##print(distances)


    
    operations2 = [[[operator.sub, 1], [operator.add, 1], [operator.sub, 1], [operator.sub, 1]],
                    [[operator.sub, 1], [operator.sub, 1], [operator.add, 0], [operator.sub, 2]],
                    [[operator.add, 0], [operator.sub, 2], [operator.add, 1], [operator.sub, 1]],
                    [[operator.add, 1], [operator.sub, 1], [operator.add, 1], [operator.add, 1]],
                    [[operator.add, 1], [operator.add, 1], [operator.add, 0], [operator.add, 2]],
                    [[operator.add, 0], [operator.add, 2], [operator.sub, 1], [operator.add, 1]]]
    direction = ['W','NW','N','NE','E','SE','S','SW']
    ##print(actorCoord)
    ##print(hexLimit)
    finalCoord = []
    goalAchieved = 0
    while goalAchieved == 0:
        for hex in range(len(distances['Ally'])):
            sumEnemies = sum([1 for dist in distances['Enemy'][hex] if dist <= hexLimit]) # number of enemenys in range
            if sumEnemies == 0:
                continue
            sumAllies = sum([1 for dist in distances['Ally'][hex] if dist <= hexLimit])
            if sumAllies == 0 and sumEnemies < desired:
                    continue
            if sumEnemies == desired:
                for op in operations2:
                    ##print('starting new op')
                    ##print(op)
                    finalCoord.clear()
                    for cell in range(hexLimit):
                        
                        if op[0][1] == 0:
                            postive = (op[0][0](movementCoords[hex][0], op[0][1]), op[1][0](op[1][0](movementCoords[hex][1], cell*2), op[1][1]))
                        else:
                            postive = (op[0][0](op[0][0](movementCoords[hex][0], cell), op[0][1]), op[1][0](op[1][0](movementCoords[hex][1], cell), op[1][1]))
                        if op[2][1] == 0:
                            ##print('operation', op[3][1])
                            negative = (op[2][0](movementCoords[hex][0], op[2][1]), op[3][0](op[3][0](movementCoords[hex][1], cell*2), op[3][1]))
                        else:
                            negative = (op[2][0](op[2][0](movementCoords[hex][0], cell), op[2][1]), op[3][0](op[3][0](movementCoords[hex][1], cell), op[3][1]))
                    
                    
                    
                        ##print(pair)

                        x1, y1 = abs(postive[0] - negative[0]), abs(postive[1] - negative[1])
                        if x1 == 0 and y1 == 2:
                            finalCoord.append(postive)
                            finalCoord.append(negative)
                        else:
                            if op[0] == op[2]: # same x value dif y values
                                maxY, minY = max(postive[1], negative[1]), min(postive[1], negative[1])
                                for i in range(minY, maxY+1):
                                    finalCoord.append((postive[0], i))
                            elif op[3][1] == 2:
                                maxY, minY = max(postive[1], negative[1]), min(postive[1], negative[1])
                                maxX, minX = max(postive[0], negative[0]), min(postive[0], negative[0])
                                yCoord = []
                                xCoord = []
                                for i in range(minY, maxY+1):
                                    ##print('y:',i)
                                    yCoord.append(i)
                                for i in range(maxX, minX-1, -1 ):
                                    ##print('x:',i)
                                    xCoord.append(i)
                                for i in range(len(xCoord)):
                                    finalCoord.append((xCoord[i], yCoord[i]))
                            else:
                                maxY, minY = max(postive[1], negative[1]), min(postive[1], negative[1])
                                maxX, minX = max(postive[0], negative[0]), min(postive[0], negative[0])
                                yCoord = []
                                xCoord = []
                                for i in range(minY, maxY+1):
                                    ##print('y:',i)
                                    yCoord.append(i)
                                for i in range(minX,maxX +1 ):
                                    ##print('x:',i)
                                    xCoord.append(i)
                                for i in range(len(xCoord)):
                                    finalCoord.append((xCoord[i], yCoord[i]))
                    enemyCoord = [list(map.arrayCenters)[ind] for ind in enemyList]
                    partyCoord = [list(map.arrayCenters)[ind] for ind in partyList]
                    
                    enemyHit = []
                    partyHit = []
                    enemyHit.clear()
                    partyHit.clear()
                    for coord in finalCoord:
                        if coord in enemyCoord:
                            enemyHit.append(coord)
                        if coord in partyCoord:
                            partyHit.append(coord)
                    if len(partyHit) == 0 and len(enemyHit) == desired:
                        totalHit = enemyHit+partyHit
                        return (desired, movementCoords[hex], movementCoords[hex], totalHit)
                    elif len(partyHit) != 0 and len(enemyHit)/len(partyHit) >= setRatio:
                        totalHit = enemyHit+partyHit
                        return (len(enemyHit), movementCoords[hex],movementCoords[hex], totalHit)


        desired -= 1
        if desired == 0:
            return (0,0)


def moveWithingReach(actor, target, reach, map):
    actorCoord = [x for x in map.arrayCenters.keys() if map.arrayCenters[x] == actor][0]
    targetCoord = [x for x in map.arrayCenters.keys() if map.arrayCenters[x] == target][0]
    ##print(actorCoord, targetCoord)
    ##print('player moveWithinReach')
    hexLimit = reach/5
    dist = map.distanceCalc(list(map.arrayCenters).index(targetCoord), list(map.arrayCenters).index(actorCoord))
    ##print(dist)
    if dist <= hexLimit:
        return
    line = drawLine(actorCoord,targetCoord, map)
    ##print(line)
    hexLimit = reach/5
    moveTo = [coord for coord in line if map.distanceCalc(list(map.arrayCenters).index(targetCoord), list(map.arrayCenters).index(coord)) <= hexLimit][0] # closest inside reach
    if map.arrayCenters[moveTo] != '':
        map.moveToNearest(actor, target)
    else:
        map.moveActor(actor, moveTo)
    ##print(actorCoord)
    ##print(target.name)
    ##print(moveTo)
    
def rollDice(n, diceType):
        
    rolls = []
    for i in range(n):
        rolls.append(r.randint(1,diceType))
    return rolls

def rollSave(actor, abilityType, dc):
    '''
    roll a saving throw

    true if failed
    '''
    roll = r.randint(1,20) # initial roll
    ##print(' in player rollSave')
    ##print(abilityType)
    ##print(dc)
    #print(down_round((actor.modDict[abilityType]- 10)/2))
    roll += down_round((actor.modDict[abilityType]- 10)/2) # add modifier
    #print(roll,'vs', dc)
    # return true false 
    ##print('\t\t\t Roll:',roll,'vs DC:', dc)
    return roll < dc

def takeDmg(actor, target, dmg, map):
    print(actor.name, 'is doing ', dmg, 'to', target.name)
    if str(type(target)) == "<class 'monster.Monster'>":
        target.health -= dmg
        if target.health <= 0:
            target.alive = 0
    else: # right now no death saves
        if 'deathSaves' in target.status:
            target.deathSaves['fail'].append(1)
            print(target.deathSaves)
            if sum(target.deathSaves['fail']) >= 3:
                target.alive = 0
        else:
            target.health -= dmg
            if target.health <= 0:
                if 'deathSaves' not in target.status:
                    target.status.append('deathSaves')
                    target.cc = []
                
                #target.alive = 0

    
                
def takeReaction(actor, m, target):
    map = m
    
    player = 1
    if str(type(actor)) == "<class 'monster.Monster'>":
        player = 0
    myIndex = [list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] == actor][0]
    targetIndex = [list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] == target][0]
    minDist = map.distanceCalc(myIndex, targetIndex)
    

    
    #map.moveToNearest(actor, closestGuy)
    
    ##print(closestGuy)
    ##print(actor.weaponList)
    maxDmg = 0
    attackWith = actor.weaponList[0]
    attackTimes = 1
    #print(actor.weaponList)
    for weap in actor.weaponList:
        avgDmg = 0
        ##print(int((int(weap.range) + int(actor.speed))/5), minDist)
        if int(minDist) > int(weap.range)/5:
            
            ##print('not within range')
            continue
        
        if not player:
            dice = weap.diceType
            diceCount = weap.diceCount
            for di in dice:
                diceCount = weap.diceCount[weap.diceType.index(di)]
                avgDmg +=  attackTimes * (0.5 + weap.dmgMod + diceCount * di / 2 )
            prof = 0
        else:
        
            dice = int(re.findall(r'\d+',weap.diceType)[0])
            diceCount = weap.diceCount
            avgDmg +=  attackTimes * (0.5 + weap.dmgMod + diceCount * dice / 2 )
            prof = actor.proficiency

        if avgDmg > maxDmg:
            maxDmg = avgDmg
            attackWith = weap
    
    if maxDmg == 0:
        return
    rollToHit = [x + int(attackWith.attackMod) + int(prof) for x in rollDice(attackTimes, 20) ]
    ##print(rollToHit)
    ##print(target.name, target.ac)
    hits = []
    for roll in rollToHit:
        if roll >= int(target.ac):
            if roll == 20 + int(attackWith.attackMod):
                hits.append(2)
            else:
                hits.append(1)
    #hits = [1 for x in rollToHit if x >= int(target.ac)]
    ##print(hits)
    #dmg = sum(rollDice(hits*int(weap.diceCount), int(weap.diceType))) 
    dmg = 0
    for hit in hits:
        if not player:
            dmg = sum([rollDice(int(attackWith.diceCount[i]), int(attackWith.diceType[i])) for i in range(len(attackWith.diceType))][0]) + int(attackWith.dmgMod)
            if hit == 2:
                dmg = sum([rollDice(int(attackWith.diceCount[i]), int(attackWith.diceType[i])) for i in range(len(attackWith.diceType))][0]) 
        else:
            dmg += rollDice(int(attackWith.diceCount), int(int(re.findall(r'\d+', attackWith.diceType)[0])))[0] + int(attackWith.dmgMod)
            if hit == 2:
                dmg += rollDice(int(attackWith.diceCount), int(int(re.findall(r'\d+', attackWith.diceType)[0])))[0] 
    #dmg = sum([rollDice(hits*int(weap.diceCount), int(int(re.findall(r'\d+', weap.diceType)[0])))][0]) + hits*int(weap.dmgMod)
    ##print(dmg)
    ##print(target.health)
    if player:
        dmg += actor.classMeleeDmg(hits, dmg)
    takeDmg(actor, target, dmg, map)
    actor.reaction = 0
    #print(actor.name,'is doing a weapon attack and is doing', dmg, 'to', target.name, 'and they are now at', target.health)

def rollDeathSave(actor):
    print(actor.name, ' is rolling death saves')
    roll = rollDice(1, 20)[0]
    if roll <= 10:
        print(actor.name, 'failed death save with ', roll)
        if roll == 1:
            actor.deathSaves['fail'].append(2)    
        actor.deathSaves['fail'].append(1)
    else:
        if roll == 20:
            print(actor.name, 'is getting up with a Natural 20!')
            actor.deathSaves['pass'].append(3)    
            actor.health = 1
            actor.status.remove('deathSaves')
            actor.deathSaves = {'pass':[], 'fail':[]}
            return
        actor.deathSaves['pass'].append(1)
        print(actor.name, 'passed death save with ', roll)
    
    # scores
    fails = sum(actor.deathSaves['fail'])
    passes = sum(actor.deathSaves['pass'])
    if fails >= 3:
        actor.alive = 0
        #print(actor.name, 'is dead with', fails, 'fails')
    if passes >= 3 and roll != 20:
        actor.health = 1
        actor.status.append('unconscious')
        actor.status.remove('deathSaves')
        actor.deathSaves = {'pass': [], 'fail': []}
        #print(actor.name, 'passed death saves')
    #print(actor.deathSaves)

def weibull(h):
    x = 1
    y = 0
    z = 0.7
    pk = 1 - np.exp(-x*(h-y)**z)
    return pk

def col_round( x):
        frac = x - math.floor(x)
        if frac < 0.5: return math.floor(x)
        return math.ceil(x)

def down_round( x):
        frac = x - math.floor(x)
        if frac <= 0.5: return math.floor(x)
        return math.ceil(x)

def cone(x):
    area = sum([i for i in range(2,int((x/5)+2))])* 5
    return area


@dataclass
class WeaponNew:
    name: str
    attackType: str
    range: int
    attackMod: int
    diceType: list
    diceCount: list
    dmgMod: int

def text2int(textnum, numwords={}):
    if textnum.isdigit():
        return int(textnum)
    if not numwords:
      units = [
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
        "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
        "sixteen", "seventeen", "eighteen", "nineteen",
      ]

      tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

      scales = ["hundred", "thousand", "million", "billion", "trillion"]

      numwords["and"] = (1, 0)
      for idx, word in enumerate(units):    numwords[word] = (1, idx)
      for idx, word in enumerate(tens):     numwords[word] = (1, idx * 10)
      for idx, word in enumerate(scales):   numwords[word] = (10 ** (idx * 3 or 2), 0)

    current = result = 0
    for word in textnum.split():
        if word not in numwords:
          #raise Exception("Illegal word: " + word)
            return 'Not a number'
        scale, increment = numwords[word]
        current = current * scale + increment
        if scale > 100:
            result += current
            current = 0

    return result + current

def numberAfterString(text, target_string):
    """Finds the first digit that follows a given string in a text."""

    index = text.find(target_string)
    if index == -1:
        return None

    index += len(target_string)
    
    range = re.findall(r'\d+', text[index:])[0]
    return int(range)

def numberBeforeString(text, target_string):
    """Finds the first digit that follows a given string in a text."""

    index = text.find(target_string)
    if index == -1:
        return None

    #index += len(target_string)
    
    range = re.findall(r'\d+', text[:index])[-1]
    return int(range)


