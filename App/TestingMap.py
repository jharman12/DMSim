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
    QLabel, QPushButton, QLineEdit, QScrollArea, QFrame, QProgressBar, QComboBox, QSplitter, QSplitterHandle, QGroupBox,
    QMainWindow, QDockWidget, QToolBar, QMessageBox
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont

from PyQt5.QtGui import QPixmap, QIcon

from PyQt5.QtWidgets import QApplication, QPushButton, QMainWindow, QWidget, QVBoxLayout, QDockWidget, QToolBar
from PyQt5.QtCore import QSize, Qt, QEvent, QTimer

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
from dialogs import ManualRollDialog, ManualRollersDialog, ManualActionsDialog, SetStatsDialog


_UNKNOWN_IMAGE = str(_root / "App" / "unknown.jpg")
_DEFAULT_MAP = str(_root / "App" / "Maps" / "TestingMap.webp")
_OUTLINE_THICKNESS = 3   # pixels added per side by addRedOutline


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
    fog_changed = pyqtSignal(set)     # emitted with updated fog index set
    target_area_changed = pyqtSignal(set)  # emitted with highlighted hex indices (empty = cleared)

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
        self._clean_pixmaps: dict = {}   # QGraphicsPixmapItem -> outline-free QPixmap

        self.wall_mode = False
        self._wall_indices: set = set()
        self._wall_drag_adding: bool = True   # True = painting walls, False = erasing

        # Wall mode overlay toolbar (top-right of view)
        self._wall_toolbar = QFrame(self)
        self._wall_toolbar.setStyleSheet(
            "QFrame { background: rgba(30,30,40,220); border: 1px solid #555; border-radius: 6px; }"
        )
        tbl = QHBoxLayout(self._wall_toolbar)
        tbl.setContentsMargins(6, 4, 6, 4)
        tbl.setSpacing(6)

        self._wall_create_btn = QPushButton("➕ Create")
        self._wall_create_btn.setCheckable(True)
        self._wall_create_btn.setChecked(True)
        self._wall_create_btn.setStyleSheet(
            "QPushButton { color: #eee; border: 1px solid #555; border-radius: 4px; padding: 3px 8px; }"
            "QPushButton:checked { background-color: #1a6a1a; color: #ffffff; border: 2px solid #44cc44; }"
        )
        self._wall_delete_btn = QPushButton("🗑 Delete")
        self._wall_delete_btn.setCheckable(True)
        self._wall_delete_btn.setStyleSheet(
            "QPushButton { color: #eee; border: 1px solid #555; border-radius: 4px; padding: 3px 8px; }"
            "QPushButton:checked { background-color: #7a1a1a; color: #ffffff; border: 2px solid #ff4444; }"
        )

        self._wall_create_btn.clicked.connect(self._wall_mode_create)
        self._wall_delete_btn.clicked.connect(self._wall_mode_delete)

        tbl.addWidget(self._wall_create_btn)
        tbl.addWidget(self._wall_delete_btn)
        self._wall_toolbar.adjustSize()
        self._wall_toolbar.setVisible(False)
        self._wall_toolbar.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        # Fog of war state
        self.fog_mode = False
        self._fog_indices: set = set()
        self._fog_drag_adding: bool = True
        self._fog_dm_items: dict = {}   # hex_idx -> QGraphicsPolygonItem child overlay
        # Brush size in hex-radii: 0=single, 1=small cluster, 2=medium, 3=large, 4=huge
        self._fog_brush_radius: int = 0

        # Fog mode overlay toolbar (top-right, shares position with wall toolbar since exclusive)
        self._fog_toolbar = QFrame(self)
        self._fog_toolbar.setStyleSheet(
            "QFrame { background: rgba(30,30,40,220); border: 1px solid #555; border-radius: 6px; }"
        )
        ftbl = QHBoxLayout(self._fog_toolbar)
        ftbl.setContentsMargins(6, 4, 6, 4)
        ftbl.setSpacing(6)

        self._fog_create_btn = QPushButton("➕ Create")
        self._fog_create_btn.setCheckable(True)
        self._fog_create_btn.setChecked(True)
        self._fog_create_btn.setStyleSheet(
            "QPushButton { color: #eee; border: 1px solid #555; border-radius: 4px; padding: 3px 8px; }"
            "QPushButton:checked { background-color: #1a6a1a; color: #ffffff; border: 2px solid #44cc44; }"
        )
        self._fog_delete_btn = QPushButton("🗑 Delete")
        self._fog_delete_btn.setCheckable(True)
        self._fog_delete_btn.setStyleSheet(
            "QPushButton { color: #eee; border: 1px solid #555; border-radius: 4px; padding: 3px 8px; }"
            "QPushButton:checked { background-color: #7a1a1a; color: #ffffff; border: 2px solid #ff4444; }"
        )

        self._fog_create_btn.clicked.connect(self._fog_mode_create)
        self._fog_delete_btn.clicked.connect(self._fog_mode_delete)

        # Brush-size selector
        _size_lbl = QLabel("Size:")
        _size_lbl.setStyleSheet("color: #ccc; font-size: 12px;")
        self._fog_size_combo = QComboBox()
        self._fog_size_combo.addItems(["Small", "Medium", "Large", "Huge"])
        self._fog_size_combo.setStyleSheet(
            "QComboBox { color: #eee; background: #2a2a3a; border: 1px solid #555; "
            "border-radius: 4px; padding: 2px 6px; min-width: 70px; }"
            "QComboBox QAbstractItemView { color: #eee; background: #2a2a3a; }"
        )
        self._fog_size_combo.currentIndexChanged.connect(self._on_fog_size_changed)

        ftbl.addWidget(self._fog_create_btn)
        ftbl.addWidget(self._fog_delete_btn)
        ftbl.addWidget(_size_lbl)
        ftbl.addWidget(self._fog_size_combo)
        self._fog_toolbar.adjustSize()
        self._fog_toolbar.setVisible(False)
        self._fog_toolbar.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        self._persistent_zones: dict = {}  # spell_name -> list[hex_index]

        # Callback to fetch prev-turn data from MapWidget — set by MapWidget after init
        self._prev_turn_lookup = None   # callable(actor) -> dict or None
        self._prev_turn_clear = None    # callable() to clear log + path highlights

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
        self.fogFill  = QColor(80, 80, 100, 110)  # dim grey-blue — DM fog overlay (semi-transparent)
        self.persistFill = QColor(255, 140, 0, 130)  # orange — persistent spell zones
        self.distStartFill = QColor(0, 220, 220, 160)   # cyan — distance start hex
        self.distPathFill = QColor(180, 180, 180, 80)   # dim grey — path route
        self.prevTurnPathFill = QColor(120, 80, 200, 100)  # purple — previous turn path
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)

        self.affected = None

        # Distance-calc mode state
        self._dist_mode = False
        self._dist_start_idx = None
        self._dist_path_indices: list = []

        # Overlay label (bottom-left) for displaying calculated distance
        self._dist_label = QLabel("", self)
        self._dist_label.setStyleSheet(
            "background: rgba(20,20,30,200); color: #e0e0e0; "
            "font-size: 15px; font-weight: bold; padding: 6px 10px; "
            "border-radius: 6px;"
        )
        self._dist_label.setVisible(False)
        self._dist_label.setAttribute(Qt.WA_TransparentForMouseEvents)

    def setCurTurn(self, actor):
        # Remove outline from the previous actor and restore its centered position
        if self.curActor is not None and self.curActor in self.character_objs:
            old_idx = self.character_objs.index(self.curActor)
            old_item = self.character_items[old_idx]
            clean = self._clean_pixmaps.get(old_item)
            if clean is not None:
                old_item.setPixmap(clean)
                # Undo the position shift that was applied when the outline was added
                pos = old_item.pos()
                old_item.setPos(pos.x() + _OUTLINE_THICKNESS, pos.y() + _OUTLINE_THICKNESS)

        self.curActor = actor

        # Apply outline to the new actor and shift its position to stay centered
        if actor is not None and actor in self.character_objs:
            new_idx = self.character_objs.index(actor)
            new_item = self.character_items[new_idx]
            clean = self._clean_pixmaps.get(new_item)
            if clean is not None:
                outlined = self.addRedOutline(clean)
                new_item.setPixmap(outlined)
                # Outline adds thickness pixels on each side; shift up-left to keep center
                pos = new_item.pos()
                new_item.setPos(pos.x() - _OUTLINE_THICKNESS, pos.y() - _OUTLINE_THICKNESS)

    def setCurMoveCoords(self, indexes):
        self.curMoveCoords = indexes

        # Reset all hex colors to default
        self.setHexColors(self.defaultFill, [i for i in range(len(self.hex_items))])

        # Highlight the newly allowed movement hexes
        self.setHexColors(self.moveFill, indexes)

        # Persistent spell zones render above movement highlights
        for idxs in self._persistent_zones.values():
            self.setHexColors(self.persistFill, idxs)

        # Walls always render on top
        if self._wall_indices:
            self.setHexColors(self.wallFill, list(self._wall_indices))

        # Rebuild the snap tree here
        self.build_snap_tree(indexes)

    def add_persistent_zone(self, spell_name: str, hex_indices: list):
        """Color and track a persistent spell zone."""
        self._persistent_zones[spell_name] = list(hex_indices)
        self.setHexColors(self.persistFill, hex_indices)

    def remove_persistent_zone(self, spell_name: str):
        """Remove a persistent zone and refresh hex colors."""
        if spell_name in self._persistent_zones:
            del self._persistent_zones[spell_name]
        # Refresh: reset + reapply movement + remaining zones + walls
        self.setHexColors(self.defaultFill, list(range(len(self.hex_items))))
        if self.curMoveCoords:
            self.setHexColors(self.moveFill, self.curMoveCoords)
        for idxs in self._persistent_zones.values():
            self.setHexColors(self.persistFill, idxs)
        if self._wall_indices:
            self.setHexColors(self.wallFill, list(self._wall_indices))

    # ------------------------------------------------------------------
    # Wall mode toolbar
    # ------------------------------------------------------------------

    def show_wall_toolbar(self, visible: bool):
        """Show or hide the wall mode overlay toolbar."""
        self._wall_toolbar.setVisible(visible)
        if visible:
            self._position_wall_toolbar()

    def _position_wall_toolbar(self):
        """Place the wall toolbar in the top-right of the view."""
        self._wall_toolbar.adjustSize()
        margin = 10
        x = self.width() - self._wall_toolbar.width() - margin
        self._wall_toolbar.move(x, margin)
        self._wall_toolbar.raise_()

    def _wall_mode_create(self):
        self._wall_drag_adding = True
        self._wall_create_btn.setChecked(True)
        self._wall_delete_btn.setChecked(False)

    def _wall_mode_delete(self):
        self._wall_drag_adding = False
        self._wall_delete_btn.setChecked(True)
        self._wall_create_btn.setChecked(False)

    # ------------------------------------------------------------------
    # Fog of war toolbar
    # ------------------------------------------------------------------

    def show_fog_toolbar(self, visible: bool):
        """Show or hide the fog mode overlay toolbar."""
        self._fog_toolbar.setVisible(visible)
        if visible:
            self._position_fog_toolbar()

    def _position_fog_toolbar(self):
        """Place the fog toolbar in the top-right of the view."""
        self._fog_toolbar.adjustSize()
        margin = 10
        x = self.width() - self._fog_toolbar.width() - margin
        self._fog_toolbar.move(x, margin)
        self._fog_toolbar.raise_()

    def _fog_mode_create(self):
        self._fog_drag_adding = True
        self._fog_create_btn.setChecked(True)
        self._fog_delete_btn.setChecked(False)

    def _fog_mode_delete(self):
        self._fog_drag_adding = False
        self._fog_delete_btn.setChecked(True)
        self._fog_create_btn.setChecked(False)

    def _on_fog_size_changed(self, index: int):
        """Map combo index → hex-radius used when painting/erasing fog."""
        # Small=0 → radius 0 (1 hex), Medium=1 → 1, Large=2 → 2, Huge=3 → 3
        self._fog_brush_radius = index

    def _fog_hex_cluster(self, center_idx: int) -> list[int]:
        """Return all hex indices within _fog_brush_radius hexes of center_idx.

        Uses the KD-tree with a pixel-distance cutoff derived from the hex radius
        so the result is always a compact circular cluster regardless of map scale.
        """
        if self._fog_brush_radius == 0 or self.hex_tree is None:
            return [center_idx]
        # Each hex step ≈ self.radius * 1.5 in horizontal distance for flat-top grids,
        # but using 2 * self.radius per step gives a safe over-estimate that matches
        # distanceCalc behaviour.
        pixel_radius = self._fog_brush_radius * self.radius * 2.0
        cx, cy = self.hex_centers_base[center_idx]
        indices = self.hex_tree.query_ball_point([cx, cy], pixel_radius)
        return indices

    def _add_fog_hex(self, idx: int):
        """Add a dim DM fog overlay to hex idx and record it in _fog_indices."""
        if idx in self._fog_dm_items or idx >= len(self.hex_items):
            return
        hex_item = self.hex_items[idx]
        # Overlay is a child of the hex item so it moves when the map is dragged
        overlay = QGraphicsPolygonItem(hex_item.polygon(), hex_item)
        overlay.setBrush(QBrush(self.fogFill))
        overlay.setPen(QPen(Qt.NoPen))
        overlay.setZValue(0.5)
        overlay.setAcceptedMouseButtons(Qt.NoButton)
        self._fog_dm_items[idx] = overlay
        self._fog_indices.add(idx)

    def _remove_fog_hex(self, idx: int):
        """Remove fog from hex idx."""
        if idx not in self._fog_dm_items:
            return
        overlay = self._fog_dm_items.pop(idx)
        overlay.setParentItem(None)
        if overlay.scene():
            overlay.scene().removeItem(overlay)
        self._fog_indices.discard(idx)

    def _reapply_fog(self):
        """Re-create fog DM overlays after hex grid is redrawn (preserves _fog_indices)."""
        self._fog_dm_items.clear()
        for idx in list(self._fog_indices):
            if idx < len(self.hex_items):
                hex_item = self.hex_items[idx]
                overlay = QGraphicsPolygonItem(hex_item.polygon(), hex_item)
                overlay.setBrush(QBrush(self.fogFill))
                overlay.setPen(QPen(Qt.NoPen))
                overlay.setZValue(0.5)
                overlay.setAcceptedMouseButtons(Qt.NoButton)
                self._fog_dm_items[idx] = overlay
            else:
                self._fog_indices.discard(idx)

    # ------------------------------------------------------------------
    # Distance-calc mode
    # ------------------------------------------------------------------

    def _scene_pos_to_hex_idx(self, scene_pos) -> int | None:
        """Return the hex index nearest to scene_pos using the full hex KD-tree.
        Works regardless of whether a character icon is on top of the hex."""
        if not self.hex_tree or not self.hex_centers_base:
            return None
        if self.map_item is None:
            return None
        map_offset = self.map_item.pos()
        local_x = scene_pos.x() - map_offset.x()
        local_y = scene_pos.y() - map_offset.y()
        _, idx = self.hex_tree.query((local_x, local_y))
        if idx < len(self.hex_items):
            return idx
        return None

    def set_distance_mode(self, active: bool):
        """Enter or exit distance-calculation mode."""
        self._dist_mode = active
        if not active:
            # Clear start highlight and path
            if self._dist_start_idx is not None:
                self.setHexColors(self.defaultFill, [self._dist_start_idx])
                if self.curMoveCoords:
                    if self._dist_start_idx in self.curMoveCoords:
                        self.setHexColors(self.moveFill, [self._dist_start_idx])
            if self._dist_path_indices:
                self._refresh_hex_colors()
            self._dist_start_idx = None
            self._dist_path_indices = []
            self._dist_label.setVisible(False)
            self.unsetCursor()
        else:
            # Cancel any other exclusive modes
            self.wall_mode = False
            self.spellAreaCheck = False
            self.setCursor(Qt.CrossCursor)
            self._dist_start_idx = None
            self._dist_path_indices = []
            self._dist_label.setVisible(False)

    def _find_path(self, start_idx: int, end_idx: int) -> list:
        """BFS returning the list of hex indices on the shortest wall-aware path,
        or [] if unreachable. Walls block traversal."""
        map_obj = getattr(self.encounter, 'map', None)
        if map_obj is None:
            return []

        coords = list(map_obj.arrayCenters)
        n = len(coords)
        walls = getattr(map_obj, 'walls', set())

        def _hex_dist(a, b):
            drow = abs(a[1] - b[1])
            dcol = abs(a[0] - b[0])
            return dcol + max(0, (drow - dcol) / 2)

        neighbors = [
            [j for j in range(n) if i != j and _hex_dist(coords[i], coords[j]) == 1]
            for i in range(n)
        ]

        # BFS with parent tracking — no movement limit, walls block
        parent = {start_idx: None}
        queue = [start_idx]
        while queue:
            cur = queue.pop(0)
            if cur == end_idx:
                break
            for nb in neighbors[cur]:
                if nb not in parent and nb not in walls:
                    parent[nb] = cur
                    queue.append(nb)

        if end_idx not in parent:
            return []

        # Reconstruct path
        path = []
        node = end_idx
        while node is not None:
            path.append(node)
            node = parent[node]
        path.reverse()
        return path

    def _show_dist_path(self, path: list, start_idx: int, end_idx: int):
        """Highlight the path and show the distance overlay in the bottom-left."""
        self._dist_path_indices = list(path)

        # Re-render base colors then overlay path
        self._refresh_hex_colors()
        if path:
            # Dim path (exclude start/end for special colors)
            mid = [i for i in path if i != start_idx and i != end_idx]
            if mid:
                self.setHexColors(self.distPathFill, mid)
            self.setHexColors(self.distStartFill, [start_idx])
            self.setHexColors(QColor(0, 220, 100, 180), [end_idx])  # green end

        hexes = len(path) - 1 if path else 0
        feet = hexes * 5
        if path:
            text = f"📏  {feet} ft  ({hexes} hexes)"
        else:
            text = "📏  No path"
        self._dist_label.setText(text)
        self._dist_label.adjustSize()
        self._position_dist_label()
        self._dist_label.setVisible(True)

    def _position_dist_label(self):
        """Place the distance label in the bottom-left of the view."""
        margin = 10
        lbl = self._dist_label
        x = margin
        y = self.height() - lbl.height() - margin
        lbl.move(x, y)

    def _refresh_hex_colors(self):
        """Reset all hexes and re-apply movement, zones, walls."""
        self.setHexColors(self.defaultFill, list(range(len(self.hex_items))))
        if self.curMoveCoords:
            self.setHexColors(self.moveFill, self.curMoveCoords)
        for idxs in self._persistent_zones.values():
            self.setHexColors(self.persistFill, idxs)
        if self._wall_indices:
            self.setHexColors(self.wallFill, list(self._wall_indices))

    def show_prev_turn_path(self, from_idx: int, to_idx: int | None):
        """Highlight the actor's previous-turn movement path in purple."""
        self._refresh_hex_colors()
        if from_idx is not None and to_idx is not None and from_idx != to_idx:
            path = self._find_path(from_idx, to_idx)
            if path:
                mid = [i for i in path[1:-1]]
                if mid:
                    self.setHexColors(self.prevTurnPathFill, mid)
                self.setHexColors(QColor(140, 60, 220, 180), [from_idx])   # dark purple start
                self.setHexColors(QColor(180, 100, 255, 180), [to_idx])    # bright purple end
        elif from_idx is not None:
            # Actor didn't move — just highlight their hex
            self.setHexColors(QColor(140, 60, 220, 180), [from_idx])

    def clear_prev_turn_path(self):
        """Remove previous-turn path highlights."""
        self._refresh_hex_colors()

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

    def show_character_popup(self, character_obj, scene_pos, prev_turn_callback=None, clear_callback=None):
        """
        Displays a styled info popup inside the graphics view near the clicked actor.
        prev_turn_callback: callable(actor) to show previous-turn path/log highlight.
        clear_callback: callable() to clear previous-turn highlights.
        """
        # Remove existing popup
        if self.info_popup:
            self.info_popup.deleteLater()
            self.info_popup = None

        c = character_obj
        hp = max(int(c.health), 0)
        max_hp = max(int(c.maxHealth), 1)
        hp_pct = hp / max_hp

        # Health bar colour: green → yellow → red
        if hp_pct > 0.5:
            bar_color = "#4caf50"
        elif hp_pct > 0.25:
            bar_color = "#ff9800"
        else:
            bar_color = "#f44336"

        bar_fill = max(int(hp_pct * 100), 0)

        # Collect active conditions
        conditions = []
        # Persistent display conditions set by the engine (CC, Restrained, etc.)
        for cond in sorted(getattr(c, 'active_conditions', set())):
            conditions.append(f"⚡ {cond}")
        # Concentration (always live)
        if getattr(c, 'concentration_spell', None):
            ps = c.concentration_spell
            conditions.append(f"🔮 Concentrating: {ps.spell_name}")
        if hasattr(c, 'status') and c.status:
            for s in c.status:
                if s not in ('deathSaves', 'unconscious'):
                    conditions.append(f"• {s}")
                elif s == 'deathSaves':
                    conditions.append("💀 Death Saves")
                elif s == 'unconscious':
                    conditions.append("😵 Unconscious")

        actor_type = "Player" if getattr(c, 'is_player', False) else "Monster"
        type_color = "#66aaff" if getattr(c, 'is_player', False) else "#ff7777"

        # Build popup widget
        popup = QFrame(self)
        popup.setFixedWidth(320)
        popup.setStyleSheet(f"""
            QFrame#actorPopup {{
                background-color: #1e1e2e;
                border: 1px solid #444;
                border-radius: 8px;
            }}
            QLabel {{ background: transparent; color: #eee; }}
        """)
        popup.setObjectName("actorPopup")
        popup.setFrameShape(QFrame.NoFrame)

        outer = QVBoxLayout(popup)
        outer.setContentsMargins(10, 8, 10, 10)
        outer.setSpacing(6)

        # --- Header row: name + close button ---
        header_row = QHBoxLayout()
        header_row.setSpacing(4)

        name_lbl = QLabel(f"<b>{c.name}</b>")
        name_lbl.setStyleSheet("color: #ffffff; font-size: 20px;")
        header_row.addWidget(name_lbl, stretch=1)

        type_badge = QLabel(actor_type)
        type_badge.setStyleSheet(
            f"color: {type_color}; font-size: 16px; font-style: italic;"
        )
        type_badge.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header_row.addWidget(type_badge)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #aaa;
                border: none; font-size: 16px;
            }
            QPushButton:hover { color: #fff; }
        """)
        close_btn.clicked.connect(self.hide_character_popup)
        header_row.addWidget(close_btn)
        outer.addLayout(header_row)

        # --- Divider ---
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("color: #444;")
        outer.addWidget(div)

        # --- HP bar ---
        hp_header = QHBoxLayout()
        hp_title = QLabel("HP")
        hp_title.setStyleSheet("color: #aaa; font-size: 16px;")
        hp_val = QLabel(f"{hp} / {max_hp}")
        hp_val.setStyleSheet("color: #eee; font-size: 16px;")
        hp_val.setAlignment(Qt.AlignRight)
        hp_header.addWidget(hp_title)
        hp_header.addWidget(hp_val)
        outer.addLayout(hp_header)

        bar_container = QFrame()
        bar_container.setFixedHeight(12)
        bar_container.setStyleSheet("""
            QFrame {
                background-color: #333;
                border-radius: 5px;
            }
        """)
        bar_inner_layout = QHBoxLayout(bar_container)
        bar_inner_layout.setContentsMargins(0, 0, 0, 0)
        bar_inner_layout.setSpacing(0)

        bar_fill_widget = QFrame()
        bar_fill_widget.setFixedHeight(12)
        bar_fill_widget.setStyleSheet(f"""
            QFrame {{
                background-color: {bar_color};
                border-radius: 5px;
            }}
        """)
        # Use a progress-bar-style proportional width via size policy + stretch
        bar_inner_layout.addWidget(bar_fill_widget, stretch=bar_fill)
        if bar_fill < 100:
            spacer = QFrame()
            spacer.setStyleSheet("background: transparent;")
            bar_inner_layout.addWidget(spacer, stretch=100 - bar_fill)

        outer.addWidget(bar_container)

        # --- Stats row ---
        stats_row = QHBoxLayout()
        for label, val in [("AC", c.ac), ("Speed", f"{c.speed} ft")]:
            stat_box = QVBoxLayout()
            stat_box.setSpacing(0)
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #888; font-size: 14px;")
            lbl.setAlignment(Qt.AlignCenter)
            v = QLabel(str(val))
            v.setStyleSheet("color: #ddd; font-size: 18px; font-weight: bold;")
            v.setAlignment(Qt.AlignCenter)
            stat_box.addWidget(lbl)
            stat_box.addWidget(v)
            stats_row.addLayout(stat_box)
        outer.addLayout(stats_row)

        # --- Conditions ---
        if conditions:
            cond_div = QFrame()
            cond_div.setFrameShape(QFrame.HLine)
            cond_div.setStyleSheet("color: #444;")
            outer.addWidget(cond_div)
            for cond_text in conditions:
                cond_lbl = QLabel(cond_text)
                cond_lbl.setStyleSheet("color: #ffcc66; font-size: 15px;")
                outer.addWidget(cond_lbl)

        # --- Previous Turn button (shown only when turn data exists) ---
        if prev_turn_callback is not None:
            prev_div = QFrame()
            prev_div.setFrameShape(QFrame.HLine)
            prev_div.setStyleSheet("color: #444;")
            outer.addWidget(prev_div)

            prev_btn = QPushButton("🕐 Show Previous Turn")
            prev_btn.setCheckable(True)
            prev_btn.setStyleSheet("""
                QPushButton {
                    background: #2a2a3a; color: #c0a0ff; border: 1px solid #6040aa;
                    border-radius: 4px; padding: 4px 8px; font-size: 14px;
                }
                QPushButton:checked {
                    background: #4a2a7a; color: #ffffff; border: 2px solid #a060ff;
                }
                QPushButton:hover { background: #3a2a5a; }
            """)

            def _toggle_prev_turn(checked):
                if checked:
                    prev_turn_callback(character_obj)
                else:
                    if clear_callback:
                        clear_callback()

            prev_btn.toggled.connect(_toggle_prev_turn)
            outer.addWidget(prev_btn)

        # --- Set Stats button (always shown) ---
        stats_div = QFrame()
        stats_div.setFrameShape(QFrame.HLine)
        stats_div.setStyleSheet("color: #444;")
        outer.addWidget(stats_div)

        set_stats_btn = QPushButton("⚙️ Set Stats")
        set_stats_btn.setStyleSheet("""
            QPushButton {
                background: #2a2a3a; color: #aaddff; border: 1px solid #446688;
                border-radius: 4px; padding: 4px 8px; font-size: 14px;
            }
            QPushButton:hover { background: #2a3a4a; }
        """)

        def _open_set_stats():
            dlg = SetStatsDialog(c, parent=self)
            if dlg.exec_() == SetStatsDialog.Accepted:
                dlg.apply()
                # Rebuild popup in same position to reflect new values
                popup.deleteLater()
                self.info_popup = None
                self.show_character_popup(c, scene_pos, prev_turn_callback, clear_callback)

        set_stats_btn.clicked.connect(_open_set_stats)
        outer.addWidget(set_stats_btn)

        popup.adjustSize()

        # Convert scene → view coords, clamp to stay inside the view
        view_pos = self.mapFromScene(scene_pos)
        x = min(view_pos.x() + 12, self.width() - popup.width() - 4)
        y = min(view_pos.y() + 12, self.height() - popup.height() - 4)
        popup.move(max(x, 0), max(y, 0))
        popup.show()
        popup.raise_()

        self.info_popup = popup

    def hide_character_popup(self):
        if self.info_popup:
            self.info_popup.deleteLater()
            self.info_popup = None
        # Always clear prev-turn highlights when popup is dismissed
        self.clear_prev_turn_path()

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
        self._clean_pixmaps[character_item] = pixmap   # store original for centering
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

                # Show popup — pass prev-turn callbacks if available
                prev_cb = None
                if self._prev_turn_lookup is not None:
                    record = self._prev_turn_lookup(character_obj)
                    if record is not None:
                        def _make_prev_cb(rec):
                            def _cb(actor):
                                self.show_prev_turn_path(rec.get('from_idx'), rec.get('to_idx'))
                                if self._prev_turn_clear:
                                    # signal log highlight via clear callback reference holder
                                    pass
                                # Trigger log highlight via stored log-highlight callback
                                if hasattr(self, '_prev_turn_log_highlight'):
                                    self._prev_turn_log_highlight(rec)
                            return _cb
                        prev_cb = _make_prev_cb(record)

                self.show_character_popup(character_obj, scene_pos,
                                          prev_turn_callback=prev_cb,
                                          clear_callback=self._prev_turn_clear)
            else:
                # Clicked elsewhere → hide popup
                self.hide_character_popup()
                super().mousePressEvent(event)
                return
        if event.button() == Qt.LeftButton:
            self.last_mouse_pos = event.pos()
            item = self.itemAt(event.pos())
            self.selected_item = None

            # Distance-calc mode: two-click flow — accepts hex or actor clicks
            if self._dist_mode:
                idx = self._scene_pos_to_hex_idx(self.mapToScene(event.pos()))
                if idx is not None:
                    if self._dist_start_idx is None:
                        # First click — mark start
                        self._dist_start_idx = idx
                        self._refresh_hex_colors()
                        self.setHexColors(self.distStartFill, [idx])
                    else:
                        # Second click — compute and display path
                        path = self._find_path(self._dist_start_idx, idx)
                        self._show_dist_path(path, self._dist_start_idx, idx)
                return

            # Wall-placement mode: apply according to selected Create/Delete mode
            if self.wall_mode and item in self.hex_items:
                idx = self.hex_items.index(item)
                if self._wall_drag_adding:
                    if idx not in self._wall_indices:
                        self._wall_indices.add(idx)
                        self.setHexColors(self.wallFill, [idx])
                        self.walls_changed.emit(set(self._wall_indices))
                else:
                    if idx in self._wall_indices:
                        self._wall_indices.discard(idx)
                        self.setHexColors(self.defaultFill, [idx])
                        self.walls_changed.emit(set(self._wall_indices))
                return

            # Fog-of-war mode: paint/erase fog on click
            if self.fog_mode:
                idx = self._scene_pos_to_hex_idx(self.mapToScene(event.pos()))
                if idx is not None:
                    cluster = self._fog_hex_cluster(idx)
                    changed = False
                    if self._fog_drag_adding:
                        for cidx in cluster:
                            if cidx not in self._fog_indices:
                                self._add_fog_hex(cidx)
                                changed = True
                    else:
                        for cidx in cluster:
                            if cidx in self._fog_indices:
                                self._remove_fog_hex(cidx)
                                changed = True
                    if changed:
                        self.fog_changed.emit(set(self._fog_indices))
                return

            if self.spellAreaCheck != None and self.affected != None:
                self.affectedSaved.emit(self.affected)
                # updateTargets handler will deactivate target mode via _set_target_mode

            if item == self.map_item:
                self.selected_item = item
            elif item in self.character_items:
                self.selected_item = item
            elif item in self.hex_items:  # Check if clicked item is a hexagon
                self.selected_item = item

        super().mousePressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._dist_label.isVisible():
            self._position_dist_label()
        if self._wall_toolbar.isVisible():
            self._position_wall_toolbar()
        if self._fog_toolbar.isVisible():
            self._position_fog_toolbar()

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

        # Notify the player view so it can show the targeting highlight through fog
        if self.affected is not None:
            self.target_area_changed.emit(set(self.affected))
        else:
            self.target_area_changed.emit(set())
        
        
        
        
        
        

    def mouseMoveEvent(self, event):
        
        if self.curActor != None:
            scene_pos = self.mapToScene(event.pos())
            if self.spellAreaCheck:
                self.handleSpellAreaCheck(scene_pos)

        # Wall drag-paint: paint/erase walls while LMB held
        if self.wall_mode and event.buttons() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            if item in self.hex_items:
                idx = self.hex_items.index(item)
                if self._wall_drag_adding and idx not in self._wall_indices:
                    self._wall_indices.add(idx)
                    self.setHexColors(self.wallFill, [idx])
                    self.walls_changed.emit(set(self._wall_indices))
                elif not self._wall_drag_adding and idx in self._wall_indices:
                    self._wall_indices.discard(idx)
                    self.setHexColors(self.defaultFill, [idx])
                    self.walls_changed.emit(set(self._wall_indices))
            return

        # Fog drag-paint: paint/erase fog while LMB held
        if self.fog_mode and event.buttons() == Qt.LeftButton:
            idx = self._scene_pos_to_hex_idx(self.mapToScene(event.pos()))
            if idx is not None:
                cluster = self._fog_hex_cluster(idx)
                changed = False
                if self._fog_drag_adding:
                    for cidx in cluster:
                        if cidx not in self._fog_indices:
                            self._add_fog_hex(cidx)
                            changed = True
                else:
                    for cidx in cluster:
                        if cidx in self._fog_indices:
                            self._remove_fog_hex(cidx)
                            changed = True
                if changed:
                    self.fog_changed.emit(set(self._fog_indices))
            return

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

                        # Use the clean (no-outline) pixmap size for accurate centering
                        clean = self._clean_pixmaps.get(self.selected_item)
                        if clean is not None:
                            icon_w = clean.width()
                            icon_h = clean.height()
                        else:
                            icon_w = self.selected_item.boundingRect().width()
                            icon_h = self.selected_item.boundingRect().height()
                        snap_x = snap_center_scene[0] - icon_w / 2
                        snap_y = snap_center_scene[1] - icon_h / 2
                        # Compensate if this item currently has the outline applied
                        if self.selected_item in self._clean_pixmaps:
                            actual_w = self.selected_item.boundingRect().width()
                            if actual_w > icon_w:
                                snap_x -= _OUTLINE_THICKNESS
                                snap_y -= _OUTLINE_THICKNESS
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

        # Use the clean (no-outline) pixmap size for accurate centering
        clean = self._clean_pixmaps.get(pixmap)
        if clean is not None:
            icon_w = clean.width()
            icon_h = clean.height()
        else:
            icon_w = pixmap.boundingRect().width()
            icon_h = pixmap.boundingRect().height()
        snap_x = snap_coord[0] - icon_w / 2
        snap_y = snap_coord[1] - icon_h / 2
        # Compensate if outline is currently applied
        actual_w = pixmap.boundingRect().width()
        if clean is not None and actual_w > icon_w:
            snap_x -= _OUTLINE_THICKNESS
            snap_y -= _OUTLINE_THICKNESS
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

        # Restore fog overlays on the new hex grid
        self._reapply_fog()

    def setCharsToHexes(self):
        # Iterate over character items
        for character_item in self.character_items:
            # Use the stored clean pixmap if available (avoids scaling an outlined pixmap)
            source_pixmap = self._clean_pixmaps.get(character_item, character_item.pixmap())

            # Resize the character's image to fit within the hexagon
            character_pixmap = source_pixmap.scaled(self.hex_size.toSize(), Qt.KeepAspectRatio)

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

            # Store the clean clipped pixmap BEFORE any outline is applied
            self._clean_pixmaps[character_item] = combined_pixmap

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
        # Remove fog overlays — they're children of hex items so they go with them,
        # but we clear the lookup dict so _reapply_fog can recreate them after redraw
        self._fog_dm_items.clear()
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
        Removes the red outline previously drawn around the pixmap.
        Crops by _OUTLINE_THICKNESS pixels on each side.
        """
        if pixmap.isNull():
            return pixmap

        outline = _OUTLINE_THICKNESS
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
        self._clean_pixmaps.clear()

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


# ── Combat log ──────────────────────────────────────────────────────────────

class TurnGroupFrame(QFrame):
    """
    One collapsible turn block in the combat log.
    Shows a header button (click to expand/collapse) and a body of log lines.
    Right-clicking the header offers 'Set to Current Turn'.
    """
    undo_requested = pyqtSignal(int)   # emits serial

    _HEADER_STYLE = """
        QPushButton {{
            background: {bg}; color: {fg};
            border: {border}; border-radius: 3px;
            text-align: left; padding: 3px 8px;
            font-size: 20px; font-family: Consolas, monospace; font-weight: bold;
        }}
        QPushButton:hover {{ background: #252540; }}
    """

    def __init__(self, label: str, serial: int, accessible: bool, parent=None):
        super().__init__(parent)
        self.serial = serial
        self._accessible = accessible
        self._expanded = True

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 2)
        outer.setSpacing(0)

        self._header_btn = QPushButton(f"▼  {label}")
        self._header_btn.setFlat(True)
        self._header_btn.setCursor(Qt.PointingHandCursor)
        self._header_btn.clicked.connect(self._toggle)
        self._header_btn.setContextMenuPolicy(Qt.CustomContextMenu)
        self._header_btn.customContextMenuRequested.connect(self._on_right_click)
        outer.addWidget(self._header_btn)

        self._content = QWidget()
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(16, 0, 0, 4)
        content_layout.setSpacing(1)
        self._content_layout = content_layout
        outer.addWidget(self._content)

        self._apply_style(highlighted=False)

    def add_message(self, text: str):
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lbl.setStyleSheet(
            "color: #ccc; font-size: 18px; font-family: Consolas, monospace;"
            " background: transparent;"
        )
        self._content_layout.addWidget(lbl)

    def _toggle(self):
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        arrow = "▼" if self._expanded else "▶"
        txt = self._header_btn.text()
        self._header_btn.setText(arrow + txt[1:])

    def set_expanded(self, expanded: bool):
        self._expanded = expanded
        self._content.setVisible(expanded)
        arrow = "▼" if expanded else "▶"
        txt = self._header_btn.text()
        self._header_btn.setText(arrow + txt[1:])

    def _on_right_click(self, pos):
        if not self._accessible:
            return
        menu = QMenu(self)
        act = menu.addAction("🔄  Set to Current Turn")
        chosen = menu.exec_(self._header_btn.mapToGlobal(pos))
        if chosen == act:
            self.undo_requested.emit(self.serial)

    def highlight(self, on: bool):
        self._apply_style(highlighted=on)
        if on:
            self.set_expanded(True)

    def _apply_style(self, highlighted: bool):
        if highlighted:
            bg, fg, border = "#3d2a6a", "#c0a0ff", "1px solid #7050bb"
        else:
            bg, fg, border = "#1a1a2a", "#99bbdd", "1px solid #2a2a44"
        self._header_btn.setStyleSheet(
            self._HEADER_STYLE.format(bg=bg, fg=fg, border=border)
        )


class TurnLogWidget(QWidget):
    """
    Collapsible, right-clickable combat log.  Replaces the plain QTextEdit.

    Each turn becomes a TurnGroupFrame header (click to collapse/expand).
    Right-click a header → 'Set to Current Turn' (if it's still in the undo stack).
    """
    undo_requested = pyqtSignal(int)   # emits serial to undo to

    def __init__(self, parent=None):
        super().__init__(parent)
        self._groups: list = []          # list[TurnGroupFrame]
        self._pending_serial: int = 0
        self._oldest_accessible: int = 0
        self._highlighted_group = None   # TurnGroupFrame | None
        self._current_group = None       # TurnGroupFrame | None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { border: none; background: #111; }")
        outer.addWidget(self._scroll)

        self._container = QWidget()
        self._container.setStyleSheet("background: #111;")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(2)
        self._layout.addStretch(1)
        self._scroll.setWidget(self._container)

    # ── Public API ─────────────────────────────────────────────────────────

    def prepare_serial(self, serial: int):
        """Tell the widget what serial the NEXT 'Current Turn:' message will use."""
        self._pending_serial = serial

    def set_oldest_accessible(self, oldest: int):
        """Mark groups older than `oldest` as no longer undo-able."""
        self._oldest_accessible = oldest
        for g in self._groups:
            g._accessible = g.serial >= oldest

    def log(self, text: str):
        """Route a log message; auto-starts a new group when a turn header is detected."""
        if text.startswith("Current Turn:"):
            self._start_new_group(text)
        elif self._current_group is not None:
            self._current_group.add_message(text)
        else:
            lbl = QLabel(text)
            lbl.setStyleSheet(
                "color: #aaa; font-size: 18px; font-family: Consolas, monospace;"
                " background: transparent;"
            )
            self._layout.insertWidget(self._layout.count() - 1, lbl)
        QTimer.singleShot(0, self._scroll_to_bottom)

    def truncate_after_serial(self, serial: int):
        """Remove all groups with serial >= `serial`."""
        to_remove = [g for g in self._groups if g.serial >= serial]
        for g in to_remove:
            self._groups.remove(g)
            g.deleteLater()
        self._current_group = self._groups[-1] if self._groups else None
        if self._highlighted_group in to_remove:
            self._highlighted_group = None

    def highlight_group(self, serial: int):
        """Highlight (and expand) the turn group matching `serial`."""
        if self._highlighted_group:
            self._highlighted_group.highlight(False)
            self._highlighted_group = None
        for g in self._groups:
            if g.serial == serial:
                g.highlight(True)
                self._highlighted_group = g
                QTimer.singleShot(0, lambda grp=g: self._scroll.ensureWidgetVisible(grp))
                break

    def clear_highlights(self):
        if self._highlighted_group:
            self._highlighted_group.highlight(False)
            self._highlighted_group = None

    def clear(self):
        for g in list(self._groups):
            g.deleteLater()
        self._groups.clear()
        self._current_group = None
        self._highlighted_group = None

    # ── Internals ──────────────────────────────────────────────────────────

    def _start_new_group(self, label: str):
        serial = self._pending_serial
        accessible = serial >= self._oldest_accessible
        grp = TurnGroupFrame(label, serial, accessible)
        grp.undo_requested.connect(self.undo_requested)
        self._groups.append(grp)
        self._current_group = grp
        self._layout.insertWidget(self._layout.count() - 1, grp)

    def _scroll_to_bottom(self):
        self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        )


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
        # Select Target button
        # -------------------------------
        self.select_target_button = QPushButton("🎯 Select Target")
        self.select_target_button.setCheckable(True)
        self.select_target_button.setToolTip(
            "Click to enter target-selection mode, then click a hex on the map"
        )
        self.select_target_button.setStyleSheet(
            "QPushButton:checked { background-color: #8b1a1a; color: #ffffff; border: 2px solid #ff4444; border-radius: 4px; }"
        )
        main_layout.addWidget(self.select_target_button)

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

        # ---------------- CONCENTRATION STATUS ----------------
        self.concentration_label = QLabel()
        self.concentration_label.setStyleSheet(
            "color: #c080ff; font-style: italic; padding: 2px 0;"
        )
        self.concentration_label.setAlignment(Qt.AlignCenter)
        self.concentration_label.setVisible(False)
        main_layout.addWidget(self.concentration_label)

        # Restrained status label
        self.restrained_label = QLabel("⛓️ Restrained — speed 0")
        self.restrained_label.setStyleSheet(
            "color: #e0a020; font-style: italic; padding: 2px 0;"
        )
        self.restrained_label.setAlignment(Qt.AlignCenter)
        self.restrained_label.setVisible(False)
        main_layout.addWidget(self.restrained_label)

        # ---------------- GAME LOG ----------------
        self.game_log_label = QLabel("Game Log")
        self.game_log_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(self.game_log_label)

        self.turn_log = TurnLogWidget()
        self.turn_log.setMinimumHeight(200)
        self.turn_log.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.turn_log, stretch=2)


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
        # TurnLogWidget uses fixed internal CSS; no font scaling needed
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

        # Clear existing widgets
        self.clearLayout(self.spell_slot_layout)
        self.spell_slot_widgets.clear()

        if getattr(actor, 'is_player', False):
            # --- Player: show spell slots by level ---
            slot_data = actor.spellSlots
            maxSlots = actor.maxSpellSlots

            for level in sorted(slot_data.keys()):
                if level == '0':
                    continue
                max_slots = maxSlots[level]
                remaining = slot_data[level]
                if max_slots == 0:
                    continue

                lbl = QLabel(f"Level {level}")
                set_font(lbl, self._textScale.size(self._textScale.SM), QFont.Bold)
                self.spell_slot_layout.addWidget(lbl)

                row = QHBoxLayout()
                row.setSpacing(4)
                self.spell_slot_widgets[level] = []

                for i in range(max_slots):
                    slot = QCheckBox()
                    slot.setEnabled(False)
                    slot.setChecked(i < remaining)
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

        else:
            # --- Monster: show each spell with checkboxes for remaining uses ---
            spells = getattr(actor, 'spells', {})
            for spell_name, entry in spells.items():
                # Monster spell format: [remaining_uses, spell_dict]
                if not isinstance(entry, list) or len(entry) < 2:
                    continue
                remaining, spell_dict = entry[0], entry[1]
                if spell_dict.get('combat', 'n') == 'n':
                    continue

                # Derive max uses: we don't store it separately, so use remaining as
                # a rough proxy (it only decreases, so max = remaining + used; we
                # reconstruct on first call from the actor's initial state if available).
                max_uses = getattr(actor, '_spell_max_uses', {}).get(spell_name, remaining)

                lbl = QLabel(spell_name)
                set_font(lbl, self._textScale.size(self._textScale.SM), QFont.Bold)
                self.spell_slot_layout.addWidget(lbl)

                row = QHBoxLayout()
                row.setSpacing(4)
                self.spell_slot_widgets[spell_name] = []

                for i in range(max(max_uses, 1)):
                    slot = QCheckBox()
                    slot.setEnabled(False)
                    slot.setChecked(i < remaining)
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
                    self.spell_slot_widgets[spell_name].append(slot)

                row.addStretch()
                self.spell_slot_layout.addLayout(row)



    def log(self, text):
        """Append text to the combat log."""
        self.turn_log.log(text)

    def set_concentration(self, caster_name: str, spell_name: str):
        """Show a concentration indicator below the action buttons."""
        self.concentration_label.setText(f"🔮 {caster_name} concentrating: {spell_name}")
        self.concentration_label.setVisible(True)

    def clear_concentration(self):
        """Hide the concentration indicator."""
        self.concentration_label.setVisible(False)
        self.concentration_label.setText("")

    def set_restrained(self, save_type: str, dc: int):
        """Show restrained status indicator."""
        self.restrained_label.setText(f"⛓️ Restrained — speed 0 (Break Free: {save_type} DC {dc})")
        self.restrained_label.setVisible(True)

    def clear_restrained(self):
        """Hide the restrained indicator."""
        self.restrained_label.setVisible(False)


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

        # Show/hide restrained indicator
        restrained = getattr(actor, 'restrained', [])
        if restrained:
            self.set_restrained(restrained[0], restrained[1])
        else:
            self.clear_restrained()

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
        # Monster spells: {name: [count, spell_dict]}  Player spells: {name: spell_dict}
        # Normalise to a plain dict for level grouping.
        def _spell_dict(data):
            return data[1] if isinstance(data, list) else data

        # Build dictionary grouping spell names by level:
        #   { 0: [...], 1: [...], ... }
        level_groups = {}
        for spell_name, data in spells.items():
            lvl = _spell_dict(data).get("lvl", 0)
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
                        self.action_dropdown.addItemToGroup(spell_name, data=_spell_dict(spells[spell_name]))
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


