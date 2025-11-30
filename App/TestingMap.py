'''
Things to work on:

    
    encounter playback now works (only chooses best action for right now)
        model crashes when a character dies??
        interactiveEncounter.calcTurn returns none
    
    removeDeadActor also needs to remove from GUI
        move method to do action
    
    move leg actions to doAction?
        it does not belong in calcTurn as thats just returning best action

    heal is not moving anyone
    
    need to find optimal movement for heal and some spells as well

    
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
import os
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea, QFrame, QProgressBar, QComboBox
)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QSize
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
#from interactiveMap import interactiveMap
from interactiveEncounter import interactiveEncounter
from player import createPartyList
from monster import createMonsterList, Monster
from modelMethods import myAction, doAction


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

        self.hex_centers_base = []
        self.hex_tree = None

        self.setRenderHints(
            QPainter.Antialiasing
            | QPainter.SmoothPixmapTransform
        )
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)


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
        # Zoom factor
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor

        # Determine zoom direction
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        # Apply zoom to the view (not individual items!)
        self.scale(zoom_factor, zoom_factor)
        event.accept()

    #def wheelEvent(self, event):
    #    if event.modifiers() == Qt.ControlModifier:
    #        zoom_factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
    #        self.scale(zoom_factor, zoom_factor)
    #        event.accept() # consume event
    #    else:
    #        super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.last_mouse_pos = event.pos()
            item = self.itemAt(event.pos())
            self.selected_item = None # gpt added

            if item == self.map_item:
                self.selected_item = item
            elif item in self.character_items:
                self.selected_item = item
            elif item in self.hex_items:  # Check if clicked item is a hexagon
                self.selected_item = item

        super().mousePressEvent(event)

    #def mouseMoveEvent(self, event):
    #    if event.buttons() == Qt.LeftButton and self.selected_item:
    #        delta = event.pos() - self.last_mouse_pos
    #        if self.selected_item == self.map_item or self.selected_item in self.hex_items:
    #            self.map_item.setPos(self.map_item.pos() + delta)
    #            for item in self.character_items:
    #                item.setPos(item.pos() + delta)
    #            for hex_item in self.hex_items:
    #                hex_item.setPos(hex_item.pos() + delta)
    #        elif self.selected_item in self.character_items :
    #            if len(self.hex_items) >0: # grids exist... snap else dont
    #                item = self.map_item
    #                delta_x, delta_y = item.pos().x(), item.pos().y() # this was originally 0,0 so any off is delta
    #                sceneThing = self.mapToScene(event.pos())
    #                hexCenters = [[x.x(), x.y()] for x in self.arrayCenters] # grab initial hex x,y
    #
    #                hexArrays = np.array(hexCenters) + np.array([delta_x, delta_y]) # self.arrayCenters is original coord. add delta
    #                currentArrayIndex = spatial.KDTree(hexArrays).query((sceneThing.x(), sceneThing.y()))[1] # find index of closest hex
    #                snap_coord = hexArrays[currentArrayIndex] # find that coord
    #
    #                character_size = self.selected_item.boundingRect().size()
    #                snap_x = snap_coord[0] - character_size.width() / 2
    #                snap_y = snap_coord[1] - character_size.height() / 2
    #                #testMap.convertToMyCoords(currentArrayIndex)
    #                self.selected_item.setPos(snap_x, snap_y)  # snap to this coord
    #            else:
    #                self.selected_item.setPos(self.selected_item.pos() + delta)
    #           
    #        self.last_mouse_pos = event.pos()
        

    def mouseMoveEvent(self, event):
        
        if event.buttons() == Qt.LeftButton and self.selected_item:
            # Convert view-space delta into scene-space delta
            old_pos_scene = self.mapToScene(self.last_mouse_pos)
            new_pos_scene = self.mapToScene(event.pos())
            delta_scene = new_pos_scene - old_pos_scene

            if self.selected_item == self.map_item or self.selected_item in self.hex_items:
                self.map_item.setPos(self.map_item.pos() + delta_scene)
                for item in self.character_items:
                    item.setPos(item.pos() + delta_scene)
                for hex_item in self.hex_items:
                    hex_item.setPos(hex_item.pos() + delta_scene)

            elif self.selected_item in self.character_items:
                # snapping branch unchanged except for using scene pos
                
                if self.hex_tree is not None:
                    scene_pos = self.mapToScene(event.pos())
                    # transform back into "map local" coords
                    map_offset = self.map_item.pos()
                    local_x = scene_pos.x() - map_offset.x()
                    local_y = scene_pos.y() - map_offset.y()

                    dist, idx = self.hex_tree.query((local_x, local_y))
                    snap_center_local = self.hex_centers_base[idx]
                    snap_center_scene = (
                        snap_center_local[0] + map_offset.x(),
                        snap_center_local[1] + map_offset.y()
                    )
                    character_size = self.selected_item.boundingRect().size()
                    snap_x = snap_center_scene[0] - character_size.width() / 2
                    snap_y = snap_center_scene[1] - character_size.height() / 2
                    self.selected_item.setPos(snap_x, snap_y)
                #if len(self.hex_items) > 0:
                    #item = self.map_item
                    #delta_x, delta_y = item.pos().x(), item.pos().y()

                    
                    #scene_pos = self.mapToScene(event.pos())
                    #hex_centers = [[x.x(), x.y()] for x in self.arrayCenters]

                    #hex_arrays = np.array(hex_centers) + np.array([delta_x, delta_y])
                    #current_index = spatial.KDTree(hex_arrays).query((scene_pos.x(), scene_pos.y()))[1]
                    #snap_coord = hex_arrays[current_index]

                    #character_size = self.selected_item.boundingRect().size()
                    #snap_x = snap_coord[0] - character_size.width() / 2
                    #snap_y = snap_coord[1] - character_size.height() / 2
                    #self.selected_item.setPos(snap_x, snap_y)
                else:
                    self.selected_item.setPos(self.selected_item.pos() + delta_scene)

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
        
        startingPoint = [top_left_x, top_left_y]
        r = height / (2 * (1 + (heightNumber - 1) * 2 * math.cos(math.pi * 60 / 180)))
        self.radius = r
        a = 2 * math.pi / 6
        x, y = startingPoint
        x = x + r 
        y += r * math.sin(a)
        self.arrayCenters.clear()
        self.clearGrid()
        

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
        
        
        self.hex_centers_base = [(c.x(), c.y()) for c in self.arrayCenters]
        self.hex_tree = spatial.KDTree(self.hex_centers_base)

        # Testing changing colors
        fill_color = QColor(0, 0, 255, 50) 
        hexLength = len(self.hex_items)
        allHexIndexes =  [ int(x) for x in np.linspace(0, hexLength-1, hexLength)]
        
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
        # Remove only hex grid items
        for item in self.hex_items:
            self.scene.removeItem(item)
        self.hex_items.clear()

    def addRedOutline(self, pixmap, thickness=3):
        """
        Returns a new QPixmap with a red outline drawn around it.
        :param pixmap: QPixmap to outline
        :param thickness: outline width in pixels
        """
        # Create a new pixmap big enough for outline
        outlined = QPixmap(pixmap.width() + thickness*2, pixmap.height() + thickness*2)
        outlined.fill(Qt.transparent)

        painter = QPainter(outlined)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw original pixmap
        painter.drawPixmap(thickness, thickness, pixmap)

        # Red outline
        pen = QPen(Qt.red)
        pen.setWidth(thickness)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        # Outline rectangle
        painter.drawRect(
            thickness // 2,
            thickness // 2,
            pixmap.width() + thickness,
            pixmap.height() + thickness
        )

        painter.end()

        return outlined

    def remove_red_outline(self, pixmap):
        """
        Removes a 1-pixel red outline previously drawn around the pixmap.
        Assumes the outline was drawn as a rectangle around the border.
        """
        if pixmap.isNull():
            return pixmap

        # the outline thickness you used earlier
        outline = 1

        # Crop the pixmap to remove the border
        cropped = pixmap.copy(
            outline,
            outline,
            pixmap.width() - outline * 2,
            pixmap.height() - outline * 2
        )

        return cropped
class TurnOrderWidget(QWidget):
    def __init__(self):
        super().__init__()

        layout = QHBoxLayout()
        layout.setSpacing(10)

        # Placeholder icons
        placeholder_pix = QPixmap(50, 50)
        placeholder_pix.fill(Qt.darkGray)

        # Current turn icon
        self.current_icon = QLabel()
        self.current_icon.setPixmap(placeholder_pix)
        self.current_icon.setFixedSize(50, 50)

        layout.addWidget(self.current_icon)

        # Next 5 turn icons
        self.next_icons = []
        for _ in range(5):
            lbl = QLabel()
            lbl.setPixmap(placeholder_pix)
            lbl.setFixedSize(40, 40)
            layout.addWidget(lbl)
            self.next_icons.append(lbl)

        layout.addStretch()
        self.setLayout(layout)

class TurnActionPanel(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        # -------------------------------
        # TURN INDICATOR
        # -------------------------------
        self.turn_label = QLabel("Current Turn: Placeholder")
        self.turn_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.turn_label)

        # -------------------------------
        # HEALTH BAR
        # -------------------------------
        health_layout = QHBoxLayout()
        self.health_bar = QProgressBar()
        self.health_bar.setValue(100)  # placeholder value
        self.health_bar.setTextVisible(False)
        health_layout.addWidget(self.health_bar)

        self.health_label = QLabel("100 / 100")  # placeholder health text
        health_layout.addWidget(self.health_label)

        main_layout.addLayout(health_layout)

        # -------------------------------
        # ACTION DROP-DOWN
        # -------------------------------
        self.action_dropdown = QComboBox()
        self.action_dropdown.addItems(["Attack", "Cast Spell", "Dash", "Use Item"])  # placeholder actions
        main_layout.addWidget(self.action_dropdown)

        # -------------------------------
        # Targets input
        # -------------------------------
        self.targets_input = QLineEdit()
        self.targets_input.setPlaceholderText("Targets")
        main_layout.addWidget(self.targets_input)

        # -------------------------------
        # Move coords input
        # -------------------------------
        self.move_input = QLineEdit()
        self.move_input.setPlaceholderText("Move Coords")
        main_layout.addWidget(self.move_input)

        # -------------------------------
        # Take Turn button
        # -------------------------------
        self.take_turn_button = QPushButton("Take Turn")
        #self.take_turn_button.clicked.connect(self.take_turn)
        main_layout.addWidget(self.take_turn_button)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def update_turn_panel(self, actor, turnChoices, turnChoice):
        """
        Update the entire turn panel with new values.

        :param turn_name: str, text for whose turn it is
        :param current_health: int, current health value
        :param max_health: int, maximum health value
        :param actions: list of str, available actions for dropdown
        :param selected_action: str, currently selected action
        :param targets: str, text for targets input
        :param move_coords: str, text for move coords input
        """
        # Update turn label
        
        self.turn_label.setText(f"Current Turn: {actor.name}")

        # Update health bar and health text
        
        self.health_bar.setMaximum(int(actor.maxHealth))
        self.health_bar.setValue(int(actor.health))
        self.health_label.setText(f"{actor.health} / {actor.maxHealth}")

        # Update action dropdown
        actions = [x.name for x in turnChoices]
        self.action_dropdown.clear() 
        self.action_dropdown.addItems(actions)

        # Set selected action if provided
        selected_action = turnChoice.name
        index = self.action_dropdown.findText(selected_action)
        self.action_dropdown.setCurrentIndex(index)

        # Update targets input
        targets = str(turnChoice.targets)
        self.targets_input.setText(targets)

        # Update move coords input
        move_coords = str(turnChoice.moveCoord)
        self.move_input.setText(move_coords)

class MapWidget(QWidget):
    def __init__(self, myEncounter):
        super().__init__()

        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)

         # ---- Top: Turn Order Indicator ----
        self.turn_order_widget = TurnOrderWidget()
        main_layout.addWidget(self.turn_order_widget)

        # ---- Middle: Map + Right Panel ----
        mid_layout = QHBoxLayout()

        # Map widget
        self.map_view = CustomGraphicsView()
        self.map_view.setFrameShape(QFrame.Box)
        self.map_view.setMinimumSize(900, 700)
        mid_layout.addWidget(self.map_view, 3)

        # set map max background
        pixmap = QPixmap(myEncounter.mapImage)
        self.map_view.setMapPixmap(pixmap)

        # Add every player to the map
        for player in myEncounter.totalList:
            print(player.Image, 'Trying to create character pixmap')
            if player.Image == None:
                pixmap = QPixmap(dmSimPath + "\\App\\unknown.jpg")
            elif os.path.exists(dmSimPath + player.Image):
                
                #pixmap = QPixmap(dmSimPath + "\\App\\unknown.jpeg")
                pixmap = QPixmap(dmSimPath + player.Image)
            else:
                print("path doesnt exist, trying unknown")
                pixmap = QPixmap(dmSimPath + "\\App\\unknown.jpg")
            self.map_view.addCharacterPixmap(pixmap, player)
        
        # Add hexes
        num_vertical_grids = int(myEncounter.numHexes)
        map_rect = self.map_view.map_item.boundingRect()
        self.map_view.drawHexGrid(num_vertical_grids, map_rect)

        self.myEncounter = myEncounter


        # Right-side panel
        self.turn_action_panel = TurnActionPanel()
        self.turn_action_panel.setFixedWidth(250)
        self.turn_action_panel.take_turn_button.clicked.connect(self.takeTurnButton)
        self.turnChoices = None
        self.turnChoice = None
        self.actor = None
        mid_layout.addWidget(self.turn_action_panel, 1)

        main_layout.addLayout(mid_layout)

        # ---- Bottom: Start Encounter Button ----
        self.start_button = QPushButton("Start Encounter")
        self.start_button.setFixedHeight(40)
        self.start_button.clicked.connect(self.run_command)

        main_layout.addWidget(self.start_button)

        self.setLayout(main_layout)
        
        self.testingTheory()
    
    def takeTurnButton(self):
        # now load inputs and and call doAction function
        #myAction(name =, type=, mod=, numHit=, currCoord=, moveCoord=, targets=, castCoord=)
        # grab name of spell
        if self.turnChoice != None and self.actor != None: # for now just do the best action. will work on actually choosing action
            doAction(self.actor, self.myEncounter.map, self.turnChoice)
            self.myEncounter.nextTurn()
            turns = self.myEncounter.calcTurn()
            if turns != None:
                self.actor = turns[0]
                self.turnChoices = turns[2]
                self.turnChoice = turns[3]
                self.turn_action_panel.update_turn_panel(self.actor, self.turnChoices, self.turnChoice)

        pass
    def run_command(self):
        
        turns = self.myEncounter.calcTurn()
        if turns != None:
            self.actor = turns[0]
            self.turnChoices = turns[2]
            self.turnChoice = turns[3]
            self.turn_action_panel.update_turn_panel(self.actor, self.turnChoices, self.turnChoice)

    def testingTheory(self):
        # should populate turn_order_widget
        # create the initial movement grids highlight 

        self.myEncounter.preCombat(self.map_view)
        curActor = list(self.myEncounter.sortedInitList)[self.myEncounter.curTurn]
        index = self.map_view.character_objs.index(curActor)
        item = self.map_view.character_items[index] 
        pixMap = item.pixmap()
        outlined = self.map_view.addRedOutline(pixmap=pixMap)
        item.setPixmap(outlined)
        #removeOutline = self.map_view.remove_red_outline(pixMap)
        #item.setPixmap(removeOutline)

    
        
dmSimPath = str(pathlib.Path(__file__).parent.resolve())[0:-4]
print(dmSimPath)

path = dmSimPath + '\\actors\\savedObjs\\'
myPlayers = createPartyList(['Ephraim', 'Arabella', 'Root', 'Darian'], path = path)
badGuys = createMonsterList(["Quenth"] + ["Demogorgon" for i in range(1)], path = path)
myEncounter = interactiveEncounter(myPlayers, [], badGuys, 20, dmSimPath + "\\App\\Maps\\maze Engine.webp")
#myMap = Map('mazeEngine',dmSimPath + "\\App\\Maps\\maze Engine.webp", 10, myPlayers)

app = QApplication([])

window = MapWidget(myEncounter)
window.show()

app.exec()


