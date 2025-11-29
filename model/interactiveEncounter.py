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
        initList = {x:(r.randint(1,20) + x.initMod) for x in self.totalList}
        self.sortedInitList = dict(sorted(initList.items(), key = lambda x:x[1], reverse=True))
        self.curTurn = 0

    def nextTurn(self):
        self.curTurn += 1 

    def calcTurn(self):
        # new combat... 
        # perform following actions
        #   do a health check
        #   check for actor cc and leg res to ignore cc
        #   calc best turn
        print(self.sortedInitList, self.curTurn)
        actor = list(self.sortedInitList)[self.curTurn]
        print(actor)

        # do some initial checks to see current state
        for healthCheck in list(self.sortedInitList.keys()):
            print('\t\t', healthCheck.name, healthCheck.health)
        
        if actor.legRes >= 1 and len(actor.cc) > 0: # if cced and has legendary resistance... use it and continue
            actor.legRes = actor.legRes - 1
            #print('\t Actor used Leg Res to not be cced : '+actor.name+ ' has  '+ str(actor.legRes) + ' more\n')
            actor.cc = []
        elif len(actor.cc) > 0: # if actor cced then spend turn trying to save
            outcome = rollSave(actor, actor.cc[1][0], actor.cc[2]) 
            #print('\t Actor cced, trying to save...either way no turn taken \n')
            if outcome: # if failed save... still cced
                return
            else: # if passed save... no long cced
                actor.cc = []
                return    
        if actor in self.map.enemy: # if on enemy list your enemy is the party
            if len(self.map.party) == 0: # if enemies already down... skip turn
                
                return
            return takeTurn(actor, self.map, interactive=True)
            
            
        else: # if not on enemy list your enemy is enemyList
            if len(self.map.enemy) == 0: # if enemies already down... skip turn
                return
            return takeTurn(actor, self.map, interactive=True)
            
                
    