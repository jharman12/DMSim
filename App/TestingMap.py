'''
Things to work on:


    MODEL CHANGES ***************************************************************************
    melee still calling nearestHex when inside melee range
    
    spells like harm isnt doing damage if it passes??


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

    create walls?

    create method for adding in new characters in the middle of combat

    sorceror broke


    GUI CHANGES *****************************************************************************

    

    allow moving chars before combat starts
        must call GV moveActors for all characters
    create interface for adding walls?
        might want to have an encounter builder?
        create a way to run one encounter immediately after the other
    
    save encounter

    prevent doAction if error occurs with warning of that error?

    pop up on end turn if you havent taken an action or have move left


    If i move the char on the map without pressing move or take turn we unsync the two maps

    add party & enemy health bar?
    
    show calc action mod??

    properly get changing action drop box reset hex colors and untoggle spell area button if checked

    
    

    might want to move add/remove red line to before move as its not centering icons

    Add/remove is hard coded thickness? (overtime it is making the icon turn into a square)
    
    

    create gui for character actions 
        auto-roll or manual
        
    

    Create warning for oportunity attacks

    Add distance calc feature

    
    code management *****************************************************************************
    

    restructure code files and create place methods and classes in appropiate files
        create main file
        create actual main GUI
            rebuild dnd_character_builder.py

    
    
'''


import copy
from collections import deque

import os

import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy, QTextEdit, QCheckBox, QMenuBar, QMenu, QAction,
    QLabel, QPushButton, QLineEdit, QScrollArea, QFrame, QProgressBar, QComboBox, QSplitter, QSplitterHandle, QGroupBox
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont

from PyQt5.QtGui import QPixmap, QIcon

from PyQt5.QtWidgets import QApplication, QPushButton, QMainWindow, QWidget, QVBoxLayout
from PyQt5.QtCore import QSize, Qt, QEvent

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
_root = pathlib.Path(__file__).parent.parent
sys.path.insert(1, str(_root))
from model.player import createPartyList, Player
from model.monster import createMonsterList, Monster
from engine.targeting import drawLine, calcMoveHexes, hex_calc_line, hex_calc_hexes, hex_calc_square
from model.Interactive.interactiveEncounter import interactiveEncounter
from dialogs import ManualRollDialog, ManualRollersDialog


_UNKNOWN_IMAGE = str(_root / "App" / "unknown.jpg")


def _get_actor_pixmap(actor) -> "QPixmap":
    """Return QPixmap for an actor, falling back to the unknown placeholder."""
    if actor.Image is None:
        return QPixmap(_UNKNOWN_IMAGE)
    full = str(_root) + actor.Image
    if os.path.exists(full):
        return QPixmap(full)
    if os.path.exists(actor.Image):
        return QPixmap(actor.Image)
    return QPixmap(_UNKNOWN_IMAGE)


class TextScale:
    BASE = 12  # <-- change this to scale everything

    XS  = 0.85
    SM  = 1.0
    MD  = 1.15
    LG  = 1.35
    XL  = 1.6
    XXL = 2.0
    max_BASE = 24
    min_BASE = 6

    @classmethod
    def size(cls, multiplier):
        return int(cls.BASE * multiplier)
    
    @classmethod
    def increase(self):
        self.BASE = min(self.BASE + .2, self.max_BASE)

    @classmethod
    def decrease(self):
        self.BASE = max(self.BASE - .2, self.min_BASE)


        

from PyQt5.QtGui import QFont

def set_font(widget, size, weight=QFont.Normal, monospace=False):
    if monospace:
        font = QFont("Consolas")
    else:
        font = widget.font()

    font.setPointSize(size)
    font.setWeight(weight)
    widget.setFont(font)