def _expand_polygon(poly: QPolygonF, padding: float) -> QPolygonF:
    """Return a copy of poly with each vertex pushed outward from the centroid by `padding` pixels."""
    cx = sum(poly[i].x() for i in range(poly.count())) / poly.count()
    cy = sum(poly[i].y() for i in range(poly.count())) / poly.count()
    points = []
    for i in range(poly.count()):
        dx = poly[i].x() - cx
        dy = poly[i].y() - cy
        length = math.hypot(dx, dy)
        if length > 0:
            scale = (length + padding) / length
        else:
            scale = 1.0
        points.append(QPointF(cx + dx * scale, cy + dy * scale))
    return QPolygonF(points)


class PlayerMapView(QGraphicsView):
    """Non-interactive view that shares the main scene and paints opaque fog over fogged hexes."""

    # Semi-transparent red colour that mirrors coneFill — used to show targeting through fog
    _TARGETING_COLOR = QColor(255, 60, 60, 200)

    def __init__(self, scene):
        super().__init__(scene)
        self._fog_hex_items: list = []   # reference to CustomGraphicsView.hex_items
        self._fog_indices: set = set()
        self._target_indices: set = set()   # hexes currently highlighted for targeting

    def set_hex_items(self, hex_items: list):
        self._fog_hex_items = hex_items

    def update_fog(self, fog_indices: set):
        self._fog_indices = set(fog_indices)
        if self.scene():
            self.scene().update()

    def update_target_highlight(self, target_indices: set):
        self._target_indices = set(target_indices)
        if self.scene():
            self.scene().update()

    def drawForeground(self, painter, rect):
        """Paint fully-opaque fog polygons on top of all scene content.

        Each polygon is expanded by a few pixels so actor icons and their
        red turn-indicator outlines (which extend beyond the hex boundary)
        are fully hidden.

        Hexes that are currently highlighted for spell/attack targeting are
        shown through the fog with a red tint — the player can see the area
        being targeted but not any actors hidden inside the fog.
        """
        super().drawForeground(painter, rect)
        if not self._fog_indices or not self._fog_hex_items:
            return
        painter.save()
        painter.setPen(QPen(Qt.NoPen))

        for idx in self._fog_indices:
            if idx >= len(self._fog_hex_items):
                continue
            hex_item = self._fog_hex_items[idx]
            poly = hex_item.mapToScene(hex_item.polygon())
            expanded = _expand_polygon(poly, 10)

            if idx in self._target_indices:
                # Hex is targeted — draw opaque fog first to hide actors/outlines,
                # then overlay a bright targeting colour on top so the player sees the area
                painter.setBrush(QBrush(QColor(20, 20, 30, 255)))
                painter.drawPolygon(expanded)
                painter.setBrush(QBrush(self._TARGETING_COLOR))
                painter.drawPolygon(poly)
            else:
                painter.setBrush(QBrush(QColor(20, 20, 30, 255)))
                painter.drawPolygon(expanded)

        painter.restore()


