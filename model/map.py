import random as r
import math
import inspect
import sys

import pathlib
dmSimPath = str(pathlib.Path(__file__).parent.resolve())[0:-6]
sys.path.insert(1, dmSimPath)
from modelMethods import takeReaction, drawLine

class Map:
    def __init__(self, numHex, partyList, enemyList):
        self.numHex = numHex
        ##print('defining array')
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
                    #print(actor)
                    if actor in self.enemy and actor.reaction:
                        print('youre enemyList', actor.name,'and you should be able to react')
                        takeReaction(actor, self, mover)
            if mover in self.enemy:
                for neig in neighbors:
                    actor = self.arrayCenters[list(self.arrayCenters)[neig]]
                    #print(actor)
                    if actor in self.party and actor.reaction:
                        print('youre partyList', actor.name,'and you should be able to react')
                        takeReaction(actor, self, mover)
    
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
        moverLoc = [i for i in self.arrayCenters if self.arrayCenters[i] == mover][0]
        
        Arabella = [i for i in self.arrayCenters if self.arrayCenters[i] ==target][0]
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

    def defineArrayGrid(self, heightNumber, height, width):
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
                    if self.arrayCenters[coord] == '':
                        self.arrayCenters[coord] = member
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
            distance = self.distanceCalc(index, startIndex)
            if distance <= min and self.arrayCenters[list(self.arrayCenters)[index]] == '':
                min = distance
                minIndex = index
        if minIndex == -99:
            minIndex = startIndex
            self.printCurrMap()
            #print(self.arrayCenters[list(self.arrayCenters)[startIndex]], 'going to', self.arrayCenters[list(self.arrayCenters)[endIndex]])
        #print("nearestFreehex", list(self.arrayCenters)[minIndex])
        return list(self.arrayCenters)[minIndex]
        #return minIndex
    
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

