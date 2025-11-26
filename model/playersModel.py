import random as r
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
from modelMethods import down_round, weibull, cone, WeaponNew, col_round

class Player:
    def __init__(self, name, lvl, ac, health, modDict, turnFactors, weaponList, type):
        self.name = name
        self.lvl = int(lvl)
        self.ac = int(ac)
        self.health = int(health)
        self.maxHealth = int(health)
        for key in list(modDict.keys()):
            modDict[key] = int(modDict[key])
        self.modDict = modDict
        self.weaponList = weaponList
        for key in list(turnFactors.keys()):
            turnFactors[key] = float(turnFactors[key])
        self.turnFactors = turnFactors
        self.DnDclass = type
        self.size = 25
        self.defineSpellSlots()
        self.cc = [] # if cc'ed will be length 3 and in format ['spellLvl', 'modToRoll', dcToBeat]
        self.initMod = down_round((self.modDict['Dexterity']-10)/2)
        self.legRes = 0
        self.maxLegRes = 0
        self.speed = 30 
        self.reaction = 1
        self.deathSaves = {'pass': [], 'fail': []}
        self.status = []
        self.legActions = 0
        self.maxLegActions = 0
        self.legActionWeapon = ''
        # find character proficiency
        if self.lvl >= 1:
            self.proficiency = 2
        if self.lvl >= 5:
            self.proficiency = 3
        if self.lvl >= 9:
            self.proficiency = 4
        if self.lvl >= 13:
            self.proficiency = 5
        if self.lvl >= 17:
            self.proficiency = 6
        
        charCasters = ['Paladin','Warlock','Bard','Sorceror']
        intCasters = ['Wizard']
        wisCasters = ['Cleric','Druid', 'Ranger']

        if self.DnDclass in charCasters:
            self.spellAttackMod = self.proficiency + down_round((self.modDict['Charisma']-10)/2)
            
        if self.DnDclass in intCasters:
            self.spellAttackMod = self.proficiency + down_round((self.modDict['Intelligence']-10)/2)
        if self.DnDclass in wisCasters:
            self.spellAttackMod = self.proficiency + down_round((self.modDict['Wisdom']-10)/2)
        else:
            self.spellAttackMod = 0
        self.spellDC = 8 + self.spellAttackMod
        with open(dmSimPath + "\\spells\\spellList.json", "r") as file:
            spellList = json.load(file)
        self.spells = {}
        for spell in spellList:
            if spellList[spell]['lvl'] <= self.highestSpell and self.DnDclass in spellList[spell]['classes']:
                self.spells[spell] = spellList[spell]

        self.AvgdmgCalc()

    def rollDeathSave(self):

        roll = self.rollDice(1, 20)[0]
        if roll <= 10:
            #print(self.name, 'failed death save with ', roll)
            if roll == 1:
                self.deathSaves['fail'].append(2)    
            self.deathSaves['fail'].append(1)
        else:
            if roll == 20:
                self.deathSaves['pass'].append(3)    
                self.health = 1
                self.deathSaves = {'pass':[], 'fail':[]}
            self.deathSaves['pass'].append(1)
            #print(self.name, 'passed death save with ', roll)
        
        # scores
        fails = sum(self.deathSaves['fail'])
        passes = sum(self.deathSaves['pass'])
        #if fails >= 3:
        #    #print(self.name, 'is dead with', fails, 'fails')
        if passes >= 3 and roll != 20:
            self.health = 1
            self.status.append('unconscious')
            #print(self.name, 'passed death saves')
        #print(self.deathSaves)

    def AvgdmgCalc(self):
        dmgTypes = ['Acid', 'Bludgeoning', 'Cold', 'Fire', 'Force', 'Lightning', 'Necrotic', 'Piercing', 'Poison', 'Psychic', 'Radiant', 'Slashing', 'Thunder']
        conditionsList = ['Blinded','Charmed','Deafened', 'Frightened','Grappled','Incapacitated','Invisible','Paralyzed','Petrified','Poisoned','Prone','Restrained', 'Stunned','Unconscious','Exhausted']
        spellDmg = 0
        maxDmg = 0
        ##print(self.spells)
        ##print(self.name)
        #return
        turnInfo = {}
        for spell in self.spells.keys():
            avgDmg = 0
            dice = self.spells[spell]['dice']
            effect = self.spells[spell]['effect']
            area = self.spells[spell]['area']
            if self.spells[spell]['combat'] != 'y':
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
            area = self.spells[spell]['area']
            if area == '':
                area = 0
            else:
                area = int(re.findall(r'\d+', area)[0])
           
            spellRange = int(re.findall(r'\d+', self.spells[spell]['range'])[0]) + area
            turnInfo[spell] = [avgDmg, spellRange, self.spellSlots[str(self.spells[spell]['lvl'])]]
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
            ##print(weap)
            attackTimes = 1 + self.twoAttacks
            dice = weap.diceType
            diceCount = weap.diceCount
            dice = int(re.findall(r'\d+',weap.diceType)[0])
            diceCount = weap.diceCount
            ##print(dice)
            
            avgDmg +=  attackTimes * (0.5 + weap.dmgMod + diceCount * dice / 2 )
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
            ##print(turn)
            turns = turnInfo[turn][2]
            turnRange = turnInfo[turn][1]
            turnDmg = turnInfo[turn][0]
            if turns >= 10:
                turns = 10
            tenTurnDmg = turns*turnDmg
            moreInfo.append([tenTurnDmg, turnRange, turn])
        totalDmg = sum([x[0] for x in moreInfo])
        optimalRange = 0
        for info in moreInfo:
            rangeFactor = (info[0]/totalDmg)*info[1]
            ##print(info[2], rangeFactor, info[1])
            optimalRange += rangeFactor
        self.optRange = int(optimalRange/5)
        ##print(self.optRange)

        return self.optRange #{'Melee': meleeMaxDmg, 'Ranged': rangedMaxDmg, 'Ranged Spell': maxDmg}
    

    def defineSpellSlots(self):
        ''''
        defines spellslots based on lvl.
            can be used to reset used spellslots

            making generic based on class
        '''
        fullCaster = ['Druid','Cleric','Sorceror','Wizard', 'Bard','Warlock'] # dont know if warlock should be here
        halfCaster = ['Ranger','Paladin', 'Artificer']
        self.twoAttacks = 1
        if self.DnDclass in fullCaster or self.lvl <= 4:
            self.twoAttacks = 0
        lvl = self.lvl
        self.spellSlots = {
            '0':99999,
            '1':0,
            '2':0,
            '3':0,
            '4':0,
            '5':0,
            '6':0,
            '7':0,
            '8':0,
            '9':0
        }
        if self.DnDclass in halfCaster:
            ##print(self.name, 'is restoring spell slots as a halfCaster')
            if lvl >= 2:
                self.spellSlots['1'] = 2
            if lvl >= 3:
                self.spellSlots['1'] = 3
            if lvl >= 5:
                self.spellSlots['1'] = 4
                self.spellSlots['2'] = 2
            if lvl >= 7:
                self.spellSlots['2'] = 3
            if lvl >= 9:
                self.spellSlots['3'] = 2
            if lvl >= 11:
                self.spellSlots['3'] = 3
            if lvl >= 13:
                self.spellSlots['4'] = 1
            if lvl >= 15:
                self.spellSlots['4'] = 2
            if lvl >= 17:
                self.spellSlots['4'] = 3
                self.spellSlots['5'] = 1
            if lvl >= 19:
                self.spellSlots['5'] = 2

        if self.DnDclass in fullCaster:
            ##print(self.name, 'is restoring spell slots as a fullCaster')
            if lvl >= 1:
                self.spellSlots['1'] = 2
            if lvl >= 2:
                self.spellSlots['1'] = 3
            if lvl >= 3:
                self.spellSlots['1'] = 4
                self.spellSlots['2'] = 2
            if lvl >= 4:
                self.spellSlots['2'] = 3
            if lvl >= 5:
                self.spellSlots['3'] = 2
            if lvl >= 6:
                self.spellSlots['3'] = 3
            if lvl >= 7:
                self.spellSlots['4'] = 1
            if lvl >= 8:
                self.spellSlots['4'] = 2
            if lvl >= 9:
                self.spellSlots['4'] = 3
                self.spellSlots['5'] = 1
            if lvl >= 10:
                self.spellSlots['5'] = 2
            if lvl >= 11:
                self.spellSlots['6'] = 1
            if lvl >= 13:
                self.spellSlots['7'] = 1
            if lvl >= 15:
                self.spellSlots['8'] = 1
            if lvl >= 17:
                self.spellSlots['9'] = 1
            if lvl >= 18:
                self.spellSlots['5'] = 3
            if lvl >= 19:
                self.spellSlots['6'] = 2
            if lvl >= 20:
                self.spellSlots['7'] = 2

        self.initialTotalSlots = sum(self.spellSlots.values())

        self.highestSpell = 0
        for index in range(len(list(self.spellSlots))):
            if self.spellSlots[list(self.spellSlots)[index]] > 0:
                if index +1 >= self.highestSpell:
                    self.highestSpell = index +1


    def takeReaction(self, m, target):
       
        map = m
        
        
        myIndex = [list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] == self][0]
        targetIndex = [list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] == target][0]
        minDist = map.distanceCalc(myIndex, targetIndex)
        

        
        #map.moveToNearest(self, closestGuy)
        
        ##print(closestGuy)
        ##print(self.weaponList)
        maxDmg = 0
        attackWith = self.weaponList[0]
        attackTimes = 1
        #print(self.weaponList)
        for weap in self.weaponList:
            avgDmg = 0
            ##print(int((int(weap.range) + int(self.speed))/5), minDist)
            if int(minDist) > int(weap.range)/5:
                
                ##print('not within range')
                continue
            
            
            dice = int(re.findall(r'\d+',weap.diceType)[0])
            diceCount = weap.diceCount
            ##print(dice)
            
            avgDmg +=  attackTimes * (0.5 + weap.dmgMod + diceCount * dice / 2 )
            if avgDmg > maxDmg:
                maxDmg = avgDmg
                attackWith = weap
        
        if maxDmg == 0:
            return
        rollToHit = [x + int(attackWith.attackMod) + int(self.proficiency) for x in self.rollDice(attackTimes, 20) ]
        ##print(rollToHit)
        ##print(target.name, target.ac)
        hits = []
        for roll in rollToHit:
            if roll >= int(target.ac):
                if roll == 20 + int(self.proficiency):
                    hits.append(2)
                else:
                    hits.append(1)
        #hits = [1 for x in rollToHit if x >= int(target.ac)]
        ##print(hits)
        #dmg = sum(self.rollDice(hits*int(weap.diceCount), int(weap.diceType))) 
        dmg = 0
        for hit in hits:
            dmg += self.rollDice(int(attackWith.diceCount), int(int(re.findall(r'\d+', attackWith.diceType)[0])))[0] + int(attackWith.dmgMod)
            if hit == 2:
                dmg += self.rollDice(int(attackWith.diceCount), int(int(re.findall(r'\d+', attackWith.diceType)[0])))[0] 
        #dmg = sum([self.rollDice(hits*int(weap.diceCount), int(int(re.findall(r'\d+', weap.diceType)[0])))][0]) + hits*int(weap.dmgMod)
        ##print(dmg)
        ##print(target.health)
        dmg += self.classMeleeDmg(hits, dmg)
        target.health -= dmg
        self.reaction = 0
        #print(self.name,'is doing a weapon attack and is doing', dmg, 'to', target.name, 'and they are now at', target.health)
        
    def takeTurn(self, m):
        '''
        Turn decidider function... take enemyList and decide what to do for the turn
            based on self.turnFactors
        '''
        
        global map
        map = m
        if 'deathSaves' in self.status:
            self.rollDeathSave()
            if self.deathSaves['fail'] >= 3:
                #print(self.name, 'is dead')


        self.reaction = 1
        if self in map.enemy:
            enemyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.enemy]
        
        if self in map.party:
            enemyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.party]
        
        myIndex = [list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] == self][0]
        ##print(list(map.arrayCenters)[myIndex])
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
        #neighbors = map.neighbors(closestCoord)
        #openNeighbors = [x for x in neighbors if map.arrayCetners(list(map.arrayCenters)[x]) == '']
        closestIndex = list(map.arrayCenters).index(closestCoord[0])
        distanceMatrix = [(map.distanceCalc(myIndex, index), map.distanceCalc(closestIndex, index)) for index in range(len(list(map.arrayCenters))) if map.arrayCenters[list(map.arrayCenters)[index]] == '']
        #map.moveToNearest(self, closestGuy)
        
        ##print(closestGuy)
        ##print(self.weaponList)
        turnChoices = []
        attackTimes = 1 + self.twoAttacks
        for weap in self.weaponList:
            avgDmg = 0
            ##print(int((int(weap.range) + int(self.speed))/5), minDist)
            if int(minDist) > int((int(weap.range) + int(self.speed))/5):
                
                turnChoices.append([weap.name, 'Wdmg', avgDmg])
                ##print('not within range')
                continue
            anyOpenSpot = [x for x in distanceMatrix if x[0] <= self.speed/5 and x[1] <= int(weap.range)/5] 
            if len(anyOpenSpot) == 0:
                turnChoices.append([weap.name, 'Wdmg', avgDmg])
                #sys.exit()
                ##print('not within range')
                continue
            dice = int(re.findall(r'\d+',weap.diceType)[0])
            diceCount = weap.diceCount
            ##print(dice)
            
            avgDmg +=  attackTimes * (0.5 + weap.dmgMod + diceCount * dice / 2 )
            turnChoices.append([weap.name, 'Wdmg', avgDmg])
        #map.moveToNearest(self, toAttack)
        
        conditionsList = ['Blinded','Charmed','Deafened', 'Frightened','Grappled','Incapacitated','Invisible','Paralyzed','Petrified','Poisoned','Prone','Restrained', 'Stunned','Unconscious','Exhausted']
        dmgTypes = ['Acid', 'Bludgeoning', 'Cold', 'Fire', 'Force', 'Lightning', 'Necrotic', 'Piercing', 'Poison', 'Psychic', 'Radiant', 'Slashing', 'Thunder']
        for spell in self.spells.keys():
            ##print(spell, self.spellSlots[str(self.spells[spell]['lvl'])])
            if self.spells[spell]['combat'] == 'n' or 0 >= self.spellSlots[str(self.spells[spell]['lvl'])] or self.spells[spell]['time'] != "1 Action":
                ##print(spell)
                continue
            avgDmg = 0
            if self.spells[spell]['area'] != '':
                match self.spells[spell]['area']:
                    case str(x) if 'sphere' in x:
                        numToHit = self.bestSphere(map, int(re.findall(r'\d+', self.spells[spell]['area'])[0]), int(re.findall(r'\d+', self.spells[spell]['range'])[0]))
                       
                        ##print(spell, numToHit)
                    case str(x) if 'cone' in x:
                        numToHit = self.bestCone(map, int(re.findall(r'\d+', self.spells[spell]['area'])[0]), int(re.findall(r'\d+', self.spells[spell]['range'])[0]))
                        ##print(spell, numToHit)

                    case str(x) if 'line' in x:
                        numToHit = self.bestLine2(map, int(re.findall(r'\d+', self.spells[spell]['area'])[0]), int(re.findall(r'\d+', self.spells[spell]['range'])[0]))
                        ##print(spell, numToHit)
                        #numToHit = (0,0) # suck and need to find a better way to estimate and not just properly count how many I hit
                    case str(x) if 'square' in x:
                        numToHit = self.bestSquare(map, int(re.findall(r'\d+', self.spells[spell]['area'])[0]), int(re.findall(r'\d+', self.spells[spell]['range'])[0]))
                        ##print(spell, numToHit)
                #
                ##print(spell, numToHit)
                if self.spells[spell]['effect'] in dmgTypes:
                    dice = self.spells[spell]['dice']
                    for di in dice:
                        diceCount = int(re.findall(r'\d+', di)[0])
                        diceDmg = int(re.findall(r'\d+', di)[1])
                        avgDmg += 0.5 + diceCount * diceDmg / 2
                    turnChoices.append([spell, 'Sdmg', avgDmg*numToHit[0], numToHit])
                elif self.spells[spell]['effect'] in conditionsList:
                    turnChoices.append([spell, 'cc', numToHit[0]*20, numToHit])
            else:
                hexLimit = (int(re.findall(r'\d+', self.spells[spell]['range'])[0])/5) +self.speed/5
                distance = [index for index in enemyList if map.distanceCalc(myIndex, index) <= hexLimit]
                anyOpenSpot = [x for x in distanceMatrix if x[0] <= self.speed/5 and x[1] <= int(re.findall(r'\d+', self.spells[spell]['range'])[0])/5] 
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
                elif self.spells[spell]['effect'] in dmgTypes:
                    dice = self.spells[spell]['dice']
                    for di in dice:
                        diceCount = int(re.findall(r'\d+', di)[0])
                        diceDmg = int(re.findall(r'\d+', di)[1])
                        avgDmg += 0.5 + diceCount * diceDmg / 2
                    ##print(spell, numToHit)
                    turnChoices.append([spell, 'Sdmg', avgDmg, (1,list(map.arrayCenters)[myIndex], list(map.arrayCenters)[myIndex], closestCoord)])
                elif self.spells[spell]['effect'] in conditionsList:
                    turnChoices.append([spell, 'cc', 1, 
                                        (1,list(map.arrayCenters)[myIndex], list(map.arrayCenters)[myIndex], closestCoord)])
        best = 0
        ##print(turnChoices)
        for choice in turnChoices:
            ##print(choice)
            if float(choice[2]) >= float(best):
                best = choice[2]
                turnChoice = choice
        if best == 0:
            map.dashActor(self, closestGuy)
            #print('dashing')
            return
        else:
            #print(turnChoice)
        #turnChoice = ['Tentacle', 'Wdmg']
        #turnChoice = [x for x in turnChoices if x[0] == 'Fear'][0]
        if turnChoice[1] == 'Wdmg':
            weaponChoice = [x for x in self.weaponList if x.name == turnChoice[0]][0]
            #print(weaponChoice.range)
            if weaponChoice.range/5 >= self.optRange:
                if minDist >= self.optRange + self.speed/5:
                    selfCoord = [x for x in map.arrayCenters.keys() if map.arrayCenters[x] == self][0]
                    line = self.drawLine(selfCoord, closestCoord[0])
                    options = [x for x in line if map.distanceCalc(list(map.arrayCenters).index(selfCoord), list(map.arrayCenters).index(x)) <= self.speed/5]
                    distance = map.distanceCalc(list(map.arrayCenters).index(selfCoord), list(map.arrayCenters).index(options[-1]))
                    if map.arrayCenters[options[-1]] != '' and map.arrayCenters[options[-1]] != self:
                        newCoord = map.moveToNearest(self, map.arrayCenters[options[-1]])
                    else:
                        map.moveActor(self, options[-1])
                else:
                    #print('moved here')
                    self.moveWithingReach(closestGuy, self.optRange*5, map)
            else:
                #print('moved there')
                self.moveWithingReach(closestGuy, weaponChoice.range, map)
            self.weaponAttack(closestGuy, weaponChoice)
        if turnChoice[1] == 'Sdmg' or turnChoice[1] == 'cc':
            self.castSpellTurn(turnChoice)
    
    def takeDmg(self, actor, dmg, map):
        #print(actor.name, 'is doing ', dmg, 'to', self.name)
        if 'deathSaves' in self.status:
            self.deathSaves['fail'].append(1)
            return
        self.health += dmg

        if self.health <= 0:
            #print(self.name, 'is down')
            if 'deathSaves' not in self.state:
                self.state.append('deathSaves')
    def castSpellTurn(self, turnChoice):

        
        ##print(turnChoice)
        selfCoord = [x for x in map.arrayCenters.keys() if map.arrayCenters[x] == self][0]
        ##print('Moving to', turnChoice[3][1])
        #map.arrayCenters[selfCoord] = ''
        #map.arrayCenters[turnChoice[3][1]] = self
        if map.arrayCenters[turnChoice[3][1]] != '' and map.arrayCenters[turnChoice[3][1]] != self:
            #print('moving to ',turnChoice[3][1])
            newCoord = map.moveToNearest(self, turnChoice[3][1])
            map.moveActor(self, newCoord)
        else:
            map.moveActor(self, turnChoice[3][1])
        peopleTargeted = [map.arrayCenters[x] for x in turnChoice[3][3] if map.arrayCenters[x] != '']
        ##print('in player castSpellTurn')
        ##print(peopleTargeted)
        spell = self.spells[turnChoice[0]]
        ##print(spell)
        #self.spells[turnChoice[0]][0] -= 1
        self.spellSlots[str(self.spells[turnChoice[0]]['lvl'])] -= 1
        save = spell['save'].split()
        ##print(save)
        ##print(self.modDict)
        if spell['attack'] == '' and save != []: # youre a save effect
            peopleHit = [x for x in peopleTargeted if x.rollSave(save[0], self.spellDC)]
        else: # spell attack
            reachLimit = (int(re.findall(r'\d+', self.spells[turnChoice[0]]['range'])[0])) 
            ##print('/n/n/t/t/tin spell attack')
            if reachLimit >= self.optRange:
                self.moveWithingReach(peopleTargeted[0], self.optRange, map)
            else:
                self.moveWithingReach(peopleTargeted[0], reachLimit, map)
            hitRoll = self.rollDice(1,20)[0] + int(self.spellAttackMod)
            ##print(hitRoll)
            peopleHit = [x for x in peopleTargeted if hitRoll >= x.ac]
        
        ##print(peopleHit)
        dice = spell['dice']
        ##print(dice)
        dmg = 0
        if dice[0] != '':
            for di in dice:
                diceCount = int(re.findall(r'\d+', di)[0])
                
                diceDmg = int(re.findall(r'\d+', di)[1])
                dmg += sum(self.rollDice(diceCount, diceDmg))
            ##print(dmg)

        if spell['area'] != '' and dmg > 0:
            for people in peopleTargeted:
                #print(people.name, people.health)
                if people in peopleHit:
                    #print(people.name, 'is getting hit for', dmg, 'by spell', turnChoice[0])
                    people.health -= dmg
                else:
                    #print(people.name, 'is getting hit for', dmg/2, 'by spell', turnChoice[0])
                    people.health -= col_round(dmg/2)
                #print(people.name, people.health)
        elif dmg > 0 :
            for people in peopleHit:
                #print(people.name, 'is getting hit for', dmg, 'by spell', turnChoice[0])
                people.health -= dmg
                #print(people.name, people.health)
        
        if turnChoice[1] == 'cc':
            for people in peopleHit:
                people.cc = [spell["lvl"], save, self.spellDC]
                #print(people.name, 'are now cced with', turnChoice[0], people.cc)
    
    def rollSave(self, abilityType, dc):
        '''
        roll a saving throw

        true if failed
        '''
        roll = r.randint(1,20) # initial roll
        ##print(' in player rollSave')
        ##print(abilityType)
        ##print(dc)
        #print(down_round((self.modDict[abilityType]- 10)/2))
        roll += down_round((self.modDict[abilityType]- 10)/2) # add modifier
        #print(roll,'vs', dc)
        # return true false 
        ##print('\t\t\t Roll:',roll,'vs DC:', dc)
        return roll < dc

    def weaponAttack(self, target, weap):
        #map.#printCurrMap()
        myIndex = [list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] == self][0]
        targetIndex = [list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] == target][0]
        targDistance = map.distanceCalc(myIndex, targetIndex)
        if targDistance > weap.range/5:
            #print(self.name,'out of range to hit',target.name,'with',weap.name,'...',targDistance,'..',weap.range/5)
            sys.exit()
        numAttack = self.twoAttacks + 1
        ##print(numAttack)
        rollToHit = [x + int(weap.attackMod) + int(self.proficiency) for x in self.rollDice(numAttack, 20) ]
        ##print(rollToHit)
        ##print(target.name, target.ac)
        hits = []
        for roll in rollToHit:
            if roll >= int(target.ac):
                if roll == 20 + int(self.proficiency):
                    hits.append(2)
                else:
                    hits.append(1)
        #hits = [1 for x in rollToHit if x >= int(target.ac)]
        ##print(hits)
        #dmg = sum(self.rollDice(hits*int(weap.diceCount), int(weap.diceType))) 
        dmg = 0
        for hit in hits:
            dmg += self.rollDice(int(weap.diceCount), int(int(re.findall(r'\d+', weap.diceType)[0])))[0] + int(weap.dmgMod)
            if hit == 2:
                dmg += self.rollDice(int(weap.diceCount), int(int(re.findall(r'\d+', weap.diceType)[0])))[0] 
        #dmg = sum([self.rollDice(hits*int(weap.diceCount), int(int(re.findall(r'\d+', weap.diceType)[0])))][0]) + hits*int(weap.dmgMod)
        ##print(dmg)
        ##print(target.health)
        dmg += self.classMeleeDmg(hits, dmg)
        target.health -= dmg
        #print(self.name,'is doing a weapon attack and is doing', dmg, 'to', target.name, 'and they are now at', target.health)
        ##print(target.health)

    def classMeleeDmg(self, hits, dmg):
        fullCaster = ['Druid','Cleric','Sorceror','Wizard', 'Bard','Warlock'] # dont know if warlock should be here
        if sum(hits) == 0 or self.DnDclass in fullCaster:
            return 0
        oncePerTurn = 1
        startDmg = dmg
        for hit in hits:
            if hits == 2:
                crit = 2
            else:
                crit = 1
            if self.DnDclass == 'Ranger' and oncePerTurn:
                if self.lvl >= 11:
                    dmg += sum(self.rollDice(2*crit, 8))
                elif self.lvl >= 3:
                    dmg += sum(self.rollDice(1*crit, 8))
                oncePerTurn = 0
            
            if self.DnDclass == 'Paladin' and self.lvl >= 2:
                highestSpell = 0
                for index in range(len(list(self.spellSlots))):
                    if self.spellSlots[list(self.spellSlots)[index]] > 0:
                        if index +1 >= highestSpell:
                            highestSpell = index +1
                dmg += sum(self.rollDice(crit*(highestSpell+1), 8))
        #print(self.name, 'is doing', dmg - startDmg, 'extra dmg because of class ability')
        return dmg
    def rollDice(self, n, diceType):
        
        rolls = []
        for i in range(n):
            rolls.append(r.randint(1,diceType))
        return rolls

    def moveWithingReach(self, target, reach, map):
        selfCoord = [x for x in map.arrayCenters.keys() if map.arrayCenters[x] == self][0]
        targetCoord = [x for x in map.arrayCenters.keys() if map.arrayCenters[x] == target][0]
        ##print(selfCoord, targetCoord)
        ##print('player moveWithinReach')
        hexLimit = reach/5
        dist = map.distanceCalc(list(map.arrayCenters).index(targetCoord), list(map.arrayCenters).index(selfCoord))
        ##print(dist)
        if dist <= hexLimit:
            return
        line = self.drawLine(selfCoord,targetCoord)
        ##print(line)
        hexLimit = reach/5
        moveTo = [coord for coord in line if map.distanceCalc(list(map.arrayCenters).index(targetCoord), list(map.arrayCenters).index(coord)) <= hexLimit][0] # closest inside reach
        if map.arrayCenters[moveTo] != '':
            map.moveToNearest(self, target)
        else:
            map.moveActor(self, moveTo)
        ##print(selfCoord)
        ##print(target.name)
        ##print(moveTo)

    def bestSphere(self, map, radius, reach):
        reachLimit = reach/5
        setRatio = 4
        hexLimit = radius/5
        selfCoord = [x for x in map.arrayCenters.keys() if map.arrayCenters[x] == self][0]
        if self in map.enemy:
            enemyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.enemy]
            partyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.party]
        if self in map.party:
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
                

                if sumAllies == 0 and sumEnemies == desired: # simple case
                    enemiesHit = [list(map.arrayCenters)[coord] for coord in enemyList if map.distanceCalc(coord, i)<= hexLimit]
                    partyHit = [list(map.arrayCenters)[coord] for coord in partyList if map.distanceCalc(coord, i)<= hexLimit]
                    totalHit = enemiesHit + partyHit
                    
                    return (desired, selfCoord, list(map.arrayCenters)[i], totalHit)
                if sumAllies == 0 and sumEnemies < desired:
                    continue
                if sumAllies != 0 and sumEnemies/sumAllies >= setRatio:
                    enemiesHit = [list(map.arrayCenters)[coord] for coord in enemyList if map.distanceCalc(coord, i) <= hexLimit]
                    partyHit = [list(map.arrayCenters)[coord] for coord in partyList if map.distanceCalc(coord, i) <= hexLimit]
                    totalHit = enemiesHit + partyHit
                    return (sumEnemies, selfCoord, list(map.arrayCenters)[i], totalHit)

            desired -= 1
            if desired == 0:
                return (0,0)
    
    def bestLine(self, map, length, reach):
        ##print('bestLine')
        setRatio = 4
        
        mapKeys = map.arrayCenters.keys()
        selfCoord = [x for x in map.arrayCenters.keys() if map.arrayCenters[x] == self][0]
        ##print(reach)
        moveLimit =  reach + self.speed/5
        myIndex = list(map.arrayCenters).index(selfCoord)
        movementCoords = [ coord for coord in map.arrayCenters.keys() if map.distanceCalc(myIndex, list(map.arrayCenters).index(coord)) <= moveLimit and map.arrayCenters[coord] == '']
        hexLimit = int(length/5)
        
        if self in map.enemy:
            enemyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.enemy]
            partyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.party]
        if self in map.party:
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
                line = self.drawLine(coord, moveCoord)
                sumEnemies =  sum([1 for badGuy in enemyList if list(map.arrayCenters)[badGuy] in line])
                if sumEnemies >> maxHit:
                    maxHit = sumEnemies
            finalList.append((moveCoord,maxHit))
        ##print(finalList)
        maxEnemies = max([x[1] for x in finalList])
        end = time.time()
        #print('For loop', end - start)
        return maxEnemies
        
    def bestLine2(self, map, length, reach):
        
        startTime = time.time()
        #setRatio = 4
        
        #mapKeys = map.arrayCenters.keys()
        selfCoord = [x for x in map.arrayCenters.keys() if map.arrayCenters[x] == self][0]
        ##print(reach)
        moveLimit =  reach + self.speed/5
        myIndex = list(map.arrayCenters).index(selfCoord)
        movementCoords = [ coord for coord in map.arrayCenters.keys() if map.distanceCalc(myIndex, list(map.arrayCenters).index(coord)) <= moveLimit and map.arrayCenters[coord] == '']
        hexLimit = int(length/5)
        
        if self in map.enemy:
            enemyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.enemy]
            #partyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.party]
        if self in map.party:
            enemyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.party]
            #partyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.enemy]
        if len(enemyList) == 1:
            enemyDist = map.distanceCalc(myIndex, enemyList[0])
            if enemyDist > moveLimit + hexLimit:
                return(0,0)
            targetCoord = list(map.arrayCenters)[enemyList[0]]
            line = self.drawLine(selfCoord,targetCoord)
            ##print(line)
            #hexLimit = reach/5
            moveTo = [coord for coord in line if map.distanceCalc(list(map.arrayCenters).index(targetCoord), list(map.arrayCenters).index(coord)) <= hexLimit and map.arrayCenters[coord] == ''][0] # closest inside reach
           
            return(1, moveTo, moveTo, [targetCoord])
        
            
        test = []
        ##print('before test')
        for enemy in enemyList:
            for e2 in enemyList:
                e2Dist = map.distanceCalc(myIndex, e2)
                enemyDist = map.distanceCalc(myIndex, enemy)
                if e2 == enemy or enemyDist > moveLimit + hexLimit or e2Dist > moveLimit + hexLimit:
                    continue
                enemyCoord = list(map.arrayCenters)[enemy]
                e2Coord = list(map.arrayCenters)[e2]
                line = self.drawLine(enemyCoord, e2Coord)
                sumEnemies =  sum([1 for badGuy in enemyList if list(map.arrayCenters)[badGuy] in line])
                test.append([(sumEnemies, 0), enemyCoord, e2Coord])
        test = list({tuple(sorted(i)): i for i in test}.values())
        # #print('after test')
        test.sort()
        test.reverse()
        ##print(test)
        maxX = max([coord[0] for coord in list(map.arrayCenters)])
        maxY = max([coord[1] for coord in list(map.arrayCenters)])
        
        test = np.asarray(test)
        ##print(test2)
        #mapRing =  [coord for coord in list(map.arrayCenters) if coord[1] in (0,1, maxY-1, maxY) or coord[0] in (0,maxX)]
        testRing = np.asarray([coord for coord in list(map.arrayCenters) if coord[1] in (0,1, maxY-1, maxY) or coord[0] in (0,maxX)])
        ##print(mapRing)
        ##print(testRing)
        ##print(test)
        ##print(np.asarray(test))
        
        possibleCoords = []
        ##print('before targets',time.time()-startTime)
        for targets in test:
            #startTarget = time.time()

            possibleCoords.clear()
            firstCoord = tuple(targets[1])
            secondCoord = tuple(targets[2])
            
            maX = max(firstCoord[0], secondCoord[0])
            maY = max(firstCoord[1], secondCoord[1])
            miX = min(firstCoord[0], secondCoord[0])
            miY = min(firstCoord[1], secondCoord[1])
            for coord in testRing:
                ##print(coord)
                coord = tuple(coord)
                ##print(targets)
                
                
                if (maX, maY) in [firstCoord, secondCoord]:
                    if coord[0] < maX or coord[1] < maY :
                        continue
                elif coord[0] > miX or coord[1] < maY:
                    continue
                if coord[0] > miX and coord[0] < maX or coord[1] > miY and coord[1] < maY:
                    continue
                guys = targets[0][0]
                ##print(firstCoord)
                if firstCoord != coord:
                    ##print('before line', time.time()-startTarget)
                    line = self.drawLine(coord, firstCoord)
                    ##print(line)
                    ##print('After line', time.time()-startTarget)
                    
                    inBetweenCoords = [x for x in line  if x[0] >= miX and x[0] <= maX and x[1]>= miY and x[1] <=maY]
                    sumEnemies =  sum([1 for badGuy in enemyList if list(map.arrayCenters)[badGuy] in inBetweenCoords])
                    if secondCoord in line and sumEnemies == guys:
                        possibleCoords +=  [coord for coord in line if coord not in inBetweenCoords]
                        '''for c in line:
                            map.arrayCenters[c] = 'c'''
                if secondCoord != coord:
                    line2 = self.drawLine(coord, secondCoord)
                    inBetweenCoords = [x for x in line2  if x[0] >= miX and x[0] <= maX and x[1]>= miY and x[1] <=maY]
                    sumEnemies =  sum([1 for badGuy in enemyList if list(map.arrayCenters)[badGuy] in inBetweenCoords])
                    if firstCoord in line2 and sumEnemies == guys:
                        possibleCoords +=  [coord for coord in line2 if coord not in inBetweenCoords]
                        '''for c in line2:
                            map.arrayCenters[c] = 'c'''
                moveTo = [x for x in possibleCoords if x in movementCoords]
                if len(moveTo) != 0:
                    ##print('Found my Line')
                    ##print(moveTo)
                    badGuys =  [ list(map.arrayCenters)[badGuy]for badGuy in enemyList if list(map.arrayCenters)[badGuy] in possibleCoords]
                    finalCoord = [guys, moveTo[0], moveTo[0], badGuys]
                    EndTime = time.time()
                    #print('line took', EndTime - startTime)
                    return finalCoord
            return(0,0)        
            ##print('finished first set', time.time()-startTarget)
        
    def drawLine(self, coord1, coord2):

        dist = int(map.distanceCalc(list(map.arrayCenters).index(coord1), list(map.arrayCenters).index(coord2)))

        x1, y1 = coord1
        x2, y2 = coord2

        xDiff = x2 -x1
        yDiff = y2-y1
        ##print('start ', coord1)
        ##print('end', coord2)
        ##print(dist)
        ##print(dist)
        
        pts = np.array(list(map.arrayCenters))
        #t = time.time()
        lineCoord = np.array([(0.0,0.0) for i in range(dist +1)]) 
        for i in range(int(dist)+1):
            lineCoord[i] = [coord1[0] + i*xDiff/dist, coord1[1] + i*yDiff/dist-0.01]
        
            #lineCoord.append((coord1[0] + i*xDiff/dist, coord1[1] + i*yDiff/dist-0.01))
        snapCoord = [tuple(pts[spatial.KDTree(pts).query(coord)[1]]) for coord in lineCoord]
        ##print('array time', time.time()-t)
        '''t = time.time()
        line2 = []
        for i in range(int(dist)+1):
            ##print(i)
            
        
            line2.append((coord1[0] + i*xDiff/dist, coord1[1] + i*yDiff/dist-0.01))
        
        snapCoord2 = [tuple(pts[spatial.KDTree(pts).query(coord)[1]]) for coord in line2]
        #print('line time', time.time()-t)
        ##print(lineCoord)   
        
        
        ##print(lineCoord, '\n ^^ player line drawn')
        # calc closest point in scaled arrayCenters to mouseCenter, then set
        # starting point to those coords (used in __move_char)'''
        
        
        return snapCoord

    def bestSquare(self, map, length, reach):
        setRatio = 4
        selfCoord = [x for x in map.arrayCenters.keys() if map.arrayCenters[x] == self][0]
        moveLimit =  reach/5 + self.speed/5
        #print(reach)
        myIndex = list(map.arrayCenters).index(selfCoord)
        movementCoords = [ coord for coord in map.arrayCenters.keys() if map.distanceCalc(myIndex, list(map.arrayCenters).index(coord)) <= moveLimit and map.arrayCenters[coord] == '']
        hexLimit = int(length/5)
        ##print(hexLimit)

        if self in map.enemy:
            enemyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.enemy]
            partyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.party]
        if self in map.party:
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
                    line = self.drawLine(selfCoord, moveCoord)
                    ##print(line)
                    options = [x for x in line if map.distanceCalc(list(map.arrayCenters).index(x), list(map.arrayCenters).index(selfCoord)) <= self.speed/5 and
                            map.distanceCalc(list(map.arrayCenters).index(x), list(map.arrayCenters).index(moveCoord)) <= reach/5]
                    ##print(options)
                    return (desired, options[0], moveCoord, totalHit)
                if sumAllies == 0 and sumEnemies < desired:
                    continue
                if sumAllies != 0 and sumEnemies/sumAllies >= setRatio:
                    enemiesHit = [list(map.arrayCenters)[ind] for ind in enemyList if list(map.arrayCenters)[ind] in squareCoords]
                    partyHit = [list(map.arrayCenters)[ind] for ind in partyList if list(map.arrayCenters)[ind] in squareCoords]
                    totalHit = enemiesHit + partyHit
                    line = self.drawLine(selfCoord, moveCoord)
                    ##print(line)
                    options = [x for x in line if map.distanceCalc(list(map.arrayCenters).index(x), list(map.arrayCenters).index(selfCoord)) <= self.speed/5 and 
                            map.distanceCalc(list(map.arrayCenters).index(x), list(map.arrayCenters).index(moveCoord)) <= reach/5]
                    ##print(options)
                    return (sumEnemies, options[0], moveCoord, totalHit)
            finalList.append((moveCoord,maxHit, totalHit))
        ##print(finalList)
        onlyHits = [x[1] for x in finalList]
        maxEnemies = max(onlyHits)
        max_index = onlyHits.index(maxEnemies)
        ##print(finalList[max_index])
        line = self.drawLine(selfCoord, finalList[max_index][0])
        options = [x for x in line if map.distanceCalc(list(map.arrayCenters).index(x), list(map.arrayCenters).index(selfCoord)) <= self.speed/5 and 
                   map.distanceCalc(list(map.arrayCenters).index(x), list(map.arrayCenters).index(finalList[max_index][0])) <= reach/5]
        return (maxEnemies, options[0], finalList[max_index][0], finalList[max_index][2])
        
    
    def bestCone(self, map, length, reach):
        '''
        step 1 make a cone at all coming from self
        '''
        ##print('bestCone')
        setRatio = 4
        mapKeys = map.arrayCenters.keys()
        selfCoord = [x for x in map.arrayCenters.keys() if map.arrayCenters[x] == self][0]
        moveLimit = self.speed/5
        myIndex = list(map.arrayCenters).index(selfCoord)
        movementCoords = [ coord for coord in map.arrayCenters.keys() if map.distanceCalc(myIndex, list(map.arrayCenters).index(coord)) <= moveLimit and map.arrayCenters[coord] == '']
        hexLimit = int(length/5)
        
        if self in map.enemy:
            enemyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.enemy]
            partyList = [ list(map.arrayCenters).index(i) for i in map.arrayCenters.keys() if map.arrayCenters[i] != '' and map.arrayCenters[i] not in map.party]
        if self in map.party:
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
        ##print(selfCoord)
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

