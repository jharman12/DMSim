from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QHBoxLayout, QTabBar,
    QPushButton, QMessageBox, QLabel, QApplication, QAction, QActionGroup,
    QListWidget, QDialog, QLineEdit, QSpinBox, QGroupBox, QListWidgetItem,
    QFileDialog, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QEvent

from newCharWindow import CharacterEditor, CharacterStore
from monsterWindow import MonsterEditor, MonsterStore
from TestingMap import MapWidget
import pathlib
import json
from pathlib import Path
from player import createPartyList
from monster import createMonsterList
dmSimPath = str(pathlib.Path(__file__).parent.resolve())[0:-4]
from player import createPartyList
from monster import createMonsterList
from interactiveEncounter import interactiveEncounter

class EncounterStore:
    def __init__(self, file_path=None):
        if file_path is None:
            file_path = Path(__file__).parent.parent / "actors" / "savedObjs" / "encounters.json"
        self.file_path = Path(file_path)
        self.encounters = {}
        self.load()

    def load(self):
        if self.file_path.exists():
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self.encounters = data
            elif isinstance(data, list):
                self.encounters = {e.get("name", f"encounter_{i}"): e for i, e in enumerate(data)}
        else:
            self.encounters = {}

    def save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.encounters, f, indent=4)

    def add_encounter(self, name, party, npcs, enemies, numHexes, mapImage):
        self.encounters[name] = {
            "name": name,
            "party": party,
            "npcs": npcs,
            "enemies": enemies,
            "numHexes": numHexes,
            "mapImage": mapImage
        }
        self.save()

    def delete_encounter(self, name):
        if name in self.encounters:
            del self.encounters[name]
            self.save()

    def get_encounter(self, name):
        return self.encounters.get(name)

class TextScale:
    XS = 0
    SM = 1
    MD = 2
    LG = 3
    XL = 4

    BASE = 11  # default font size

    SCALE_MAP = {
        XS: 0.85,
        SM: 0.95,
        MD: 1.00,
        LG: 1.15,
        XL: 1.30,
    }

    
    max_BASE = 24
    min_BASE = 6

    @classmethod
    def size(cls, scale):
        return int(cls.BASE * cls.SCALE_MAP[scale])
    
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

