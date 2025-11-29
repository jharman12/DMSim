from dataclasses import dataclass
import random as r
import numpy as np
#import matplotlib.pyplot as plt
import time
#import pandas as pd
import numpy as np
import time
from map import Map
import sys
from interactiveMap import interactiveMap
from PyQt5.QtCore import QThread, pyqtSignal
import pathlib
dmSimPath = str(pathlib.Path(__file__).parent.resolve())[0:-6]
sys.path.insert(1, dmSimPath)
print(dmSimPath)
from modelMethods import takeTurn, removeDeadActors, rollSave


class interactiveEncounter(QThread):
    output_received = pyqtSignal(str)

    def __init__(self, partyList, npcList, enemyList, numHexes, mapImage):
        self.numHexes = numHexes
        self.mapImage = mapImage
        self.enemy2List = [enemy for enemy in enemyList]
        self.party2List = [party for party in partyList] + [npc for npc in npcList]
        self.totalList = self.enemy2List+self.party2List
        for actor in self.totalList:
            actor.health = actor.maxHealth
            actor.defineSpellSlots()
            actor.legRes = actor.maxLegRes
            actor.legActions = actor.maxLegActions
            actor.cc = []
    def preCombat(self, graphicsViewer):
        partyList = self.party2List
        enemyList = self.enemy2List
        self.map = interactiveMap(self.numHexes, partyList, enemyList, graphicsViewer)
        self.map.defineArrayGrid(self.numHexes)
        self.map.populateMap(self.party2List, self.enemy2List)

    def combat(self):
        
        partyList = self.party2List
        enemyList = self.enemy2List
        map = self.map
        
        totalList = enemyList + partyList
        initList = {x:(r.randint(1,20) + x.initMod) for x in totalList}
        sortedInitList = dict(sorted(initList.items(), key = lambda x:x[1], reverse=True))
        turn = 0
        while len(map.party) != 0 and len(map.enemy) != 0:
            '''
            combat order:
                see if you have legRes and are cc'ed
                    if yes to both, use legRes and not be cc'ed
                if you are still cc'ed, spend turn trying to not be cc'ed
                    either way skip turn
            '''
            turn += 1
            for actor in list(sortedInitList.keys()):
                
                print('\t It is: '+actor.name+ ' turn w/ health = '+ str(actor.health) + '\n')
                #time.sleep(10)
                for healthCheck in list(sortedInitList.keys()):
                    print('\t\t', healthCheck.name, healthCheck.health)
                if not actor in list(sortedInitList.keys()): # you've already been removed
                    continue
                if actor.legRes >= 1 and len(actor.cc) > 0: # if cced and has legendary resistance... use it and continue
                    actor.legRes = actor.legRes - 1
                    #print('\t Actor used Leg Res to not be cced : '+actor.name+ ' has  '+ str(actor.legRes) + ' more\n')
                    actor.cc = []
                elif len(actor.cc) > 0: # if actor cced then spend turn trying to save
                    outcome = rollSave(actor, actor.cc[1][0], actor.cc[2]) 
                    #print('\t Actor cced, trying to save...either way no turn taken \n')
                    if outcome: # if failed save... still cced
                        continue
                    else: # if passed save... no long cced
                        actor.cc = []
                        continue    
                if actor in map.enemy: # if on enemy list your enemy is the party
                    if len(map.party) == 0: # if enemies already down... skip turn
                        
                        continue
                    takeTurn(actor, map)
                    removeDeadActors(map, sortedInitList)
                    
                else: # if not on enemy list your enemy is enemyList
                    if len(map.enemy) == 0: # if enemies already down... skip turn
                        continue
                    takeTurn(actor, map, interactive=True)
                    removeDeadActors(map, sortedInitList)

                    for enemy in map.enemy:
                        if enemy.legActions >= 1 and len(map.party) != 0:
                            print('\t Legendary Action taken by: ' + enemy.name + '\n')
                            enemy.takeLegAction(map)
                            removeDeadActors(map, sortedInitList)
                
            
                
        survivors = [x.name for x in list(sortedInitList.keys()) if x.health > 0]
        print(survivors)
        if len(enemyList) == 0:
            winner = 'Party'
        else:
            winner = 'Enemy'
        print('Winner: ' + winner+ '. Turns: '+ str(turn) + '. Survivors: ' + str(survivors) + '\n')