import random as r
import math
import inspect
import sys
import pathlib

_root = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(1, str(_root))

from engine.combat import takeReaction
from engine.utils import dprint

class Map:
    def __init__(self, numHex, partyList, enemyList, graphicsViewer=None):
        self.numHex = numHex
        self.graphicsViewer = graphicsViewer
        self.combatLog = None
        
        ##dprint('defining array')
        if graphicsViewer is not None:
            self.defineArrayGrid(numHex)
        else:
            self.defineArrayGrid(numHex, 1, 0.5)
        ##dprint('distance')
        #self.distanceCalc(0,23)

        self.party = partyList
        self.enemy = enemyList
        self.walls: set = set()           # (col, row) coord tuples for impassable wall hexes
        self.wall_data: dict = {}         # coord → {'hp': None, 'ac': None, 'color': '#707070', 'destructible': False}
        self.persistent_spells: list = [] # active PersistentSpell zones
        self.populateMap(self.party, self.enemy)
        
        #dprint('spawns as')
        self.printCurrMap()
        #self.moveToNearest(Ephraim, Arabella)
        
 
    def moveActor(self, mover, coord):
        from engine.size_utils import get_size_cat, compute_footprint, get_actor_anchor, can_place_footprint

        size_cat = get_size_cat(mover)

        # --- Pre-validate: for large actors, refuse move if footprint would overwrite another actor ---
        if size_cat not in ('Tiny', 'Small', 'Medium'):
            if not can_place_footprint(coord, size_cat, self, mover):
                dprint(f'WARNING: {mover.name} blocked from moving to {coord} — footprint occupied')
                return

        # --- Clear all current footprint hexes ---
        old_anchor = get_actor_anchor(mover, self)
        old_footprint = [c for c, v in self.arrayCenters.items() if v is mover]
        for c in old_footprint:
            self.arrayCenters[c] = ''

        moverCoord = old_anchor if old_anchor is not None else (old_footprint[0] if old_footprint else coord)
        moverIndex = list(self.arrayCenters).index(moverCoord)
        coordIndex = list(self.arrayCenters).index(coord)
        neighbors = self.neighbors(moverCoord)
        dprint(neighbors)

        distance = self.distanceCalc(moverIndex, coordIndex)
        dprint('\t\t', mover.name, 'is going from', moverCoord, 'to', coord, 'which is a distance of', distance)
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        if distance > mover.speed/5 and calframe[1][3] != 'dashActor':
            raise SystemExit('Crashed in map moveActor')

        # --- Place actor in new footprint hexes ---
        size_cat = get_size_cat(mover)
        new_footprint = compute_footprint(coord, size_cat, self)
        for c in new_footprint:
            if c in self.arrayCenters:
                self.arrayCenters[c] = mover
        mover._anchor_coord = coord

        self.printCurrMap()
        if moverCoord != coord:
            reacted: set = set()
            if mover in self.party:
                for neig in neighbors:
                    actor = self.arrayCenters[list(self.arrayCenters)[neig]]
                    if actor in self.enemy and actor.reaction and id(actor) not in reacted:
                        reactDis = self.distanceCalc(neig, coordIndex)
                        if reactDis >= 2:
                            reacted.add(id(actor))
                            dprint('youre enemyList', actor.name, 'and you should be able to react')
                            takeReaction(actor, self, mover)
            if mover in self.enemy:
                for neig in neighbors:
                    actor = self.arrayCenters[list(self.arrayCenters)[neig]]
                    if actor in self.party and actor.reaction and id(actor) not in reacted:
                        reactDis = self.distanceCalc(neig, coordIndex)
                        if reactDis >= 2:
                            reacted.add(id(actor))
                            dprint('youre partyList', actor.name, 'and you should be able to react')
                            takeReaction(actor, self, mover)
            if self.graphicsViewer is not None:
                newIndex = self.convertToViewerCoords(coord)
                fp_indices = [self.convertToViewerCoords(c) for c in new_footprint if c in self.arrayCenters]
                self.graphicsViewer.moveActor(mover, newIndex, fp_indices)
    
    def dashActor(self, mover, targetCoord):
        """Move mover up to double-speed toward targetCoord, following the
        wall-aware BFS path rather than a straight line."""
        from engine.targeting import _bfs_path_dest
        dprint(mover.name, ' is taking the dash action to ', targetCoord)

        moverCoord = next((c for c in self.arrayCenters if self.arrayCenters[c] is mover), None)
        if moverCoord is None:
            return
        start_idx  = self._coord_idx[moverCoord]
        target_idx = self._coord_idx.get(targetCoord)
        if target_idx is None:
            return

        speed_hexes = int(mover.speed / 5) * 2  # dash = double movement
        dest_idx = _bfs_path_dest(start_idx, target_idx, speed_hexes, self)
        if dest_idx is None or dest_idx == start_idx:
            return

        best_coord = self._coord_list[dest_idx]
        if self.arrayCenters.get(best_coord) not in ('', mover):
            best_coord = self.nearestFreeHex(start_idx, dest_idx, actor=mover)

        self.moveActor(mover, best_coord)
        

    def moveToNearest(self, mover, target):
        if mover == target:
            return
        dprint(mover, target)
        moverLoc = [i for i in self.arrayCenters if self.arrayCenters[i] == mover][0]
        
        Arabella = target
        moverIndex = list(self.arrayCenters).index(moverLoc)
        Arabella = list(self.arrayCenters).index(Arabella)

        moverNew = self.nearestFreeHex(moverIndex, Arabella, actor=mover)
        self.moveActor(mover, moverNew)

    def repositionActor(self, actor, coord):
        """Directly reposition actor to coord with no speed check, reactions, or effects.

        For pre-combat actor placement only. If the full footprint doesn't fit
        at coord (another actor is already there), the call is silently ignored.
        """
        from engine.size_utils import get_size_cat, compute_footprint, can_place_footprint

        size_cat = get_size_cat(actor)
        if not can_place_footprint(coord, size_cat, self, actor):
            return

        # Clear old footprint
        for c in [c for c, v in self.arrayCenters.items() if v is actor]:
            self.arrayCenters[c] = ''

        # Place new footprint
        new_footprint = compute_footprint(coord, size_cat, self)
        for c in new_footprint:
            if c in self.arrayCenters:
                self.arrayCenters[c] = actor
        actor._anchor_coord = coord

    def defineArrayGrid(self, heightNumber, height=None, width=None):
        """
        Initialize the hexagonal grid.
        When a graphicsViewer is provided the traversal matches drawHexGrid
        exactly (same start, same boundaries) so every model index i maps
        to view index i with no conversion required.
        """
        if self.graphicsViewer is not None:
            map_rect = self.graphicsViewer.map_item.boundingRect()
            height = map_rect.height()
            width = map_rect.width()
        else:
            if height is None or width is None:
                height = 1
                width = 0.5

        dprint(height, width)
        r = height / (2 * (1 + (heightNumber - 1) * 2 * math.cos(math.pi * 60 / 180)))
        self.radius = r
        a = 2 * math.pi / 6
        x_mod = r * (1 + math.cos(a))
        y_mod = r * math.sin(a)

        self.arrayCenters = {}

        if self.graphicsViewer is not None:
            # Start at the same pixel as drawHexGrid so indices are identical.
            # Coords are normalised relative to origin so first hex is always (0,0).
            origin_x = r
            origin_y = r * math.sin(a)
            x, y = origin_x, origin_y
            inner_limit = width + r        # matches drawHexGrid: <= width + startingPoint[0] + r
            outer_limit = height           # matches drawHexGrid: y + r*sin <= height + 2*startingPoint[1]
        else:
            # Headless / test mode: plain (0,0) origin, original boundaries.
            origin_x, origin_y = 0.0, 0.0
            x, y = 0.0, 0.0
            inner_limit = width
            outer_limit = height

        while y + r * math.sin(a) <= outer_limit:
            previousY = y
            previousX = x
            j = 0
            while x + r * (1 + math.cos(a)) <= inner_limit:
                coord = (self.col_round((x - origin_x) / x_mod),
                         self.col_round((y - origin_y) / y_mod))
                self.arrayCenters[coord] = ''
                x += r * (1 + math.cos(a))
                y += (-1) ** j * r * math.sin(a)
                j += 1
            x = previousX
            y = previousY
            y += 2 * r * math.sin(a)

        self._rebuild_coord_cache()

    def _rebuild_coord_cache(self):
        """Rebuild the cached coord list and reverse-index dict.
        Called once after defineArrayGrid; keys are stable after that."""
        self._coord_list: list = list(self.arrayCenters.keys())
        self._coord_idx: dict = {c: i for i, c in enumerate(self._coord_list)}

    def _neighbors_of(self, coord: tuple) -> list:
        """Return index list of the (up to 6) hex-adjacent coords using O(1) math.

        This map uses a doubled-height coordinate system where valid hexes always
        share the same parity (both col and row are even, or both are odd).
        The 6 neighbors all preserve parity:
          diagonal steps (±1, ±1) → distance = 1 + max(0,(1-1)/2) = 1
          vertical steps  (0,  ±2) → distance = 0 + max(0,(2-0)/2) = 1
        """
        col, row = coord
        candidates = [
            (col + 1, row + 1),
            (col + 1, row - 1),
            (col - 1, row + 1),
            (col - 1, row - 1),
            (col,     row + 2),
            (col,     row - 2),
        ]
        return [self._coord_idx[c] for c in candidates if c in self._coord_idx]

    def distanceCalc(self, index1, index2):
        return self.doubledHeight(self._coord_list[index1], self._coord_list[index2])

    def col_round(self, x):
        frac = x - math.floor(x)
        if frac <= 0.5: return math.floor(x)
        return math.ceil(x)
    def axial_to_cube(self, x, y):
        s = -x-y
        return [x,y,s]
    
    def oddq_to_axial(self, x, y):
        q = x
        r =  y - ((q + (q&1)))/2
        return [q, r]
    
    def axial_distance(self, a, b):
        '''
        a and b are (q1, r1) & (q2, r2)
        '''
        return (abs(a[0] - b[0]) + abs(a[0] + a[1] - b[0] + b[1]) + abs(a[1] - b[1])) /2 
    

    def doubledHeight(self, a, b):
        drow = abs(a[1] - b[1])
        dcol = abs(a[0] - b[0])
        return dcol + max(0, (drow - dcol)/2)
    
    def populateMap(self, party, enemy):
        from engine.size_utils import get_size_cat, compute_footprint, can_place_footprint

        totalArea = len(self._coord_list) * 25
        totalParty = sum([x.size if isinstance(x.size, (int, float)) else 25 for x in party])
        totalEnemy = sum([x.size if isinstance(x.size, (int, float)) else 25 for x in enemy])
        partyEnemyRatio = totalParty / totalEnemy if totalEnemy else 1
        maxX = max(x[0] for x in self._coord_list)
        maxY = max(x[1] for x in self._coord_list)
        partyX = self.col_round(partyEnemyRatio * maxX / 2)
        if partyEnemyRatio > 1:
            newX = 1 - 1 / partyEnemyRatio
            partyX = self.col_round(newX * maxX)

        partySide = []
        enemySide = []
        walls = getattr(self, 'walls', set())
        for key in self.arrayCenters.keys():
            if key in walls:
                continue  # never spawn on a wall hex
            if key[0] <= partyX:
                partySide.append(key)
            else:
                enemySide.append(key)

        totalList = [party, enemy]
        for side in totalList:
            for member in side:
                size_cat = get_size_cat(member)
                sample_side = partySide if member in party else enemySide
                saved = False
                for _ in range(500):
                    coord = r.sample(sample_side, 1)[0]
                    if can_place_footprint(coord, size_cat, self):
                        footprint = compute_footprint(coord, size_cat, self)
                        for c in footprint:
                            self.arrayCenters[c] = member
                        member._anchor_coord = coord
                        if self.graphicsViewer is not None:
                            gViewerCoord = self.convertToViewerCoords(coord)
                            fp_indices = [self.convertToViewerCoords(c) for c in footprint]
                            self.graphicsViewer.moveActor(member, gViewerCoord, fp_indices)
                        saved = True
                        break
                if not saved:
                    # Fallback: place in first available empty hex (single hex)
                    for coord in sample_side:
                        if self.arrayCenters[coord] == '':
                            self.arrayCenters[coord] = member
                            member._anchor_coord = coord
                            if self.graphicsViewer is not None:
                                gViewerCoord = self.convertToViewerCoords(coord)
                                self.graphicsViewer.moveActor(member, gViewerCoord, [gViewerCoord])
                            break
    
    def neighbors(self, testCoord):
        """Return index list of adjacent hexes. O(6) using precomputed coord map."""
        return self._neighbors_of(testCoord)


    def nearestFreeHex(self, startIndex, endIndex, actor=None):
        from engine.size_utils import get_size_cat, can_place_footprint
        nearIndexList = self._neighbors_of(self._coord_list[endIndex])
        min_dist = 999999
        minIndex = -99

        # Determine if we need footprint-aware checks
        size_cat = get_size_cat(actor) if actor is not None else 'Medium'
        multi_hex = size_cat not in ('Tiny', 'Small', 'Medium')

        walls = getattr(self, 'walls', set())
        for index in nearIndexList:
            distance = self.distanceCalc(index, startIndex)
            coord = self._coord_list[index]
            if coord in walls:
                continue  # never return a wall hex
            if multi_hex:
                valid = can_place_footprint(coord, size_cat, self, actor)
            else:
                valid = self.arrayCenters[coord] == ''
            if valid and distance <= min_dist:
                min_dist = distance
                minIndex = index

        if minIndex == -99:
            minIndex = startIndex
            self.printCurrMap()
        return self._coord_list[minIndex]

    def convertToMyCoords(self, index):
        """Convert viewer index to map coordinates."""
        return self._coord_list[index]

    def convertToViewerCoords(self, coord):
        """Convert map coordinates to viewer index. O(1) via cached dict."""
        return self._coord_idx[coord]


    def printCurrMap(self):
        string = ''
        coordList = self._coord_list
        maxX = max(x[0] for x in self._coord_list)
        maxY = max(x[1] for x in self._coord_list)
        ##dprint(maxY)
        for y in range(maxY + 1):
            ##dprint(y)
            x = 0
            string += '\n'
            while x <= maxX:
                
                if x % 2 == 0 and y % 2 == 0:
                    coord = (x, y)
                    if self.arrayCenters[coord] == '':
                        input = '.'
                    elif self.arrayCenters[coord] == 'c': 
                        input = self.arrayCenters[coord]
                    else:
                        input = self.arrayCenters[coord].name[0]
                    string += input + '\t\t'
                elif x % 2 != 0 and y % 2 != 0:
                    coord = (x, y)
                    if self.arrayCenters[coord] == '':
                        input = '.'
                    elif self.arrayCenters[coord] == 'c': 
                        input = self.arrayCenters[coord]
                    else:
                        input = self.arrayCenters[coord].name[0]
                    string += '\t' + input + '\t'
                x += 1
        dprint(string)


        '''for coord in coordList:
            
            if self.arrayCenters[coord] == '':
                string += 'X' + '\t'
            else:
                string += self.arrayCenters[coord].name[0] + '\t'
                #dprint(self.arrayCenters[coord].name)
                self.neighbors(coord)
            if coord[0] == maxX:
                string += '\n'
        #dprint(string)'''

