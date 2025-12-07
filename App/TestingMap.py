'''
Things to work on:


    MODEL CHANGES ***************************************************************************
    melee still calling nearestHex when inside melee range
    
    move leg actions to doAction?
        it does not belong in calcTurn as thats just returning best action

    heal is not moving anyone
    
    need to find optimal movement for heal and some spells as well

    Make custom player spells (currently just assumes you have access to all spells)
        this will also make the turnchoice faster 

    Eventually, check that model sim actually works and calls all of the same methods as interactive
        finding a lot of errors in the model while playing out (best choice is always the best choice)

    add specific status effects to characters during their turn
        a lot of work here
    
    add unique spell interaction (outside of basic)
        bonus actions
        concentration
        hex like spells
    GUI CHANGES *****************************************************************************

    
    create best square
        choose which op to do (currently just does a default operation)
    figure out targeting of non spells
        melee is just a 1 hex sphere
    
    show character spell slots
    
    prevent doAction if error occurs with warning of that error?

    show calc action mod??

    properly get changing action drop box reset hex colors and untoggle spell area button if checked

    move character to on GV to what the best location is?
    
            
    
    Build model log
        must also make print statements into a file
        display contents of file to either popup window or somwhere on the main window

    might want to move add/remove red line to before move as its not centering icons

    Add/remove is hard coded thickness? (overtime it is making the icon turn into a square)
    
    

    create gui for character actions 
        auto-roll or manual
        disaggregate move, action and turn done    
        turn done
    

    Create warning for oportunity attacks

    Add distance calc feature

    
    
    
    
'''




import os

import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy,
    QLabel, QPushButton, QLineEdit, QScrollArea, QFrame, QProgressBar, QComboBox, QSplitter, QSplitterHandle
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont

from PyQt5.QtGui import QPixmap, QIcon

from PyQt5.QtWidgets import QApplication, QPushButton, QMainWindow, QWidget, QVBoxLayout
from PyQt5.QtCore import QSize, Qt

from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPolygonItem
from PyQt5.QtCore import Qt, QPointF, QRectF, QSizeF, pyqtSignal
from PyQt5.QtGui import QPixmap, QPen, QPolygonF, QPainter, QPainterPath, QBitmap, QColor, QBrush
import math
from scipy import spatial
import numpy as np
import sys
from functools import lru_cache
import pathlib
import re
dmSimPath = str(pathlib.Path(__file__).parent.resolve())[0:-4]
print(dmSimPath)
sys.path.insert(1, dmSimPath + '\\model')
#from interactiveMap import interactiveMap
from interactiveEncounter import interactiveEncounter
from player import createPartyList
from monster import createMonsterList, Monster
from modelMethods import myAction, doAction, drawLine, calcMoveHexes


#class Player:
#    def __init__(self, name, image):
#        self.name = name
#        self.image = image # path to image






        

        