class CustomGraphicsView(QGraphicsView):
    affectedSaved = pyqtSignal(list)
    walls_changed = pyqtSignal(set)   # emitted with the new wall index set

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

        self.wall_mode = False
        self._wall_indices: set = set()

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
        self.moveFill = QColor(0, 255, 0, 50)
        self.coneFill = QColor(255, 0, 0, 50)
        self.wallFill = QColor(80, 50, 20, 220)   # dark brown — always on top
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

        # Walls always render on top of movement highlights
        if self._wall_indices:
            self.setHexColors(self.wallFill, list(self._wall_indices))

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
            self.selected_item = None

            # Wall-placement mode: toggle the clicked hex as a wall
            if self.wall_mode and item in self.hex_items:
                idx = self.hex_items.index(item)
                if idx in self._wall_indices:
                    self._wall_indices.discard(idx)
                    self.setHexColors(self.defaultFill, [idx])
                else:
                    self._wall_indices.add(idx)
                    self.setHexColors(self.wallFill, [idx])
                self.walls_changed.emit(set(self._wall_indices))
                return

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
        
        if self.spellAreaType == 'sphere':
            affected = self.getSphereHexes(distance_hexes=self.spellDistance, mouse_pos=mouse_pos, spellRange=self.spellRange)
            self.setHexColors(self.coneFill, affected)
        
        if self.spellAreaType == 'single':
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
        #print(actor.name, newIndex)
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
        #print(snap_x, snap_y)
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
        """Return smallest angular difference (kept for backward compat)."""
        import math
        diff = abs(a - b) % (2 * math.pi)
        if diff > math.pi:
            diff = 2 * math.pi - diff
        return diff

    @lru_cache(maxsize=2048)
    def calcLine(self, index1, index2, hexLimit):
        return hex_calc_line(index1, index2, hexLimit, self.encounter.map)

    @lru_cache(maxsize=2048)
    def calcHexes(self, index1, index2, hexLimit):
        return hex_calc_hexes(index1, index2, hexLimit, self.encounter.map)

    def calcSquare(self, index1, index2, hexLimit):
        return hex_calc_square(index1, index2, hexLimit, self.encounter.map)
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
        #print(target_hex)
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
            self.hex_size = QSizeF(4*r * (1+ math.cos(a))/3, 2*r * math.sin(a))  # Adjust size as needed
            self.hex_path = self.createHexagonPath(self.hex_size.toSize())
            self.setCharsToHexes()
        
        self.hex_centers_base = [(c.x(), c.y()) for c in self.arrayCenters]
        self.hex_tree = spatial.KDTree(self.hex_centers_base)

        # Testing changing colors
        fill_color = QColor(0, 0, 255, 50) 
        hexLength = len(self.hex_items)
        allHexIndexes =  [ int(x) for x in np.linspace(0, hexLength-1, hexLength)]
        
        self.setHexColors(fill_color, allHexIndexes)

    def setCharsToHexes(self):
        # Iterate over character items
        for character_item in self.character_items:
            # Resize the character's image to fit within the hexagon
            character_pixmap = character_item.pixmap().scaled(self.hex_size.toSize(), Qt.KeepAspectRatio)

            # Create a painter path for the character image
            character_path = QPainterPath()
            character_path.addRect(QRectF(QPointF(), self.hex_size))

            # Clip the character image with the hexagon path
            character_path = character_path.intersected(self.hex_path)

            # Create a new pixmap and paint the character image onto it
            combined_pixmap = QPixmap(self.hex_size.toSize())
            combined_pixmap.fill(Qt.transparent)
            painter = QPainter(combined_pixmap)
            painter.setClipPath(character_path)
            painter.drawPixmap(combined_pixmap.rect(), character_pixmap)
            painter.end()

            # Set the combined pixmap as the pixmap for the character item
            character_item.setPixmap(combined_pixmap)
    
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

    def removeAllActors(self):
        for item in self.character_items:
            self.scene.removeItem(item)
        
        self.character_items.clear()
        self.character_objs.clear()

        #self.character_items = []
        #self.character_objs = []

    def loadFromEncounter(self, myEncounter):
        
        self.removeAllActors()
        for player in myEncounter.totalList:
            px = _get_actor_pixmap(player)
            self.addCharacterPixmap(px, player)
        
        # resize them
        self.setCharsToHexes()

        # set curActor
        self.curActor = list(myEncounter.sortedInitList)[myEncounter.curTurn]

        # now move chars into character spot
        map = myEncounter.map
        for coord in map.arrayCenters:
            if map.arrayCenters[coord] != '': # youre a character
                gvIndex = map.convertToViewerCoords(coord)
                self.moveActor(map.arrayCenters[coord], gvIndex)




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
        mainLayout = QHBoxLayout()
        self.box = QGroupBox("Turn Order")
        mainLayout.addWidget(self.box)
        layout = QHBoxLayout()
        layout.setSpacing(10)
        self.box.setLayout(layout)
        # Placeholder icons
        placeholder_pix = QPixmap(50, 50)
        placeholder_pix.fill(Qt.darkGray)

        # Current turn icon
        self.current_icon = QLabel()
        self.current_icon.setPixmap(placeholder_pix)
        self.current_icon.setFixedSize(70, 70)
        self.current_icon.setScaledContents(True)


        layout.addWidget(self.current_icon)

        # Next 5 turn icons
        self.next_icons = []
        for _ in range(5):
            lbl = QLabel()
            lbl.setPixmap(placeholder_pix)
            lbl.setFixedSize(60, 60)
            lbl.setScaledContents(True)
            layout.addWidget(lbl)
            self.next_icons.append(lbl)

        layout.addStretch()
        self.setLayout(mainLayout)
    
    def applyFonts(self, textScale):
        """Apply font scaling from textScale object."""
        set_font(self.box, textScale.size(textScale.MD), QFont.Bold)
    
    


class TurnActionPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._textScale = None
        box = QGroupBox("Turn Actions")
        final_layout = QVBoxLayout()
        final_layout.addWidget(box)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        box.setLayout(main_layout)
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

       # ================= SPELL SLOTS (SCROLLABLE) =================
        self.spell_slot_title = QLabel("Spell Slots")
        self.spell_slot_title.setStyleSheet("font-weight: bold; margin-top: 6px;")
        main_layout.addWidget(self.spell_slot_title)

        self.spell_slot_scroll = QScrollArea()
        self.spell_slot_scroll.setWidgetResizable(True)
        self.spell_slot_scroll.setMinimumHeight(100)
        self.spell_slot_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Inner container
        self.spell_slot_container = QWidget()
        self.spell_slot_layout = QVBoxLayout(self.spell_slot_container)
        self.spell_slot_layout.setContentsMargins(4, 4, 4, 4)
        self.spell_slot_layout.setSpacing(6)

        self.spell_slot_scroll.setWidget(self.spell_slot_container)
        main_layout.addWidget(self.spell_slot_scroll, stretch= 1)

        # Track widgets
        self.spell_slot_widgets = {}


        # -------------------------------
        # ACTION DROP-DOWN
        # -------------------------------
        actionBox = QHBoxLayout()
        self.actionLbl = QLabel('Action:')
        actionBox.addWidget(self.actionLbl)
        self.action_dropdown = GroupedComboBox()
        self.action_dropdown.addItems(["Attack", "Cast Spell", "Dash", "Use Item"])  # placeholder actions
        actionBox.addWidget(self.action_dropdown, 1)
        main_layout.addLayout(actionBox)

        # -------------------------------
        # Targets input
        # -------------------------------
        targets_layout = QHBoxLayout()
        self.targets_title_label = QLabel("Targets:")
        targets_layout.addWidget(self.targets_title_label)
        self.targets_label = QLabel("")
        self.targets_label.setWordWrap(True)
        targets_layout.addWidget(self.targets_label)
        main_layout.addLayout(targets_layout)

        # -------------------------------
        # Move coords input
        # -------------------------------
        
        self.move_Action_layout = QHBoxLayout()
        self.move_input = QPushButton('Move')
        
        self.move_Action_layout.addWidget(self.move_input)

        

        # -------------------------------
        # Take Turn button
        # -------------------------------
        self.take_turn_button = QPushButton("Take Turn")
        #self.take_turn_button.clicked.connect(self.take_turn)
        self.move_Action_layout.addWidget(self.take_turn_button)
        main_layout.addLayout(self.move_Action_layout)

        # -------------------------------
        # End Turn button
        # -------------------------------
        self.endTurnButton = QPushButton('End Turn')

        main_layout.addWidget(self.endTurnButton)
        # ---------------- GAME LOG ----------------
        self.game_log_label = QLabel("Game Log")
        self.game_log_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(self.game_log_label)

        self.game_log_box = QTextEdit() 
        self.game_log_box.setReadOnly(True)
        self.game_log_box.setMinimumHeight(200)
        self.game_log_box.setStyleSheet(
            "background-color: #111; color: #ddd; font-family: Consolas, monospace;"
        )
        self.game_log_box.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        main_layout.addWidget(self.game_log_box, stretch=2)


        #main_layout.addStretch(1)
        self.setLayout(final_layout)

    def applyFonts(self, textScale):
        self._textScale = textScale
        set_font(self.turn_label, textScale.size(textScale.LG), QFont.Bold)
        set_font(self.health_label, textScale.size(textScale.SM))
        set_font(self.spell_slot_title, textScale.size(textScale.MD), QFont.Bold)

        
        set_font(self.actionLbl, textScale.size(textScale.SM))
        set_font(self.action_dropdown, textScale.size(textScale.SM))
        set_font(self.targets_title_label, textScale.size(textScale.SM))
        set_font(self.targets_label, textScale.size(textScale.SM))

        
        set_font(self.endTurnButton, textScale.size(textScale.SM))
        set_font(self.move_input, textScale.size(textScale.SM))
        set_font(self.take_turn_button, textScale.size(textScale.SM))

        set_font(self.game_log_label, textScale.size(textScale.MD), QFont.Bold)
        set_font(
            self.game_log_box,
            textScale.size(textScale.MD),
            monospace=True
        )
        # Apply font to grouped boxes and their title
        for child in self.findChildren(QGroupBox):
            set_font(child, textScale.size(textScale.MD), QFont.Bold)
    
    def clearLayout(self, layout):
        while layout.count():
            item = layout.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

            elif item.layout():
                self.clearLayout(item.layout())


    def buildSpellSlots(self, actor):
        if not self._textScale:
            return  # fonts not initialized yet

        slot_data = actor.spellSlots
        maxSlots = actor.maxSpellSlots

        # Clear existing widgets
        self.clearLayout(self.spell_slot_layout)
        self.spell_slot_widgets.clear()


        self.spell_slot_widgets.clear()

        for level in sorted(slot_data.keys()):
            if level == '0':
                continue

            max_slots = maxSlots[level]
            remaining = slot_data[level]

            if max_slots == 0:
                continue

            # --- Level Label ---
            lbl = QLabel(f"Level {level}")
            set_font(
                lbl,
                self._textScale.size(self._textScale.SM),
                QFont.Bold
            )
            self.spell_slot_layout.addWidget(lbl)

            # --- Slot Row ---
            row = QHBoxLayout()
            row.setSpacing(4)

            self.spell_slot_widgets[level] = []

            for i in range(max_slots):
                slot = QCheckBox()
                slot.setEnabled(False)
                slot.setChecked(i < remaining)

                # Scale checkbox size
                box_size = self._textScale.size(self._textScale.XS)
                slot.setFixedSize(box_size + 4, box_size + 4)

                slot.setStyleSheet(f"""
                    QCheckBox::indicator {{
                        width: {box_size}px;
                        height: {box_size}px;
                        border: 2px solid #999;
                        background: #222;
                    }}
                    QCheckBox::indicator:checked {{
                        background: #66ccff;
                    }}
                """)

                row.addWidget(slot)
                self.spell_slot_widgets[level].append(slot)

            row.addStretch()
            self.spell_slot_layout.addLayout(row)



    def log(self, text):
        """Append text to the game log (like print())."""
        self.game_log_box.append(text)
        self.game_log_box.verticalScrollBar().setValue(
            self.game_log_box.verticalScrollBar().maximum()
        )


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
        #targets = str(turnChoice.targets)
        targets = ''
        for target in turnChoice.targets:
            targets += ' ' + str(target) + ','
        targets = targets[:-1] if targets else ""
        self.targets_label.setText(targets)

        # Update move coords input
        move_coords = str(turnChoice.moveCoord)
        #self.move_input.setText(move_coords)



