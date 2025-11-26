# dnd_character_editor.py
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QStackedWidget
from character_widget import CharacterWidget
from map_widget import MapWidget
from encounter_widget import EncounterWidget
from test_widget import Ui_Form
import pathlib
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, QLineEdit
from custom_graphics_view import CustomGraphicsView
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QRectF
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPolygonItem
from PyQt5.QtCore import Qt, QPointF, QRectF, QSizeF
from PyQt5.QtGui import QPixmap, QPen, QPolygonF, QPainter, QPainterPath, QBitmap
import math
from scipy import spatial
import numpy as np
import math
dmSimPath = str(pathlib.Path(__file__).parent.resolve())[0:-4]
print(dmSimPath)

sys.path.insert(1, dmSimPath + '/model')
from player import createPartyList, Player
from monster import Monster, MonsterDump, createMonsterList
import map

class DNDCharacterEditor(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("D&D Character Editor")
        self.setGeometry(400, 100, 1600, 800)

        self.data = {"character": {}, "monster": {}}

        self.stacked_widget = QStackedWidget()
        self.create_widgets()
        #self.create_navigation_buttons()

        main_layout = QHBoxLayout()
        #main_layout.addWidget(self.navigation_widget)
        main_layout.addWidget(self.stacked_widget)
        self.setLayout(main_layout)

    def create_widgets(self):
        #character_widget = CharacterWidget() #self.data
        self.map_widget = MapWidget()
        #encounter_widget = EncounterWidget()
        
        
        #self.stacked_widget.addWidget(character_widget)
        self.stacked_widget.addWidget(self.map_widget)
        #self.stacked_widget.addWidget(encounter_widget)

class MapWidget(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        self.graphics_view = CustomGraphicsView()
        layout.addWidget(self.graphics_view)
        
        
        self.setLayout(layout)
        #self.import_map_button = QPushButton("Import Map")
        #self.import_map_button.clicked.connect(self.import_map)
        #layout.addWidget(self.import_map_button)

        #self.import_character_button = QPushButton("Import Character")
        #self.import_character_button.clicked.connect(self.import_character)
        #layout.addWidget(self.import_character_button)

        # Add input for the number of vertical grids
        #self.num_vertical_grids_label = QLabel("Number of Vertical Grids:")
        #layout.addWidget(self.num_vertical_grids_label)

        #self.num_vertical_grids_input = QLineEdit()
        #layout.addWidget(self.num_vertical_grids_input)

        # Add a button to draw hexagonal grid
        #self.draw_grid_button = QPushButton("Draw Hexagonal Grid")
        #self.draw_grid_button.clicked.connect(self.draw_hexagonal_grid)
        #layout.addWidget(self.draw_grid_button)

    def createMap(self, file_path, size):
        pixmap = QPixmap(file_path)
        self.graphics_view.setMapPixmap(pixmap)
        
        map_rect = self.graphics_view.map_item.boundingRect()
        
        self.graphics_view.drawHexGrid(size, map_rect)
        

    def createCharacter(self, file_path, name):
        path = dmSimPath + '/App/Monsters/dem.webp'
        pixmap = QPixmap(file_path)
        self.graphics_view.addCharacterPixmap(pixmap, name)

class connectionHandler:
    def __init__(self, party, enemy, size, mapImage):
        Ephraim = dmSimPath + '/App/Characters/Ephraim.jpg'
        Arabella = dmSimPath + '/App/Characters/Arabella.jpg'
        dem = dmSimPath + '/App/Monsters/dem.webp'
        self.map = map.Map(15, party, enemy)

        app = QApplication(sys.argv)
        editor = DNDCharacterEditor()
        editor.map_widget.createCharacter(Ephraim, 'Ephraim')
        #editor.map_widget.createCharacter(Arabella, 'Arebella')
        
        #editor.map_widget.createCharacter(dem, 'dem')
        editor.show()
        
        editor.map_widget.createMap(mapImage, size)
        sys.exit(app.exec_())
        
if __name__ == "__main__":
    path = dmSimPath + '\\actors\\savedObjs\\'
    party = createPartyList(['Ephraim', 'Darian', 'Root','Arabella'], path = path)
    enemy = createMonsterList( ["Demogorgon" for i in range(1)], path = path)
    mapPath = dmSimPath + '/App/Maps/OozingTemple.jpg'
    connectionHandler(party, enemy, 15, mapPath)