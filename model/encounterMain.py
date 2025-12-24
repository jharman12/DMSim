from encounterSim import Encounter
#from playersModel import Player
from monster import Monster, MonsterDump, createMonsterList
import sys
import json
import pathlib
dmSimPath = str(pathlib.Path(__file__).parent.resolve())[0:-6]


sys.path.insert(1, dmSimPath + '/actors/statReader')
from textReader import buildMonsterFromString
from player import createPartyList, Player
import random as r 
from map import Map
sys.path.insert(1, dmSimPath)
from modelMethods import takeTurn, removeDeadActors, myAction


if __name__ == "__main__":

    test = buildMonsterFromString('''
Acolyte
Medium humanoid (any race), any alignment
Armor Class 10
Hit Points 9 (2d8)
Speed 30 ft.
STR DEX CON INT WIS CHA
10 (+0) 10 (+0) 10 (+0) 10 (+0) 14 (+2) 11 (+0)
Skills Medicine +4, Religion +2
Senses passive Perception 12
Languages any one language (usually Common)
Challenge 1/4 (50 XP)
Spellcasting. The acolyte is a 1st-­‐level spellcaster. Its
spellcasting ability is Wisdom (spell save DC 12, +4 to
hit with spell attacks). The acolyte has following cleric
spells prepared:
Cantrips (at will): light, sacred flame, thaumaturgy
1st level (3 slots): bless, cure wounds, sanctuary
Actions
Club. Melee Weapon Attack: +2 to hit, reach 5 ft., one
target. Hit: 2 (1d4) bludgeoning damage.
Acolytes are junior members of a clergy, usually
answerable to a priest. They perform a variety of
functions in a temple and are granted minor
spellcasting power by their deities.
                                  ''')
    print(test)
    MonsterDump(test.monster, path = dmSimPath + '\\actors\\savedObjs\\')
    #r.seed(1)
    path = dmSimPath + '\\actors\\savedObjs\\'
    party = createPartyList(['Ephraim', 'Darian', 'Root','Arabella'], path = path)
    enemy = createPartyList(['Darian'], path = path)
    enemy = createMonsterList(["Quenth"] + ["Demogorgon" for i in range(1)], path = path)
    map = Map(10, party, enemy)
    #print(party[0].Image)
    #for spell in party[1].spells:
    #    print(spell)
    #takeTurn(party[0], map, interactive=False)
    states = Encounter(party, [], enemyList=enemy, n =1)
    takeTurn(party[2], map, True)
    '''enemy = createMonsterList(["Quenth"] + ["Drow" for i in range(10)], path = path)
    enemy = createMonsterList(["Quenth"] , path = path)
    map = Map(15, party, enemy)
    range = 0
    area = 60
    #print(party[2].takeTurn(map))
    ##print(party[0].rollDeathSave())
    ##print(party[2].name)
    #print(party)
    #enemy = createMonsterList(["Quenth"] + ["Demogorgon" for i in range(1)], path = path)
    enemy = createPartyList(['Root', 'Arabella'], path = path)
    #print(enemy)
    states = Encounter(party, [], enemyList=enemy, n =1)
    
    '''
    
