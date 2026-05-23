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
if getattr(sys, 'frozen', False):
    import app_paths as _ap
    dmSimPath = str(_ap.APP_ROOT)
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
        # Clamp curTurn in case removeDeadActors() just shrank the list
        if len(self.sortedInitList) == 0:
            return
        if self.curTurn >= len(self.sortedInitList):
            self.curTurn = len(self.sortedInitList) - 1

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

        if len(self.sortedInitList) == 0:
            return

        # Update red outline to new actor
        curActor = list(self.sortedInitList)[self.curTurn]
        self.graphicsViewer.setCurTurn(curActor)
        curIndex = self.graphicsViewer.character_objs.index(curActor)
        item = self.graphicsViewer.character_items[curIndex]
        pixMap = item.pixmap()
        removeOutline = self.graphicsViewer.addRedOutline(pixMap)
        item.setPixmap(removeOutline)

    def calcTurn(self):
        """Advance the encounter until the next interactive actor's turn.

        Uses an iterative loop instead of recursion to avoid Python stack
        overflow when many automated actors act in a row.
        Returns the interactive turn object when an interactive actor is
        reached, or None when combat ends.
        """
        _MAX_AUTO_STEPS = 10000  # safety valve

        for _step in range(_MAX_AUTO_STEPS):
            if len(self.sortedInitList) == 0:
                return None

            actor = list(self.sortedInitList)[self.curTurn]
            self.map.combatLog('Current Turn:' + str(self.curTurn) + '\n\t' + actor.name)

            # Reset per-turn action economy
            actor.hasAction = True
            actor.hasBonusAction = True

            for healthCheck in list(self.sortedInitList.keys()):
                dprint('\t\t', healthCheck.name, healthCheck.health)

            # --- Persistent zone effects at start of turn ---
            actor_died = False
            for ps in list(self.map.persistent_spells):
                apply_zone_to_actor(ps, actor, self.map)
                self.removeDeadActors()
                if actor not in self.map.party and actor not in self.map.enemy:
                    actor_died = True
                    break

            if actor_died:
                if not self.sortedInitList:
                    return None
                self.nextTurn()
                continue

            # --- Log restrained status ---
            if getattr(actor, 'restrained', []):
                self.map.combatLog(f'\t{actor.name} is Restrained (speed 0; can try to break free)')

            # --- Crowd-control check ---
            if actor.legRes >= 1 and len(actor.cc) > 0:
                actor.legRes -= 1
                actor.cc = []
                self.nextTurn()
                continue

            if len(actor.cc) > 0:
                zone_applied = len(actor.cc) > 3 and actor.cc[3] is True
                if zone_applied:
                    self.map.combatLog('\t' + actor.name + ' is incapacitated by the zone effect.')
                    actor.cc = []
                    self.nextTurn()
                    continue
                self.map.combatLog('\t' + actor.name + ' is cc\'ed. Rolling Save')
                rollSave(actor, actor.cc[1][0], actor.cc[2])
                actor.cc = []
                self.nextTurn()
                continue

            # --- Actor takes their turn ---
            if actor in self.map.enemy:
                if len(self.map.party) == 0:
                    return None
                is_interactive = actor.name in getattr(self, 'interactive_actors', set())
                if is_interactive:
                    turn = takeTurn(actor, self.map, interactive=True)
                    if turn is None:
                        self.nextTurn()
                        continue
                    return turn
                else:
                    takeTurn(actor, self.map, interactive=False)
                    self.nextTurn()
                    continue
            else:
                if len(self.map.enemy) == 0:
                    return None
                is_interactive = actor.name in getattr(self, 'interactive_actors', set())
                if is_interactive:
                    turn = takeTurn(actor, self.map, interactive=True)
                    if turn is None:
                        self.nextTurn()
                        continue
                    return turn
                else:
                    takeTurn(actor, self.map, interactive=False)
                    self.nextTurn()
                    continue

        dprint("calcTurn: hit max auto-step limit — returning None")
        return None

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
                # Clear ALL footprint hexes (multi-hex actors occupy multiple coords)
                for coord in list(map.arrayCenters):
                    if map.arrayCenters[coord] is deadActor:
                        map.arrayCenters[coord] = ''
                del self.sortedInitList[deadActor]
                if deadActor in self.graphicsViewer.character_objs:
                    charIndex = self.graphicsViewer.character_objs.index(deadActor)
                    dead_item = self.graphicsViewer.character_items[charIndex]
                    self.graphicsViewer.scene.removeItem(dead_item)
                    # Clean up pixmap caches so loadFromEncounter won't ghost this actor
                    self.graphicsViewer._clean_pixmaps.pop(dead_item, None)
                    self.graphicsViewer._original_pixmaps.pop(dead_item, None)
                    del self.graphicsViewer.character_items[charIndex]
                    del self.graphicsViewer.character_objs[charIndex]

        return deadActors
    