import re
import math
import numpy as np
import time
import operator
from scipy import spatial
import numpy as np
import time
import sys
import json
import array
import pathlib
dmSimPath = str(pathlib.Path(__file__).parent.resolve())[0:-6]
sys.path.insert(1, dmSimPath)
from modelMethods import down_round, weibull, cone, WeaponNew, col_round, bestSphere, \
    bestCone, bestLine2, bestSquare, takeDmg, takeReaction, moveWithingReach, rollDice, \
    rollSave, rollDeathSave
    
class Monster:
    def __init__(self, name, ac, health, speed, modDict, turnFactors, weaponList, size, spells, spellMod, multiAttack, legRes = 0, legAction = [0, '']):
        self.name = name
        self.ac = ac
        self.health = health
        self.maxHealth = health
        self.speed = speed
        self.modDict = modDict
        self.weaponList = weaponList
        self.turnFactors = turnFactors
        self.initTF = self.turnFactors
        self.size = size
        self.initSpells = spells
        self.spells = spells
        self.multiAttack = multiAttack 
        self.cc = [] # if cc'ed will be length 3 and in format ['spellLvl', 'modToRoll', dcToBeat]
        self.initMod = down_round((self.modDict['Dexterity']-10)/2)
        self.spellAttackMod = spellMod
        self.spellDC = 8 + self.spellAttackMod
        self.legRes = legRes
        self.maxLegRes = legRes
        self.legActions = legAction[0]
        self.maxLegActions = legAction[0]
        self.legActionWeapon = legAction[1]
        self.reaction = 1
        self.alive = 1
        self.AvgdmgCalc()

    def AvgdmgCalc(self):
        dmgTypes = ['Acid', 'Bludgeoning', 'Cold', 'Fire', 'Force', 'Lightning', 'Necrotic', 'Piercing', 'Poison', 'Psychic', 'Radiant', 'Slashing', 'Thunder']
        conditionsList = ['Blinded','Charmed','Deafened', 'Frightened','Grappled','Incapacitated','Invisible','Paralyzed','Petrified','Poisoned','Prone','Restrained', 'Stunned','Unconscious','Exhausted']
        spellDmg = 0
        maxDmg = 0
        turnInfo = {}
        for spell in self.spells.keys():
            avgDmg = 0
            dice = self.spells[spell][1]['dice']
            effect = self.spells[spell][1]['effect']
            area = self.spells[spell][1]['area']
            if self.spells[spell][1]['combat'] != 'y':
                continue
            if effect in dmgTypes:
                for di in dice:
                    diceCount = int(re.findall(r'\d+', di)[0])

                    diceDmg = int(re.findall(r'\d+', di)[1])
                    avgDmg += 0.5 + diceCount * diceDmg / 2
            if effect in conditionsList:
                avgDmg = 20
            if area != '':
                match area:
                    case str(x) if 'sphere' in x:
                        radius = int(re.findall(r'\d+', area)[0])
                        area = math.pi * radius*radius
                        party = 4
                        
                    case str(x) if 'line' in x:
                        length = int(re.findall(r'\d+', area)[0])
                        area = length * 5
                        party = math.sqrt(4) # assume lay out party in square and single line can only hit one line in square

                    case str(x) if 'square' in x:
                        width = int(re.findall(r'\d+', area)[0])
                        area = width * width
                        party = 4
                    
                    case str(x) if 'cone' in x:
                        width = int(re.findall(r'\d+', area)[0])
                        area = cone(width)
                        party = 4

                ##print(area)
                ratio =  area / 25*party
                percentHit = weibull(ratio)
                ##print(percentHit)
                totalHit = down_round(party * percentHit)
                ##print(totalHit)
                avgDmg = totalHit * avgDmg 

                ##print(spell)
                ##print(totalDmg)
            area = self.spells[spell][1]['area']
            if area == '':
                area = 0
            else:
                area = int(re.findall(r'\d+', area)[0])
            spellRange = int(re.findall(r'\d+', self.spells[spell][1]['range'])[0]) + area
            turnInfo[spell] = [avgDmg, spellRange, self.spells[spell][0]]
            ##print(spell, self.spells[spell][0],  spellRange)
            if avgDmg >= maxDmg:
                maxDmg = avgDmg
            spellDmg += avgDmg
        ##print(maxDmg)
        
        meleeMaxDmg = 0
        rangedMaxDmg = 0
        weaponChoices = {}
        for weap in self.weaponList:
            avgDmg = 0
            if weap.name in self.multiAttack.keys():
                attackTimes = self.multiAttack[weap.name]
            else:
                attackTimes = 1
            dice = weap.diceType
            diceCount = weap.diceCount
            for di in dice:
                    diceCount = weap.diceCount[weap.diceType.index(di)]
                    avgDmg +=  attackTimes * (0.5 + weap.dmgMod + diceCount * di / 2 )
            match weap.attackType:
                case 'Ranged':
                    if avgDmg >= rangedMaxDmg:
                        rangedMaxDmg = avgDmg
                        weaponChoices[weap.name] = rangedMaxDmg
                case 'Melee':
                    if avgDmg >= meleeMaxDmg:
                        meleeMaxDmg = avgDmg
                        weaponChoices[weap.name] = meleeMaxDmg
            turnInfo[weap.name] = [avgDmg, weap.range, 9999]
        ##print(turnInfo)
        moreInfo = []
        for turn in turnInfo.keys():
            turns = turnInfo[turn][2]
            turnRange = turnInfo[turn][1]
            turnDmg = turnInfo[turn][0]
            if turns >= 10:
                turn = 10
            tenTurnDmg = turns*turnDmg
            moreInfo.append([tenTurnDmg, turnRange])
        totalDmg = sum([x[0] for x in moreInfo])
        optimalRange = 0
        for info in moreInfo:
            rangeFactor = (info[0]/totalDmg)*info[1]
            optimalRange += rangeFactor
        self.optRange = int(optimalRange/5)
        #print(self.optRange)

        return {'Melee': meleeMaxDmg, 'Ranged': rangedMaxDmg, 'Ranged Spell': maxDmg}
    
    def defineSpellSlots(self):
        '''' checked
        defines spellslots based on inputs.
            can be used to reset used spellslots

        '''
        self.spells = self.initSpells
        self.turnFactors = self.initTF
        self.legActions = self.maxLegActions
        self.alive = 1
        #self.initialTotalSlots = sum(self.spellSlots.values())
    
    def takeLegAction(self, m):
        ''' double checked
        Turn decider function for legendary action
        '''
        map = m
        if self in map.enemy:
            enemyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.enemy]
        
        if self in map.party:
            enemyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.party]
        
        myIndex = [list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] == self][0]
        #print(list(map.arrayCenters)[myIndex])
        closest = 999
        distance = []
        for index in enemyList:
            dist = map.distanceCalc(myIndex, index)
            distance.append(dist)
            if dist <= closest:
                closest = dist
                toAttack = map.arrayCenters[list(map.arrayCenters)[index]]

        minDist = min(distance)
        target = map.arrayCenters[list(map.arrayCenters)[enemyList[distance.index(minDist)]]]
        
        maxDmg = 0
        attackTimes = 1
        for weap in self.legActionWeapon:
            avgDmg = 0
            ##print(int((int(weap.range) + int(self.speed))/5), minDist)
            if int(minDist) > int((int(weap.range) )/5):
               
                ##print('not within range')
                continue
           
            
            
            dice = weap.diceType
            diceCount = weap.diceCount
            for di in dice:
                    diceCount = weap.diceCount[weap.diceType.index(di)]
                    ##print(diceCount)
                    avgDmg +=  attackTimes * (0.5 + weap.dmgMod + diceCount * di / 2 )
            if maxDmg < avgDmg:
                maxDmg = avgDmg
                attackWith = weap
        if maxDmg == 0:
            return
        rollToHit = [x + int(attackWith.attackMod) for x in rollDice(attackTimes, 20) ]
        ##print(rollToHit)
        ##print(target.name, target.ac)
        hits = sum([1 for x in rollToHit if x >= int(target.ac)])
        ##print(hits)
        #dmg = sum(rollDice(hits*int(weap.diceCount), int(weap.diceType))) 
        dmg = sum([rollDice(hits*int(attackWith.diceCount[i]), int(attackWith.diceType[i])) for i in range(len(attackWith.diceType))][0]) + hits*int(attackWith.dmgMod)
        ##print(dmg)
        ##print(target.health)
        #target.health -= dmg
        
        takeDmg(self, target, dmg, map)
        self.legActions -= 1
        ##print(self.name,'is doing a weapon attack and is doing', dmg, 'to', target.name, 'and they are now at', target.health)

        
        

