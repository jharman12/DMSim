from encounterSim import Encounter
#from playersModel import Player
from monster import Monster, MonsterDump, createMonsterList
import sys
import json
import pathlib
dmSimPath = str(pathlib.Path(__file__).parent.resolve())[0:-6]


sys.path.insert(1, dmSimPath + '/actors/statReader')
#from textReader import buildMonsterFromString
from player import createPartyList, Player
import random as r 
from map import Map
sys.path.insert(1, dmSimPath)
from modelMethods import takeTurn, removeDeadActors, myAction


if __name__ == "__main__":

    
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
    #MonsterDump(test, path = 'A:\\Code\\Python\\DmSim\\actors\\savedObjs\\')
    '''
    
