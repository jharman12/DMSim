import random as r
import math
import inspect
import sys
import pathlib

_root = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(1, str(_root))

from engine.combat import takeReaction
from engine.targeting import drawLine
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
        self.walls: set = set()           # hex indices that are impassable walls
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
        dprint(mover.name, ' is taking the dash action to ', targetCoord)
        movement = 2*(mover.speed/5)
        moverCoord = [i for i in self.arrayCenters if self.arrayCenters[i] ==mover][0]
        line = drawLine(moverCoord, targetCoord, self)
        #dprint(line)
        options = [x for x in line
                   if x != moverCoord
                   and self.distanceCalc(list(self.arrayCenters).index(moverCoord),
                                         list(self.arrayCenters).index(x)) <= movement]
        # If no options (movement = 0 or already adjacent with no path), stay put
        if not options:
            return
        
        if self.arrayCenters[options[-1]] != '':
            moverIndex = list(self.arrayCenters).index(moverCoord)
            targetIndex = list(self.arrayCenters).index(targetCoord)
            moverNew = self.nearestFreeHex(moverIndex, targetIndex, actor=mover)
            self.moveActor(mover, moverNew)
        else:
            self.moveActor(mover, options[-1])
        

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

    def defineArrayGrid(self, heightNumber, height=None, width=None):
        """
        Initialize the hexagonal grid. 
        If graphicsViewer is provided, uses its bounding rect; otherwise uses provided height/width.
        """
        if self.graphicsViewer is not None:
            # Use graphics viewer dimensions
            map_rect = self.graphicsViewer.map_item.boundingRect()
            height = map_rect.height() 
            width = map_rect.width()
        else:
            # Use provided dimensions or defaults
            if height is None or width is None:
                height = 1
                width = 0.5
        
        dprint(height, width)
        startingPoint = [0, 0]
        r = height / (2 * (1 + (heightNumber - 1) * 2 * math.cos(math.pi * 60 / 180)))
        self.radius = r
        a = 2 * math.pi / 6
        x, y = startingPoint
        self.arrayCenters = {}
        self.arrayCenters.clear()

        while y + r * math.sin(a) <= height + 2 * startingPoint[1]:
            previousY = y
            previousX = x
            j = 0
            while x + r * (1 + math.cos(a)) <= width + startingPoint[0]:
                a = 2*math.pi /6
                x_mod = self.radius * (1 + math.cos(a))
                y_mod =  self.radius * math.sin(a)
                center = (self.col_round(x/x_mod), self.col_round(y/y_mod))
                self.arrayCenters[center] = ''

                x += r * (1 + math.cos(a))
                y += (-1) ** j * r * math.sin(a)
                j += 1

            x = previousX
            y = previousY
            y += 2 * r * math.sin(a)
        

    def distanceCalc(self, index1, index2):
        ##dprint(list(self.arrayCenters)[index1])
        ##dprint(list(self.arrayCenters)[index2])
        test = self.doubledHeight(list(self.arrayCenters)[index1], list(self.arrayCenters)[index2])
        ##dprint(test)
        return test
    
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

        totalArea = len(list(self.arrayCenters)) * 25
        totalParty = sum([x.size if isinstance(x.size, (int, float)) else 25 for x in party])
        totalEnemy = sum([x.size if isinstance(x.size, (int, float)) else 25 for x in enemy])
        partyEnemyRatio = totalParty / totalEnemy if totalEnemy else 1
        maxX = max([x[0] for x in list(self.arrayCenters)])
        maxY = max([x[1] for x in list(self.arrayCenters)])
        partyX = self.col_round(partyEnemyRatio * maxX / 2)
        if partyEnemyRatio > 1:
            newX = 1 - 1 / partyEnemyRatio
            partyX = self.col_round(newX * maxX)

        partySide = []
        enemySide = []
        for key in self.arrayCenters.keys():
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

        coordList = list(self.arrayCenters)
        testIndex = coordList.index(testCoord)
        distanceList =[self.distanceCalc(testIndex, coordList.index(i)) for i in coordList]
        ##dprint(len(distanceList))
        yourNeighbors = [i for i, x in enumerate(distanceList) if x == 1 ]
        ##dprint('Your neighors Cood', [list(self.arrayCenters)[x] for x in yourNeighbors])
        return(yourNeighbors)
    
    def nearestFreeHex(self, startIndex, endIndex, actor=None):
        from engine.size_utils import get_size_cat, can_place_footprint
        nearIndexList = self.neighbors(list(self.arrayCenters)[endIndex])
        min_dist = 999999
        minIndex = -99
        coords = list(self.arrayCenters)

        # Determine if we need footprint-aware checks
        size_cat = get_size_cat(actor) if actor is not None else 'Medium'
        multi_hex = size_cat not in ('Tiny', 'Small', 'Medium')

        for index in nearIndexList:
            distance = self.distanceCalc(index, startIndex)
            if multi_hex:
                valid = can_place_footprint(coords[index], size_cat, self, actor)
            else:
                valid = self.arrayCenters[coords[index]] == ''
            if valid and distance <= min_dist:
                min_dist = distance
                minIndex = index

        if minIndex == -99:
            minIndex = startIndex
            self.printCurrMap()
        return coords[minIndex]
    
    def convertToMyCoords(self, index):
        """Convert viewer index to map coordinates."""
        centers = list(self.arrayCenters.keys())
        return centers[index]
    
    def convertToViewerCoords(self, coord):
        """Convert map coordinates to viewer index."""
        return list(self.arrayCenters).index(coord)
    
    def printCurrMap(self):
        string = ''
        coordList = list(self.arrayCenters)
        maxX = max([x[0] for x in list(self.arrayCenters)])
        maxY = max([x[1] for x in list(self.arrayCenters)])
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

