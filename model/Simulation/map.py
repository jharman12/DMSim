import random as r
import math
import inspect
import sys

import pathlib
dmSimPath = str(pathlib.Path(__file__).parent.resolve())[0:-6]
sys.path.insert(1, dmSimPath)
from modelMethods import takeReaction, drawLine
from wall import Wall

class Map:
    def __init__(self, numHex, partyList, enemyList, graphicsViewer=None):
        self.numHex = numHex
        self.graphicsViewer = graphicsViewer
        self.combatLog = None
        
        # Walls are now stored directly in arrayCenters as Wall objects
        
        ##print('defining array')
        if graphicsViewer is not None:
            self.defineArrayGrid(numHex)
        else:
            self.defineArrayGrid(numHex, 1, 0.5)
        ##print('distance')
        #self.distanceCalc(0,23)

        self.party = partyList
        self.enemy = enemyList
        self.populateMap(self.party, self.enemy)
        
        #print('spawns as')
        self.printCurrMap()
        #self.moveToNearest(Ephraim, Arabella)
        
 
    def moveActor(self, mover, coord):
        moverCoord = [x for x in list(self.arrayCenters) if self.arrayCenters[x] == mover][0]
        moverIndex = list(self.arrayCenters).index(moverCoord)
        coordIndex = list(self.arrayCenters).index(coord)
        neighbors = self.neighbors(moverCoord)
        print(neighbors)
        
                
        distance = self.distanceCalc(list(self.arrayCenters).index(moverCoord), list(self.arrayCenters).index(coord))
        print('\t\t',mover.name,'is going from', moverCoord, 'to', coord,'which is a distance of', distance)
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        #print(calframe[1][3])
        if distance > mover.speed/5 and calframe[1][3] != 'dashActor':
            
            raise SystemExit('Crashed in map moveActor')
        self.arrayCenters[moverCoord] = ''
        self.arrayCenters[coord] = mover
        self.printCurrMap()
        if moverCoord != coord:
            if mover in self.party:
                for neig in neighbors:
                    actor = self.arrayCenters[list(self.arrayCenters)[neig]]
                    reactDis = self.distanceCalc(neig, coordIndex)
                    #print(actor)
                    if actor in self.enemy and actor.reaction and reactDis >= 2: 
                        print('youre enemyList', actor.name,'and you should be able to react')
                        takeReaction(actor, self, mover)
            if mover in self.enemy:
                for neig in neighbors:
                    actor = self.arrayCenters[list(self.arrayCenters)[neig]]
                    reactDis = self.distanceCalc(neig, coordIndex)
                    #print(actor)
                    if actor in self.party and actor.reaction and reactDis >= 2:
                        print('youre partyList', actor.name,'and you should be able to react')
                        takeReaction(actor, self, mover)
            # Update graphics viewer if it exists
            if self.graphicsViewer is not None:
                newIndex = self.convertToViewerCoords(coord)
                self.graphicsViewer.moveActor(mover, newIndex)
    
    def dashActor(self, mover, targetCoord):
        print(mover.name, ' is taking the dash action to ', targetCoord)
        movement = 2*(mover.speed/5)
        #targetCoord = [i for i in self.arrayCenters if self.arrayCenters[i] ==target][0]
        moverCoord = [i for i in self.arrayCenters if self.arrayCenters[i] ==mover][0]

        line = drawLine(moverCoord, targetCoord, self)
        #print(line)
        options = [x for x in line if self.distanceCalc(list(self.arrayCenters).index(moverCoord), list(self.arrayCenters).index(x)) <= movement]
        if options[-1] == targetCoord or self.arrayCenters[options[-1]] != '':
            moverIndex = list(self.arrayCenters).index(moverCoord)
            targetIndex = list(self.arrayCenters).index(targetCoord)
            moverNew = self.nearestFreeHex(moverIndex, targetIndex)
            #print('nearestFreeHex chose', moverNew)
            self.moveActor(mover, moverNew)
        else:
            #print('going option[-1]', options[-1])
            self.moveActor(mover, options[-1])
        

    def moveToNearest(self, mover, target):
        #print(mover.name, ' is going to ', target.name)
        if mover == target:
            #self.printCurrMap()
            return
        print(mover, target)
        moverLoc = [i for i in self.arrayCenters if self.arrayCenters[i] == mover][0]
        
        Arabella = target
        #print(moverLoc)
        #print(Arabella)
        moverIndex = list(self.arrayCenters).index(moverLoc)
        Arabella = list(self.arrayCenters).index(Arabella)
        

        moverNew = self.nearestFreeHex(moverIndex, Arabella)
        ##print(moverNew)
        self.moveActor(mover, moverNew)
        ##print(Ephraim)
        #self.arrayCenters[moverLoc] = ''
        #self.arrayCenters[moverNew] = mover
        #self.printCurrMap()

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
        
        print(height, width)
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
        ##print(list(self.arrayCenters)[index1])
        ##print(list(self.arrayCenters)[index2])
        test = self.doubledHeight(list(self.arrayCenters)[index1], list(self.arrayCenters)[index2])
        ##print(test)
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
        totalArea = len(list(self.arrayCenters)) * 25
        totalParty = sum([x.size for x in party])
        totalEnemy = sum([x.size for x in enemy])
        partyEnemyRatio = totalParty/totalEnemy
        maxX = max([x[0] for x in list(self.arrayCenters)])
        maxY = max([x[1] for x in list(self.arrayCenters)])
        ##print(maxY)
        partyX = self.col_round(partyEnemyRatio*maxX/2)
        if partyEnemyRatio > 1:
            newX = 1 - 1/partyEnemyRatio
            partyX = self.col_round(newX*maxX)

        ##print(partyX)
        partySide = []
        enemySide = []
        for key in self.arrayCenters.keys():
            if key[0] <= partyX:
                partySide.append(key)
            else:
                enemySide.append(key)
        ##print(enemySide)
        totalList = [party, enemy]
        for side in totalList:
            for member in side:
                saved = 0
                while saved == 0:
                    if member in party:
                        coord = r.sample(partySide, 1)[0]
                        #print(member.name, coord)
                    else:
                        coord = r.sample(enemySide, 1)[0]
                        #print(member.name, coord)
                    # Check if coordinate is free and not a wall
                    if self.arrayCenters[coord] == '' and not self.isWall(coord):
                        self.arrayCenters[coord] = member
                        # Update graphics viewer if it exists
                        if self.graphicsViewer is not None:
                            gViewerCoord = self.convertToViewerCoords(coord)
                            self.graphicsViewer.moveActor(member, gViewerCoord)
                        saved = 1
                    else:
                        continue
        ##print(self.arrayCenters)
    
    def neighbors(self, testCoord):

        coordList = list(self.arrayCenters)
        testIndex = coordList.index(testCoord)
        distanceList =[self.distanceCalc(testIndex, coordList.index(i)) for i in coordList]
        ##print(len(distanceList))
        yourNeighbors = [i for i, x in enumerate(distanceList) if x == 1 ]
        ##print('Your neighors Cood', [list(self.arrayCenters)[x] for x in yourNeighbors])
        return(yourNeighbors)
    
    def nearestFreeHex(self, startIndex, endIndex):
        ##print(startIndex, endIndex)
        nearIndexList = self.neighbors(list(self.arrayCenters)[endIndex])
        min = 999999
        minIndex = -99 # invalid index to catch if nothing is in reach
        for index in nearIndexList:
            coord = list(self.arrayCenters)[index]
            distance = self.distanceCalc(index, startIndex)
            # Check if hex is free (not occupied by actor or wall)
            if distance <= min and self.arrayCenters[coord] == '' and not self.isWall(coord):
                min = distance
                minIndex = index
        if minIndex == -99:
            minIndex = startIndex
            self.printCurrMap()
            #print(self.arrayCenters[list(self.arrayCenters)[startIndex]], 'going to', self.arrayCenters[list(self.arrayCenters)[endIndex]])
        #print("nearestFreehex", list(self.arrayCenters)[minIndex])
        return list(self.arrayCenters)[minIndex]
        #return minIndex
    
    def convertToMyCoords(self, index):
        """Convert viewer index to map coordinates."""
        centers = list(self.arrayCenters.keys())
        return centers[index]
    
    def convertToViewerCoords(self, coord):
        """Convert map coordinates to viewer index."""
        return list(self.arrayCenters).index(coord)
    
    def addWall(self, coord, hp=20, name="Wall", ac=15):
        """
        Add a wall at the specified coordinate.
        
        Args:
            coord: Tuple (x, y) coordinate for the wall
            hp: Hit points of the wall (default: 20)
            name: Name/description of the wall (default: "Wall")
            ac: Armor class of the wall (default: 15)
        """
        if coord in self.arrayCenters:
            # Create a Wall object and place it in the map
            wall = Wall(name=name, health=hp, ac=ac)
            self.arrayCenters[coord] = wall
            print(f"Added {name} at {coord} with {hp} HP")
            
            # Update graphics viewer if it exists
            if self.graphicsViewer is not None:
                wallIndex = self.convertToViewerCoords(coord)
                self.graphicsViewer.addWall(wallIndex)
        else:
            print(f"Cannot add wall: coordinate {coord} not in map")
    
    def removeWall(self, coord):
        """
        Remove a wall at the specified coordinate.
        
        Args:
            coord: Tuple (x, y) coordinate of the wall to remove
        """
        if self.isWall(coord):
            self.arrayCenters[coord] = ''
            print(f"Removed wall at {coord}")
            
            # Update graphics viewer if it exists
            if self.graphicsViewer is not None:
                wallIndex = self.convertToViewerCoords(coord)
                self.graphicsViewer.removeWall(wallIndex)
        else:
            print(f"No wall at coordinate {coord}")
    
    def damageWall(self, coord, damage):
        """
        Deal damage to a wall. Removes the wall if HP drops to 0 or below.
        
        Args:
            coord: Tuple (x, y) coordinate of the wall
            damage: Amount of damage to deal
            
        Returns:
            bool: True if wall was destroyed, False otherwise
        """
        if self.isWall(coord):
            wall = self.arrayCenters[coord]
            destroyed = wall.takeDamage(damage)
            
            if destroyed:
                self.removeWall(coord)
                return True
            return False
        else:
            print(f"No wall at coordinate {coord}")
            return False
    
    def isWall(self, coord):
        """
        Check if a coordinate contains a wall.
        
        Args:
            coord: Tuple (x, y) coordinate to check
            
        Returns:
            bool: True if coordinate has a wall, False otherwise
        """
        if coord not in self.arrayCenters:
            return False
        obj = self.arrayCenters[coord]
        return hasattr(obj, 'isWall') and obj.isWall
    
    def getWallInfo(self, coord):
        """
        Get information about a wall.
        
        Args:
            coord: Tuple (x, y) coordinate of the wall
            
        Returns:
            Wall object or None: Wall object or None if no wall exists
        """
        if self.isWall(coord):
            return self.arrayCenters[coord]
        return None
    
    def printCurrMap(self):
        string = ''
        coordList = list(self.arrayCenters)
        maxX = max([x[0] for x in list(self.arrayCenters)])
        maxY = max([x[1] for x in list(self.arrayCenters)])
        ##print(maxY)
        for y in range(maxY + 1):
            ##print(y)
            x = 0
            string += '\n'
            while x <= maxX:
                
                if x % 2 == 0 and y % 2 == 0:
                    coord = (x, y)
                    if self.isWall(coord):
                        input = '#'  # Display walls as #
                    elif self.arrayCenters[coord] == '':
                        input = '.'
                    elif self.arrayCenters[coord] == 'c': 
                        input = self.arrayCenters[coord]
                    else:
                        input = self.arrayCenters[coord].name[0]
                    string += input + '\t\t'
                elif x % 2 != 0 and y % 2 != 0:
                    coord = (x, y)
                    if self.isWall(coord):
                        input = '#'  # Display walls as #
                    elif self.arrayCenters[coord] == '':
                        input = '.'
                    elif self.arrayCenters[coord] == 'c': 
                        input = self.arrayCenters[coord]
                    else:
                        input = self.arrayCenters[coord].name[0]
                    string += '\t' + input + '\t'
                x += 1
        print(string)


        '''for coord in coordList:
            
            if self.arrayCenters[coord] == '':
                string += 'X' + '\t'
            else:
                string += self.arrayCenters[coord].name[0] + '\t'
                #print(self.arrayCenters[coord].name)
                self.neighbors(coord)
            if coord[0] == maxX:
                string += '\n'
        #print(string)'''

