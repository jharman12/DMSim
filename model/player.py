
import re
import math
import sys
import json
import pathlib

_root = pathlib.Path(__file__).parent.parent
if getattr(sys, 'frozen', False):
    import app_paths as _ap
    _root = _ap.APP_ROOT
sys.path.insert(1, str(_root))

from engine.dice import down_round, weibull, cone, col_round, rollDice
from engine.utils import dprint
from model.weapon import WeaponNew
from model.actor import Actor



class Player(Actor):
    is_player = True

    def __init__(self, name, lvl, ac, health, modDict, turnFactors, weaponList, type, Image=False, known_spells=None, size='Medium'):
        self.name = name
        
        # Support multiclassing: type can be either a string (single class) or dict (multiclass)
        # e.g., "Wizard" or {"Wizard": 5, "Cleric": 3}
        if isinstance(type, dict):
            self.classes = type  # {"ClassName": level}
            self.lvl = sum(type.values())  # Total character level
            # Primary class is the one with highest level (for display/compatibility)
            self.DnDclass = max(type.items(), key=lambda x: x[1])[0]
        else:
            # Single class - maintain backward compatibility
            self.classes = {type: int(lvl)}
            self.lvl = int(lvl)
            self.DnDclass = type
        
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
        self.size = size  # D&D 5e size category string ('Medium', 'Large', 'Huge', 'Gargantuan', etc.)
        self.defineSpellSlots()
        # Optional known spells filter (backward compatible when None)
        self.known_spells = set(known_spells) if known_spells else None
        self.cc = [] # if cc'ed will be length 3 and in format ['spellLvl', 'modToRoll', dcToBeat]
        self.initMod = down_round((self.modDict['Dexterity']-10)/2)
        self.legRes = 0
        self.maxLegRes = 0
        self.speed = 30 
        self.maxSpeed = 30
        self.reaction = 1
        self.deathSaves = {'pass': [], 'fail': []}
        self.alive = 1
        self.status = []
        self.legActions = 0
        self.maxLegActions = 0
        self.legActionWeapon = ''
        self.hasAction = True
        self.hasBonusAction = True
        
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
        
        charCasters = ['Paladin','Warlock','Bard','Sorcerer']
        intCasters = ['Wizard']
        wisCasters = ['Cleric','Druid', 'Ranger']

        # Determine spellcasting ability based on highest-level caster class
        self.spellAttackMod = 0
        highestCasterLevel = 0
        spellcastingAbility = None
        
        for className in self.classes.keys():
            classLevel = self.classes[className]
            if className in charCasters and classLevel > highestCasterLevel:
                highestCasterLevel = classLevel
                spellcastingAbility = 'Charisma'
            elif className in intCasters and classLevel > highestCasterLevel:
                highestCasterLevel = classLevel
                spellcastingAbility = 'Intelligence'
            elif className in wisCasters and classLevel > highestCasterLevel:
                highestCasterLevel = classLevel
                spellcastingAbility = 'Wisdom'
        
        if spellcastingAbility:
            self.spellAttackMod = self.proficiency + down_round((self.modDict[spellcastingAbility]-10)/2)
        self.spellDC = 8 + self.spellAttackMod
        with open(str(_root / "spells" / "spellList.json"), "r", encoding="utf-8") as file:
            spellList = json.load(file)
        self.spells = {}
        for spell in spellList:
            # Check if any of the character's classes can cast this spell
            canCast = any(className in spellList[spell]['classes'] for className in self.classes.keys())
            if self.known_spells is not None and spell not in self.known_spells:
                continue
            if spellList[spell]['lvl'] <= self.highestSpell and canCast:
                self.spells[spell] = spellList[spell]
        self.possibleActions = {}
        dmgTypes = ['Acid', 'Bludgeoning', 'Cold', 'Fire', 'Force', 'Lightning', 'Necrotic', 'Piercing', 'Poison', 'Psychic', 'Radiant', 'Slashing', 'Thunder']
        conditionsList = ['Blinded','Charmed','Deafened', 'Frightened','Grappled','Incapacitated','Invisible','Paralyzed','Petrified','Poisoned','Prone','Restrained', 'Stunned','Unconscious','Exhausted']
        for spell in self.spells:
            if self.spells[spell]['effect'] in dmgTypes:
                self.possibleActions[spell] = 'Sdmg'
            elif self.spells[spell]['effect'] in conditionsList:
                self.possibleActions[spell] = 'cc'
        for weap in self.weaponList:
            self.possibleActions[weap.name] = 'Wdmg'
        self.AvgdmgCalc()
    
    def getClassLevel(self, className):
        """Get the level in a specific class (0 if not that class)"""
        return self.classes.get(className, 0)
    
    def hasClass(self, className):
        """Check if character has levels in a specific class"""
        return className in self.classes
    
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
           
            _range_nums = re.findall(r'\d+', self.spells[spell]['range'])
            spellRange = (int(_range_nums[0]) if _range_nums else 0) + area
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
            For multiclass: combines caster levels (full caster + half caster/2)

            also used in Encounter to reset fights
        '''
        fullCaster = ['Druid','Cleric','Sorcerer','Wizard', 'Bard','Warlock'] # dont know if warlock should be here
        halfCaster = ['Ranger','Paladin', 'Artificer']
        
        # Calculate effective caster level for multiclassing
        casterLevel = 0
        for className, classLevel in self.classes.items():
            if className in fullCaster:
                casterLevel += classLevel
            elif className in halfCaster:
                casterLevel += classLevel // 2  # Half casters contribute half their levels
        
        # Determine twoAttacks based on martial classes
        self.twoAttacks = 1
        # Check if any martial class is level 5+
        martialClasses = ['Fighter', 'Ranger', 'Paladin', 'Barbarian', 'Monk', 'Rogue']
        hasExtraAttack = any(self.getClassLevel(c) >= 5 for c in martialClasses)
        allFullCasters = all(c in fullCaster for c in self.classes.keys())
        
        if allFullCasters or (not hasExtraAttack and self.lvl <= 4):
            self.twoAttacks = 0
        
        self.deathSaves = {'pass': [], 'fail': []}
        self.alive = 1
        self.status = []
        
        lvl = casterLevel  # Use caster level for spell slots
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
        
        # Determine if character has any half-caster or full-caster levels
        hasHalfCaster = any(c in halfCaster for c in self.classes.keys())
        hasFullCaster = any(c in fullCaster for c in self.classes.keys())
        
        # If character has only half-caster levels (no full caster), use half-caster progression
        # Otherwise, use full caster progression based on combined caster level
        if hasHalfCaster and not hasFullCaster:
            # Pure half-caster or multi-half-caster progression
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
        elif hasFullCaster or casterLevel > 0:
            # Full caster progression (or mix of full and half casters)
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
        
        
        self.maxSpellSlots = {}
        for level in self.spellSlots:
            
            self.maxSpellSlots[level] = self.spellSlots[level]
        
        self.highestSpell = 0
        for index in range(len(list(self.spellSlots))):
            if self.spellSlots[list(self.spellSlots)[index]] > 0:
                if index +1 >= self.highestSpell:
                    self.highestSpell = index +1

   
    def classMeleeDmg(self, hits, dmg):
        fullCaster = ['Druid','Cleric','Sorcerer','Wizard', 'Bard','Warlock'] # dont know if warlock should be here
        # Check if character is ONLY full casters (no martial classes)
        onlyFullCasters = all(c in fullCaster for c in self.classes.keys())
        if sum(hits) == 0 or onlyFullCasters:
            return 0
        oncePerTurn = 1
        startDmg = dmg
        for hit in hits:
            if hits == 2:
                crit = 2
            else:
                crit = 1
            # Ranger Hunter's Mark - check Ranger level specifically
            rangerLevel = self.getClassLevel('Ranger')
            if rangerLevel > 0 and oncePerTurn:
                if rangerLevel >= 11:
                    dmg += sum(rollDice(2*crit, 8))
                elif rangerLevel >= 3:
                    dmg += sum(rollDice(1*crit, 8))
                oncePerTurn = 0
            
            # Paladin Divine Smite - check Paladin level specifically
            paladinLevel = self.getClassLevel('Paladin')
            if paladinLevel >= 2:
                highestSpell = 0
                for index in range(len(list(self.spellSlots))):
                    if self.spellSlots[list(self.spellSlots)[index]] > 0:
                        if index +1 >= highestSpell:
                            highestSpell = index +1
                dmg += sum(rollDice(crit*(highestSpell+1), 8))
        return dmg
    


def createPartyList(nameList, path):
    """Load newChars.json and create Player instances for each name in nameList."""
    try:
        with open(path + "newChars.json", "r") as file:
            data = json.load(file)
            characters = data#.get("characters", {})
    except FileNotFoundError:
        dprint('Failed to load characters')
        characters = {}
    
    partyList = [Player(name = name, 
                        lvl = int(characters[name]['level']),
                        ac = int(characters[name]['ac']),
                        health = int(characters[name]['hp']),
                        modDict= {  # Map abbreviations to full names
                            'Strength': characters[name]['mods'].get('str', 10),
                            'Dexterity': characters[name]['mods'].get('dex', 10),
                            'Constitution': characters[name]['mods'].get('con', 10),
                            'Intelligence': characters[name]['mods'].get('int', 10),
                            'Wisdom': characters[name]['mods'].get('wis', 10),
                            'Charisma': characters[name]['mods'].get('cha', 10)
                        },
                        turnFactors= {'Melee': 1.0, 'Ranged': 1.0, 'Ranged Spell': 1.0, 'Spell CC': 1.0},  # Default
                        weaponList= [WeaponNew(name=weapon['name'],
                                           attackType=weapon['type'],
                                           range=int(weapon['range']),
                                           attackMod=int(weapon['attack_mod']),
                                           diceType= weapon['dice_type'],
                                           diceCount= int(weapon['dice_count']),
                                           dmgMod= int(weapon['damage_mod']))
                                           
                                           for weapon in characters[name]['weapons']], 
                        type = characters[name]['class'],
                        Image= characters[name]['image'],
                        known_spells=characters[name].get('known_spells'),
                        size=characters[name].get('size', 'Medium'))
                        
                        for name in nameList if name in list(characters.keys())]
    return partyList