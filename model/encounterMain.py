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
Stone Giant
Huge giant , neutral

Armor Class 17 (natural armor)  
Hit Points 126 (11d12 + 55)
Speed 40 ft.

STR
23
(+6)
DEX
15
(+2)
CON
20
(+5)
INT
10
(0)
WIS
12
(+1)
CHA
9
(-1)

Saving Throws DEX +5, CON +8, WIS +4
Skills Athletics +12, Perception +4
Senses Darkvision 60 ft.
Languages Giant
Challenge 7 (2900 XP)
Proficiency Bonus +3

Stone Camouflage. The giant has advantage on Dexterity (Stealth) checks made to hide in rocky terrain.

Actions
Multiattack. The giant makes two greatclub attacks.

Greatclub. Melee Weapon Attack: +9 to hit, reach 15 ft., one target. Hit: 19 (3d8 + 6) bludgeoning damage.

Rock. Ranged Weapon Attack: +9 to hit, range 60/240 ft., one target. Hit: 28 (4d10 + 6) bludgeoning damage. If the target is a creature, it must succeed on a DC 17 Strength saving throw or be knocked prone.

Reactions
Rock Catching. If a rock or similar object is hurled at the giant, the giant can, with a successful DC 10 Dexterity saving throw, catch the missile and take no bludgeoning damage from it.
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
    