class MapWidget(QWidget):
    def __init__(self, controller):
        super().__init__()
        global gViewer

        # Accept either a SimController (new) or a bare interactiveEncounter (legacy).
        from controller import SimController
        if isinstance(controller, SimController):
            self.controller = controller
        else:
            # Wrap legacy encounter so the rest of the code is uniform
            self.controller = SimController(controller)

        # Convenience alias — all internal code uses this directly
        self.myEncounter = self.controller.encounter

        self.installEventFilter(self)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)

        # ---- Menu Bar ----
        self.menu_bar = QMenuBar(self)

        # File menu
        file_menu = self.menu_bar.addMenu("File")

        save_action = QAction("Save Encounter", self)
        save_action.triggered.connect(self.saveEncounter)
        file_menu.addAction(save_action)

        # Optional placeholders
        edit_menu = self.menu_bar.addMenu("Edit")
        view_menu = self.menu_bar.addMenu("View")
        help_menu = self.menu_bar.addMenu("Help")

        # Add menu bar to layout
        main_layout.addWidget(self.menu_bar)

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

        # ---- Left buttons ----
        self.distance_button = QPushButton("Distance Calc")
        self.distance_button.setCheckable(True)
        top_button_row.addWidget(self.distance_button)

        self.spell_button = QPushButton("Spell Area")
        self.spell_button.setCheckable(True)
        self.spell_button.clicked.connect(self.spellButton_pressed)
        top_button_row.addWidget(self.spell_button)

        self.wall_button = QPushButton("🧱 Walls")
        self.wall_button.setCheckable(True)
        self.wall_button.setToolTip("Click hexes to mark them as impassable walls")
        self.wall_button.clicked.connect(self._toggle_wall_mode)
        top_button_row.addWidget(self.wall_button)

        self.manual_dice_button = QPushButton("🎲 Manual Rollers")
        self.manual_dice_button.setToolTip(
            "Choose which actors roll their own physical dice"
        )
        self.manual_dice_button.clicked.connect(self.openManualRollersDialog)
        top_button_row.addWidget(self.manual_dice_button)

        # ---- Stretch pushes next widget to the right ----
        top_button_row.addStretch(1)

        # ---- Right button ----
        self.undo_button = QPushButton("Undo Turn")
        self.undo_button.setCheckable(True)
        self.undo_button.clicked.connect(self.undoTurn)
        top_button_row.addWidget(self.undo_button)

        map_frame_layout.addLayout(top_button_row)

        # --- Map widget ---
        self.map_view = CustomGraphicsView(self.myEncounter)
        gViewer = self.map_view
        self.map_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


        self.map_view.setFrameShape(QFrame.Box)
        self.map_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.map_view.setMinimumWidth(300)    # use smaller minimum

        map_frame_layout.addWidget(self.map_view, stretch=1) 

        self.map_view.affectedSaved.connect(self.updateTargets)

        # Add left side to splitter
        self.splitter.addWidget(self.map_frame)

        # ============================================================
        # SETUP MAP PIXMAP
        # ============================================================
        pixmap = QPixmap(self.myEncounter.mapImage)
        self.map_view.setMapPixmap(pixmap)

        # Add players to map
        for player in self.myEncounter.totalList:
            px = _get_actor_pixmap(player)
            self.map_view.addCharacterPixmap(px, player)

        # Add hex grid
        num_vertical_grids = int(self.myEncounter.numHexes)
        map_rect = self.map_view.map_item.boundingRect()
        self.map_view.drawHexGrid(num_vertical_grids, map_rect)

        self.undo_stack = deque(maxlen=20)  # cap memory
        # ============================================================
        # RIGHT SIDE: TURN ACTION PANEL
        # ============================================================
        self.turn_action_panel = TurnActionPanel()
        #self.turn_action_panel.setMinimumWidth(250)
        #self.turn_action_panel.setMaximumWidth(500)  # optional
        self.turn_action_panel.take_turn_button.clicked.connect(self.takeTurnButton)
        self.turn_action_panel.move_input.clicked.connect(self.moveButton)
        self.turn_action_panel.endTurnButton.clicked.connect(self.endTurnButton)
        self.turn_action_panel.action_dropdown.currentTextChanged.connect(self.actionChanged)

        self.turn_action_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
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
        main_layout.addWidget(self.splitter, 1)

        # ---- Bottom: Start Encounter Button ----
        self.start_button = QPushButton("Start Encounter")
        self.start_button.setFixedHeight(40)
        self.start_button.clicked.connect(self.run_command)
        main_layout.addWidget(self.start_button)

        self.setLayout(main_layout)

        # ---- Wire SimController signals ----
        self.controller.log_message.connect(self.turn_action_panel.log)
        self.controller.turn_changed.connect(self._on_turn_changed)
        self.controller.actor_died.connect(self._on_actor_died)
        self.controller.encounter_ended.connect(self._on_encounter_ended)

        # ---- Wire wall changes from the map view to the engine map ----
        self.map_view.walls_changed.connect(self._on_walls_changed)

        # ---- Give controller access to the manual-roll dialog factory ----
        self.controller.roll_provider_factory = self._make_roll_provider

        # Default: all players roll manually so the DM doesn't need to configure this.
        default_manual = {
            a.name for a in self.myEncounter.totalList
            if getattr(a, 'is_player', False)
        }
        self.controller.set_manual_actors(default_manual)

        self.testingTheory()

        self.TextScale = TextScale
        self.setAllFonts()


    # ------------------------------------------------------------------
    # SimController signal handlers
    # ------------------------------------------------------------------

    def _make_roll_provider(self, actor_name: str):
        """
        Return a callable suitable for engine.dice.set_roll_provider.
        Shows ManualRollDialog for each rollDice / rollSave call.
        """
        parent = self

        def provider(n: int, sides: int, context: str, actor_name=actor_name):
            dlg = ManualRollDialog(actor_name, context, n, sides, parent=parent)
            if dlg.exec_() == ManualRollDialog.Accepted:
                return dlg.get_rolls()
            return None  # fallback to random if user cancels

        return provider

    def openManualRollersDialog(self):
        """Open the Manual Rollers configuration dialog."""
        all_actors = list(self.myEncounter.totalList)
        dlg = ManualRollersDialog(all_actors, self.controller.manual_actors, parent=self)
        if dlg.exec_() == ManualRollersDialog.Accepted:
            self.controller.set_manual_actors(dlg.get_selected())

    def _on_turn_changed(self, actor):
        """Called by SimController.turn_changed signal when the active actor changes."""
        self.map_view.setCurTurn(actor)
        self.updateTurnOrder()

    def _on_actor_died(self, actor):
        """Called by SimController.actor_died signal."""
        self.turn_action_panel.log(f'{actor.name} has died!')

    def _on_encounter_ended(self, winner):
        """Called by SimController.encounter_ended signal."""
        self.turn_action_panel.log(f'--- Encounter over! {winner} wins! ---')
        self.start_button.setEnabled(False)

    def _toggle_wall_mode(self, checked: bool):
        """Enable or disable wall-placement mode on the map view."""
        self.map_view.wall_mode = checked
        # Visual cue: change cursor so the user knows they're placing walls
        if checked:
            self.map_view.setCursor(Qt.CrossCursor)
        else:
            self.map_view.unsetCursor()

    def _on_walls_changed(self, wall_indices: set):
        """Sync wall indices from the view into the engine map."""
        if self.myEncounter.map is not None:
            self.myEncounter.map.walls = wall_indices

    # ------------------------------------------------------------------

    def saveEncounter(self):
        print("Saving encounter...")
        # later:
        # - deepcopy encounter
        # - serialize to JSON / pickle
        # - QFileDialog.getSaveFileName()


    def saveTurnSnapshot(self):
        # remove pyqt widgets
        self.myEncounter.graphicsViewer = None
        self.myEncounter.map.graphicsViewer = None
        self.myEncounter.map.combatLog = None
        snapshot = copy.deepcopy(self.myEncounter)
        self.myEncounter.graphicsViewer = self.map_view
        self.myEncounter.map.graphicsViewer = self.map_view
        self.myEncounter.map.combatLog = self.turn_action_panel.log
        self.undo_stack.append(snapshot)
        print('undo stack length', len(self.undo_stack))
    
    def undoTurn(self):
        if not self.undo_stack:
            return

        self.myEncounter = self.undo_stack.pop()
        self.myEncounter.graphicsViewer = self.map_view
        self.myEncounter.map.graphicsViewer = self.map_view
        self.myEncounter.map.combatLog = self.turn_action_panel.log
        self.rebuildFromEncounter()
        print('Undo stack length', len(self.undo_stack))

    def rebuildFromEncounter(self):
        # need to build restarts here.
        self.map_view.loadFromEncounter(self.myEncounter)
        turns = self.myEncounter.calcTurn()
            
        if turns != None:
            self.actor = turns[0]
            self.turnChoices = turns[2]
            self.turnChoice = turns[3]
            self.turn_action_panel.update_turn_panel(self.actor, self.turnChoices, self.turnChoice)
        self.turn_action_panel.buildSpellSlots(self.actor)
        self.updateTurnOrder()
        
        newMoveHexes = calcMoveHexes(self.actor, self.myEncounter.map)
        self.map_view.setCurMoveCoords(newMoveHexes)
        # i need to now whether the undo was a 
        self.turn_action_panel.take_turn_button.setEnabled(True)
        self.turn_action_panel.action_dropdown.setEnabled(True)
        pass


    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            if QApplication.keyboardModifiers() & Qt.ControlModifier:
                delta = event.angleDelta().y()

                if delta > 0:
                    self.TextScale.increase()
                else:
                    self.TextScale.decrease()

                self.applyTextScale()
                return True  # stop normal scrolling

        return super().eventFilter(obj, event)

    def applyTextScale(self):
        # Turn order widget
        self.turn_order_widget.applyFonts(self.TextScale)
        
        # Turn action panel
        self.turn_action_panel.applyFonts(self.TextScale)

        # Rebuild dynamic widgets
        if self.actor:
            self.turn_action_panel.buildSpellSlots(self.actor)

        # Buttons above map
        
        set_font(self.undo_button, self.TextScale.size(self.TextScale.SM))
        set_font(self.distance_button, self.TextScale.size(self.TextScale.SM))
        set_font(self.spell_button, self.TextScale.size(self.TextScale.SM))

    def setAllFonts(self):
        self.turn_order_widget.applyFonts(self.TextScale)
        self.turn_action_panel.applyFonts(self.TextScale)

        
    def updateTurnOrder(self):
        encounter = self.myEncounter
        turnOrder = encounter.sortedInitList
        curTurn = [encounter.curTurn][0]

        for i in range(6): # hard set to five for now but this should be length of turn indicator
            player = list(turnOrder)[curTurn]
            pixmap = _get_actor_pixmap(player)

            if i == 0:
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
            

        #print('Current Turn', encounter.curTurn)


    def updateTargets(self, affectedHexes):
        #print(affectedHexes)
        targetsHit = [list(self.myEncounter.map.arrayCenters)[ind] for ind in affectedHexes if 
                      self.myEncounter.map.arrayCenters[list(self.myEncounter.map.arrayCenters)[ind]] != '']
        #print(targetsHit)
        self.turnChoice.targets = targetsHit
        targetNames = [self.myEncounter.map.arrayCenters[coord].name for coord in targetsHit]
        targetString = ''
        for target in targetNames:
            targetString += ' ' + target + ','
        targetString = targetString[:-1] if targetString else ""
        self.turn_action_panel.targets_label.setText(targetString)

    def actionChanged(self):
        self.spellButton_pressed()
        action = self.turn_action_panel.action_dropdown.currentText()
        if action == 'dash':
            self.turn_action_panel.move_input.setEnabled(False)
        else:
            self.turn_action_panel.move_input.setEnabled(True)
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

            else: #youre a single target spell
                self.map_view.spellAreaType = 'single'
                self.map_view.spellRange = int(int(re.findall(r'\d+', actor.spells[action]['range'])[0])/5) 
                self.map_view.spellDistance = 0 
                self.map_view.calcSpellLimit(self.map_view.spellRange)
        elif action in weapons:
            weapon = actor.weaponList[weapons.index(action)]
            self.map_view.spellAreaType = 'single'
            self.map_view.spellRange = weapon.range/5
            self.map_view.spellDistance = 0 
            self.map_view.calcSpellLimit(self.map_view.spellRange)
        elif action == 'dash':
            #print('dash action')
            newMoves = calcMoveHexes(actor, self.myEncounter.map, type = 'dash')
            self.map_view.setCurMoveCoords(newMoves)

                

                
        pass
    
    def moveButton(self):
        hexIndex = self.map_view.getCurActorHexIndex()
        if self.turnChoice is not None and self.actor is not None and hexIndex is not None:
            self.saveTurnSnapshot()
            currLocation = list(self.myEncounter.map.arrayCenters)[hexIndex]
            self.turnChoice.moveCoord = currLocation
            dist, new_move_hexes = self.controller.move_actor(self.actor, currLocation, hexIndex)
            self.map_view.setCurMoveCoords(new_move_hexes)

    def endTurnButton(self):
        self.map_view.spellAreaCheck = None
        self.map_view.affected = None

        turns = self.controller.end_turn(self.actor)
        if turns is not None:
            self.actor = turns[0]
            self.turnChoices = turns[2]
            self.turnChoice = turns[3]
            self.turn_action_panel.update_turn_panel(self.actor, self.turnChoices, self.turnChoice)

        self.turn_action_panel.buildSpellSlots(self.actor)
        self.updateTurnOrder()
        self.turn_action_panel.take_turn_button.setEnabled(True)
        self.turn_action_panel.action_dropdown.setEnabled(True)

    def takeTurnButton(self):
        hexIndex = self.map_view.getCurActorHexIndex()
        if self.turnChoice is not None and self.actor is not None:
            if hexIndex is not None:
                currLocation = list(self.myEncounter.map.arrayCenters)[hexIndex]
                self.turnChoice.moveCoord = currLocation
            self.saveTurnSnapshot()
            currAction = self.turn_action_panel.action_dropdown.currentText()
            self.turnChoice.type = [x.type for x in self.turnChoices if x.name == currAction][0]
            self.turnChoice.name = currAction
            self.controller.take_action(self.actor, self.turnChoice)
            self.turn_action_panel.take_turn_button.setEnabled(False)
            self.turn_action_panel.action_dropdown.setEnabled(False)
            self.turn_action_panel.buildSpellSlots(self.actor)
        
    def run_command(self):
        self.turn_action_panel.log('Starting Combat!')
        turns = self.myEncounter.calcTurn()
        if turns != None:
            self.actor = turns[0]
            self.map_view.setCurTurn(self.actor)
            self.turnChoices = turns[2]
            self.turnChoice = turns[3]
            self.turn_action_panel.update_turn_panel(self.actor, self.turnChoices, self.turnChoice)
            self.turn_action_panel.buildSpellSlots(self.actor)
        self.saveTurnSnapshot() # save start of new turn

    def testingTheory(self):
        
        # should populate turn_order_widget
        # create the initial movement grids highlight 

        self.myEncounter.preCombat(self.map_view)
        self.myEncounter.map.combatLog = self.turn_action_panel.log
        curActor = list(self.myEncounter.sortedInitList)[self.myEncounter.curTurn]
        index = self.map_view.character_objs.index(curActor)
        item = self.map_view.character_items[index] 
        pixMap = item.pixmap()
        outlined = self.map_view.addRedOutline(pixmap=pixMap)
        item.setPixmap(outlined)
        self.updateTurnOrder()
        #removeOutline = self.map_view.remove_red_outline(pixMap)
        #item.setPixmap(removeOutline)

    
        





#myMap = Map('mazeEngine',dmSimPath + "\\App\\Maps\\maze Engine.webp", 10, myPlayers)

#app = QApplication([])

#window = MapWidget(myEncounter)
#window.show()

#app.exec()


