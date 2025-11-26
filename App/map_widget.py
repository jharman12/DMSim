from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, QLineEdit
from custom_graphics_view import CustomGraphicsView
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QRectF


class MapWidget(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        self.graphics_view = CustomGraphicsView()
        layout.addWidget(self.graphics_view)

        self.import_map_button = QPushButton("Import Map")
        self.import_map_button.clicked.connect(self.import_map)
        layout.addWidget(self.import_map_button)

        self.import_character_button = QPushButton("Import Character")
        self.import_character_button.clicked.connect(self.import_character)
        layout.addWidget(self.import_character_button)

        # Add input for the number of vertical grids
        self.num_vertical_grids_label = QLabel("Number of Vertical Grids:")
        layout.addWidget(self.num_vertical_grids_label)

        self.num_vertical_grids_input = QLineEdit()
        layout.addWidget(self.num_vertical_grids_input)

        # Add a button to draw hexagonal grid
        self.draw_grid_button = QPushButton("Draw Hexagonal Grid")
        self.draw_grid_button.clicked.connect(self.draw_hexagonal_grid)
        layout.addWidget(self.draw_grid_button)

        self.setLayout(layout)

    def import_map(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, 'Import Map', '', 'Image Files (*.png *.jpg *.jpeg)')
        if file_path:
            pixmap = QPixmap(file_path)
            self.graphics_view.setMapPixmap(pixmap)

    def import_character(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, 'Import Character', '', 'Image Files (*.png *.jpg *.jpeg)')
        if file_path:
            pixmap = QPixmap(file_path)
            self.graphics_view.addCharacterPixmap(pixmap)

    def draw_hexagonal_grid(self):
        num_vertical_grids = int(self.num_vertical_grids_input.text())
        map_rect = self.graphics_view.map_item.boundingRect()
        self.graphics_view.drawHexGrid(num_vertical_grids, map_rect)
