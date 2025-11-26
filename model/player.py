
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
    


class Player:
    def __init__(self, name, lvl, ac, health, modDict, turnFactors, weaponList, type, Image = False):
        self.name = name
        self.lvl = int(lvl)
        self.Image = Image
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
        self.alive = 1
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
    
    def AvgdmgCalc(self):
        dmgTypes = ['Acid', 'Bludgeoning', 'Cold', 'Fire', 'Force', 'Lightning', 'Necrotic', 'Piercing', 'Poison', 'Psychic', 'Radiant', 'Slashing', 'Thunder']
        conditionsList = ['Blinded','Charmed','Deafened', 'Frightened','Grappled','Incapacitated','Invisible','Paralyzed','Petrified','Poisoned','Prone','Restrained', 'Stunned','Unconscious','Exhausted']
        spellDmg = 0
        maxDmg = 0
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

                
                ratio =  area / 25*party
                percentHit = weibull(ratio)
                totalHit = down_round(party * percentHit)
                avgDmg = totalHit * avgDmg 

            area = self.spells[spell]['area']
            if area == '':
                area = 0
            else:
                area = int(re.findall(r'\d+', area)[0])
           
            spellRange = int(re.findall(r'\d+', self.spells[spell]['range'])[0]) + area
            turnInfo[spell] = [avgDmg, spellRange, self.spellSlots[str(self.spells[spell]['lvl'])]]
            if avgDmg >= maxDmg:
                maxDmg = avgDmg
            spellDmg += avgDmg
        
        meleeMaxDmg = 0
        rangedMaxDmg = 0
        weaponChoices = {}
        for weap in self.weaponList:
            avgDmg = 0
            attackTimes = 1 + self.twoAttacks
            dice = weap.diceType
            diceCount = weap.diceCount
            dice = int(re.findall(r'\d+',weap.diceType)[0])
            diceCount = weap.diceCount
            
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
        moreInfo = []
        for turn in turnInfo.keys():
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
            optimalRange += rangeFactor
        self.optRange = int(optimalRange/5)

        return self.optRange #{'Melee': meleeMaxDmg, 'Ranged': rangedMaxDmg, 'Ranged Spell': maxDmg}
    

    def defineSpellSlots(self):
        ''''
        defines spellslots based on lvl.
            can be used to reset used spellslots

            making generic based on class

            also used in Encounter to reset fights
        '''
        fullCaster = ['Druid','Cleric','Sorceror','Wizard', 'Bard','Warlock'] # dont know if warlock should be here
        halfCaster = ['Ranger','Paladin', 'Artificer']
        self.twoAttacks = 1
        self.deathSaves = {'pass': [], 'fail': []}
        self.alive = 1
        
        self.status = []
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
                    dmg += sum(rollDice(2*crit, 8))
                elif self.lvl >= 3:
                    dmg += sum(rollDice(1*crit, 8))
                oncePerTurn = 0
            
            if self.DnDclass == 'Paladin' and self.lvl >= 2:
                highestSpell = 0
                for index in range(len(list(self.spellSlots))):
                    if self.spellSlots[list(self.spellSlots)[index]] > 0:
                        if index +1 >= highestSpell:
                            highestSpell = index +1
                dmg += sum(rollDice(crit*(highestSpell+1), 8))
        return dmg
    


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
    print(path+'character.json')
    print("C:\\Users\\jackh\\Code\\Python\\DmSim2\\actors\\savedObjs\\characters.json")
    print(characters['Ephraim']['Image'])
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
                        type = characters[name]['Class'],
                        Image= characters[name]['Image'])  # need to make this a variable in the json
                        
                        for name in nameList if name in list(characters.keys())]
    print("in create partyList", partyList[0].Image)
    return partyList