class CustomGraphicsView(QGraphicsView):
    affectedSaved = pyqtSignal(list)
    def __init__(self, encounter):
        super().__init__()

        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        self.spellAreaCheck = False
        self.spellAreaType = None
        self.spellRange = None
        self.spellDistance = None
        self.encounter = encounter
        self.curActor = None
        self.curMoveCoords = None

        self.info_popup = None
        self.map_item = None
        self.character_items = []
        self.character_objs = []
        self.hex_items = []  # Added hex_items attribute
        self.selected_item = None
        self.last_mouse_pos = QPointF()
        self.arrayCenters = []

        self.hex_centers_base = []
        self.hex_tree = None

        self.spell_centers = []
        self.spell_tree = None
        self.spell_index = []

        self.setSceneRect(0, 0, self.width(), self.height())
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        self.setRenderHints(
            QPainter.Antialiasing
            | QPainter.SmoothPixmapTransform
        )
        self.defaultFill = QColor(0, 0, 255, 50) 
        self.moveFill =  QColor(0, 255, 0, 50) 
        self.coneFill =  QColor(255, 0, 0, 50) 
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)

        self.affected = None

    def setCurTurn(self, actor):
        self.curActor = actor

    def setCurMoveCoords(self, indexes):
        self.curMoveCoords = indexes

        # Reset all hex colors to default
        self.setHexColors(self.defaultFill, [i for i in range(len(self.hex_items))])

        # Highlight the newly allowed movement hexes
        self.setHexColors(self.moveFill, indexes)

        # Rebuild the snap tree here
        self.build_snap_tree(indexes)

    def build_snap_tree(self, indexes):
        """
        Build a KD-Tree for snapping characters, using only the hexes
        passed in `indexes`. This allows snapping only to allowed hexes.
        """

        # Build list of (x, y) coordinates for *allowed* hexes
        snap_centers = [self.hex_centers_base[i] for i in indexes]

        if not snap_centers:
            self.snap_centers = []
            self.snap_tree = None
            return

        # Store filtered centers
        self.snap_centers = snap_centers

        # Build KD-Tree from filtered centers
        self.snap_tree = spatial.KDTree(self.snap_centers)

        #print("Snap KD-Tree built with", len(self.snap_centers), "hexes")
    
    def build_spell_tree(self, indexes):
        snap_centers = [self.hex_centers_base[i] for i in indexes]

        if not snap_centers:
            self.spell_centers = []
            self.spell_tree = None
            return

        self.spell_centers = snap_centers
        self.spell_index = indexes

        self.spell_tree = spatial.KDTree(self.spell_centers)

    def getSnapSpellIndex(self, scene_pos):
        if not self.spell_tree:
            return None

        map_offset = self.map_item.pos()
        local_x = scene_pos.x() - map_offset.x()
        local_y = scene_pos.y() - map_offset.y()

        dist, snap_idx = self.spell_tree.query((local_x, local_y))

        # Convert snap_idx → real index in hex grid
        
        return snap_idx
    
    def getSnapHexIndex(self, scene_pos):
        if not self.snap_tree:
            return None

        map_offset = self.map_item.pos()
        local_x = scene_pos.x() - map_offset.x()
        local_y = scene_pos.y() - map_offset.y()

        dist, snap_idx = self.snap_tree.query((local_x, local_y))

        # Convert snap_idx → real index in hex grid
        real_hex_index = self.curMoveCoords[snap_idx]
        return real_hex_index

    def show_character_popup(self, character_obj, scene_pos):
        """
        Displays an info popup inside the graphics view near the scene position.
        """
        # Remove existing popup
        if self.info_popup:
            self.info_popup.deleteLater()
            self.info_popup = None

        # Create popup container
        popup = QFrame(self)
        popup.setStyleSheet("""
            QFrame {
                background-color: #2c2c2c;
                border: 2px solid red;
                border-radius: 6px;
            }
            QLabel {
                color: white;
            }
        """)
        popup.setFrameShape(QFrame.Box)

        layout = QVBoxLayout(popup)
        layout.setContentsMargins(8, 8, 8, 8)

        # Build text from the character object
        # (You can replace this with whatever attributes exist)
        info_text = (
            f"<b>{character_obj.name}</b><br>"
            f"HP: {character_obj.health}/{character_obj.maxHealth}<br>"
            f"AC: {character_obj.ac}<br>"
            f"Speed: {character_obj.speed}<br>"
        )

        label = QLabel(info_text)
        label.setWordWrap(True)
        layout.addWidget(label)

        popup.adjustSize()

        # Convert scene → view coords
        view_pos = self.mapFromScene(scene_pos)

        # Position popup slightly offset
        popup.move(view_pos.x() + 10, view_pos.y() + 10)
        popup.show()

        self.info_popup = popup

    def hide_character_popup(self):
        if self.info_popup:
            self.info_popup.deleteLater()
            self.info_popup = None

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

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.RightButton:
            scene_pos = self.mapToScene(event.pos())

            # Check if clicked a character icon
            clicked_item = self.itemAt(event.pos())

            if clicked_item in self.character_items:
                index = self.character_items.index(clicked_item)
                character_obj = self.character_objs[index]

                # Show popup
                self.show_character_popup(character_obj, scene_pos)
            else:
                # Clicked elsewhere → hide popup
                self.hide_character_popup()
                super().mousePressEvent(event)
                return
        if event.button() == Qt.LeftButton:
            self.last_mouse_pos = event.pos()
            item = self.itemAt(event.pos())
            self.selected_item = None # gpt added
            if self.spellAreaCheck != None and self.affected != None:
                self.affectedSaved.emit(self.affected)
                self.spellAreaCheck = None

            if item == self.map_item:
                self.selected_item = item
            elif item in self.character_items:
                self.selected_item = item
            elif item in self.hex_items:  # Check if clicked item is a hexagon
                self.selected_item = item

        super().mousePressEvent(event)

    def handleSpellAreaCheck(self, mouse_pos):
        # need to pass hex distance and spell range through here
        # create self.spellrange and self.spellhexdistance?
        # cone and line assume its coming from char
        if self.spellAreaType == 'cone':
            affected = self.getConeHexes(distance_hexes=self.spellDistance, mouse_pos=mouse_pos)
            self.setHexColors(self.coneFill, affected)
        
        if self.spellAreaType == 'line':
            affected = self.getLineHexes(distance_hexes=self.spellDistance, mouse_pos=mouse_pos)
            self.setHexColors(self.coneFill, affected)
        
        # uses spell range
        if self.spellAreaType == 'square':
            affected = self.getSquareHexes(distance_hexes=self.spellDistance, mouse_pos=mouse_pos, spellRange = self.spellRange)
            self.setHexColors(self.coneFill, affected)
        
        if self.spellAreaType == 'sphere' or self.spellAreaType == 'weapon':
            affected = self.getSphereHexes(distance_hexes=self.spellDistance, mouse_pos=mouse_pos, spellRange=self.spellRange)
            self.setHexColors(self.coneFill, affected)
        
        
        
        
        
        

    def mouseMoveEvent(self, event):
        
        if self.curActor != None:
            scene_pos = self.mapToScene(event.pos())
            #print('Trying to drawHex')
            if self.spellAreaCheck:
                self.handleSpellAreaCheck(scene_pos)
                #affected = self.getConeHexes(distance_hexes=6, mouse_pos=scene_pos)
                #self.setHexColors(self.coneFill, affected)
            #print('setting', affected)

        if event.buttons() == Qt.LeftButton and self.selected_item:
            # Convert view-space delta into scene-space delta
            old_pos_scene = self.mapToScene(self.last_mouse_pos)
            new_pos_scene = self.mapToScene(event.pos())
            delta_scene = new_pos_scene - old_pos_scene
            if self.curActor != None:
                turnCharacterItem = self.character_items[self.character_objs.index(self.curActor)]
            else:
                turnCharacterItem = None

            if self.selected_item == self.map_item or self.selected_item in self.hex_items:
                self.map_item.setPos(self.map_item.pos() + delta_scene)
                for item in self.character_items:
                    item.setPos(item.pos() + delta_scene)
                for hex_item in self.hex_items:
                    hex_item.setPos(hex_item.pos() + delta_scene)

            # now instead of any character, only if youre the selected actor
            elif self.selected_item == turnCharacterItem:

                # snapping branch unchanged except for using scene pos
                
                if self.snap_tree is not None:
                    scene_pos = self.mapToScene(event.pos())
                    real_hex_index = self.getSnapHexIndex(scene_pos)

                    if real_hex_index is not None:
                        snap_center_local = self.hex_centers_base[real_hex_index]
                        map_offset = self.map_item.pos()

                        snap_center_scene = (
                            snap_center_local[0] + map_offset.x(),
                            snap_center_local[1] + map_offset.y()
                        )

                        character_size = self.selected_item.boundingRect().size()
                        snap_x = snap_center_scene[0] - character_size.width() / 2
                        snap_y = snap_center_scene[1] - character_size.height() / 2
                        self.selected_item.setPos(snap_x, snap_y)

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

    def getCurActorHexIndex(self):
        """
        Returns the hex index (in self.arrayCenters) of the hex where
        the current active actor is standing.

        Uses the actor's scene position and the hex KD-tree.
        """

        # Must have an active actor selected
        if self.curActor is None:
            return None

        # Character's scene position (center point)
        charIndex = self.character_objs.index(self.curActor)
        char_item = self.character_items[charIndex]
        char_rect = char_item.boundingRect()
        char_center = char_item.mapToScene(char_rect.center())

        # Convert scene position → map-local position
        map_offset = self.map_item.pos()
        local_x = char_center.x() - map_offset.x()
        local_y = char_center.y() - map_offset.y()

        # Query the full hex grid KD-tree
        if self.hex_tree is None:
            return None

        dist, hex_index = self.hex_tree.query((local_x, local_y))

        return hex_index

        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected_item = None

    def getHexFromPoint(self, scene_pos):
        if not self.hex_tree:
            return None

        map_offset = self.map_item.pos()
        local_x = scene_pos.x() - map_offset.x()
        local_y = scene_pos.y() - map_offset.y()

        dist, snap_idx = self.hex_tree.query((local_x, local_y))

        
        return snap_idx

    def angleDiff(self, a, b):
        """Return smallest angular difference."""
        diff = abs(a - b) % (2 * math.pi)
        if diff > math.pi:
            diff = 2 * math.pi - diff
        return diff

    @lru_cache(maxsize=2048)
    def calcLine(self, index1, index2, hexLimit):
        # move this, cone, and square into model methods?
        # mainly just want to see if we can use this version on line
        # in the main model
        
        map = self.encounter.map
        coord1 = list(map.arrayCenters)[index1]
        coord2 = list(map.arrayCenters)[index2]
        # simple case... outside hexlimit
        if map.distanceCalc(index1, index2) >= hexLimit:

            line = drawLine(coord1, coord2, map)
            hexes = [list(map.arrayCenters).index(coord) for coord in line]
            affected = [ind for ind in hexes if map.distanceCalc(ind, index1) <= hexLimit and ind != index1]
            return affected
        
        cone = self.calcHexes(index1, index2, hexLimit)
        
        maxDist = [ind for ind in cone if map.distanceCalc(ind, index1) == hexLimit]
        
        for ind in maxDist:
            newCoord = list(map.arrayCenters)[ind]
            line = drawLine(coord1, newCoord, map)
            #print(coord2, line)
            if coord2 in line:
                #print(line)
                return [list(map.arrayCenters).index(x) for x in line if x != coord1]
            
        #print('Error calcLine failed')
        return []
 
    @lru_cache(maxsize=2048)
    def calcHexes(self, index1, index2, hexLimit):
        import operator, math

        map = self.encounter.map
        arrayCenters = list(map.arrayCenters)

        # === OPERATIONS (your provided table) =========================
        operations2 = [
            [[operator.sub, 1], [operator.add, 1], [operator.sub, 1], [operator.sub, 1]],
            [[operator.sub, 1], [operator.sub, 1], [operator.add, 0], [operator.sub, 2]],
            [[operator.add, 0], [operator.sub, 2], [operator.add, 1], [operator.sub, 1]],
            [[operator.add, 1], [operator.sub, 1], [operator.add, 1], [operator.add, 1]],
            [[operator.add, 1], [operator.add, 1], [operator.add, 0], [operator.add, 2]],
            [[operator.add, 0], [operator.add, 2], [operator.sub, 1], [operator.add, 1]]
        ]

        # === STEP 1: Use ALREADY double-coords ========================
        ox, oy = arrayCenters[index1]
        tx, ty = arrayCenters[index2]

        # === STEP 2: compute angle using double-coords ================
        angle = math.atan2((oy - ty), (ox - tx))


        # Hex direction center angles (still correct for double axial)
        dirAngles = [
            math.radians(0),     # E
            math.radians(60),    # NE
            math.radians(120),   # NW
            math.radians(180),   # W
            math.radians(-120),  # SW
            math.radians(-60)    # SE
        ]

        # Select closest operation
        bestOpIndex = min(
            range(6),
            key=lambda i: abs((angle - dirAngles[i] + math.pi) % (2 * math.pi) - math.pi)
        )
        selectedOp = operations2[bestOpIndex]

        affectedCoords = []

        # === STEP 3: Cone sweep (EXACT logic from your method) ========
        for cell in range(hexLimit):

            # POSITIVE direction
            if selectedOp[0][1] == 0:
                px = selectedOp[0][0](ox, selectedOp[0][1])
                py = selectedOp[1][0](selectedOp[1][0](oy, cell * 2), selectedOp[1][1])
            else:
                px = selectedOp[0][0](selectedOp[0][0](ox, cell), selectedOp[0][1])
                py = selectedOp[1][0](selectedOp[1][0](oy, cell), selectedOp[1][1])

            # NEGATIVE direction
            if selectedOp[2][1] == 0:
                nx = selectedOp[2][0](ox, selectedOp[2][1])
                ny = selectedOp[3][0](selectedOp[3][0](oy, cell * 2), selectedOp[3][1])
            else:
                nx = selectedOp[2][0](selectedOp[2][0](ox, cell), selectedOp[2][1])
                ny = selectedOp[3][0](selectedOp[3][0](oy, cell), selectedOp[3][1])

            dx = abs(px - nx)
            dy = abs(py - ny)

            if dx == 0 and dy == 2:
                affectedCoords.append((px, py))
                affectedCoords.append((nx, ny))
            else:
                maxX, minX = max(px, nx), min(px, nx)
                maxY, minY = max(py, ny), min(py, ny)

                if selectedOp[0] == selectedOp[2]:
                    # vertical fill
                    for y in range(minY, maxY + 1):
                        affectedCoords.append((px, y))
                else:
                    # diagonal fill
                    if selectedOp[3][1] == 2:
                        yLine = list(range(minY, maxY + 1))
                        xLine = list(range(maxX, minX - 1, -1))
                    else:
                        yLine = list(range(minY, maxY + 1))
                        xLine = list(range(minX, maxX + 1))

                    for k in range(len(xLine)):
                        affectedCoords.append((xLine[k], yLine[k]))

        # === STEP 4: Convert axial coords → indexes ====================
        affectedIndexes = []

        coordSet = set(affectedCoords)
        for i, coord in enumerate(arrayCenters):
            if coord in coordSet:
                affectedIndexes.append(i)

        return affectedIndexes

    #def calcSquare(self, index1, index2, hexLimit):
    #
    #    map = self.encounter.map
    #    centers = list(map.arrayCenters)
    #
    #    c1 = centers[index1]
    #    c2 = centers[index2]
    #
    #    # angle from index1 → index2
    #    angle = math.atan2(c2[1] - c1[1], c2[0] - c1[0])
    #
    #    # 8 direction vectors in double-coordinate space
    #    dirs8 = [
    #        ( 1,  0),   # E
    #        ( 1, -1),   # NE
    #        ( 0, -1),   # N
    #        (-1, -1),   # NW
    #        (-1,  0),   # W
    #        (-1,  1),   # SW
    #        ( 0,  1),   # S
    #        ( 1,  1),   # SE
    #    ]
    #
    #    dir_angles = [math.atan2(dy, dx) for dx, dy in dirs8]
    #
    #    # choose the closest directional facing
    #    best_dir = min(range(8), key=lambda i: abs(self.angleDiff(angle, dir_angles[i])))
    #    dx, dy = dirs8[best_dir]
    #
    #    # square is centered directly on index1 (spellRange removed)
    #    cx, cy = c1
    #
    #    # orthogonal axis (90° rotated)
    #    ox, oy = -dy, dx
    #
    #    affected = []
    #    center_to_index = {xy: i for i, xy in enumerate(centers)}
    #
    #    # Build the hex “square”
    #    for i in range(-hexLimit//2, hexLimit//2 + 1):
    #        for j in range(-hexLimit//2, hexLimit//2 + 1):
    #
    #            x = cx + dx * i + ox * j
    #            y = cy + dy * i + oy * j
    #
    #            # fix hex parity drift (your original rule)
    #            if (x + y) % 2 != (cx + cy) % 2:
    #                y += 1
    #
    #            if (x, y) in center_to_index:
    #                affected.append(center_to_index[(x, y)])
    #
    #    return affected
    #
    def calcSquare(self, index1, index2, hexLimit):
        import operator, math

        map = self.encounter.map
        arrayCenters = list(map.arrayCenters)
        # === STEP 1: Use ALREADY double-coords ========================
        ox, oy = arrayCenters[index1]
        tx, ty = arrayCenters[index2]

        # === STEP 2: compute angle using double-coords ================
        angle = math.atan2((oy - ty), (ox - tx))

        
        operations = [[operator.sub,1, operator.add, 1,operator.add,0,operator.sub,0], 
                    [operator.sub, 1, operator.sub, 1,operator.add,0,operator.sub,0],
                    [operator.add,1, operator.add, 1,operator.add,0,operator.sub,0], 
                    [operator.add, 1, operator.sub, 1,operator.add,0,operator.sub,0],
                    [operator.sub, 1, operator.add, 2,operator.add,1,operator.sub,5],
                    [operator.add, 1, operator.sub, 2,operator.sub,1,operator.add,5],
                    [operator.add, 1, operator.sub, 2,operator.sub,1,operator.sub,5],
                    [operator.sub, 1, operator.add, 2,operator.add,1,operator.add,5]]
        moveCoord = list(arrayCenters)[index2]
        op = operations[0]
        startCoord = (op[0](moveCoord[0], op[1]), op[2](moveCoord[1], op[3]))
        squareCoords = []
        ##print(op)
        for k in range(hexLimit):
            for l in range(hexLimit):
                x = op[4](op[0](startCoord[0], k),op[5])
                if op[2] == operator.add:
                    y= op[6](operator.sub(startCoord[1], 2*l),op[7])
                else:
                    y= op[6](operator.add(startCoord[1], 2*l),op[7])
                if x % 2 != y % 2 :
                    y = op[2](y, 1)
                if (x,y) in list(arrayCenters):
                    squareCoords.append((x,y))
        return [list(arrayCenters).index(coord) for coord in squareCoords]
            
        #return []
    def getSphereHexes(self, distance_hexes, spellRange, mouse_pos):
        
        if self.affected != None:
            self.setHexColors(self.defaultFill, self.affected)
            self.setCurMoveCoords(self.curMoveCoords)
            self.affected = None

        actor_hex = self.getCurActorHexIndex()
        if actor_hex is None or actor_hex < 0:
            return []
        

        # calc snap coords this section should be moved to combo box change (calc spell hexes once not on each mouse move)
        
        spellSnapInd = self.getSnapSpellIndex(mouse_pos)
        target_hex = self.spell_index[spellSnapInd]
        print(target_hex)
        if target_hex is None:
            return []
        map = self.encounter.map
        affected = [ind for ind in range(len(self.hex_centers_base ))
                    if map.distanceCalc(target_hex, ind) <= distance_hexes]

        self.affected = affected
        
        return affected
    
    def calcSpellLimit(self, spellRange):
        actor_hex = self.getCurActorHexIndex()
        arrayCenters = self.encounter.map.arrayCenters
        hexInRange = [list(arrayCenters).index(coord) for coord in arrayCenters 
                      if self.encounter.map.distanceCalc(actor_hex, list(arrayCenters).index(coord)) <= spellRange]
        self.build_spell_tree(hexInRange)
    def getLineHexes(self, distance_hexes, mouse_pos):
        
        if self.affected != None:
            self.setHexColors(self.defaultFill, self.affected)
            self.setCurMoveCoords(self.curMoveCoords)
            self.affected = None
        # Validate actor
        actor_hex = self.getCurActorHexIndex()
        if actor_hex is None or actor_hex < 0:
            return []

        ax, ay = self.hex_centers_base[actor_hex]

        # Identify which hex mouse is pointing at
        target_hex = self.getHexFromPoint(mouse_pos)
        if target_hex is None:
            return []
        affected = self.calcLine(actor_hex, target_hex, distance_hexes)
        self.affected = affected
        return affected


    def getSquareHexes(self, distance_hexes, mouse_pos, spellRange):
        if self.affected != None:
            self.setHexColors(self.defaultFill, self.affected)
            self.setCurMoveCoords(self.curMoveCoords)
            self.affected = None
        # Validate actor
        actor_hex = self.getCurActorHexIndex()
        if actor_hex is None or actor_hex < 0:
            return []

        ax, ay = self.hex_centers_base[actor_hex]

        # Identify which hex mouse is pointing at
        spellSnapInd = self.getSnapSpellIndex(mouse_pos)
        target_hex = self.spell_index[spellSnapInd]
        if target_hex is None:
            return []
        affected = self.calcSquare(actor_hex, target_hex, distance_hexes)
        self.affected = affected
        return affected

    def getConeHexes(self, distance_hexes, mouse_pos):
        """
        Returns a list of hex indices affected by a cone originating from
        the current actor, snapped to nearest hex direction.

        No drawing or highlighting — just logic.
        """
        
        if self.affected != None:
            self.setHexColors(self.defaultFill, self.affected)
            self.setCurMoveCoords(self.curMoveCoords)
            self.affected = None
        # Validate actor
        actor_hex = self.getCurActorHexIndex()
        if actor_hex is None or actor_hex < 0:
            return []

        ax, ay = self.hex_centers_base[actor_hex]

        # Identify which hex mouse is pointing at
        target_hex = self.getHexFromPoint(mouse_pos)
        if target_hex is None:
            return []
        affected = self.calcHexes(actor_hex, target_hex, distance_hexes)
        self.affected = affected
        return affected
       


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
        #print('trying to remove red Outline')
        if pixmap.isNull():
            print("pixmap is NULL")
            return pixmap

        # the outline thickness you used earlier
        outline = 4

        # Crop the pixmap to remove the border
        cropped = pixmap.copy(
            outline,
            outline,
            pixmap.width() - outline * 2,
            pixmap.height() - outline * 2
        )

        return cropped



