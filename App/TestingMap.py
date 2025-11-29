'''
Things to work on:

    
    
    heal is not moving anyone
    
    need to find optimal movement for heal and some spells as well

    add blank image if nothing image = none or cant find path

    create a class for turn choices so that everything has to be uniform
    
    Create encounter play back that goes one turn at a time
        link encounter to map so that everything is calling the same map 
        populate the map in the encounter and place those icons in those hexes
        create method for choosing a possible action during your turn
            optional move to hex (1,2)
            input action some way take turn does
                break actual turn actions 

    
    create display character move range function
    
    add right click to see popup of character stats
    
    create functions similar to bestSphere but with inputted sphere (spells originating from self will be hard)
    create gui for character actions 
        list possible actions
        select target (hex of area or creature if single)
            add not an appropiate target reselect feature for single target
        auto-roll or manual
        display best turn action?
        turn done

    create gui for encounter 
        list turn with icon order at top of the screen 
        Possibly back button to undo a turn

    Create warning for oportunity attacks

    Add distance calc feature

    add display shape when choosing a hex to cast a spell
    
    Make custom player spells (currently just assumes you have access to all spells)
        this will also make the turnchoice faster 
    
'''

from PyQt5.QtWidgets import QApplication, QPushButton, QMainWindow, QWidget, QVBoxLayout
from PyQt5.QtCore import QSize, Qt
#from custom_graphics_view import CustomGraphicsView
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPolygonItem
from PyQt5.QtCore import Qt, QPointF, QRectF, QSizeF
from PyQt5.QtGui import QPixmap, QPen, QPolygonF, QPainter, QPainterPath, QBitmap, QColor, QBrush
import math
from scipy import spatial
import numpy as np
import sys
import pathlib
dmSimPath = str(pathlib.Path(__file__).parent.resolve())[0:-4]
print(dmSimPath)
sys.path.insert(1, dmSimPath + '\\model')
from interactiveMap import interactiveMap
from interactiveEncounter import interactiveEncounter
from player import createPartyList, Player




#class Player:
#    def __init__(self, name, image):
#        self.name = name
#        self.image = image # path to image




class Map:
    def __init__(self, name, image, hexes, myPlayers):
        self.name = name
        self.image = image
        self.hexes = hexes
        self.myPlayers = myPlayers