class EncounterBuilderTab(QWidget):
    
    def __init__(self, start_callback, main_window, char_store, mon_store, enc_store):
        super().__init__()

        self.start_callback = start_callback
        self.main_window = main_window
        self.char_store = char_store
        self.mon_store = mon_store
        self.enc_store = enc_store

        layout = QVBoxLayout(self)

        # Encounter Management
        enc_group = QGroupBox("Encounters")
        enc_layout = QVBoxLayout()
        # Search bar
        self.enc_search = QLineEdit()
        self.enc_search.setPlaceholderText("Search encounters...")
        self.enc_search.textChanged.connect(self.filter_encounters)
        enc_layout.addWidget(self.enc_search)
        self.enc_list = QListWidget()
        self.update_enc_list()
        enc_layout.addWidget(self.enc_list)
        enc_buttons = QHBoxLayout()
        new_enc_btn = QPushButton("New")
        new_enc_btn.clicked.connect(self.new_encounter)
        edit_enc_btn = QPushButton("Edit")
        edit_enc_btn.clicked.connect(self.edit_encounter)
        save_enc_btn = QPushButton("Save")
        save_enc_btn.clicked.connect(self.save_encounter)
        del_enc_btn = QPushButton("Delete")
        del_enc_btn.clicked.connect(self.delete_encounter)
        load_enc_btn = QPushButton("Load")
        load_enc_btn.clicked.connect(self.load_encounter)
        enc_buttons.addWidget(new_enc_btn)
        enc_buttons.addWidget(edit_enc_btn)
        enc_buttons.addWidget(save_enc_btn)
        enc_buttons.addWidget(del_enc_btn)
        enc_buttons.addWidget(load_enc_btn)
        enc_layout.addLayout(enc_buttons)
        enc_group.setLayout(enc_layout)
        layout.addWidget(enc_group)

        # Encounter Details Group
        details_group = QGroupBox("Encounter Details")
        details_layout = QVBoxLayout()

        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        name_layout.addWidget(self.name_edit)
        details_layout.addLayout(name_layout)

        # Num Hexes
        hex_layout = QHBoxLayout()
        hex_layout.addWidget(QLabel("Num Hexes:"))
        self.hex_spin = QSpinBox()
        self.hex_spin.setRange(5, 100)
        self.hex_spin.setValue(20)
        hex_layout.addWidget(self.hex_spin)
        details_layout.addLayout(hex_layout)

        # Map Image
        map_layout = QHBoxLayout()
        map_layout.addWidget(QLabel("Map Image Path:"))
        self.map_edit = QLineEdit()
        map_layout.addWidget(self.map_edit)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_map_image)
        map_layout.addWidget(browse_btn)
        details_layout.addLayout(map_layout)

        details_group.setLayout(details_layout)
        layout.addWidget(details_group)

        # Setup lists
        self.setup_lists(layout)

    def setup_lists(self, layout):
        # Available characters and monsters
        self.avail_chars = self.char_store.get_names()
        self.avail_mons = self.mon_store.get_names()

        # Create group boxes
        party_group = QGroupBox("Party")
        party_layout = QVBoxLayout()
        self.party_combo = QComboBox()
        self.party_combo.setEditable(True)
        self.party_combo.addItems(self.avail_chars)
        self.party_combo.setCurrentIndex(-1)  # No selection
        party_layout.addWidget(self.party_combo)
        self.party_list = QListWidget()
        party_layout.addWidget(self.party_list)
        party_buttons = QHBoxLayout()
        add_party_btn = QPushButton("Add")
        add_party_btn.clicked.connect(lambda: self.add_from_combo(self.party_combo, self.party_list))
        self.party_combo.lineEdit().returnPressed.connect(lambda: self.add_from_combo(self.party_combo, self.party_list))
        remove_party_btn = QPushButton("Remove")
        remove_party_btn.clicked.connect(lambda: self.remove_from_list(self.party_list))
        party_buttons.addWidget(add_party_btn)
        party_buttons.addWidget(remove_party_btn)
        party_layout.addLayout(party_buttons)
        party_group.setLayout(party_layout)

        npc_group = QGroupBox("NPCs")
        npc_layout = QVBoxLayout()
        self.npc_combo = QComboBox()
        self.npc_combo.setEditable(True)
        self.npc_combo.addItems(self.avail_chars)
        self.npc_combo.setCurrentIndex(-1)
        npc_layout.addWidget(self.npc_combo)
        self.npc_list = QListWidget()
        npc_layout.addWidget(self.npc_list)
        npc_buttons = QHBoxLayout()
        add_npc_btn = QPushButton("Add")
        add_npc_btn.clicked.connect(lambda: self.add_from_combo(self.npc_combo, self.npc_list))
        self.npc_combo.lineEdit().returnPressed.connect(lambda: self.add_from_combo(self.npc_combo, self.npc_list))
        remove_npc_btn = QPushButton("Remove")
        remove_npc_btn.clicked.connect(lambda: self.remove_from_list(self.npc_list))
        npc_buttons.addWidget(add_npc_btn)
        npc_buttons.addWidget(remove_npc_btn)
        npc_layout.addLayout(npc_buttons)
        npc_group.setLayout(npc_layout)

        enemy_group = QGroupBox("Enemies")
        enemy_layout = QVBoxLayout()
        self.enemy_combo = QComboBox()
        self.enemy_combo.setEditable(True)
        self.enemy_combo.addItems(self.avail_mons)
        self.enemy_combo.setCurrentIndex(-1)
        enemy_layout.addWidget(self.enemy_combo)
        self.enemy_list = QListWidget()
        enemy_layout.addWidget(self.enemy_list)
        enemy_buttons = QHBoxLayout()
        add_enemy_btn = QPushButton("Add")
        add_enemy_btn.clicked.connect(lambda: self.add_from_combo(self.enemy_combo, self.enemy_list))
        self.enemy_combo.lineEdit().returnPressed.connect(lambda: self.add_from_combo(self.enemy_combo, self.enemy_list))
        remove_enemy_btn = QPushButton("Remove")
        remove_enemy_btn.clicked.connect(lambda: self.remove_from_list(self.enemy_list))
        enemy_buttons.addWidget(add_enemy_btn)
        enemy_buttons.addWidget(remove_enemy_btn)
        enemy_layout.addLayout(enemy_buttons)
        enemy_group.setLayout(enemy_layout)

        lists_layout = QHBoxLayout()
        lists_layout.addWidget(party_group)
        lists_layout.addWidget(npc_group)
        lists_layout.addWidget(enemy_group)
        layout.addLayout(lists_layout)

    def browse_map_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Map Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_path:
            self.map_edit.setText(file_path)

    def add_from_combo(self, combo, list_widget):
        text = combo.currentText().strip()
        if text and not any(list_widget.item(i).text() == text for i in range(list_widget.count())):
            list_widget.addItem(text)
            combo.setCurrentIndex(-1)  # Clear selection

    def add_to_list(self, list_widget, avail):
        # Simple dialog to select from avail
        from PyQt5.QtWidgets import QInputDialog
        item, ok = QInputDialog.getItem(self, "Select", "Choose:", avail, 0, False)
        if ok and item:
            list_widget.addItem(item)

    def remove_from_list(self, list_widget):
        current = list_widget.currentItem()
        if current:
            list_widget.takeItem(list_widget.row(current))

    def get_current_data(self):
        party = [self.party_list.item(i).text() for i in range(self.party_list.count())]
        npcs = [self.npc_list.item(i).text() for i in range(self.npc_list.count())]
        enemies = [self.enemy_list.item(i).text() for i in range(self.enemy_list.count())]
        return {
            "name": self.name_edit.text(),
            "party": party,
            "npcs": npcs,
            "enemies": enemies,
            "numHexes": self.hex_spin.value(),
            "mapImage": self.map_edit.text()
        }

    def set_current_data(self, data):
        self.name_edit.setText(data.get("name", ""))
        self.hex_spin.setValue(data.get("numHexes", 20))
        self.map_edit.setText(data.get("mapImage", ""))
        self.party_list.clear()
        for name in data.get("party", []):
            self.party_list.addItem(name)
        self.npc_list.clear()
        for name in data.get("npcs", []):
            self.npc_list.addItem(name)
        self.enemy_list.clear()
        for name in data.get("enemies", []):
            self.enemy_list.addItem(name)

    def update_enc_list(self):
        self.enc_list.clear()
        filter_text = self.enc_search.text()
        all_names = sorted(self.enc_store.encounters.keys())
        filtered_names = [name for name in all_names if filter_text.lower() in name.lower()]
        for name in filtered_names:
            self.enc_list.addItem(name)

    def filter_encounters(self):
        self.update_enc_list()

    def new_encounter(self):
        self.set_current_data({})

    def edit_encounter(self):
        current = self.enc_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Warning", "Select an encounter to edit")
            return
        name = current.text()
        encounter = self.enc_store.get_encounter(name)
        self.set_current_data(encounter)

    def save_encounter(self):
        data = self.get_current_data()
        name = data["name"]
        if not name:
            QMessageBox.warning(self, "Warning", "Enter a name for the encounter")
            return
        self.enc_store.add_encounter(name, data["party"], data["npcs"], data["enemies"], data["numHexes"], data["mapImage"])
        self.update_enc_list()

    def delete_encounter(self):
        current = self.enc_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Warning", "Select an encounter to delete")
            return
        name = current.text()
        self.enc_store.delete_encounter(name)
        self.update_enc_list()

    def load_encounter(self):
        current = self.enc_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Warning", "Select an encounter to load")
            return
        name = current.text()
        enc_data = self.enc_store.get_encounter(name)
        path = dmSimPath + '\\actors\\savedObjs\\'
        party = createPartyList(enc_data["party"], path=path)
        npcs = createPartyList(enc_data["npcs"], path=path)
        enemies = createMonsterList(enc_data["enemies"], path=path)
        encounter = interactiveEncounter(party, npcs, enemies, enc_data["numHexes"], enc_data["mapImage"])
        self.start_callback(encounter)

    def buildEncounter(self):
        # Keep for compatibility, but not used
        pass
    
    def applyFonts(self):
        mw = self.window()
        if mw is None:
            return

        base = mw.TextScale.size(mw.text_scale)
        # Apply to buttons, etc.
        for widget in self.findChildren(QPushButton):
            set_font(widget, base)

