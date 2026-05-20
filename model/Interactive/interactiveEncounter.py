from dataclasses import dataclass
import random as r
import numpy as np
import time
import numpy as np
import time
import sys
import pathlib
from PyQt5.QtCore import QThread, pyqtSignal

# Add root directory to path for imports
dmSimPath = str(pathlib.Path(__file__).parent.parent.parent.resolve())
sys.path.insert(0, dmSimPath)
from engine.combat import takeTurn, removeDeadActors
from engine.dice import rollSave
from engine.persistent import apply_zone_to_actor, tick_persistent_spells
from engine.utils import dprint
from model.map import Map


class interactiveEncounter:

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
            actor.restrained = []
            actor.concentration_spell = None  # no active concentration on encounter start
            actor.active_conditions = set()   # display-only condition tracking
            # Ensure every actor has maxSpeed so end_turn can restore it correctly.
            if not hasattr(actor, 'maxSpeed'):
                actor.maxSpeed = actor.speed
            actor.hasAction = True
            actor.hasBonusAction = True
            # Reset damage dealt counter for player actors.
            if getattr(actor, 'is_player', False):
                actor._damage_dealt = 0
            # Snapshot monster spell use counts so the GUI can show max checkboxes correctly.
            if not getattr(actor, 'is_player', False):
                actor._spell_max_uses = {
                    name: entry[0]
                    for name, entry in getattr(actor, 'spells', {}).items()
                    if isinstance(entry, list) and len(entry) >= 2
                }

    
    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop("qtStuff", None)
        return state

    def preCombat(self, graphicsViewer):
        partyList = self.party2List
        enemyList = self.enemy2List
        self.map = Map(self.numHexes, partyList, enemyList, graphicsViewer=graphicsViewer)
        initList = {x:(r.randint(1,20) + x.initMod) for x in self.totalList}
        self.sortedInitList = dict(sorted(initList.items(), key = lambda x:x[1], reverse=True))
        self.curTurn = 0
        self.graphicsViewer = graphicsViewer
        # interactive_actors is injected by SimController.set_interactive_actors().
        # Default: all party members are interactive, all enemies are automated.
        if not hasattr(self, 'interactive_actors'):
            self.interactive_actors = {a.name for a in self.party2List}

    def nextTurn(self):
        # Remove red outline from current actor
        curActor = list(self.sortedInitList)[self.curTurn]
        curIndex = self.graphicsViewer.character_objs.index(curActor)
        item = self.graphicsViewer.character_items[curIndex]
        pixMap = item.pixmap()
        removeOutline = self.graphicsViewer.remove_red_outline(pixMap)
        item.setPixmap(removeOutline)

        self.removeDeadActors()
        self.curTurn += 1

        if self.curTurn >= len(self.sortedInitList):
            # New round starts — tick persistent spell durations.
            self.curTurn = 0
            expired = tick_persistent_spells(self.map)
            for ps in expired:
                self.graphicsViewer.remove_persistent_zone(ps.spell_name)

        # Update red outline to new actor
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
                dprint(deadActor.name, 'is dead')
                self.map.combatLog(deadActor.name + ' has died!')
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
        dprint(self.sortedInitList, self.curTurn)
        actor = list(self.sortedInitList)[self.curTurn]
        self.map.combatLog('Current Turn:' + str(self.curTurn) + '\n\t' + actor.name)

        # Reset per-turn action economy
        actor.hasAction = True
        actor.hasBonusAction = True

        for healthCheck in list(self.sortedInitList.keys()):
            dprint('\t\t', healthCheck.name, healthCheck.health)

        # Apply persistent zone effects at the start of this actor's turn.
        for ps in list(self.map.persistent_spells):
            apply_zone_to_actor(ps, actor, self.map)
            # Zone application may have killed the actor — check
            self.removeDeadActors()
            if actor not in self.map.party and actor not in self.map.enemy:
                # Actor died from zone; advance to next turn
                if self.sortedInitList:
                    self.nextTurn()
                    return self.calcTurn()
                return

        # Log restrained status (actor can still act, just can't move)
        if getattr(actor, 'restrained', []):
            self.map.combatLog(f'\t{actor.name} is Restrained (speed 0; can try to break free)')

        if actor.legRes >= 1 and len(actor.cc) > 0:
            actor.legRes = actor.legRes - 1
            actor.cc = []
        elif len(actor.cc) > 0:
            zone_applied = len(actor.cc) > 3 and actor.cc[3] is True
            if zone_applied:
                # CC was freshly applied by a zone this turn — save already rolled, just lose the turn.
                self.map.combatLog('\t' + actor.name + ' is incapacitated by the zone effect.')
                actor.cc = []
                self.nextTurn()
                return self.calcTurn()
            self.map.combatLog('\t' + actor.name + ' is cc\'ed. Rolling Save')
            outcome = rollSave(actor, actor.cc[1][0], actor.cc[2])
            if outcome:
                self.nextTurn()
                return self.calcTurn()
            else:
                actor.cc = []
                self.nextTurn()
                return self.calcTurn()

        if actor in self.map.enemy:
            if len(self.map.party) == 0:
                return
            is_interactive = actor.name in getattr(self, 'interactive_actors', set())
            if is_interactive:
                turn = takeTurn(actor, self.map, interactive=True)
                if turn is None:
                    self.nextTurn()
                    return self.calcTurn()
                else:
                    return turn
            else:
                takeTurn(actor, self.map, interactive=False)
                self.nextTurn()
                testing = self.calcTurn()
                return testing
        else:
            if len(self.map.enemy) == 0:
                return
            is_interactive = actor.name in getattr(self, 'interactive_actors', set())
            if is_interactive:
                turn = takeTurn(actor, self.map, interactive=True)
                if turn is None:
                    self.nextTurn()
                    return self.calcTurn()
                else:
                    return turn
            else:
                # Party member set to automated (AI-controlled)
                takeTurn(actor, self.map, interactive=False)
                self.nextTurn()
                return self.calcTurn()
    