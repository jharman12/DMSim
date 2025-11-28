import random as r
import math
import inspect
import sys

import pathlib
dmSimPath = str(pathlib.Path(__file__).parent.resolve())[0:-6]
sys.path.insert(1, dmSimPath)
from modelMethods import takeReaction, drawLine

class interactiveMap:
    def __init__(self, numHex, partyList, enemyList, graphicsViewer):
        self.numHex = numHex
        self.graphicsViewer = graphicsViewer
        ##print('defining array')
        #self.defineArrayGrid(numHex, 100, 100)
        ##print('distance')
        #self.distanceCalc(0,23)

        self.party = partyList
        self.enemy = enemyList
        #self.populateMap(self.party, self.enemy)

    def col_round(self, x):
        frac = x - math.floor(x)
        if frac <= 0.5: return math.floor(x)
        return math.ceil(x)
    
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
        # now should I take a reaction and actually move in graphics Viewer
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
            # now move in graphics veiwer is map moves
            if self.graphicsViewer != None: # i might want to use a self.graphicsViewer here instead as to not change medol methods
                
                # find starting index and ending index
                oldIndex = self.convertToViewerCoords(moverCoord)
                newIndex = self.convertToViewerCoords(coord)
                self.graphicsViewer.moveActor(newIndex)
                
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

    def distanceCalc(self, index1, index2):
        ##print(list(self.arrayCenters)[index1])
        ##print(list(self.arrayCenters)[index2])
        test = self.doubledHeight(list(self.arrayCenters)[index1], list(self.arrayCenters)[index2])
        ##print(test)
        return test

    def convertToMyCoords(self, index):
        # viewer and interactive map shares common index but interactive map needs coords not index 
        centers = list(self.arrayCenters.keys())
        return centers[index]
    
    def convertToViewerCoords(self, coord):
        # viewer and interactive map shares common index but interactive map needs coords not index 
        return list(self.arrayCenters).index(coord)


    def defineArrayGrid(self, heightNumber):
        # convert back to old way of doing things
        # create method for converting hex coord to graphicsViewer coord
        #   reset top_left coords
        #   use r in hCoord and gCoord
        map_rect = self.graphicsViewer.map_item.boundingRect()
        # height and width only matters with their relationship to each other
        # radius is calculated in relationship to height, so just creates hexes 
        #   until hexes reach the width
        height = map_rect.height() 
        width = map_rect.width()

        
        
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

    def doubledHeight(self, a, b):
        drow = abs(a[1] - b[1])
        dcol = abs(a[0] - b[0])
        return dcol + max(0, (drow - dcol)/2)
    
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
