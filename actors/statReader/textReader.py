import math
import re
import sys 
import pathlib
dmSimPath = str(pathlib.Path(__file__).parent.resolve())[0:-18]

sys.path.insert(1, dmSimPath)
from modelMethods import numberAfterString, numberBeforeString, text2int, WeaponNew, down_round, weibull
import json
sys.path.insert(1, dmSimPath + '\model')
from monsterModel import Monster

class buildMonsterFromString:
    def __init__(self, text):
        '''
        need the following:
            name, ac, health, modDict, turnFactors, weaponList, size, speed, spells, spellMod, multiAttack, legRes, legAction
        '''
        with open(dmSimPath + "\\spells\\spellList.json", "r") as file:
            spellList = json.load(file)
        # predefine things on start up
        self.modDict = {}
        self.spells = {}
        savingThrows = {}

        multiattackLine = []
        aWeapons = []
        legWeapons = []
        lairWeapons = []

        bActions = 0
        bLegActions = 0
        legActions = 0
        bSpells = 0
        findWeapon = 0
        
        possibleSizes = {'Tiny': 6.25,'Small': 25, 'Medium': 25,'Large': 100,'Huge':225, 'Gargantuan':400}
        grabNumberAfterKey = {
            'Armor Class': 0,
            'Hit Points': 0,
            'Speed': 0,
            'Legendary Resistance': 0,
            'Challenge': 0,
            'Proficiency': 0

        }
        modNumLine = -1 # set to -1 so it doesnt trigger until you see the mod
        lineNum = 1
        setName = 0
        ##print(text.splitlines())
        for line in text.splitlines():
            # Name is alone on first line
            if len(line) != 0 and not setName:
                setName = 1
                self.name = line

            '''if text.split().index(line) == 1:
                self.name = line
                #print(self.name)'''
            
            for size in possibleSizes.keys():
                if size in line:
                    self.size = possibleSizes[size]
            # for things easy to find in line
            for item in grabNumberAfterKey.keys():
                match line:
                    case str(x) if item in x:
                        grabNumberAfterKey[item] = numberAfterString(x, item)
                    
                    
            

            if 'Spellcasting.' in line and 'DC' in line:
                bSpells = 1
                self.spellDC = numberAfterString(line, 'DC')
            
            if bSpells and 'day each' in line:
                for name in spellList.keys():
                    if name.lower() in line:
                        times = numberBeforeString(line, '/')
                        ##print(times)
                        self.spells[name] = [times, spellList[name]]
            elif bSpells and 'At will' in line:
                for name in spellList.keys():
                    if name.lower() in line:
                        times = 9999
                        self.spells[name] = [times, spellList[name]]

            mods = ['STR','DEX', 'CON', 'INT', 'WIS', 'CHA']
            saveModsAs = ['Strength', 'Dexterity', 'Constitution', 'Intelligence', 'Wisdom', 'Charisma']
            '''if any(x == line for x in mods):
                mod = line
                modNumLine = lineNum + 1
                #print(line)'''
            
            for mod in mods:
                match line:
                    case str(x) if mod in x and 'Saving Throws' in x:
                        savingThrows[mod] = numberAfterString(x, mod)
                    
                    case str(x) if mod in x:
                        index = text.splitlines().index(line) + 1
                        ##print('saving ', mod)
                        self.modDict[saveModsAs[mods.index(mod)]] = int(re.findall(r'\d+', text.splitlines()[index])[0])

            
            if 'legendary actions' in line:
                legActions = numberBeforeString(line, 'legendary actions')
            
            if 'Multiattack.' in line: # would like to save this now, but it lists weapons BEFORE weapons defined... so grab after for loop
                multiattackLine = line.split()
                
            """
            need to figure out turn Factors... probably at the end based on weapons & spell slots?
            """

            if findWeapon and '+' in line:
                weaponInfo = []
                avgDmg = 0
                dmgMod = 0
                wName = line.split('.')[0]
                toHit = re.findall(r'\d+', line)[0]
                dmging = re.findall(r'\(.*?\)', line)
                #d = find_digit_after_string(line, 'reach')
                if 'reach' in line:
                    range = numberAfterString(line, 'reach')
                    attackType = 'Melee'
                if 'ranged' in line:
                    range = numberAfterString(line, 'ranged')
                    attackType = 'Ranged'
                diceDmg_list = []
                diceCount_list = []
                for dmg in dmging:
                    diceCount = int(re.findall(r'\d+', dmg)[0])
                    diceDmg = int(re.findall(r'\d+', dmg)[1])
                    if len(re.findall(r'\d+', dmg)) == 3:
                        dmgMod += int(re.findall(r'\d+', dmg)[2])
                    #avgDmg += 0.5 + int(diceCount) *int(diceDmg)/2 
                    if diceDmg in diceDmg_list:
                        diceCount_list[diceDmg_list.index(diceDmg)] += int(diceCount)
                    else:
                        diceCount_list.append(int(diceCount))
                        diceDmg_list.append(int(diceDmg))

                weaponInfo.append(wName)
                weaponInfo.append(attackType)
                weaponInfo.append(range)
                weaponInfo.append(toHit)
                weaponInfo.append(diceDmg_list)
                weaponInfo.append(diceCount_list)
                weaponInfo.append(dmgMod)
                if bActions:
                    aWeapons.append(WeaponNew(wName, attackType, range, toHit, diceDmg_list, diceCount_list, dmgMod))
                if bLegActions:
                    legWeapons.append(WeaponNew(wName, attackType, range, toHit, diceDmg_list, diceCount_list, dmgMod))
            if 'Actions' in line:
                bActions = 1
                findWeapon = 1
                if 'Legendary Actions' in line:
                    bActions = 0
                    bLegActions = 1
                continue

            
            lineNum += 1
        
        weaponNames = [weap.name for weap in aWeapons]
        self.multiattack = {}
        if len(multiattackLine) != 0:
            for item in multiattackLine:
                if item in weaponNames:
                    index = multiattackLine.index(item) - 1
                    self.multiattack[item] = text2int(multiattackLine[index])
        self.aWeapons=aWeapons
        self.legWeapons = [legActions, legWeapons]

        #for key in grabNumberAfterKey.keys():
        self.ac = grabNumberAfterKey['Armor Class']
        self.health = grabNumberAfterKey['Hit Points']
        self.speed = grabNumberAfterKey['Speed']
        self.legRes = grabNumberAfterKey['Legendary Resistance']
        self.CR = grabNumberAfterKey['Challenge']
        self.spellMod = self.spellDC - grabNumberAfterKey['Proficiency']
        dmgTypes = ['Acid', 'Bludgeoning', 'Cold', 'Fire', 'Force', 'Lightning', 'Necrotic', 'Piercing', 'Poison', 'Psychic', 'Radiant', 'Slashing', 'Thunder']
        spellDmg = 0
        maxDmg = 0
        for spell in self.spells.keys():
            avgDmg = 0
            dice = self.spells[spell][1]['dice']
            effect = self.spells[spell][1]['effect']
            area = self.spells[spell][1]['area']
            if effect in dmgTypes:
                for di in dice:
                    diceCount = int(re.findall(r'\d+', di)[0])
                    diceDmg = int(re.findall(r'\d+', di)[1])
                    avgDmg += 0.5 + diceCount * diceDmg / 2
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

                    ##print(area)
                    ratio =  area / 25*party
                    percentHit = weibull(ratio)
                    ##print(percentHit)
                    totalHit = down_round(party * percentHit)
                    ##print(totalHit)
                    avgDmg = totalHit * avgDmg
                    ##print(spell)
                    ##print(totalDmg)
                            
            
            if avgDmg >= maxDmg:
                maxDmg = avgDmg
            spellDmg += avgDmg
        ##print(maxDmg)
        meleeMaxDmg = 0
        rangedMaxDmg = 0
        for weap in self.aWeapons:
            avgDmg = 0
            if weap.name in self.multiattack.keys():
                attackTimes = self.multiattack[weap.name]
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
                case 'Melee':
                    if avgDmg >= meleeMaxDmg:
                        meleeMaxDmg = avgDmg
        
        totalMax = meleeMaxDmg + rangedMaxDmg + maxDmg
        
        self.turnFactors = {}
        self.turnFactors['Melee'] = meleeMaxDmg/totalMax
        self.turnFactors['Ranged'] = rangedMaxDmg/totalMax
        self.turnFactors['Ranged Spell'] = maxDmg/totalMax
        self.turnFactors['Spell CC'] = 0
        # name, ac, health, modDict, turnFactors, weaponList, size, speed, spells, spellMod, multiAttack, legRes, legAction
        '''#print('name: ', self.name)
        #print('AC: ', self.ac)
        #print('health: ', self.health)
        #print('Mod Dict: ', self.modDict)
        #print('Turn Factors: ', self.turnFactors)
        #print('Action Weapons: ', self.aWeapons)
        #print('Size: ', self.size)
        #print('SPeed: ',self.speed)
        #print('SPells: ', self.spells)
        #print('Spell Mod: ', self.spellMod)
        #print('Multiattack: ', self.multiattack)
        #print('Leg Res: ', self.legRes)
        #print('Leg Actions: ', self.legWeapons)'''
        
        self.monster = Monster(self.name, self.ac, self.health, self.speed, self.modDict, self.turnFactors, self.aWeapons, self.size, self.spells,
               self.spellMod, self.multiattack, self.legRes, self.legWeapons)
        