class CustomGraphicsView(QGraphicsView):
    def __init__(self):
        super().__init__()

        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        self.map_item = None
        self.character_items = []
        self.character_objs = []
        self.hex_items = []  # Added hex_items attribute
        self.selected_item = None
        self.last_mouse_pos = QPointF()
        self.arrayCenters = []

        self.setSceneRect(0, 0, self.width(), self.height())
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    def setMapPixmap(self, pixmap):
        if self.map_item is not None:
            self.scene.removeItem(self.map_item)
        self.map_item = self.scene.addPixmap(pixmap)
        self.map_item.setZValue(0)

    def addCharacterPixmap(self, pixmap, character):
        # add player object to character items to more easily move characters and retrieve character info
        character_item = self.scene.addPixmap(pixmap)
        self.character_objs.append(character)
        self.character_items.append(character_item)
        character_item.setZValue(2)
        if len(self.hex_items) > 0:
            for hex in self.hex_items:
                hex.setZValue(1)
        

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            zoom_factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
            self.scale(zoom_factor, zoom_factor)
            event.accept() # consume event
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.last_mouse_pos = event.pos()
            item = self.itemAt(event.pos())
            if item == self.map_item:
                self.selected_item = item
            elif item in self.character_items:
                self.selected_item = item
            elif item in self.hex_items:  # Check if clicked item is a hexagon
                self.selected_item = item

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.selected_item:
            delta = event.pos() - self.last_mouse_pos
            if self.selected_item == self.map_item or self.selected_item in self.hex_items:
                self.map_item.setPos(self.map_item.pos() + delta)
                for item in self.character_items:
                    item.setPos(item.pos() + delta)
                for hex_item in self.hex_items:
                    hex_item.setPos(hex_item.pos() + delta)
            elif self.selected_item in self.character_items :
                if len(self.hex_items) >0: # grids exist... snap else dont
                    item = self.map_item
                    delta_x, delta_y = item.pos().x(), item.pos().y() # this was originally 0,0 so any off is delta
                    sceneThing = self.mapToScene(event.pos())
                    hexCenters = [[x.x(), x.y()] for x in self.arrayCenters] # grab initial hex x,y

                    hexArrays = np.array(hexCenters) + np.array([delta_x, delta_y]) # self.arrayCenters is original coord. add delta
                    currentArrayIndex = spatial.KDTree(hexArrays).query((sceneThing.x(), sceneThing.y()))[1] # find index of closest hex
                    snap_coord = hexArrays[currentArrayIndex] # find that coord

                    character_size = self.selected_item.boundingRect().size()
                    snap_x = snap_coord[0] - character_size.width() / 2
                    snap_y = snap_coord[1] - character_size.height() / 2
                    #testMap.convertToMyCoords(currentArrayIndex)
                    self.selected_item.setPos(snap_x, snap_y)  # snap to this coord
                else:
                    self.selected_item.setPos(self.selected_item.pos() + delta)
               
            self.last_mouse_pos = event.pos()

    def moveActor(self, actor, newIndex):
        print(actor.name, newIndex)
        index = self.character_objs.index(actor)
        pixmap = self.character_items[index]

        item = self.map_item
        delta_x, delta_y = item.pos().x(), item.pos().y()

        hexCenters = [[x.x(), x.y()] for x in self.arrayCenters] # grab initial hex x,y

        hexArrays = np.array(hexCenters) + np.array([delta_x, delta_y]) # self.arrayCenters is original coord. add delta
        snap_coord = hexArrays[newIndex] # find that coord

        character_size = pixmap.boundingRect().size()
        snap_x = snap_coord[0] - character_size.width() / 2
        snap_y = snap_coord[1] - character_size.height() / 2
        print(snap_x, snap_y)
        pixmap.setPos(snap_x, snap_y)  # snap to this coord

        # this might be kinda hard... 
        # i think I'll have to find delta_x, delta_y
        # find hex polygon from self.arrayCenters
        # find hexes current coords using delta
        # find character based on its current position vs closest hex from starting index
        # snap character to newIndexes current position

        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected_item = None


    def drawHexGrid(self, heightNumber, map_rect):
        if heightNumber == 0:
            self.arrayCenters.clear()
            self.clearGrid()
            return
        height = map_rect.height()
        width = map_rect.width()
        map_item_pos = self.map_item.pos()
        top_left_x = map_item_pos.x()
        top_left_y = map_item_pos.y()
        print("in DrawHexGrid", [top_left_x, top_left_y])
        startingPoint = [top_left_x, top_left_y]
        r = height / (2 * (1 + (heightNumber - 1) * 2 * math.cos(math.pi * 60 / 180)))
        self.radius = r
        a = 2 * math.pi / 6
        x, y = startingPoint
        x = x + r 
        y += r * math.sin(a)
        self.arrayCenters.clear()
        self.clearGrid()
        self.hex_items.clear()

        while y + r * math.sin(a) <= height + 2 * startingPoint[1] :
            previousY = y
            previousX = x
            j = 0
            while x + r * (1 + math.cos(a)) <= width + startingPoint[0] + r :
                center = QPointF(x, y)
                self.arrayCenters.append(center)

                # Draw hexagon at center
                hex_points = []
                for i in range(6):
                    angle_rad = a * i
                    x_i = x + r * math.cos(angle_rad)
                    y_i = y + r * math.sin(angle_rad)
                    hex_points.append(QPointF(x_i, y_i))

                hex_polygon = QGraphicsPolygonItem()
                hex_polygon.setPolygon(QPolygonF(hex_points))
                # Set fill and outline colors
                
                self.scene.addItem(hex_polygon)
                self.hex_items.append(hex_polygon)  # Store hexagon in hex_items

                x += r * (1 + math.cos(a))
                y += (-1) ** j * r * math.sin(a)
                j += 1

            x = previousX
            y = previousY
            y += 2 * r * math.sin(a)

        if heightNumber > 0:
            hex_size = QSizeF(4*r * (1+ math.cos(a))/3, 2*r * math.sin(a))  # Adjust size as needed
            hex_path = self.createHexagonPath(hex_size.toSize())

            # Iterate over character items
            for character_item in self.character_items:
                # Resize the character's image to fit within the hexagon
                character_pixmap = character_item.pixmap().scaled(hex_size.toSize(), Qt.KeepAspectRatio)

                # Create a painter path for the character image
                character_path = QPainterPath()
                character_path.addRect(QRectF(QPointF(), hex_size))

                # Clip the character image with the hexagon path
                character_path = character_path.intersected(hex_path)

                # Create a new pixmap and paint the character image onto it
                combined_pixmap = QPixmap(hex_size.toSize())
                combined_pixmap.fill(Qt.transparent)
                painter = QPainter(combined_pixmap)
                painter.setClipPath(character_path)
                painter.drawPixmap(combined_pixmap.rect(), character_pixmap)
                painter.end()

                # Set the combined pixmap as the pixmap for the character item
                character_item.setPixmap(combined_pixmap)
        # Testing changing colors
        fill_color = QColor(0, 0, 255, 50) 
        hexLength = len(self.hex_items)
        allHexIndexes =  [ int(x) for x in np.linspace(0, hexLength-1, hexLength)]
        print(hexLength, allHexIndexes)
        self.setHexColors(fill_color, allHexIndexes)
    
    def setHexColors(self, fill_color, indexes):
        
        brush = QBrush(fill_color) 
        # For a solid outline, you can use an opaque color
        outline_color = QColor(0, 0, 0, 255) # Black, fully opaque
        pen = QPen(outline_color)
        pen.setWidth(2)
        for ind in indexes:
            hex_polygon = self.hex_items[ind]
            hex_polygon.setBrush(brush)
            hex_polygon.setPen(pen)

    def createHexagonPath(self, size):
        path = QPainterPath()
        path.moveTo(size.width() / 4, 0)
        path.lineTo(3 * size.width() / 4, 0)
        path.lineTo(size.width(), size.height() / 2)
        path.lineTo(3 * size.width() / 4, size.height())
        path.lineTo(size.width() / 4, size.height())
        path.lineTo(0, size.height() / 2)
        path.closeSubpath()
        return path
   

    def clearGrid(self):
        # Clear all grid items from the scene
        for item in self.scene.items():
            if isinstance(item, QGraphicsPolygonItem):
                self.scene.removeItem(item)

