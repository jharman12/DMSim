# dnd_character_editor.py
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QStackedWidget
from character_widget import CharacterWidget
from map_widget import MapWidget
from encounter_widget import EncounterWidget
from test_widget import Ui_Form


class DNDCharacterEditor(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("D&D Character Editor")
        self.setGeometry(400, 100, 1600, 800)

        self.data = {"character": {}, "monster": {}}

        self.stacked_widget = QStackedWidget()
        self.create_widgets()
        self.create_navigation_buttons()

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.navigation_widget)
        main_layout.addWidget(self.stacked_widget)
        self.setLayout(main_layout)

    def create_widgets(self):
        character_widget = CharacterWidget() #self.data
        map_widget = MapWidget()
        encounter_widget = EncounterWidget()
        
        
        self.stacked_widget.addWidget(character_widget)
        self.stacked_widget.addWidget(map_widget)
        self.stacked_widget.addWidget(encounter_widget)

    def create_navigation_buttons(self):
        self.navigation_widget = QWidget()
        button_layout = QVBoxLayout()
        button_names = ["Character", "Map", "Encounter"]
        for i, window_name in enumerate(button_names):
            button = QPushButton(window_name)
            button.clicked.connect(lambda _, index=i: self.stacked_widget.setCurrentIndex(index))
            button_layout.addWidget(button)

        self.navigation_widget.setLayout(button_layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = DNDCharacterEditor()
    editor.show()
    sys.exit(app.exec_())