class GroupedComboBox(QComboBox):
    """
    A QComboBox that supports non-selectable section headers,
    useful for grouping items such as spell levels.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Use a standard item model so we can mark headers as unselectable
        self.model = QStandardItemModel()
        self.setModel(self.model)

    def addHeader(self, text):
        """
        Add a non-selectable header row.
        """
        item = QStandardItem(text)

        # Make header visually distinct
        font = QFont()
        font.setBold(True)
        item.setFont(font)
        item.setFlags(Qt.NoItemFlags)     # Not selectable
        item.setData(True, Qt.UserRole+1) # custom flag marking this as a header

        self.model.appendRow(item)

    def addItemToGroup(self, text, data=None):
        """
        Add a normal selectable item.
        """
        item = QStandardItem(text)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        if data is not None:
            item.setData(data, Qt.UserRole)

        self.model.appendRow(item)

    def isHeader(self, index):
        """
        Optional helper to check if a model row is a header.
        """
        item = self.model.item(index)
        if item:
            return bool(item.data(Qt.UserRole+1))
        return False

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
        self.current_icon.setScaledContents(True)


        layout.addWidget(self.current_icon)

        # Next 5 turn icons
        self.next_icons = []
        for _ in range(5):
            lbl = QLabel()
            lbl.setPixmap(placeholder_pix)
            lbl.setFixedSize(40, 40)
            lbl.setScaledContents(True)
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
        self.action_dropdown = GroupedComboBox()
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
        # add weapon to actions
        self.action_dropdown.addHeader('Wepons*******')
        for weap in actor.weaponList:
            if weap.name in actions:    
                self.action_dropdown.addItemToGroup(weap.name, data=weap.name)
                actions.remove(weap.name)

        self.action_dropdown.addHeader('\nSpells*******')
        # add spells to dropdown
        spells = actor.spells  # dictionary of spells
        # Build dictionary grouping spell names by level:
        #   { 0: [...], 1: [...], ... }
        level_groups = {}
        for spell_name, data in spells.items():
            lvl = data.get("lvl", 0)
            level_groups.setdefault(lvl, []).append(spell_name)

        # Loop levels in ascending order
        for lvl in sorted(level_groups.keys()):
            if any(x in actions for x in level_groups[lvl]):
                # Add header
                header_text = f"\nLevel {lvl} Spells"
                self.action_dropdown.addHeader(header_text)

                # Add spell items underneath
                for spell_name in sorted(level_groups[lvl]):   # alphabetical
                    if spell_name in actions:
                        self.action_dropdown.addItemToGroup(spell_name, data=spells[spell_name])
                        actions.remove(spell_name)
        self.action_dropdown.addHeader('\nOther*******')
        for item in actions:
            self.action_dropdown.addItemToGroup(item, data=item)

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
        global gViewer

        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)

        # ---- Top: Turn Order Indicator ----
        self.turn_order_widget = TurnOrderWidget()
        main_layout.addWidget(self.turn_order_widget)

        # ------------------------------------------------------------------
        # CUSTOM SPLITTER WITH HOVER-CURSOR + DOUBLE CLICK BEHAVIOR
        # ------------------------------------------------------------------
        class SmartSplitter(QSplitter):
            def __init__(self, orientation):
                super().__init__(orientation)
                self.setHandleWidth(10)

            def createHandle(self):
                return SmartSplitterHandle(self.orientation(), self)

        class SmartSplitterHandle(QSplitterHandle):
            def mouseMoveEvent(self, event):
                splitter = self.splitter()

                # Mouse coordinate in global splitter space
                pos = event.pos().x() if splitter.orientation() == Qt.Horizontal else event.pos().y()

                # Set sizes based on mouse position directly
                total = sum(splitter.sizes())

                # clamp positions
                pos = max(100, min(total - 100, pos))

                # New sizes
                if splitter.orientation() == Qt.Horizontal:
                    sizes = [pos, total - pos]
                else:
                    sizes = [pos, total - pos]

                splitter.setSizes(sizes)

                super().mouseMoveEvent(event)

            def mouseDoubleClickEvent(self, event):
                # Keep your double-click behavior
                splitter = self.splitter()
                right = splitter.widget(1)
                splitter.setSizes([2000, right.minimumWidth()])
                super().mouseDoubleClickEvent(event)


            self.splitter = SmartSplitter(Qt.Horizontal)

        # ============================================================
        # LEFT SIDE: MAP FRAME (buttons + graphics viewer)
        # ============================================================
        self.map_frame = QFrame()
        map_frame_layout = QVBoxLayout(self.map_frame)
        map_frame_layout.setContentsMargins(0, 0, 0, 0)
        map_frame_layout.setSpacing(5)

        # --- Buttons above the map ---
        top_button_row = QHBoxLayout()
        top_button_row.setSpacing(10)

        self.distance_button = QPushButton("Distance Calc")
        self.distance_button.setCheckable(True)
        top_button_row.addWidget(self.distance_button)

        self.spell_button = QPushButton("Spell Area")
        self.spell_button.setCheckable(True)
        self.spell_button.clicked.connect(self.spellButton_pressed)
        top_button_row.addWidget(self.spell_button)

        top_button_row.addStretch()
        map_frame_layout.addLayout(top_button_row)

        # --- Map widget ---
        self.map_view = CustomGraphicsView(myEncounter)
        gViewer = self.map_view
        self.map_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


        self.map_view.setFrameShape(QFrame.Box)
        self.map_view.setMinimumHeight(1400)   # allow width to shrink
        self.map_view.setMinimumWidth(300)    # use smaller minimum

        map_frame_layout.addWidget(self.map_view, stretch=1) 

        self.map_view.affectedSaved.connect(self.updateTargets)

        # Add left side to splitter
        self.splitter.addWidget(self.map_frame)

        # ============================================================
        # SETUP MAP PIXMAP
        # ============================================================
        pixmap = QPixmap(myEncounter.mapImage)
        self.map_view.setMapPixmap(pixmap)

        # Add players to map
        for player in myEncounter.totalList:
            if player.Image is None:
                px = QPixmap(dmSimPath + "\\App\\unknown.jpg")
            elif os.path.exists(dmSimPath + player.Image):
                px = QPixmap(dmSimPath + player.Image)
            else:
                px = QPixmap(dmSimPath + "\\App\\unknown.jpg")

            self.map_view.addCharacterPixmap(px, player)

        # Add hex grid
        num_vertical_grids = int(myEncounter.numHexes)
        map_rect = self.map_view.map_item.boundingRect()
        self.map_view.drawHexGrid(num_vertical_grids, map_rect)

        self.myEncounter = myEncounter

        # ============================================================
        # RIGHT SIDE: TURN ACTION PANEL
        # ============================================================
        self.turn_action_panel = TurnActionPanel()
        self.turn_action_panel.setMinimumWidth(250)
        #self.turn_action_panel.setMaximumWidth(500)  # optional
        self.turn_action_panel.take_turn_button.clicked.connect(self.takeTurnButton)
        self.turn_action_panel.action_dropdown.currentTextChanged.connect(self.actionChanged)

        self.turnChoices = None
        self.turnChoice = None
        self.actor = None

        # Add right panel to splitter
        self.splitter.addWidget(self.turn_action_panel)

        # ------------------------------------------------------------
        # SPLITTER BEHAVIOR IMPROVEMENTS
        # ------------------------------------------------------------

        # Map gets 3x more space than action panel initially
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([1100, 300])

        # Double-click handle to restore action panel to minimum width
        def resetPanels():
            self.splitter.setSizes([2000, self.turn_action_panel.minimumWidth()])

        handle = self.splitter.handle(1)
        oldDoubleClick = handle.mouseDoubleClickEvent

        def doubleClickOverride(event):
            resetPanels()
            oldDoubleClick(event)

        handle.mouseDoubleClickEvent = doubleClickOverride

        # Add splitter to layout
        main_layout.addWidget(self.splitter)

        # ---- Bottom: Start Encounter Button ----
        self.start_button = QPushButton("Start Encounter")
        self.start_button.setFixedHeight(40)
        self.start_button.clicked.connect(self.run_command)
        main_layout.addWidget(self.start_button)

        self.setLayout(main_layout)

        self.testingTheory()

    def updateTurnOrder(self):
        encounter = self.myEncounter
        turnOrder = encounter.sortedInitList
        curTurn = [encounter.curTurn][0]
        print('Current Turn', curTurn)
        print(turnOrder)
        
        for i in range(6): # hard set to five for now but this should be length of turn indicator
            print('\t', list(turnOrder)[curTurn].name)
            player = list(turnOrder)[curTurn]
            if player.Image == None:
                pixmap = QPixmap(dmSimPath + "\\App\\unknown.jpg")
            elif os.path.exists(dmSimPath + player.Image):
                pixmap = QPixmap(dmSimPath + player.Image)
            else:
                print("path doesnt exist, trying unknown")
                pixmap = QPixmap(dmSimPath + "\\App\\unknown.jpg")
            
            if i ==0:
                lbl = self.turn_order_widget.current_icon
            else:
                lbl = self.turn_order_widget.next_icons[i-1]

            # ⬇️ SCALE PIXMAP TO LABEL SIZE
            scaled = pixmap.scaled(
                lbl.width(),
                lbl.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            lbl.setPixmap(scaled)
            curTurn += 1
            if curTurn + 1 > len(turnOrder):
                curTurn = 0
            

        print('Current Turn', encounter.curTurn)


    def updateTargets(self, affectedHexes):
        #print(affectedHexes)
        targetsHit = [list(self.myEncounter.map.arrayCenters)[ind] for ind in affectedHexes if 
                      self.myEncounter.map.arrayCenters[list(self.myEncounter.map.arrayCenters)[ind]] != '']
        print(targetsHit)
        self.turnChoice.targets = targetsHit
        targetNames = [self.myEncounter.map.arrayCenters[coord].name for coord in targetsHit]
        self.turn_action_panel.targets_input.setText(str(targetNames))

    def actionChanged(self):
        self.spellButton_pressed()
        #self.spell_button.setChecked(False)
    
    def spellButton_pressed(self):
        if self.map_view.curActor == None:
            return
        if self.map_view.spellAreaCheck:
            self.map_view.spellAreaCheck = False
        else:
            self.map_view.spellAreaCheck = True
        
        actor = self.map_view.curActor
        newMoves = calcMoveHexes(actor, self.myEncounter.map)
        self.map_view.setCurMoveCoords(newMoves)
        
        action = self.turn_action_panel.action_dropdown.currentText()
        weapons = [x.name for x in actor.weaponList]
        # set spell defaults to none
        self.map_view.spellAreaType = None
        self.map_view.spellRange = None # line assume spell range = 0
        self.map_view.spellDistance = None
        self.map_view.spell_centers = []
        self.map_view.spell_tree = None
        self.map_view.spell_index = []
        if action in actor.spells.keys():
            if 'cone' in actor.spells[action]['area']:
                self.map_view.spellAreaType = 'cone'
                self.map_view.spellRange = None # cones assume spell range = 0
                self.map_view.spellDistance = int(int(re.findall(r'\d+', actor.spells[action]['area'])[0])/5)

            elif 'sphere' in actor.spells[action]['area']:
                self.map_view.spellAreaType = 'sphere'
                self.map_view.spellRange = int(int(re.findall(r'\d+', actor.spells[action]['range'])[0])/5) 
                self.map_view.spellDistance = int(int(re.findall(r'\d+', actor.spells[action]['area'])[0])/5)
                self.map_view.calcSpellLimit(self.map_view.spellRange)
            
            elif 'line' in actor.spells[action]['area']:
                self.map_view.spellAreaType = 'line'
                self.map_view.spellRange = None # line assume spell range = 0
                self.map_view.spellDistance = int(int(re.findall(r'\d+', actor.spells[action]['area'])[0])/5)
            
            elif 'square' in actor.spells[action]['area']:
                self.map_view.spellAreaType = 'square'
                self.map_view.spellRange = int(int(re.findall(r'\d+', actor.spells[action]['range'])[0])/5) 
                self.map_view.spellDistance = int(int(re.findall(r'\d+', actor.spells[action]['area'])[0])/5)
                self.map_view.calcSpellLimit(self.map_view.spellRange)

            else:
                self.map_view.spellAreaType = None
        elif action in weapons:
            weapon = actor.weaponList[weapons.index(action)]
            print(weapon.name, weapon.range)
        elif action == 'dash':
            print('dash action')
            newMoves = calcMoveHexes(actor, self.myEncounter.map, type = 'dash')
            self.map_view.setCurMoveCoords(newMoves)

                

                
        pass
    def takeTurnButton(self):
        # now load inputs and and call doAction function
        #myAction(name =, type=, mod=, numHit=, currCoord=, moveCoord=, targets=, castCoord=)
        # grab name of spell
        hexIndex = self.map_view.getCurActorHexIndex()
        
        #print('Current Actors current location on the map', currLocation)
        if self.turnChoice != None and self.actor != None: # for now just do the best action. will work on actually choosing action
            if hexIndex != None:
                currLocation = list(self.myEncounter.map.arrayCenters)[hexIndex]
                self.turnChoice.moveCoord = currLocation
            currAction = self.turn_action_panel.action_dropdown.currentText()
            self.turnChoice.type = [x.type for x in self.turnChoices if x.name == currAction][0]
            self.turnChoice.name = currAction
            doAction(self.actor, self.myEncounter.map, self.turnChoice)
            self.map_view.spellAreaCheck = None
            self.map_view.affected = None
            self.myEncounter.nextTurn()
            turns = self.myEncounter.calcTurn()
            if turns != None:
                self.actor = turns[0]
                self.turnChoices = turns[2]
                self.turnChoice = turns[3]
                self.turn_action_panel.update_turn_panel(self.actor, self.turnChoices, self.turnChoice)
        self.updateTurnOrder()
        pass
    def run_command(self):
        
        turns = self.myEncounter.calcTurn()
        if turns != None:
            self.actor = turns[0]
            self.map_view.setCurTurn(self.actor)
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
        self.updateTurnOrder()
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