class MapWidget(QWidget):
    def __init__(self, myEncounter):
        super().__init__()
        global testMap
        layout = QVBoxLayout()

        self.graphics_view = CustomGraphicsView()
        layout.addWidget(self.graphics_view)

        # set map max background
        pixmap = QPixmap(myEncounter.mapImage)
        self.graphics_view.setMapPixmap(pixmap)

        # Add every player to the map
        for player in myEncounter.totalList:
            print(player.Image, 'Trying to create character pixmap')
            pixmap = QPixmap(dmSimPath + player.Image)
            self.graphics_view.addCharacterPixmap(pixmap, player)

        # Add hexes
        num_vertical_grids = int(myEncounter.numHexes)
        map_rect = self.graphics_view.map_item.boundingRect()
        self.graphics_view.drawHexGrid(num_vertical_grids, map_rect)

        self.myEncounter = myEncounter

        self.run_button = QPushButton("start encounters")
        self.run_button.clicked.connect(self.run_command)
        layout.addWidget(self.run_button)
        
        # below will be an encounter object that is passed into this widget later 
        # for now lets just do it here for testings purposes

        # create new encounter class and define it here 
        #testMap = interactiveMap(num_vertical_grids, [], [], self.graphics_view)
        #testMap.defineArrayGrid(num_vertical_grids)
        #testMap.printCurrMap()
        #testMap.convertToGCoord(self.graphics_view, [0,1])
        
        
        
        self.setLayout(layout)
        # might have to split up encounter into functions
        self.testingTheory()
    
    def run_command(self):
        # this crashes with input... in order to get this working, will need to create atleast a dialog box
        # for the inputs... everything else can still print out...
        # this means that I am going to have to change the interactive encounter and taketurn func
        #   probably not to hard... most of it at least
        #       remove chooseAction function entirely and create dialog box for each of those questions
        #       split combat out of while loop with a "next" type function
        #           This will go next when doAction called 
        #   
        self.myEncounter.combat()

    def testingTheory(self):
        
        self.myEncounter.preCombat(self.graphics_view)
            

    
        
dmSimPath = str(pathlib.Path(__file__).parent.resolve())[0:-4]
print(dmSimPath)

path = dmSimPath + '\\actors\\savedObjs\\'
myPlayers = createPartyList(['Ephraim', 'Arabella'], path = path)
badGuys = createPartyList(['Root', 'Darian'], path = path)
myEncounter = interactiveEncounter(myPlayers, [], badGuys, 20, dmSimPath + "\\App\\Maps\\maze Engine.webp")
#myMap = Map('mazeEngine',dmSimPath + "\\App\\Maps\\maze Engine.webp", 10, myPlayers)

app = QApplication([])

window = MapWidget(myEncounter)
window.show()

app.exec()


