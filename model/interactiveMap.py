import random as r
import math
import inspect
import sys


class interactiveMap:
    def __init__(self, numHex, partyList, enemyList):
        self.numHex = numHex
        
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
    
    

    def grabMapLoc(self, index):
        centers = list(self.arrayCenters.keys())
        return centers[index]

    def defineArrayGrid(self, heightNumber, graphicsViewer):
        # convert back to old way of doing things
        # create method for converting hex coord to graphicsViewer coord
        #   reset top_left coords
        #   use r in hCoord and gCoord
        map_rect = graphicsViewer.map_item.boundingRect()
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
