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
        self.graphicsViewer = graphicsViewer

    def nextTurn(self):
        
        
        # Add remove red outline, add red line to new turn
        # should probably just make below a function
        
        curActor = list(self.sortedInitList)[self.curTurn]
        #print("trying to remove red outline from ", curActor.name)
        curIndex = self.graphicsViewer.character_objs.index(curActor)
        item = self.graphicsViewer.character_items[curIndex]
        pixMap = item.pixmap()
        removeOutline = self.graphicsViewer.remove_red_outline(pixMap)
        item.setPixmap(removeOutline)

        self.removeDeadActors()
        self.curTurn += 1 
        
        if self.curTurn >= len(self.sortedInitList):
            self.curTurn = 0
        
        # now that turn has changed, updated who has a red line
        curActor = list(self.sortedInitList)[self.curTurn]
        self.graphicsViewer.setCurTurn(curActor)
        curIndex = self.graphicsViewer.character_objs.index(curActor)
        item = self.graphicsViewer.character_items[curIndex]
        pixMap = item.pixmap()
        removeOutline = self.graphicsViewer.addRedOutline(pixMap)
        item.setPixmap(removeOutline)


    def removeDeadActors(self):
        map = self.map
        totalList = map.party + map.enemy
        deadActors = [actor for actor in totalList if not actor.alive]
        if len(deadActors) >= 1:
            for deadActor in deadActors:
                print(deadActor.name, 'is dead')
                if deadActor in map.party:
                    map.party.remove(deadActor)
                else:
                    map.enemy.remove(deadActor)
                actorCoord = [coord for coord in list(map.arrayCenters) if map.arrayCenters[coord] == deadActor][0]
                map.arrayCenters[actorCoord] = ''
                del self.sortedInitList[deadActor]
                charIndex = self.graphicsViewer.character_objs.index(deadActor)
                self.graphicsViewer.scene.removeItem(self.graphicsViewer.character_items[charIndex])
                del self.graphicsViewer.character_items[charIndex]
                del self.graphicsViewer.character_objs[charIndex]
                
        return deadActors

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
                self.nextTurn()
                return self.calcTurn()
            else: # if passed save... no long cced
                actor.cc = []
                self.nextTurn()
                return self.calcTurn()
        if actor in self.map.enemy: # if on enemy list your enemy is the party
            if len(self.map.party) == 0: # if enemies already down... skip turn
                
                return
            takeTurn(actor, self.map, interactive=False)
            self.nextTurn()
            testing = self.calcTurn()
            print("return ", testing)
            return testing
            
            
        else: # if not on enemy list your enemy is enemyList
            if len(self.map.enemy) == 0: # if enemies already down... skip turn
                return
            
            turn =  takeTurn(actor, self.map, interactive=True)
            if turn == None:
                self.nextTurn()
                return self.calcTurn()
            else:
                return turn
            
                
    