from PyQt5 import QtCore, QtGui, QtWidgets


class TabBar(QtWidgets.QTabBar):
    def tabSizeHint(self, index):
        s = QtWidgets.QTabBar.tabSizeHint(self, index)
        s.transpose()
        return s

    def paintEvent(self, event):
        painter = QtWidgets.QStylePainter(self)
        opt = QtWidgets.QStyleOptionTab()

        for i in range(self.count()):
            self.initStyleOption(opt, i)
            painter.drawControl(QtWidgets.QStyle.CE_TabBarTabShape, opt)
            painter.save()

            s = opt.rect.size()
            s.transpose()
            r = QtCore.QRect(QtCore.QPoint(), s)
            r.moveCenter(opt.rect.center())
            opt.rect = r

            c = self.tabRect(i).center()
            painter.translate(c)
            painter.rotate(90)
            painter.translate(-c)
            painter.drawControl(QtWidgets.QStyle.CE_TabBarTabLabel, opt);
            painter.restore()


class TabWidget(QtWidgets.QTabWidget):
    def __init__(self, *args, **kwargs):
        QtWidgets.QTabWidget.__init__(self, *args, **kwargs)
        self.setTabBar(TabBar(self))
        self.setTabPosition(QtWidgets.QTabWidget.West)


class AppThemes:
    LIGHT = """
    QWidget {
        background-color: #f4f4f4;
        color: #111;
        font-family: Segoe UI;
    }

    QGroupBox {
        background-color: #e8e8e8;
        border: 1px solid #bbb;
        border-radius: 4px;
        margin-top: 2ex;
        padding: 10px;
        font-weight: bold;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px 0 5px;
        color: #111;
    }

    QLabel {
        background-color: #e8e8e8;
        color: #111;
    }

    QLineEdit, QTextEdit, QComboBox {
        background-color: #ffffff;
        border: 1px solid #bbb;
        padding: 4px;
    }

    QPushButton {
        background-color: #e0e0e0;
        border: 1px solid #999;
        padding: 6px;
    }

    QPushButton:hover {
        background-color: #d6d6d6;
    }

    QProgressBar {
        border: 1px solid #aaa;
        background: #ddd;
    }

    QProgressBar::chunk {
        background: #4caf50;
    }
    """

    DARK = """
    QWidget {
        background-color: #1e1e1e;
        color: #ddd;
        font-family: Segoe UI;
    }

    QGroupBox {
        background-color: #3a3a3a;
        border: 1px solid #555;
        border-radius: 4px;
        margin-top: 10ex;
        padding: 10px;
        font-weight: bold;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px 0 5px;
        color: #ddd;
    }

    QLabel {
        background-color: #3a3a3a;
        color: #ddd;
    }

    QLineEdit, QTextEdit, QComboBox {
        background-color: #2a2a2a;
        border: 1px solid #555;
        color: #ddd;
        padding: 4px;
    }

    QPushButton {
        background-color: #333;
        border: 1px solid #555;
        padding: 6px;
        color: #ddd;
    }

    QPushButton:hover {
        background-color: #444;
    }

    QProgressBar {
        border: 1px solid #555;
        background: #2a2a2a;
    }

    QProgressBar::chunk {
        background: #66ccff;
    }
    """


