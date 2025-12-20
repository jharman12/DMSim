from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QPushButton, QMessageBox, QLabel, QApplication
)
from PyQt5.QtCore import Qt

from newCharWindow import CharacterEditor, CharacterStore
from TestingMap import MapWidget
import pathlib
dmSimPath = str(pathlib.Path(__file__).parent.resolve())[0:-4]
from player import createPartyList
from monster import createMonsterList
from interactiveEncounter import interactiveEncounter

class EncounterBuilderTab(QWidget):
    def __init__(self, start_callback):
        super().__init__()

        self.start_callback = start_callback

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Encounter Builder"))

        self.start_button = QPushButton("Start Encounter")
        self.start_button.clicked.connect(self.start_callback)

        layout.addWidget(self.start_button)
        layout.addStretch()
    def buildEncounter(self):
        path = dmSimPath + '\\actors\\savedObjs\\'
        myPlayers = createPartyList(['Arabella', 'Root', 'Ephraim',  'Darian'], path = path)
        myPlayers = createPartyList(['Aldric',  'Galleus', 'Adrel', 'VV', 'Cobo'], path = path)
        #badGuys = createMonsterList(["Quenth"] + ["Demogorgon" for i in range(1)], path = path)
        badGuys = createMonsterList(["Myconid Sovereign" for i in range(2)] + ["Myconid Adult" for i in range(6)], path = path)
        myEncounter = interactiveEncounter(myPlayers, [], badGuys, 20, dmSimPath + "\\App\\Maps\\maze Engine.webp")
        return myEncounter


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("DnD Encounter Manager")
        self.resize(1400, 900)

        # ---- Central widget ----
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # ---- Tabs ----
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        layout.addWidget(self.tabs)

        # ---- Tabs ----
        store = CharacterStore()
        self.character_editor = CharacterEditor(store)
        self.encounter_builder = EncounterBuilderTab(self.startEncounter)

        self.tabs.addTab(self.character_editor, "Characters")
        self.tabs.addTab(self.encounter_builder, "Encounter Builder")

        # Keep reference so it doesn’t get GC’d
        self.map_window = None

    def startEncounter(self):
        encounter = self.encounter_builder.buildEncounter()
        if not encounter:
            QMessageBox.warning(self, "Error", "Invalid encounter setup")
            return

        # Close old map window if it exists
        if self.map_window:
            self.map_window.close()

        self.map_window = MapWidget(encounter)
        self.map_window.show()

app = QApplication([])

window = MainWindow()
window.show()

app.exec()