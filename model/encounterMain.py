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
Myconid Adult
Medium Plant, Lawful Neutral

Armor Class 12 (natural armor)
Hit Points 22 (4d8 + 4)
Speed 20 ft.

STR
10 (+0)
DEX
10 (+0)
CON
12 (+1)
INT
10 (+0)
WIS
13 (+1)
CHA
7 (-2)

Senses Darkvision 120 ft., Passive Perception 11
Languages --
Challenge 1/2 (100 XP)
Proficiency Bonus +2

Traits
Distress Spores. When the myconid takes damage, all other myconids within 240 feet of it can sense its pain.

Sun Sickness. While in sunlight, the myconid has disadvantage on ability checks, attack rolls, and saving throws. The myconid dies if it spends more than 1 hour in direct sunlight.

Actions
Fist. Melee Weapon Attack: +2 to hit, reach 5 ft., one target. Hit: 5 (2d4) bludgeoning damage plus 5 (2d4) poison damage.

Pacifying Spores (3/Day). The myconid ejects spores at one creature it can see within 5 feet of it. The target must succeed on a DC 11 Constitution saving throw or be stunned for 1 minute. The target can repeat the saving throw at the end of each of its turns, ending the effect on itself on a success.

Rapport Spores. A 20-foot radius of spores extends from the myconid. These spores can go around corners and affect only creatures with an Intelligence of 2 or higher that aren’t undead, constructs, or elementals. Affected creatures can communicate telepathically with one another while they are within 30 feet of each other. The effect lasts for 1 hour.
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
    