def createPartyList(nameList, path):
    '''
    Load characters.json from charcter_widget.py and create player classes
    from out put. 
    nameList is a list of characters names to be matched to characters.json
    '''
    try:
        with open(path + "characters.json", "r") as file:
            characters = json.load(file)
    except FileNotFoundError:
        #print('path filed to load characters')
        pass
    ##print(characters)
   
    partyList = [Player(name = name, 
                        lvl = int(characters[name]['Level']),
                        ac = int(characters[name]['AC']),
                        health = int(characters[name]['HP']),
                        modDict= characters[name]['AbilityModifiers'],
                        turnFactors= characters[name]['TurnFactors'],
                        weaponList= [WeaponNew(name=characters[name]['Weapons'][x][0],
                                           attackType=characters[name]['Weapons'][x][1],
                                           range=int(characters[name]['Weapons'][x][2]),
                                           attackMod=int(characters[name]['Weapons'][x][3]),
                                           diceType= characters[name]['Weapons'][x][4],
                                           diceCount= int(characters[name]['Weapons'][x][5]),
                                           dmgMod= int(characters[name]['Weapons'][x][6]))
                                           
                                           for x in range(len(characters[name]['Weapons']))], 
                        type = characters[name]['Class'])  # need to make this a variable in the json
                        
                        for name in nameList if name in list(characters.keys())]
    return partyList