class MainWindow(QMainWindow):
    textScaleChanged = pyqtSignal()
    def __init__(self):
        
        super().__init__()

        self.TextScale = TextScale()
        self.text_scale = TextScale.MD
        
        menubar = self.menuBar()

        view_menu = menubar.addMenu("View")
        theme_menu = view_menu.addMenu("Theme")

        self.light_action = QAction("Light", self, checkable=True)
        self.dark_action = QAction("Dark", self, checkable=True)

        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)

        theme_group.addAction(self.light_action)
        theme_group.addAction(self.dark_action)

        theme_menu.addAction(self.light_action)
        theme_menu.addAction(self.dark_action)

        self.light_action.triggered.connect(lambda: self.setTheme("light"))
        self.dark_action.triggered.connect(lambda: self.setTheme("dark"))


        self.setWindowTitle("GM Sim")
        self.resize(1400, 900)

        # ---- Central widget ----
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # ---- Tabs ----
        self.tabs = TabWidget()
        #self.tabs.setTabPosition(QTabWidget.West)
        #self.tabs.tabBar().setShape(QTabBar.RoundedWest)


        #self.tabs.setMovable(False)
        #self.tabs.setUsesScrollButtons(True)
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                padding: 8px 14px;
                min-width: 130px;
                text-align: left;
                transform: rotate(-180deg);   
            }
            QTabBar::tab:selected {
                background: #2a2a2a;
            }
            
            """)

        layout.addWidget(self.tabs)

        # ---- Tabs ----
        self.char_store = CharacterStore()
        self.character_editor = CharacterEditor(self.char_store)

        # ---- Monsters tab ----
        self.monster_store = MonsterStore()
        self.monster_editor = MonsterEditor(self.monster_store)

        self.encounter_store = EncounterStore()
        self.encounter_builder = EncounterBuilderTab(self.startEncounter, self, self.char_store, self.monster_store, self.encounter_store)

        self.tabs.addTab(self.character_editor, "Characters")
        self.tabs.addTab(self.encounter_builder, "Encounter Builder")
        self.tabs.addTab(self.monster_editor, "Monsters")

        # Keep reference so it doesn’t get GC’d
        self.map_window = None

        # signals
        self.textScaleChanged.connect(self.character_editor.applyFonts)
        self.textScaleChanged.connect(self.encounter_builder.applyFonts)
        self.textScaleChanged.connect(self.monster_editor.applyFonts)

        # Install event filter so the main window can capture Ctrl+Wheel
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        self.setTheme("dark")  # default

        self.setTextScale(self.text_scale)

    def setTextScale(self, scale):
        self.text_scale = scale
        base_size = TextScale.size(scale)

        def apply(widget):
            font = widget.font()
            font.setPointSize(base_size)
            widget.setFont(font)

            for child in widget.findChildren(QWidget):
                apply(child)

        apply(self)

        # notify child widgets that care about more targeted font application
        try:
            self.textScaleChanged.emit()
        except Exception:
            pass

    def setTheme(self, theme_name):
        app = QApplication.instance()

        if theme_name == "dark":
            app.setStyleSheet(AppThemes.DARK)
            self.dark_action.setChecked(True)
        else:
            app.setStyleSheet(AppThemes.LIGHT)
            self.light_action.setChecked(True)

        self.current_theme = theme_name

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            if QApplication.keyboardModifiers() & Qt.ControlModifier:
                delta = event.angleDelta().y()

                if delta > 0:
                    self.TextScale.increase()
                else:
                    self.TextScale.decrease()

                # Re-apply the current scale (uses TextScale.BASE internally)
                self.setTextScale(self.text_scale)
                return True  # stop normal scrolling

        return False


    def startEncounter(self, encounter=None):
        if encounter is None:
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
window.setWindowIcon(QtGui.QIcon( dmSimPath + '\\DM_Sim_Icon.png'))
window.show()

app.exec()