class SecondaryMapWindow(QMainWindow):
    """Read-only mirror of the encounter map for display on a second screen.

    Shares the same QGraphicsScene as the main CustomGraphicsView so all
    updates (movement, highlights, outlines) are reflected automatically.
    The PlayerMapView subclass paints opaque fog over fogged hexes.
    """

    def __init__(self, scene, hex_items, fog_indices, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Player Map View")
        self.resize(900, 700)

        self._view = PlayerMapView(scene)
        self._view.set_hex_items(hex_items)
        self._view.update_fog(fog_indices)
        self._view.setRenderHints(
            QPainter.Antialiasing | QPainter.SmoothPixmapTransform
        )
        # Disable all interaction — this window is purely for display
        self._view.setInteractive(False)
        self._view.setDragMode(QGraphicsView.NoDrag)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.setFrameShape(QFrame.NoFrame)
        self._view.setBackgroundBrush(QBrush(QColor(20, 20, 20)))

        self.setCentralWidget(self._view)
        self._fit()

    def update_fog(self, fog_indices: set):
        """Relay fog changes from the main view to the player view."""
        self._view.update_fog(fog_indices)

    def update_target_highlight(self, target_indices: set):
        """Relay targeting highlight changes to the player view."""
        self._view.update_target_highlight(target_indices)

    def _fit(self):
        """Scale the view so the whole scene is visible."""
        scene = self._view.scene()
        if scene:
            self._view.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()

    def showEvent(self, event):
        super().showEvent(event)
        self._fit()


class MapWidget(QMainWindow):
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

        # ------------------------------------------------------------------
        # MENU BAR  (QMainWindow provides self.menuBar() for free)
        # ------------------------------------------------------------------
        file_menu = self.menuBar().addMenu("File")
        save_action = QAction("Save Encounter", self)
        save_action.triggered.connect(self.saveEncounter)
        file_menu.addAction(save_action)

        self.menuBar().addMenu("Edit")
        view_menu = self.menuBar().addMenu("View")
        self.menuBar().addMenu("Help")

        # ------------------------------------------------------------------
        # CENTRAL WIDGET: map toolbar + hex grid view
        # ------------------------------------------------------------------
        self.map_frame = QFrame()
        map_frame_layout = QVBoxLayout(self.map_frame)
        map_frame_layout.setContentsMargins(0, 0, 0, 0)
        map_frame_layout.setSpacing(5)

        # ---- Buttons above the map ----
        top_button_row = QHBoxLayout()
        top_button_row.setSpacing(10)

        self.distance_button = QPushButton("📏 Distance Calc")
        self.distance_button.setCheckable(True)
        self.distance_button.setToolTip(
            "Click to enter distance mode — click a start hex, then an end hex to measure the path"
        )
        self.distance_button.setStyleSheet(
            "QPushButton:checked { background-color: #1a6fa8; color: #ffffff; border: 2px solid #4ab0ff; border-radius: 4px; }"
        )
        self.distance_button.clicked.connect(self._toggle_distance_mode)
        top_button_row.addWidget(self.distance_button)

        self.wall_button = QPushButton("🧱 Walls")
        self.wall_button.setCheckable(True)
        self.wall_button.setToolTip("Click hexes to mark them as impassable walls")
        self.wall_button.setStyleSheet(
            "QPushButton:checked { background-color: #7a4a10; color: #ffffff; border: 2px solid #d08030; border-radius: 4px; }"
        )
        self.wall_button.clicked.connect(self._toggle_wall_mode)
        top_button_row.addWidget(self.wall_button)

        self.fog_button = QPushButton("🌫️ Fog")
        self.fog_button.setCheckable(True)
        self.fog_button.setToolTip(
            "Paint fog of war on hexes — hidden on the player display, dim on the DM view"
        )
        self.fog_button.setStyleSheet(
            "QPushButton:checked { background-color: #2a3a4a; color: #ccccdd; border: 2px solid #7799bb; border-radius: 4px; }"
        )
        self.fog_button.clicked.connect(self._toggle_fog_mode)
        top_button_row.addWidget(self.fog_button)

        self.manual_dice_button = QPushButton("🎲 Manual Rollers")
        self.manual_dice_button.setToolTip(
            "Choose which actors roll their own physical dice"
        )
        self.manual_dice_button.clicked.connect(self.openManualRollersDialog)
        top_button_row.addWidget(self.manual_dice_button)

        self.manual_actions_button = QPushButton("🎮 Manual Actions")
        self.manual_actions_button.setToolTip(
            "Choose which actors have their actions controlled by you (vs. the AI)"
        )
        self.manual_actions_button.clicked.connect(self.openManualActionsDialog)
        top_button_row.addWidget(self.manual_actions_button)

        top_button_row.addStretch(1)

        self.player_view_button = QPushButton("🖥️ Player View")
        self.player_view_button.setCheckable(True)
        self.player_view_button.setToolTip(
            "Open a read-only map window to show players on a second monitor"
        )
        self.player_view_button.setStyleSheet(
            "QPushButton:checked { background-color: #2a4a8a; color: #ffffff; border: 2px solid #6699ff; border-radius: 4px; }"
        )
        self.player_view_button.clicked.connect(self._toggle_player_view)
        top_button_row.addWidget(self.player_view_button)

        self.undo_button = QPushButton("Undo Turn")
        self.undo_button.setCheckable(True)
        self.undo_button.clicked.connect(self.undoTurn)
        top_button_row.addWidget(self.undo_button)

        map_frame_layout.addLayout(top_button_row)

        # ---- Map view ----
        self.map_view = CustomGraphicsView(self.myEncounter)
        gViewer = self.map_view
        self.map_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.map_view.setFrameShape(QFrame.Box)
        self.map_view.setMinimumWidth(300)
        map_frame_layout.addWidget(self.map_view, stretch=1)

        self.map_view.affectedSaved.connect(self.updateTargets)

        # ---- Start button at bottom of central area ----
        self.start_button = QPushButton("Start Encounter")
        self.start_button.setFixedHeight(40)
        self.start_button.clicked.connect(self.run_command)
        map_frame_layout.addWidget(self.start_button)

        self.setCentralWidget(self.map_frame)

        # ------------------------------------------------------------------
        # SETUP MAP PIXMAP, ACTORS, HEX GRID
        # ------------------------------------------------------------------
        map_path = self.myEncounter.mapImage or _DEFAULT_MAP
        pixmap = QPixmap(map_path)
        if pixmap.isNull():
            pixmap = QPixmap(_DEFAULT_MAP)
        self.map_view.setMapPixmap(pixmap)

        for player in self.myEncounter.totalList:
            px = _get_actor_pixmap(player)
            self.map_view.addCharacterPixmap(px, player)

        num_vertical_grids = int(self.myEncounter.numHexes)
        map_rect = self.map_view.map_item.boundingRect()
        self.map_view.drawHexGrid(num_vertical_grids, map_rect)

        self.undo_stack = deque(maxlen=20)
        self._turn_serial: int = 0    # increments on each saveTurnSnapshot()
        self._oldest_serial: int = 1  # serial of oldest entry in undo_stack

        # ------------------------------------------------------------------
        # DOCK: TURN ORDER (top)
        # ------------------------------------------------------------------
        self.turn_order_widget = TurnOrderWidget()
        turn_order_dock = QDockWidget("Turn Order", self)
        turn_order_dock.setObjectName("TurnOrderDock")
        turn_order_dock.setWidget(self.turn_order_widget)
        turn_order_dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        turn_order_dock.setFeatures(
            QDockWidget.DockWidgetMovable |
            QDockWidget.DockWidgetFloatable |
            QDockWidget.DockWidgetClosable
        )
        self.addDockWidget(Qt.TopDockWidgetArea, turn_order_dock)

        # ------------------------------------------------------------------
        # DOCK: TURN ACTION PANEL (right)
        # ------------------------------------------------------------------
        self.turn_action_panel = TurnActionPanel()
        self.turn_action_panel.take_turn_button.clicked.connect(self.takeTurnButton)
        self.turn_action_panel.move_input.clicked.connect(self.moveButton)
        self.turn_action_panel.endTurnButton.clicked.connect(self.endTurnButton)
        self.turn_action_panel.action_dropdown.currentTextChanged.connect(self.actionChanged)
        self.turn_action_panel.select_target_button.clicked.connect(self.spellButton_pressed)
        self.turn_action_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.turn_action_panel.turn_log.undo_requested.connect(self._undo_to_serial)

        action_dock = QDockWidget("Turn Actions", self)
        action_dock.setObjectName("TurnActionsDock")
        action_dock.setWidget(self.turn_action_panel)
        action_dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        action_dock.setFeatures(
            QDockWidget.DockWidgetMovable |
            QDockWidget.DockWidgetFloatable |
            QDockWidget.DockWidgetClosable
        )
        action_dock.setMinimumWidth(250)
        self.addDockWidget(Qt.RightDockWidgetArea, action_dock)

        self.turnChoices = None
        self.turnChoice = None
        self.actor = None

        self._secondary_map_window = None   # SecondaryMapWindow instance

        # Previous-turn data keyed by actor name: {actor_name: {from_idx, to_idx, serial}}
        self._turn_records: dict = {}
        self._current_actor_serial: int = 0  # serial of the currently-running turn

        # ------------------------------------------------------------------
        # VIEW MENU: toggle dock visibility
        # ------------------------------------------------------------------
        view_menu.addAction(turn_order_dock.toggleViewAction())
        view_menu.addAction(action_dock.toggleViewAction())

        # ------------------------------------------------------------------
        # SIGNAL WIRING
        # ------------------------------------------------------------------
        self.controller.log_message.connect(self.turn_action_panel.log)
        self.controller.turn_changed.connect(self._on_turn_changed)
        self.controller.actor_died.connect(self._on_actor_died)
        self.controller.encounter_ended.connect(self._on_encounter_ended)
        self.controller.persistent_spell_created.connect(self._on_persistent_spell_created)
        self.controller.persistent_spell_ended.connect(self._on_persistent_spell_ended)
        self.map_view.walls_changed.connect(self._on_walls_changed)
        self.map_view.fog_changed.connect(self._on_fog_changed)
        self.map_view.target_area_changed.connect(self._on_target_area_changed)

        self.controller.roll_provider_factory = self._make_roll_provider

        default_manual = {
            a.name for a in self.myEncounter.totalList
            if getattr(a, 'is_player', False)
        }
        self.controller.set_manual_actors(default_manual)

        # By default players are interactive (user controls actions); monsters are automated.
        default_interactive = {
            a.name for a in self.myEncounter.totalList
            if getattr(a, 'is_player', False)
        }
        self.controller.set_interactive_actors(default_interactive)
        # Also set on the encounter directly in case preCombat hasn't been called yet.
        self.myEncounter.interactive_actors = default_interactive

        # Wire prev-turn callbacks into the map view
        self.map_view._prev_turn_lookup = self._lookup_turn_record
        self.map_view._prev_turn_clear = self._clear_prev_turn_highlights
        self.map_view._prev_turn_log_highlight = self._highlight_log_entries

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

    def openManualActionsDialog(self):
        """Open the Manual Actions configuration dialog."""
        all_actors = list(self.myEncounter.totalList)
        dlg = ManualActionsDialog(all_actors, self.controller.interactive_actors, parent=self)
        if dlg.exec_() == ManualActionsDialog.Accepted:
            new_interactive = dlg.get_selected()
            self.controller.set_interactive_actors(new_interactive)
            self.myEncounter.interactive_actors = new_interactive

    def _on_turn_changed(self, actor):
        """Called by SimController.turn_changed signal when the active actor changes."""
        self.map_view.setCurTurn(actor)
        self.updateTurnOrder()
        # Sync concentration label to actual engine state
        self._refresh_concentration_label()

    # ------------------------------------------------------------------
    # Previous-turn tracking
    # ------------------------------------------------------------------

    def _actor_hex_idx(self, actor) -> int | None:
        """Return the current hex index of an actor on the map, or None."""
        coords = list(self.myEncounter.map.arrayCenters)
        for i, coord in enumerate(coords):
            if self.myEncounter.map.arrayCenters[coord] == actor:
                return i
        return None

    def _record_turn_start(self, actor):
        """Snapshot actor's hex position and current turn serial."""
        if actor is None:
            return
        idx = self._actor_hex_idx(actor)
        self._turn_records.setdefault(actor.name, {})['from_idx'] = idx
        self._current_actor_serial = self._turn_serial

    def _record_turn_end(self, actor):
        """Record where actor ended up and which serial their turn used."""
        if actor is None:
            return
        idx = self._actor_hex_idx(actor)
        rec = self._turn_records.setdefault(actor.name, {})
        rec['to_idx'] = idx
        rec['serial'] = self._current_actor_serial

    def _lookup_turn_record(self, actor) -> dict | None:
        """Return the stored turn record for an actor, or None if no data yet."""
        return self._turn_records.get(actor.name)

    def _highlight_log_entries(self, record: dict):
        """Highlight the turn group for the given actor record."""
        serial = record.get('serial')
        if serial is not None:
            self.turn_action_panel.turn_log.highlight_group(serial)

    def _clear_prev_turn_highlights(self):
        """Clear both the log highlights and the map path highlight."""
        self.turn_action_panel.turn_log.clear_highlights()
        self.map_view.clear_prev_turn_path()

    def _on_actor_died(self, actor):
        """Called by SimController.actor_died signal."""
        self.turn_action_panel.log(f'{actor.name} has died!')

    def _on_encounter_ended(self, winner):
        """Called by SimController.encounter_ended signal."""
        self.turn_action_panel.log(f'--- Encounter over! {winner} wins! ---')
        self.start_button.setEnabled(False)

    def _toggle_wall_mode(self, checked: bool):
        """Enable or disable wall-placement mode on the map view."""
        if checked:
            # Deactivate distance mode if active
            self.distance_button.setChecked(False)
            self.map_view.set_distance_mode(False)
            # Deactivate fog mode if active
            self.fog_button.setChecked(False)
            self.map_view.fog_mode = False
            self.map_view.show_fog_toolbar(False)
        self.map_view.wall_mode = checked
        if checked:
            self.map_view.setCursor(Qt.CrossCursor)
            # Reset to Create mode each time wall mode is activated
            self.map_view._wall_mode_create()
        else:
            self.map_view.unsetCursor()
        self.map_view.show_wall_toolbar(checked)

    def _toggle_distance_mode(self, checked: bool):
        """Enable or disable distance-measurement mode on the map view."""
        if checked:
            # Deactivate wall mode if active
            self.wall_button.setChecked(False)
            self.map_view.wall_mode = False
            self.map_view.show_wall_toolbar(False)
            self.map_view.unsetCursor()
            # Deactivate fog mode if active
            self.fog_button.setChecked(False)
            self.map_view.fog_mode = False
            self.map_view.show_fog_toolbar(False)
            # Deactivate spell targeting too
            self._set_target_mode(False)
        self.map_view.set_distance_mode(checked)

    def _toggle_fog_mode(self, checked: bool):
        """Enable or disable fog-of-war painting mode."""
        if checked:
            # Deactivate wall mode if active
            self.wall_button.setChecked(False)
            self.map_view.wall_mode = False
            self.map_view.show_wall_toolbar(False)
            # Deactivate distance mode if active
            self.distance_button.setChecked(False)
            self.map_view.set_distance_mode(False)
            # Deactivate spell targeting too
            self._set_target_mode(False)
        self.map_view.fog_mode = checked
        if checked:
            self.map_view.setCursor(Qt.CrossCursor)
            self.map_view._fog_mode_create()
        else:
            self.map_view.unsetCursor()
        self.map_view.show_fog_toolbar(checked)

    def _toggle_player_view(self, checked: bool):
        """Open or close the secondary read-only player map window."""
        if checked:
            if self._secondary_map_window is None or not self._secondary_map_window.isVisible():
                self._secondary_map_window = SecondaryMapWindow(
                    self.map_view.scene,
                    self.map_view.hex_items,
                    self.map_view._fog_indices,
                    parent=None,
                )
                self._secondary_map_window.setAttribute(Qt.WA_DeleteOnClose, False)
                # Move to second screen if available
                screens = QApplication.screens()
                if len(screens) > 1:
                    geom = screens[1].geometry()
                    self._secondary_map_window.setGeometry(geom)
                    self._secondary_map_window.showMaximized()
                else:
                    self._secondary_map_window.show()
                # Uncheck button when user closes the window manually
                self._secondary_map_window.destroyed.connect(
                    lambda: self.player_view_button.setChecked(False)
                )
            else:
                self._secondary_map_window.raise_()
                self._secondary_map_window.activateWindow()
        else:
            if self._secondary_map_window is not None:
                self._secondary_map_window.close()
                self._secondary_map_window = None

    def _on_fog_changed(self, fog_indices: set):
        """Relay fog changes to the player view if it's open."""
        if self._secondary_map_window is not None and self._secondary_map_window.isVisible():
            self._secondary_map_window.update_fog(fog_indices)

    def _on_target_area_changed(self, target_indices: set):
        """Relay targeting highlight to the player view if it's open."""
        if self._secondary_map_window is not None and self._secondary_map_window.isVisible():
            self._secondary_map_window.update_target_highlight(target_indices)

    def _on_walls_changed(self, wall_indices: set):
        """Sync wall indices from the view into the engine map."""
        if self.myEncounter.map is not None:
            self.myEncounter.map.walls = wall_indices

    def _on_persistent_spell_created(self, ps):
        """Paint and track a new persistent spell zone on the map."""
        self.map_view.add_persistent_zone(ps.spell_name, ps.affected_hex_indices)
        self.turn_action_panel.set_concentration(ps.caster.name, ps.spell_name)

    def _on_persistent_spell_ended(self, ps):
        """Remove the zone and clear concentration label."""
        self.map_view.remove_persistent_zone(ps.spell_name)
        self._refresh_concentration_label()

    def _refresh_concentration_label(self):
        """Sync the concentration label to actual engine state — clears if no one is concentrating."""
        if not hasattr(self.myEncounter, 'map') or self.myEncounter.map is None:
            return
        active_zones = getattr(self.myEncounter.map, 'persistent_spells', [])
        if active_zones:
            ps = active_zones[0]  # show the first active concentration spell
            self.turn_action_panel.set_concentration(ps.caster.name, ps.spell_name)
        else:
            self.turn_action_panel.clear_concentration()

    def _rebuild_persistent_zones(self):
        """Clear all GUI persistent-zone state and repaint from the engine's source of truth.

        Called after undo (or any full encounter restore) so the coloured hex zones
        and concentration label always match map.persistent_spells.
        """
        # Wipe every zone the GUI currently knows about
        for spell_name in list(self.map_view._persistent_zones.keys()):
            self.map_view.remove_persistent_zone(spell_name)

        # Repaint from what the engine actually has
        active_zones = getattr(self.myEncounter.map, 'persistent_spells', [])
        for ps in active_zones:
            self.map_view.add_persistent_zone(ps.spell_name, ps.affected_hex_indices)

        # Sync the concentration label
        self._refresh_concentration_label()

    # ------------------------------------------------------------------

    def saveEncounter(self):
        print("Saving encounter...")
        # later:
        # - deepcopy encounter
        # - serialize to JSON / pickle
        # - QFileDialog.getSaveFileName()


    def saveTurnSnapshot(self):
        # Nullify PyQt widgets before deep-copy
        self.myEncounter.graphicsViewer = None
        self.myEncounter.map.graphicsViewer = None
        self.myEncounter.map.combatLog = None
        snapshot = copy.deepcopy(self.myEncounter)
        self.myEncounter.graphicsViewer = self.map_view
        self.myEncounter.map.graphicsViewer = self.map_view
        self.myEncounter.map.combatLog = self.turn_action_panel.log

        # Track oldest accessible serial when deque is full
        if len(self.undo_stack) == 20:
            self._oldest_serial += 1
            self.turn_action_panel.turn_log.set_oldest_accessible(self._oldest_serial)

        self.undo_stack.append(snapshot)
        self._turn_serial += 1
        self.turn_action_panel.turn_log.prepare_serial(self._turn_serial)

    def undoTurn(self):
        if not self.undo_stack:
            return

        # Truncate the current in-progress turn group then re-log it after restore.
        # _turn_serial stays the same — we are replaying the same turn.
        self.turn_action_panel.turn_log.truncate_after_serial(self._turn_serial)

        self.myEncounter = self.undo_stack.pop()
        self.myEncounter.graphicsViewer = self.map_view
        self.myEncounter.map.graphicsViewer = self.map_view
        self.myEncounter.map.combatLog = self.turn_action_panel.log
        self.controller._encounter = self.myEncounter

        self.turn_action_panel.turn_log.prepare_serial(self._turn_serial)
        self.rebuildFromEncounter(relog_turn_header=True)

    def _undo_to_serial(self, serial: int):
        """Undo the encounter back to the start of the given turn serial."""
        undo_count = self._turn_serial - serial + 1
        if undo_count <= 0 or undo_count > len(self.undo_stack):
            return

        reply = QMessageBox.warning(
            self,
            "Set to Current Turn",
            f"This will restore the encounter to the state at the start of that turn and "
            f"remove all log entries after it.\n\nThis cannot be undone. Continue?",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if reply != QMessageBox.Yes:
            return

        # Truncate log to just before this turn
        self.turn_action_panel.turn_log.truncate_after_serial(serial)

        # Pop all snapshots down to the target (silently, without rebuilding)
        for _ in range(undo_count - 1):
            if self.undo_stack:
                self.undo_stack.pop()
        # _turn_serial becomes `serial` — the restored state IS at serial's turn
        self._turn_serial = serial

        # Final pop + restore
        self.myEncounter = self.undo_stack.pop()
        self.myEncounter.graphicsViewer = self.map_view
        self.myEncounter.map.graphicsViewer = self.map_view
        self.myEncounter.map.combatLog = self.turn_action_panel.log
        self.controller._encounter = self.myEncounter

        # Prepare serial so calcTurn re-logs the header into the correct group
        self.turn_action_panel.turn_log.prepare_serial(serial)
        self.rebuildFromEncounter(relog_turn_header=True)

    def rebuildFromEncounter(self, relog_turn_header: bool = False):
        self.map_view.loadFromEncounter(self.myEncounter)

        if relog_turn_header:
            # Called from undo paths — let calcTurn write the header into the log
            # so the current group is re-created after truncation.
            turns = self.myEncounter.calcTurn()
        else:
            # Normal rebuild — suppress the header so it isn't double-logged.
            _noop = lambda *_: None
            old_log = self.myEncounter.map.combatLog
            self.myEncounter.map.combatLog = _noop
            turns = self.myEncounter.calcTurn()
            self.myEncounter.map.combatLog = old_log
            
        if turns != None:
            self.actor = turns[0]
            self.turnChoices = turns[2]
            self.turnChoice = turns[3]
            self.turn_action_panel.update_turn_panel(self.actor, self.turnChoices, self.turnChoice)
        self.turn_action_panel.buildSpellSlots(self.actor)
        self.updateTurnOrder()
        
        newMoveHexes = calcMoveHexes(self.actor, self.myEncounter.map)
        self.map_view.setCurMoveCoords(newMoveHexes)

        # Resync persistent spell zones — clear GUI state then repaint from engine
        self._rebuild_persistent_zones()

        self.turn_action_panel.take_turn_button.setEnabled(True)
        self.turn_action_panel.action_dropdown.setEnabled(True)


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
        coords = list(self.myEncounter.map.arrayCenters)
        arrayCenters = self.myEncounter.map.arrayCenters

        # All area coords (occupied or not) — used for persistent zone coverage
        all_area_coords = [coords[ind] for ind in affectedHexes if ind < len(coords)]

        # Only occupied coords, excluding the acting actor (no self-targeting)
        actor_coord = None
        if self.actor is not None:
            for coord, occupant in arrayCenters.items():
                if occupant == self.actor:
                    actor_coord = coord
                    break

        targetsHit = [
            coords[ind] for ind in affectedHexes
            if ind < len(coords)
            and arrayCenters[coords[ind]] != ''
            and coords[ind] != actor_coord
        ]

        if not targetsHit and not all_area_coords:
            self.turn_action_panel.log("⚠️ No valid targets in selection — try a different hex.")
            # Leave targeting mode off but don't update turnChoice
            self._set_target_mode(False)
            return

        self.turnChoice.targets = targetsHit
        self.turnChoice.area_coords = all_area_coords

        targetNames = [arrayCenters[coord].name for coord in targetsHit]
        targetString = ', '.join(targetNames) if targetNames else '(no actors hit — miss)'
        self.turn_action_panel.targets_label.setText(targetString)
        if not targetsHit:
            self.turn_action_panel.log("⚔️ No actors at target location — action will miss.")

        # Targeting mode complete — deactivate the button
        self._set_target_mode(False)

    def actionChanged(self):
        action = self.turn_action_panel.action_dropdown.currentText()
        if action == 'dash':
            self.turn_action_panel.move_input.setEnabled(False)
        else:
            self.turn_action_panel.move_input.setEnabled(True)
        # Configure target params for the new action and auto-activate targeting
        self._setup_target_params()
        self._set_target_mode(True)

    def _set_target_mode(self, active: bool):
        """Turn targeting mode on or off and sync the button state."""
        self.map_view.spellAreaCheck = True if active else False
        self.turn_action_panel.select_target_button.setChecked(active)
        if not active:
            # Clear targeting highlight on the player view
            self.map_view.target_area_changed.emit(set())

    def spellButton_pressed(self):
        if self.map_view.curActor is None:
            return
        # Toggle targeting mode
        currently_on = bool(self.map_view.spellAreaCheck)
        self._setup_target_params()
        self._set_target_mode(not currently_on)

    def _setup_target_params(self):
        """Configure spell/weapon area parameters on the map view for the current action."""
        actor = self.map_view.curActor
        if actor is None:
            return

        newMoves = calcMoveHexes(actor, self.myEncounter.map)
        self.map_view.setCurMoveCoords(newMoves)

        action = self.turn_action_panel.action_dropdown.currentText()
        weapons = [x.name for x in actor.weaponList]

        # Reset area parameters
        self.map_view.spellAreaType = None
        self.map_view.spellRange = None
        self.map_view.spellDistance = None
        self.map_view.spell_centers = []
        self.map_view.spell_tree = None
        self.map_view.spell_index = []

        spell_data = None
        if action in actor.spells:
            raw = actor.spells[action]
            # Monsters store spells as [count, dict]; players store dict directly
            spell_data = raw[1] if isinstance(raw, list) else raw
        
        if spell_data is not None:
            area = spell_data.get('area', '')
            if 'cone' in area:
                self.map_view.spellAreaType = 'cone'
                self.map_view.spellRange = None
                self.map_view.spellDistance = int(int(re.findall(r'\d+', area)[0]) / 5)
            elif 'sphere' in area:
                self.map_view.spellAreaType = 'sphere'
                self.map_view.spellRange = int(int(re.findall(r'\d+', spell_data['range'])[0]) / 5)
                self.map_view.spellDistance = int(int(re.findall(r'\d+', area)[0]) / 5)
                self.map_view.calcSpellLimit(self.map_view.spellRange)
            elif 'line' in area:
                self.map_view.spellAreaType = 'line'
                self.map_view.spellRange = None
                self.map_view.spellDistance = int(int(re.findall(r'\d+', area)[0]) / 5)
            elif 'square' in area:
                self.map_view.spellAreaType = 'square'
                self.map_view.spellRange = int(int(re.findall(r'\d+', spell_data['range'])[0]) / 5)
                self.map_view.spellDistance = int(int(re.findall(r'\d+', area)[0]) / 5)
                self.map_view.calcSpellLimit(self.map_view.spellRange)
            else:  # single target spell
                self.map_view.spellAreaType = 'single'
                self.map_view.spellRange = int(int(re.findall(r'\d+', spell_data['range'])[0]) / 5)
                self.map_view.spellDistance = 0
                self.map_view.calcSpellLimit(self.map_view.spellRange)
        elif action in weapons:
            weapon = actor.weaponList[weapons.index(action)]
            self.map_view.spellAreaType = 'single'
            self.map_view.spellRange = weapon.range / 5
            self.map_view.spellDistance = 0
            self.map_view.calcSpellLimit(self.map_view.spellRange)
        elif action == 'dash':
            newMoves = calcMoveHexes(actor, self.myEncounter.map, type='dash')
            self.map_view.setCurMoveCoords(newMoves)
    
    def moveButton(self):
        hexIndex = self.map_view.getCurActorHexIndex()
        if self.turnChoice is not None and self.actor is not None and hexIndex is not None:
            currLocation = list(self.myEncounter.map.arrayCenters)[hexIndex]
            self.turnChoice.moveCoord = currLocation
            dist, new_move_hexes = self.controller.move_actor(self.actor, currLocation, hexIndex)
            self.map_view.setCurMoveCoords(new_move_hexes)

    def endTurnButton(self):
        self._set_target_mode(False)
        self.map_view.affected = None
        # Clear distance mode on new turn
        self.distance_button.setChecked(False)
        self.map_view.set_distance_mode(False)

        # Record end-of-turn state for the current actor before advancing
        self._record_turn_end(self.actor)

        # Save snapshot of the completed turn (= start of next turn state)
        self.saveTurnSnapshot()

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

        # Record start-of-turn state for the new actor
        self._record_turn_start(self.actor)

    def takeTurnButton(self):
        hexIndex = self.map_view.getCurActorHexIndex()
        if self.turnChoice is not None and self.actor is not None:
            if hexIndex is not None:
                currLocation = list(self.myEncounter.map.arrayCenters)[hexIndex]
                self.turnChoice.moveCoord = currLocation
            currAction = self.turn_action_panel.action_dropdown.currentText()
            self.turnChoice.type = [x.type for x in self.turnChoices if x.name == currAction][0]
            self.turnChoice.name = currAction
            self.controller.take_action(self.actor, self.turnChoice)
            self.turn_action_panel.take_turn_button.setEnabled(False)
            self.turn_action_panel.action_dropdown.setEnabled(False)
            self.turn_action_panel.buildSpellSlots(self.actor)
        
    def run_command(self):
        self.turn_action_panel.log('Starting Combat!')
        # Snapshot BEFORE calcTurn so serial 1 covers the first turn header logged below
        self.saveTurnSnapshot()
        turns = self.myEncounter.calcTurn()
        if turns != None:
            self.actor = turns[0]
            self.map_view.setCurTurn(self.actor)
            self.turnChoices = turns[2]
            self.turnChoice = turns[3]
            self.turn_action_panel.update_turn_panel(self.actor, self.turnChoices, self.turnChoice)
            self.turn_action_panel.buildSpellSlots(self.actor)
        # Record starting position for first actor
        self._record_turn_start(self.actor)

    def testingTheory(self):
        # should populate turn_order_widget
        # create the initial movement grids highlight 

        self.myEncounter.preCombat(self.map_view)
        self.myEncounter.map.combatLog = self.turn_action_panel.log
        # Red outline is now managed by setCurTurn — trigger it for the starting actor
        curActor = list(self.myEncounter.sortedInitList)[self.myEncounter.curTurn]
        self.map_view.setCurTurn(curActor)
        self.updateTurnOrder()

    
        





#myMap = Map('mazeEngine',dmSimPath + "\\App\\Maps\\maze Engine.webp", 10, myPlayers)

#app = QApplication([])

#window = MapWidget(myEncounter)
#window.show()

#app.exec()