class MonsterDump:
    def __init__(self, obj, path):
        
        try:
            with open(path + "monsters.json", "r") as file:
                monsters = json.load(file)
        except FileNotFoundError:
            #print('path filed to load characters')
            pass
        #print(monsters)
        newList = []
        for weap in obj.weaponList:
            newList.append(weap.__dict__)
        legList = []
        for weap in obj.legActionWeapon:
            legList.append(weap.__dict__)

        obj.weaponList = newList
        obj.legActionWeapon = legList
        jsonObj = json.dumps(obj.__dict__)
        test = json.loads(jsonObj)
        del test["maxLegActions"]
        del test["initTF"]
        del test["initSpells"]
        del test["cc"]
        del test["initMod"]
        del test["spellDC"]
        del test["maxLegRes"]
        test["legActions"] = [test["legActions"], test["legActionWeapon"]]
        del test["legActionWeapon"]
        del test['reaction']
        del test['optRange']
        
        name = test['name']
        del test['name']
        monsters[name] = test
        
        with open(path + "monsters.json", "w") as file:
            json.dump(monsters, file, indent = 4)
        

def createMonsterList(nameList, path):

    try:
        with open(path + "monsters.json", "r") as file:
            monsters = json.load(file)
    except FileNotFoundError:
        #print('path filed to load characters')
        pass

    monsterList = [Monster(name = name,
                           ac= monsters[name]['ac'],
                           health=monsters[name]['health'],
                           speed=monsters[name]['speed'],
                           modDict=monsters[name]['modDict'],
                           weaponList= [  
                               WeaponNew(name = x['name'],
                                         attackType=x["attackType"],
                                         range=x['range'],
                                         attackMod=x['attackMod'],
                                         diceType=x['diceType'],
                                         diceCount=x['diceCount'],
                                         dmgMod=x['dmgMod']
                                         )
                               for x in monsters[name]['weaponList']],
                            turnFactors=  monsters[name]['turnFactors'],
                            size = monsters[name]['size'],
                            spells = monsters[name]['spells'],
                            multiAttack=monsters[name]['multiAttack'],
                            spellMod=monsters[name]['spellAttackMod'],
                            legRes=monsters[name]['legRes'],
                            legAction=[
                                monsters[name]['legActions'][0],
                                [
                                    WeaponNew(
                                        name = x['name'],
                                         attackType=x["attackType"],
                                         range=x['range'],
                                         attackMod=x['attackMod'],
                                         diceType=x['diceType'],
                                         diceCount=x['diceCount'],
                                         dmgMod=x['dmgMod']
                                    )
                                    for x in monsters[name]['legActions'][1]
                                ]       
                                       ]



    ) 
    for name in nameList if name in list(monsters.keys())]
    return monsterList