from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QHBoxLayout, QTabBar,
    QPushButton, QMessageBox, QLabel, QApplication, QAction, QActionGroup,
    QListWidget, QDialog, QLineEdit, QSpinBox, QGroupBox, QListWidgetItem,
    QFileDialog, QComboBox, QTextEdit, QProgressDialog, QInputDialog,
    QScrollArea, QShortcut,
)
from PyQt5.QtCore import Qt, pyqtSignal, QEvent, QSettings
from PyQt5.QtGui import QPixmap, QKeySequence

import pathlib
import json
import pickle
import sys
import argparse
import traceback
import shutil
from pathlib import Path

if getattr(sys, 'frozen', False):
    import app_paths as _ap
    _root = _ap.APP_ROOT
else:
    _root = pathlib.Path(__file__).parent.parent
    sys.path.insert(1, str(_root))
    sys.path.insert(2, str(_root / 'App'))

from newCharWindow import CharacterEditor, CharacterStore
from monsterWindow import MonsterEditor, MonsterStore
from spellEditor import SpellEditorTab
from TestingMap import MapWidget
from model.player import createPartyList
from model.monster import createMonsterList
from model.Interactive.interactiveEncounter import interactiveEncounter
from model.Simulation.encounterSim import Encounter
from controller import SimController
from engine.difficulty import calculate_difficulty, parse_cr
import engine.utils as _engine_utils

_SAVED_OBJS = _root / "actors" / "savedObjs"
_DEFAULT_MAP = _root / "App" / "Maps" / "TestingMap.webp"


def _resolve_map_image(path: str) -> str:
    """Return *path* if it points to a readable image, otherwise the default map path."""
    if path:
        p = Path(path)
        if not p.is_absolute():
            p = _root / p
        if p.exists():
            return str(p)
    return str(_DEFAULT_MAP)


'''

fix model to run to grade combat through model interactions
add spell creation window
add default map image if none is provided

move spell area button next to targets input

Add auto generate encounter by difficulty
'''
class EncounterStore:
    def __init__(self, file_path=None):
        if file_path is None:
            file_path = _root / "actors" / "savedObjs" / "encounters.json"
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

class Spacing:
    XS = 2
    SM = 4
    MD = 8
    LG = 12
    XL = 16
    XXL = 24


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

        # Wrap all content in a scroll area so the tab is scrollable on small windows
        _content = QWidget()
        layout = QVBoxLayout(_content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        _scroll = QScrollArea()
        _scroll.setWidget(_content)
        _scroll.setWidgetResizable(True)
        _scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        _scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        _outer = QVBoxLayout(self)
        _outer.setContentsMargins(0, 0, 0, 0)
        _outer.addWidget(_scroll)

        # Encounter Management
        enc_group = QGroupBox("Encounters")
        enc_layout = QVBoxLayout()
        enc_layout.setContentsMargins(10, 10, 10, 10)
        enc_layout.setSpacing(8)
        # Search bar
        self.enc_search = QLineEdit()
        self.enc_search.setPlaceholderText("Search encounters...")
        self.enc_search.textChanged.connect(self.filter_encounters)
        enc_layout.addWidget(self.enc_search)
        self.enc_list = QListWidget()
        self.enc_list.setMinimumHeight(200)
        self.update_enc_list()
        enc_layout.addWidget(self.enc_list)
        enc_buttons = QHBoxLayout()
        enc_buttons.setSpacing(6)
        new_enc_btn = QPushButton("New")
        new_enc_btn.setMinimumHeight(30)
        new_enc_btn.setToolTip("Create a new empty encounter")
        new_enc_btn.clicked.connect(self.new_encounter)
        edit_enc_btn = QPushButton("Edit")
        edit_enc_btn.setMinimumHeight(30)
        edit_enc_btn.setToolTip("Load the selected encounter into the editor")
        edit_enc_btn.clicked.connect(self.edit_encounter)
        save_enc_btn = QPushButton("Save")
        save_enc_btn.setMinimumHeight(30)
        save_enc_btn.setToolTip("Save the current encounter details (Ctrl+S)")
        save_enc_btn.clicked.connect(self.save_encounter)
        del_enc_btn = QPushButton("Delete")
        del_enc_btn.setMinimumHeight(30)
        del_enc_btn.setToolTip("Permanently delete the selected encounter")
        del_enc_btn.clicked.connect(self.delete_encounter)
        load_enc_btn = QPushButton("▶ Start")
        load_enc_btn.setMinimumHeight(30)
        load_enc_btn.setToolTip("Start combat with the selected encounter (F5)")
        load_enc_btn.setProperty("class", "primary")
        load_enc_btn.clicked.connect(self.load_encounter)
        enc_buttons.addWidget(new_enc_btn)
        enc_buttons.addWidget(edit_enc_btn)
        enc_buttons.addWidget(save_enc_btn)
        enc_buttons.addWidget(del_enc_btn)
        enc_buttons.addWidget(load_enc_btn)
        enc_layout.addLayout(enc_buttons)

        # Resume saved combat button (loads a .dmsave file)
        resume_btn = QPushButton("▶ Resume Saved Combat")
        resume_btn.setMinimumHeight(30)
        resume_btn.setToolTip("Load a previously saved mid-combat .dmsave file")
        resume_btn.clicked.connect(self.load_saved_combat)
        enc_layout.addWidget(resume_btn)

        enc_group.setLayout(enc_layout)
        layout.addWidget(enc_group)

        # Encounter Details Group
        details_group = QGroupBox("Encounter Details")
        details_layout = QVBoxLayout()
        details_layout.setContentsMargins(10, 10, 10, 10)
        details_layout.setSpacing(8)

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
        map_layout.addWidget(QLabel("Map Image:"))
        self.map_edit = QLineEdit()
        self.map_edit.setReadOnly(True)
        self.map_edit.setPlaceholderText("(default map)")
        self.map_edit.textChanged.connect(self._update_map_preview)
        map_layout.addWidget(self.map_edit)
        import_map_btn = QPushButton("📥 Import New Map")
        import_map_btn.setToolTip("Choose an image from your drive and save it into App/Maps")
        import_map_btn.clicked.connect(self.import_map_image)
        saved_map_btn = QPushButton("🗺 Select Saved Map")
        saved_map_btn.setToolTip("Pick from maps already imported into App/Maps")
        saved_map_btn.clicked.connect(self.select_saved_map)
        clear_btn = QPushButton("✕")
        clear_btn.setFixedWidth(28)
        clear_btn.setToolTip("Clear selection and use default map")
        clear_btn.clicked.connect(lambda: self.map_edit.setText(""))
        map_layout.addWidget(import_map_btn)
        map_layout.addWidget(saved_map_btn)
        map_layout.addWidget(clear_btn)
        details_layout.addLayout(map_layout)

        # Map preview thumbnail
        self._map_preview = QLabel()
        self._map_preview.setFixedSize(240, 135)
        self._map_preview.setAlignment(Qt.AlignCenter)
        self._map_preview.setStyleSheet("border: 1px solid #555; background: #222;")
        details_layout.addWidget(self._map_preview)
        self._update_map_preview("")  # load default preview

        details_group.setLayout(details_layout)
        layout.addWidget(details_group)

        # Setup lists
        self.setup_lists(layout)
        
        # Encounter Difficulty Group
        self.setup_difficulty_group(layout)

    def setup_difficulty_group(self, layout):
        difficulty_group = QGroupBox("Encounter Difficulty")
        difficulty_layout = QVBoxLayout()
        difficulty_layout.setContentsMargins(10, 10, 10, 10)
        difficulty_layout.setSpacing(8)
        
        # Party info layout
        party_info_layout = QHBoxLayout()
        party_info_layout.addWidget(QLabel("Party Size:"))
        self.party_size_label = QLabel("0")
        party_info_layout.addWidget(self.party_size_label)
        
        party_info_layout.addWidget(QLabel("Party Level:"))
        self.party_level_label = QLabel("—")
        party_info_layout.addWidget(self.party_level_label)
        party_info_layout.addStretch()
        difficulty_layout.addLayout(party_info_layout)
        
        # Difficulty info layout
        difficulty_info_layout = QHBoxLayout()
        difficulty_info_layout.addWidget(QLabel("Total Enemy CR:"))
        self.total_cr_label = QLabel("0")
        difficulty_info_layout.addWidget(self.total_cr_label)
        
        difficulty_info_layout.addWidget(QLabel("Difficulty:"))
        self.difficulty_label = QLabel("—")
        difficulty_info_layout.addWidget(self.difficulty_label)
        difficulty_info_layout.addStretch()
        difficulty_layout.addLayout(difficulty_info_layout)
        
        # Simulate button
        simulate_btn = QPushButton("Simulate Encounter")
        simulate_btn.setMinimumHeight(32)
        simulate_btn.setToolTip("Run an automated simulation to estimate encounter difficulty")
        simulate_btn.clicked.connect(self.simulate_encounter)
        difficulty_layout.addWidget(simulate_btn)
        
        difficulty_group.setLayout(difficulty_layout)
        layout.addWidget(difficulty_group)

    def setup_lists(self, layout):
        # Available characters and monsters
        self.avail_chars = self.char_store.get_names()
        self.avail_mons = self.mon_store.get_names()

        # Create group boxes
        party_group = QGroupBox("Party")
        party_layout = QVBoxLayout()
        party_layout.setContentsMargins(10, 10, 10, 10)
        party_layout.setSpacing(8)
        self.party_combo = QComboBox()
        self.party_combo.setEditable(True)
        self.party_combo.addItems(self.avail_chars)
        self.party_combo.setCurrentIndex(-1)  # No selection
        party_layout.addWidget(self.party_combo)
        self.party_list = QListWidget()
        self.party_list.setMinimumHeight(150)
        party_layout.addWidget(self.party_list)
        party_buttons = QHBoxLayout()
        party_buttons.setSpacing(6)
        add_party_btn = QPushButton("Add")
        add_party_btn.setMinimumHeight(30)
        add_party_btn.setToolTip("Add selected character to the party")
        add_party_btn.clicked.connect(lambda: self.add_from_combo(self.party_combo, self.party_list))
        self.party_combo.lineEdit().returnPressed.connect(lambda: self.add_from_combo(self.party_combo, self.party_list))
        remove_party_btn = QPushButton("Remove")
        remove_party_btn.setMinimumHeight(30)
        remove_party_btn.setToolTip("Remove selected character from the party")
        remove_party_btn.clicked.connect(lambda: self.remove_from_list(self.party_list))
        party_buttons.addWidget(add_party_btn)
        party_buttons.addWidget(remove_party_btn)
        party_layout.addLayout(party_buttons)
        party_group.setLayout(party_layout)

        npc_group = QGroupBox("NPCs")
        npc_layout = QVBoxLayout()
        npc_layout.setContentsMargins(10, 10, 10, 10)
        npc_layout.setSpacing(8)
        self.npc_combo = QComboBox()
        self.npc_combo.setEditable(True)
        self.npc_combo.addItems(self.avail_chars)
        self.npc_combo.setCurrentIndex(-1)
        npc_layout.addWidget(self.npc_combo)
        self.npc_list = QListWidget()
        self.npc_list.setMinimumHeight(150)
        npc_layout.addWidget(self.npc_list)
        npc_buttons = QHBoxLayout()
        npc_buttons.setSpacing(6)
        add_npc_btn = QPushButton("Add")
        add_npc_btn.setMinimumHeight(30)
        add_npc_btn.setToolTip("Add selected character as an NPC (allied combatant)")
        add_npc_btn.clicked.connect(lambda: self.add_from_combo(self.npc_combo, self.npc_list))
        self.npc_combo.lineEdit().returnPressed.connect(lambda: self.add_from_combo(self.npc_combo, self.npc_list))
        remove_npc_btn = QPushButton("Remove")
        remove_npc_btn.setMinimumHeight(30)
        remove_npc_btn.setToolTip("Remove selected NPC from the list")
        remove_npc_btn.clicked.connect(lambda: self.remove_from_list(self.npc_list))
        npc_buttons.addWidget(add_npc_btn)
        npc_buttons.addWidget(remove_npc_btn)
        npc_layout.addLayout(npc_buttons)
        npc_group.setLayout(npc_layout)

        enemy_group = QGroupBox("Enemies")
        enemy_layout = QVBoxLayout()
        enemy_layout.setContentsMargins(10, 10, 10, 10)
        enemy_layout.setSpacing(8)
        enemy_combo_layout = QHBoxLayout()
        self.enemy_combo = QComboBox()
        self.enemy_combo.setEditable(True)
        self.enemy_combo.addItems(self.avail_mons)
        self.enemy_combo.setCurrentIndex(-1)
        enemy_combo_layout.addWidget(self.enemy_combo)
        enemy_combo_layout.addWidget(QLabel("Qty:"))
        self.enemy_qty_spin = QSpinBox()
        self.enemy_qty_spin.setRange(1, 100)
        self.enemy_qty_spin.setValue(1)
        self.enemy_qty_spin.setMaximumWidth(60)
        enemy_combo_layout.addWidget(self.enemy_qty_spin)
        enemy_layout.addLayout(enemy_combo_layout)
        self.enemy_list = QListWidget()
        self.enemy_list.setMinimumHeight(150)
        enemy_layout.addWidget(self.enemy_list)
        enemy_buttons = QHBoxLayout()
        enemy_buttons.setSpacing(6)
        add_enemy_btn = QPushButton("Add")
        add_enemy_btn.setMinimumHeight(30)
        add_enemy_btn.setToolTip("Add the selected monster (with quantity) to the enemy list")
        add_enemy_btn.clicked.connect(self.add_multiple_enemies)
        self.enemy_combo.lineEdit().returnPressed.connect(self.add_multiple_enemies)
        remove_enemy_btn = QPushButton("Remove")
        remove_enemy_btn.setMinimumHeight(30)
        remove_enemy_btn.setToolTip("Remove the selected enemy from the list")
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

    def _update_map_preview(self, path: str):
        """Refresh the thumbnail to show the selected map (or the default)."""
        resolved = _resolve_map_image(path)
        px = QPixmap(resolved)
        if px.isNull():
            self._map_preview.setText("No preview")
        else:
            self._map_preview.setPixmap(
                px.scaled(240, 135, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        # Update placeholder hint
        if path:
            self._map_preview.setToolTip(path)
        else:
            self._map_preview.setToolTip(f"Default map: {_DEFAULT_MAP.name}")

    def import_map_image(self):
        """Pick any image from disk, copy it into App/Maps, and select it."""
        maps_dir = _root / "App" / "Maps"
        maps_dir.mkdir(parents=True, exist_ok=True)

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Map Image",
            str(Path.home()),
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        if not file_path:
            return

        src = Path(file_path)
        if src.parent.resolve() == maps_dir.resolve():
            # Already in App/Maps — just select it
            self.map_edit.setText("App\\Maps\\" + src.name)
            return

        destination = maps_dir / src.name
        counter = 1
        while destination.exists():
            destination = maps_dir / f"{src.stem}_{counter}{src.suffix}"
            counter += 1

        try:
            shutil.copy2(src, destination)
            relative_path = "App\\Maps\\" + destination.name
            self.map_edit.setText(relative_path)
            QMessageBox.information(
                self, "Map Imported",
                f"Map saved as: {destination.name}\n\nIt is now available in 'Select Saved Map'."
            )
        except Exception as e:
            QMessageBox.warning(self, "Import Failed", f"Could not copy map image:\n{e}")

    def select_saved_map(self):
        """Pick from maps already saved in App/Maps."""
        maps_dir = _root / "App" / "Maps"
        maps_dir.mkdir(parents=True, exist_ok=True)

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Saved Map",
            str(maps_dir),
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        if file_path:
            src = Path(file_path)
            if src.parent.resolve() == maps_dir.resolve():
                self.map_edit.setText("App\\Maps\\" + src.name)
            else:
                # User navigated outside — treat as an import
                QMessageBox.information(
                    self, "Outside Saved Maps",
                    "That file is outside the saved maps folder.\n"
                    "Use 'Import New Map' to copy it in first."
                )

    # ------------------------------------------------------------------
    # Enemy list grouping helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _enemy_display(name: str, count: int) -> str:
        return f"{name} x {count}" if count > 1 else name

    @staticmethod
    def _enemy_parse(text: str) -> tuple:
        """Parse 'Orc x 3' -> ('Orc', 3); 'Orc' -> ('Orc', 1)."""
        if ' x ' in text:
            parts = text.rsplit(' x ', 1)
            try:
                return parts[0], int(parts[1])
            except ValueError:
                pass
        return text, 1

    def add_from_combo(self, combo, list_widget):
        text = combo.currentText().strip()
        if text and not any(list_widget.item(i).text() == text for i in range(list_widget.count())):
            list_widget.addItem(text)
            combo.setCurrentIndex(-1)  # Clear selection
            # Update difficulty if adding to party or enemies
            if list_widget == self.party_list or list_widget == self.enemy_list:
                self.update_difficulty()

    def add_multiple_enemies(self):
        """Add enemies to the list, merging with existing entries of the same type."""
        text = self.enemy_combo.currentText().strip()
        quantity = self.enemy_qty_spin.value()
        if not text:
            return
        # Find existing row with this name and increment its count
        for i in range(self.enemy_list.count()):
            item_name, item_count = self._enemy_parse(self.enemy_list.item(i).text())
            if item_name == text:
                self.enemy_list.item(i).setText(
                    self._enemy_display(text, item_count + quantity)
                )
                self.enemy_combo.setCurrentIndex(-1)
                self.update_difficulty()
                return
        # No existing entry — add a new grouped item
        self.enemy_list.addItem(self._enemy_display(text, quantity))
        self.enemy_combo.setCurrentIndex(-1)
        self.update_difficulty()

    def add_to_list(self, list_widget, avail):
        item, ok = QInputDialog.getItem(self, "Select", "Choose:", avail, 0, False)
        if ok and item:
            list_widget.addItem(item)

    def remove_from_list(self, list_widget):
        current = list_widget.currentItem()
        if not current:
            return
        if list_widget == self.enemy_list:
            item_name, item_count = self._enemy_parse(current.text())
            if item_count > 1:
                dlg = QDialog(self)
                dlg.setWindowTitle("Remove Enemies")
                dlg.setMinimumWidth(280)
                layout = QVBoxLayout(dlg)
                layout.setSpacing(12)
                layout.setContentsMargins(16, 16, 16, 16)

                name_lbl = QLabel(f"<b>{item_name}</b>")
                name_lbl.setAlignment(Qt.AlignCenter)
                layout.addWidget(name_lbl)

                count_lbl = QLabel(f"Currently on roster: {item_count}")
                count_lbl.setAlignment(Qt.AlignCenter)
                count_lbl.setStyleSheet("color: #aaa;")
                layout.addWidget(count_lbl)

                spin_row = QHBoxLayout()
                spin_row.addWidget(QLabel("Remove:"))
                spin = QSpinBox()
                spin.setRange(1, item_count)
                spin.setValue(1)
                spin.setMinimumWidth(70)
                spin_row.addWidget(spin)
                spin_row.addStretch()
                layout.addLayout(spin_row)

                btn_row = QHBoxLayout()
                btn_row.addStretch()
                cancel_btn = QPushButton("Cancel")
                cancel_btn.clicked.connect(dlg.reject)
                ok_btn = QPushButton("Remove")
                ok_btn.setDefault(True)
                ok_btn.clicked.connect(dlg.accept)
                btn_row.addWidget(cancel_btn)
                btn_row.addWidget(ok_btn)
                layout.addLayout(btn_row)

                if dlg.exec_() != QDialog.Accepted:
                    return
                new_count = item_count - spin.value()
                if new_count <= 0:
                    list_widget.takeItem(list_widget.row(current))
                else:
                    current.setText(self._enemy_display(item_name, new_count))
                self.update_difficulty()
                return
        list_widget.takeItem(list_widget.row(current))
        if list_widget == self.party_list or list_widget == self.enemy_list:
            self.update_difficulty()

    def get_current_data(self):
        party = [self.party_list.item(i).text() for i in range(self.party_list.count())]
        npcs = [self.npc_list.item(i).text() for i in range(self.npc_list.count())]
        # Expand grouped entries: "Orc x 3" -> ["Orc", "Orc", "Orc"]
        enemies = []
        for i in range(self.enemy_list.count()):
            name, count = self._enemy_parse(self.enemy_list.item(i).text())
            enemies.extend([name] * count)
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
        # Group enemies by name when loading saved data
        from collections import Counter
        counts = Counter(data.get("enemies", []))
        for name, count in counts.items():
            self.enemy_list.addItem(self._enemy_display(name, count))
        self.update_difficulty()

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
        if hasattr(self.main_window, 'show_status'):
            self.main_window.show_status(f"Encounter '{name}' saved.", 4000)

    def delete_encounter(self):
        current = self.enc_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Warning", "Select an encounter to delete")
            return
        name = current.text()
        self.enc_store.delete_encounter(name)
        self.update_enc_list()
        if hasattr(self.main_window, 'show_status'):
            self.main_window.show_status(f"Encounter '{name}' deleted.", 4000)

    def load_encounter(self):
        current = self.enc_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Warning", "Select an encounter to load")
            return
        name = current.text()
        enc_data = self.enc_store.get_encounter(name)
        path = str(_SAVED_OBJS) + "\\"
        party = createPartyList(enc_data["party"], path=path)
        npcs = createPartyList(enc_data["npcs"], path=path)
        enemies = createMonsterList(enc_data["enemies"], path=path)
        encounter = interactiveEncounter(party, npcs, enemies, enc_data["numHexes"], _resolve_map_image(enc_data["mapImage"]))
        controller = SimController(encounter)
        if hasattr(self.main_window, 'show_status'):
            self.main_window.show_status(f"Encounter '{name}' loaded — starting combat.", 5000)
        self.start_callback(controller)

    def load_saved_combat(self):
        """Open a .dmsave file and resume the encounter from saved state."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Resume Saved Combat", "", "DMSim Save (*.dmsave);;All Files (*)"
        )
        if not filepath:
            return
        try:
            with open(filepath, 'rb') as f:
                save_data = pickle.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Load Failed", f"Could not load save file:\n{e}")
            return

        # Pass a COPY to SimController so testingTheory()/preCombat() doesn't corrupt
        # the saved encounter we're about to restore from.
        import copy
        enc_dummy = copy.deepcopy(save_data['encounter'])
        controller = SimController(enc_dummy)
        self.start_callback(controller, save_data=save_data)

    def buildEncounter(self):
        # Keep for compatibility, but not used
        pass

    def update_difficulty(self):
        """Update the encounter difficulty display based on party and enemies using D&D 5e rules."""
        party_size = self.party_list.count()
        self.party_size_label.setText(str(party_size))

        # Average party level
        levels = []
        for i in range(party_size):
            char_data = self.char_store.get(self.party_list.item(i).text())
            if char_data:
                try:
                    levels.append(int(char_data.get("level", 1)))
                except (ValueError, TypeError):
                    pass
        avg_level = (sum(levels) // len(levels)) if levels else 1
        self.party_level_label.setText(str(avg_level))

        # Collect enemy CRs
        enemy_crs = []
        total_cr = 0.0
        for i in range(self.enemy_list.count()):
            monster_data = self.mon_store.get(self.enemy_list.item(i).text())
            if monster_data:
                cr = parse_cr(monster_data.get("cr", "0"))
                enemy_crs.append(cr)
                total_cr += cr
        self.total_cr_label.setText(f"{total_cr:.1f}")

        difficulty = calculate_difficulty(party_size, avg_level, enemy_crs)
        self.difficulty_label.setText(difficulty)

    def simulate_encounter(self):
        """Run encounter simulation and show results in a popup."""
        # Get current encounter data
        data = self.get_current_data()
        
        # Validate we have party and enemies
        if not data["party"]:
            QMessageBox.warning(self, "Warning", "Add at least one party member to simulate")
            return
        
        if not data["enemies"]:
            QMessageBox.warning(self, "Warning", "Add at least one enemy to simulate")
            return
        
        # Create progress dialog
        progress = QProgressDialog("Running encounter simulations...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        QApplication.processEvents()
        
        try:
            # Load party, npcs, and enemies
            path = str(_SAVED_OBJS) + "\\"
            party = createPartyList(data["party"], path=path)
            npcs = createPartyList(data["npcs"], path=path)
            enemies = createMonsterList(data["enemies"], path=path)
            
            progress.setValue(10)
            QApplication.processEvents()
            
            # Run simulation — tick progress bar after each completed sim
            num_sims = 10

            def _on_sim_done(completed, total):
                if progress.wasCanceled():
                    return
                value = 10 + int(completed / total * 85)
                progress.setValue(value)
                QApplication.processEvents()

            encounter_sim = Encounter(party, npcs, enemies, num_sims,
                                      progress_callback=_on_sim_done)
            
            progress.setValue(90)
            QApplication.processEvents()
            
            # Show results in dialog
            self.show_simulation_results(encounter_sim)
            
            progress.setValue(100)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Simulation failed: {str(e)}")
            traceback.print_exc()
        finally:
            progress.close()
    
    def _rate_simulation_difficulty(self, stats: list) -> tuple[str, str, str]:
        """
        Rate the encounter difficulty from simulation results.

        Returns (label, color_hex, description).

        Two-stage algorithm:
          Stage 1 — Win rate gates Hard / Deadly / TPK:
            - TPK    : party never wins
            - Deadly : party wins fewer than half the time
            - Hard   : party wins most of the time but deaths occur, or win rate < ~90%

          Stage 2 — For encounters where the party wins consistently with no deaths,
          resource consumption (HP remaining + spell slot pressure) determines
          Trivial / Easy / Medium:
            - Trivial : high HP left AND minimal spell slot use
            - Easy    : moderate HP or moderate slot use
            - Medium  : low HP remaining or heavy slot expenditure
        """
        n = len(stats)
        if n == 0:
            return ("Unknown", "#888888", "No simulation data available.")

        party_wins = sum(1 for s in stats if s['winner'] == 'Party')
        win_rate = party_wins / n
        death_rate = sum(1 for s in stats if s['any_deaths']) / n

        # Avg party HP % averaged across ALL runs (winners + losers)
        hp_remaining = sum(
            sum(p['health_percent'] for p in s['party_stats']) / max(len(s['party_stats']), 1)
            for s in stats
        ) / n

        # Spell pressure: fraction of runs where any caster burned ≥50% of any slot level
        slot_pressure_runs = 0
        for s in stats:
            for p in s['party_stats']:
                used = p.get('spell_slots_used', {})
                remaining = p.get('spell_slots_remaining', {})
                for lvl in used:
                    if lvl == '0':
                        continue
                    total = used.get(lvl, 0) + remaining.get(lvl, 0)
                    if total > 0 and used.get(lvl, 0) / total >= 0.5:
                        slot_pressure_runs += 1
                        break
        slot_pressure = slot_pressure_runs / n

        # ----------------------------------------------------------------
        # Stage 1: win rate / death rate gates the upper difficulty tiers
        # ----------------------------------------------------------------
        if win_rate == 0.0:
            return ("TPK", "#8B0000",
                    "Total Party Kill. The party has no realistic chance of survival.")

        if win_rate < 0.5 or death_rate > 0:
            return ("Deadly", "#CC2200",
                    "Deadly. The party is likely to have significant losses.")

        # Party wins at least half the time — now check deaths / consistency
        # Hard if: win rate below ~90%, OR deaths occur in a significant number of runs
        if hp_remaining <= 0.50 or slot_pressure >= 0.60:
            return ("Hard", "#E06000",
                    "Hard. The party can win but expect it be close and have heavy resource expenditure.")

        # ----------------------------------------------------------------
        # Stage 2: Party wins consistently (~always) with negligible deaths.
        # Distinguish Trivial / Easy / Medium purely by resource consumption.
        # ----------------------------------------------------------------
        #   Trivial : HP ≥ 70% remaining AND slot pressure < 25%
        #   Easy    : HP ≥ 50% remaining AND slot pressure < 60%
        #   Medium  : everything else (high slot drain or low HP)
        if hp_remaining >= 85 and slot_pressure < 0.25:
            return ("Trivial", "#2060CC",
                    "Trivial. The party wins without breaking a sweat.")

        if hp_remaining >= 70 and slot_pressure < 0.40:
            return ("Easy", "#4A8F00",
                    "Easy. The party wins comfortably with moderate resource use.")

        return ("Medium", "#B8A000",
                "Medium. The party always wins but spends significant health and spell slots to do so.")

    def show_simulation_results(self, encounter_sim):
        """Display simulation results in a dialog window."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Encounter Simulation Results")
        dialog.resize(700, 640)

        layout = QVBoxLayout(dialog)

        # ── Difficulty Banner ────────────────────────────────────────────
        rating_label, rating_color, rating_desc = self._rate_simulation_difficulty(
            encounter_sim.combatStats
        )
        banner = QLabel(f"Simulation Difficulty:  {rating_label}")
        banner.setAlignment(Qt.AlignCenter)
        banner.setStyleSheet(
            f"background-color: {rating_color}; color: white; "
            f"font-size: 18px; font-weight: bold; padding: 10px; border-radius: 6px;"
        )
        layout.addWidget(banner)

        desc_lbl = QLabel(rating_desc)
        desc_lbl.setAlignment(Qt.AlignCenter)
        desc_lbl.setStyleSheet("font-style: italic; padding: 4px 0 8px 0;")
        layout.addWidget(desc_lbl)

        # ── Detailed Results ─────────────────────────────────────────────
        results_text = QTextEdit()
        results_text.setReadOnly(True)
        results_text.setStyleSheet("font-family: Consolas, monospace;")
        
        # Build results text
        text = ""
        n_sims = len(encounter_sim.combatStats)
        party_wins = sum(1 for stat in encounter_sim.combatStats if stat['winner'] == 'Party')
        enemy_wins = sum(1 for stat in encounter_sim.combatStats if stat['winner'] == 'Enemy')

        text += "=" * 60 + "\n"
        text += "ENCOUNTER SIMULATION RESULTS\n"
        text += "=" * 60 + "\n\n"

        text += f"DIFFICULTY RATING: {rating_label}\n"
        text += f"  {rating_desc}\n\n"

        # Win rate
        text += "Win Rate:\n"
        text += f"  Party Wins: {party_wins}/{n_sims} ({party_wins/n_sims*100:.1f}%)\n"
        text += f"  Enemy Wins: {enemy_wins}/{n_sims} ({enemy_wins/n_sims*100:.1f}%)\n\n"

        # Combat length
        avg_turns = sum(stat['turns'] for stat in encounter_sim.combatStats) / n_sims
        min_turns = min(stat['turns'] for stat in encounter_sim.combatStats)
        max_turns = max(stat['turns'] for stat in encounter_sim.combatStats)
        text += "Combat Duration:\n"
        text += f"  Average Rounds: {avg_turns:.1f}\n"
        text += f"  Min Rounds: {min_turns}\n"
        text += f"  Max Rounds: {max_turns}\n\n"

        # Death statistics
        combats_with_deaths = sum(1 for stat in encounter_sim.combatStats if stat['any_deaths'])
        text += "Party Deaths:\n"
        text += f"  Combats with deaths: {combats_with_deaths}/{n_sims} ({combats_with_deaths/n_sims*100:.1f}%)\n\n"
        
        # Per-character statistics
        if encounter_sim.combatStats and encounter_sim.combatStats[0]['party_stats']:
            text += "Per-Character Statistics:\n"
            text += "-" * 60 + "\n"
            
            # Get unique character names
            char_names = list(set(s['name'] for combat in encounter_sim.combatStats for s in combat['party_stats']))
            
            for char_name in sorted(char_names):
                char_stats = []
                for combat in encounter_sim.combatStats:
                    char_stat = next((s for s in combat['party_stats'] if s['name'] == char_name), None)
                    if char_stat:
                        char_stats.append(char_stat)
                
                if not char_stats:
                    continue
                
                deaths = sum(1 for s in char_stats if not s['is_alive'])
                avg_health_percent = sum(s['health_percent'] for s in char_stats) / len(char_stats)
                avg_final_health = sum(s['final_health'] for s in char_stats) / len(char_stats)
                max_health = char_stats[0]['max_health']
                
                text += f"\n{char_name}:\n"
                text += f"  Death Rate: {deaths}/{n_sims} ({deaths/n_sims*100:.1f}%)\n"
                text += f"  Avg Final Health: {avg_final_health:.1f}/{max_health} ({avg_health_percent:.1f}%)\n"
                
                # Spell slot usage
                if char_stats[0]['spell_slots_used']:
                    text += f"  Avg Spell Slots Used:\n"
                    for level in sorted(char_stats[0]['spell_slots_used'].keys()):
                        if level == '0':
                            continue
                        total_used = sum(s['spell_slots_used'].get(level, 0) for s in char_stats)
                        avg_used = total_used / len(char_stats)
                        max_slots = char_stats[0]['spell_slots_used'].get(level, 0) + char_stats[0]['spell_slots_remaining'].get(level, 0)
                        if max_slots > 0:
                            text += f"    Level {level}: {avg_used:.1f}/{max_slots}\n"
        
        text += "\n" + "=" * 60 + "\n"
        
        results_text.setPlainText(text)
        layout.addWidget(results_text)
        
        # Add close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec_()
    
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
    /* ── Base ── */
    QWidget {
        background-color: #f0f2f5;
        color: #1a1a2e;
        font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    }
    QMainWindow, QDialog {
        background-color: #f0f2f5;
    }

    /* ── GroupBox ── */
    QGroupBox {
        background-color: #e8ecf2;
        border: 1px solid #c0c8d8;
        border-radius: 6px;
        margin-top: 10px;
        padding-top: 6px;
        font-weight: bold;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 10px;
        padding: 2px 6px;
        color: #1a4a8a;
        background-color: #f0f2f5;
        border-radius: 3px;
    }

    /* ── Labels ── */
    QLabel {
        background-color: transparent;
        color: #1a1a2e;
    }

    /* ── Inputs ── */
    QLineEdit, QTextEdit, QPlainTextEdit {
        background-color: #ffffff;
        border: 1px solid #b0bcd0;
        border-radius: 4px;
        padding: 4px 6px;
        color: #1a1a2e;
        selection-background-color: #a8c8f0;
    }
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
        border: 1px solid #1a6bb0;
        background-color: #fafdff;
    }
    QLineEdit:read-only { background-color: #ebebeb; color: #666; }

    QComboBox {
        background-color: #ffffff;
        border: 1px solid #b0bcd0;
        border-radius: 4px;
        padding: 4px 6px;
        color: #1a1a2e;
        min-height: 24px;
    }
    QComboBox:focus { border: 1px solid #1a6bb0; }
    QComboBox::drop-down { border: none; width: 20px; }
    QComboBox::down-arrow { image: none; width: 0; height: 0;
        border-left: 4px solid transparent; border-right: 4px solid transparent;
        border-top: 5px solid #666; margin-right: 4px; }
    QComboBox QAbstractItemView {
        background-color: #ffffff; border: 1px solid #b0bcd0;
        selection-background-color: #d0e8f8; color: #1a1a2e;
    }

    QSpinBox, QDoubleSpinBox {
        background-color: #ffffff;
        border: 1px solid #b0bcd0;
        border-radius: 4px;
        padding: 3px 6px;
        color: #1a1a2e;
    }
    QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid #1a6bb0; }

    /* ── Buttons ── */
    QPushButton {
        background-color: #e0e8f4;
        border: 1px solid #a0b8d8;
        border-radius: 4px;
        padding: 5px 12px;
        color: #1a1a2e;
        font-weight: 500;
        min-height: 26px;
    }
    QPushButton:hover { background-color: #cddaf0; border-color: #7899c8; }
    QPushButton:pressed { background-color: #b8cbea; }
    QPushButton:checked { background-color: #c8f0c8; color: #1a5a1a; border: 2px solid #4caf50; }
    QPushButton:disabled { background-color: #d8d8d8; color: #999; border-color: #ccc; }
    QPushButton[class="primary"] {
        background-color: #1a6bb0; color: #ffffff;
        border: 1px solid #1254a0; border-radius: 4px;
        padding: 6px 16px; font-weight: bold;
    }
    QPushButton[class="primary"]:hover { background-color: #2577be; border-color: #0e4a8e; }
    QPushButton[class="primary"]:pressed { background-color: #0f5090; }
    QPushButton[class="primary"]:disabled { background-color: #a0b8cc; color: #ddd; }

    QToolButton {
        background-color: #e0e8f4; border: 1px solid #a0b8d8;
        border-radius: 4px; padding: 5px 8px; color: #1a1a2e;
    }
    QToolButton:hover { background-color: #cddaf0; border-color: #7899c8; }
    QToolButton:pressed { background-color: #b8cbea; }
    QToolButton:checked { background-color: #c8f0c8; color: #1a5a1a; border: 2px solid #4caf50; }

    /* ── Progress ── */
    QProgressBar {
        border: 1px solid #b0bcd0; border-radius: 4px;
        background: #dde4ee; text-align: center; color: #333;
    }
    QProgressBar::chunk { background: #4caf50; border-radius: 3px; }

    /* ── Lists & Tables ── */
    QListWidget, QTreeWidget, QTableWidget {
        background-color: #ffffff; border: 1px solid #c0c8d8;
        border-radius: 4px; outline: none;
    }
    QListWidget::item { padding: 3px 6px; border-radius: 3px; }
    QListWidget::item:hover { background-color: #e0eaf6; }
    QListWidget::item:selected { background-color: #b8d4f0; color: #1a1a2e; }

    /* ── Scroll bars ── */
    QScrollBar:vertical { background: #e8ecf2; width: 10px; border-radius: 5px; margin: 0; }
    QScrollBar::handle:vertical { background: #b0bcd0; min-height: 20px; border-radius: 5px; }
    QScrollBar::handle:vertical:hover { background: #8899b8; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
    QScrollBar:horizontal { background: #e8ecf2; height: 10px; border-radius: 5px; margin: 0; }
    QScrollBar::handle:horizontal { background: #b0bcd0; min-width: 20px; border-radius: 5px; }
    QScrollBar::handle:horizontal:hover { background: #8899b8; }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }

    /* ── Splitter ── */
    QSplitter::handle { background: #c0c8d8; }
    QSplitter::handle:hover { background: #1a6bb0; }
    QSplitter::handle:horizontal { width: 4px; }
    QSplitter::handle:vertical { height: 4px; }

    /* ── Menu bar ── */
    QMenuBar { background-color: #e4eaf4; color: #1a1a2e; border-bottom: 1px solid #c0c8d8; padding: 2px; }
    QMenuBar::item { padding: 4px 10px; border-radius: 4px; }
    QMenuBar::item:selected { background-color: #d0dcea; }
    QMenuBar::item:pressed { background-color: #b8cadf; }

    QMenu { background-color: #f8f9fc; color: #1a1a2e; border: 1px solid #b0bcd0; border-radius: 6px; padding: 4px; }
    QMenu::item { padding: 5px 24px 5px 16px; border-radius: 3px; }
    QMenu::item:selected { background-color: #d0e4f4; color: #1a1a2e; }
    QMenu::separator { height: 1px; background: #d0d8e4; margin: 4px 8px; }

    /* ── Tab bar ── */
    QTabWidget::pane { border: 1px solid #c0c8d8; border-radius: 4px; }
    QTabBar::tab {
        background-color: #dce4f0; color: #555; padding: 7px 12px;
        border: 1px solid #c0c8d8; margin: 1px; border-radius: 4px 4px 0 0;
        min-width: 70px;
    }
    QTabBar::tab:selected { background-color: #ccd8f0; color: #1a1a2e; border-bottom: 2px solid #1a6bb0; font-weight: bold; }
    QTabBar::tab:hover:!selected { background-color: #d0dcea; color: #333; }

    /* ── Header ── */
    QHeaderView::section {
        background-color: #dce4f0; color: #1a1a2e; padding: 5px 8px;
        border: none; border-right: 1px solid #c0c8d8; border-bottom: 1px solid #c0c8d8;
        font-weight: bold;
    }
    QHeaderView::section:hover { background-color: #ccd8f0; }

    /* ── Dock widgets ── */
    QDockWidget { font-weight: bold; }
    QDockWidget::title {
        background-color: #dce4f0; padding: 6px 8px;
        border-bottom: 2px solid #1a6bb0; color: #1a3060; font-weight: bold;
    }
    QDockWidget::close-button, QDockWidget::float-button { background: transparent; border: none; padding: 2px; }
    QDockWidget::close-button:hover, QDockWidget::float-button:hover { background-color: #c0ccdc; border-radius: 3px; }

    /* ── Tooltip ── */
    QToolTip {
        background-color: #fffef0; color: #1a1a2e;
        border: 1px solid #1a6bb0; padding: 4px 8px;
        border-radius: 4px; font-size: 10px;
    }

    /* ── Status bar ── */
    QStatusBar { background-color: #dce4f0; color: #444; border-top: 1px solid #c0c8d8; padding: 2px 8px; font-size: 10px; }
    QStatusBar::item { border: none; }

    /* ── Checkboxes & Radio ── */
    QCheckBox { color: #1a1a2e; spacing: 6px; }
    QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #b0bcd0; border-radius: 3px; background: #fff; }
    QCheckBox::indicator:checked { background-color: #1a6bb0; border-color: #1a6bb0; }
    QCheckBox::indicator:hover { border-color: #7899c8; }
    QRadioButton { color: #1a1a2e; spacing: 6px; }
    QRadioButton::indicator { width: 14px; height: 14px; border-radius: 7px; border: 2px solid #b0bcd0; background: #fff; }
    QRadioButton::indicator:checked { background-color: #1a6bb0; border-color: #1a6bb0; }

    /* ── Scroll area ── */
    QScrollArea { border: none; }

    /* ── Frame separators ── */
    QFrame[frameShape="4"], QFrame[frameShape="5"] { color: #c0c8d8; }
    """

    DARK = """
    /* ── Base ── */
    QWidget {
        background-color: #1e1e2e;
        color: #d0d4e0;
        font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    }
    QMainWindow, QDialog {
        background-color: #1e1e2e;
    }

    /* ── GroupBox ── */
    QGroupBox {
        background-color: #252535;
        border: 1px solid #44485a;
        border-radius: 6px;
        margin-top: 10px;
        padding-top: 6px;
        font-weight: bold;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 10px;
        padding: 2px 6px;
        color: #7ab4ff;
        background-color: #1e1e2e;
        border-radius: 3px;
    }

    /* ── Labels ── */
    QLabel {
        background-color: transparent;
        color: #d0d4e0;
    }

    /* ── Inputs ── */
    QLineEdit, QTextEdit, QPlainTextEdit {
        background-color: #16162a;
        border: 1px solid #44485a;
        border-radius: 4px;
        padding: 4px 6px;
        color: #d0d4e0;
        selection-background-color: #2a4a7a;
    }
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
        border: 1px solid #5588cc;
        background-color: #1a1a30;
    }
    QLineEdit:read-only { background-color: #1a1a28; color: #888; }

    QComboBox {
        background-color: #16162a;
        border: 1px solid #44485a;
        border-radius: 4px;
        padding: 4px 6px;
        color: #d0d4e0;
        min-height: 24px;
    }
    QComboBox:focus { border: 1px solid #5588cc; }
    QComboBox::drop-down { border: none; width: 20px; }
    QComboBox::down-arrow { image: none; width: 0; height: 0;
        border-left: 4px solid transparent; border-right: 4px solid transparent;
        border-top: 5px solid #888; margin-right: 4px; }
    QComboBox QAbstractItemView {
        background-color: #1e1e2e; border: 1px solid #44485a;
        selection-background-color: #2a4a7a; color: #d0d4e0;
    }

    QSpinBox, QDoubleSpinBox {
        background-color: #16162a;
        border: 1px solid #44485a;
        border-radius: 4px;
        padding: 3px 6px;
        color: #d0d4e0;
    }
    QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid #5588cc; }

    /* ── Buttons ── */
    QPushButton {
        background-color: #2a2a3e;
        border: 1px solid #44485a;
        border-radius: 4px;
        padding: 5px 12px;
        color: #d0d4e0;
        font-weight: 500;
        min-height: 26px;
    }
    QPushButton:hover { background-color: #343450; border-color: #6670a0; }
    QPushButton:pressed { background-color: #1e1e30; }
    QPushButton:checked { background-color: #1a4a1a; color: #88ee88; border: 2px solid #44cc44; }
    QPushButton:disabled { background-color: #1e1e2a; color: #556; border-color: #333; }
    QPushButton[class="primary"] {
        background-color: #1a4a8a; color: #e0f0ff;
        border: 1px solid #4a8adf; border-radius: 4px;
        padding: 6px 16px; font-weight: bold;
    }
    QPushButton[class="primary"]:hover { background-color: #2a5a9a; border-color: #66aaff; }
    QPushButton[class="primary"]:pressed { background-color: #103070; }
    QPushButton[class="primary"]:disabled { background-color: #1a2a40; color: #556; }

    QToolButton {
        background-color: #2a2a3e; border: 1px solid #44485a;
        border-radius: 4px; padding: 5px 8px; color: #d0d4e0;
    }
    QToolButton:hover { background-color: #343450; border-color: #6670a0; }
    QToolButton:pressed { background-color: #1e1e30; }
    QToolButton:checked { background-color: #1a4a1a; color: #88ee88; border: 2px solid #44cc44; }

    /* ── Progress ── */
    QProgressBar {
        border: 1px solid #44485a; border-radius: 4px;
        background: #16162a; text-align: center; color: #aaa;
    }
    QProgressBar::chunk { background: #4a9eff; border-radius: 3px; }

    /* ── Lists & Tables ── */
    QListWidget, QTreeWidget, QTableWidget {
        background-color: #16162a; border: 1px solid #44485a;
        border-radius: 4px; outline: none;
    }
    QListWidget::item { padding: 3px 6px; border-radius: 3px; }
    QListWidget::item:hover { background-color: #252545; }
    QListWidget::item:selected { background-color: #2a4a7a; color: #e0f0ff; }

    /* ── Scroll bars ── */
    QScrollBar:vertical { background: #16162a; width: 10px; border-radius: 5px; margin: 0; }
    QScrollBar::handle:vertical { background: #44485a; min-height: 20px; border-radius: 5px; }
    QScrollBar::handle:vertical:hover { background: #6670a0; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
    QScrollBar:horizontal { background: #16162a; height: 10px; border-radius: 5px; margin: 0; }
    QScrollBar::handle:horizontal { background: #44485a; min-width: 20px; border-radius: 5px; }
    QScrollBar::handle:horizontal:hover { background: #6670a0; }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }

    /* ── Splitter ── */
    QSplitter::handle { background: #2e2e44; }
    QSplitter::handle:hover { background: #4a9eff; }
    QSplitter::handle:horizontal { width: 4px; }
    QSplitter::handle:vertical { height: 4px; }

    /* ── Menu bar ── */
    QMenuBar { background-color: #16162a; color: #d0d4e0; border-bottom: 1px solid #2e2e44; padding: 2px; }
    QMenuBar::item { padding: 4px 10px; border-radius: 4px; }
    QMenuBar::item:selected { background-color: #252545; }
    QMenuBar::item:pressed { background-color: #2a2a50; }

    QMenu { background-color: #1e1e30; color: #d0d4e0; border: 1px solid #44485a; border-radius: 6px; padding: 4px; }
    QMenu::item { padding: 5px 24px 5px 16px; border-radius: 3px; }
    QMenu::item:selected { background-color: #2a3a6a; color: #e0f0ff; }
    QMenu::separator { height: 1px; background: #2e2e44; margin: 4px 8px; }

    /* ── Tab bar ── */
    QTabWidget::pane { border: 1px solid #2e2e44; border-radius: 4px; }
    QTabBar::tab {
        background-color: #252535; color: #888; padding: 7px 12px;
        border: 1px solid #2e2e44; margin: 1px; border-radius: 4px 4px 0 0;
        min-width: 70px;
    }
    QTabBar::tab:selected { background-color: #2a2a4a; color: #d0d4e0; border-bottom: 2px solid #4a9eff; font-weight: bold; }
    QTabBar::tab:hover:!selected { background-color: #2e2e48; color: #bbb; }

    /* ── Header ── */
    QHeaderView::section {
        background-color: #252535; color: #aaa; padding: 5px 8px;
        border: none; border-right: 1px solid #2e2e44; border-bottom: 1px solid #2e2e44;
        font-weight: bold;
    }
    QHeaderView::section:hover { background-color: #2a2a4a; color: #d0d4e0; }

    /* ── Dock widgets ── */
    QDockWidget { font-weight: bold; }
    QDockWidget::title {
        background-color: #16162a; padding: 6px 8px;
        border-bottom: 2px solid #4a9eff; color: #a0c0ff; font-weight: bold;
    }
    QDockWidget::close-button, QDockWidget::float-button { background: transparent; border: none; padding: 2px; }
    QDockWidget::close-button:hover, QDockWidget::float-button:hover { background-color: #2a2a44; border-radius: 3px; }

    /* ── Tooltip ── */
    QToolTip {
        background-color: #1e1e30; color: #d0d4e0;
        border: 1px solid #4a9eff; padding: 4px 8px;
        border-radius: 4px; font-size: 10px;
    }

    /* ── Status bar ── */
    QStatusBar { background-color: #16162a; color: #888; border-top: 1px solid #2e2e44; padding: 2px 8px; font-size: 10px; }
    QStatusBar::item { border: none; }

    /* ── Checkboxes & Radio ── */
    QCheckBox { color: #d0d4e0; spacing: 6px; }
    QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #44485a; border-radius: 3px; background: #16162a; }
    QCheckBox::indicator:checked { background-color: #4a9eff; border-color: #4a9eff; }
    QCheckBox::indicator:hover { border-color: #6670a0; }
    QRadioButton { color: #d0d4e0; spacing: 6px; }
    QRadioButton::indicator { width: 14px; height: 14px; border-radius: 7px; border: 2px solid #44485a; background: #16162a; }
    QRadioButton::indicator:checked { background-color: #4a9eff; border-color: #4a9eff; }

    /* ── Scroll area ── */
    QScrollArea { border: none; }

    /* ── Frame separators ── */
    QFrame[frameShape="4"], QFrame[frameShape="5"] { color: #2e2e44; }
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

        # ---- Debug menu ----
        debug_menu = menubar.addMenu("Debug")
        self.debug_action = QAction("Enable Debug Output", self, checkable=True)
        self.debug_action.setChecked(_engine_utils.DEBUG)
        self.debug_action.setToolTip(
            "Print verbose engine messages to the console (useful for diagnosing crashes)"
        )
        self.debug_action.toggled.connect(_engine_utils.set_debug)
        debug_menu.addAction(self.debug_action)


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
        self._tab_base_style = """
            QTabBar::tab {{
                padding: 8px 14px;
                min-width: 130px;
                text-align: left;
            }}
            QTabBar::tab:selected {{
                background: {sel_bg};
                color: {sel_fg};
                border-right: 3px solid {accent};
                font-weight: bold;
            }}
        """
        self.tabs.setStyleSheet(self._tab_base_style.format(
            sel_bg="#2a2a4a", sel_fg="#d0d4e0", accent="#4a9eff"
        ))

        layout.addWidget(self.tabs)

        # ---- Tabs ----
        self.char_store = CharacterStore()
        self.character_editor = CharacterEditor(self.char_store)

        # ---- Monsters tab ----
        self.monster_store = MonsterStore()
        self.monster_editor = MonsterEditor(self.monster_store)

        self.encounter_store = EncounterStore()
        self.encounter_builder = EncounterBuilderTab(self.startEncounter, self, self.char_store, self.monster_store, self.encounter_store)

        self.spell_editor = SpellEditorTab()

        self.tabs.addTab(self.character_editor, "Characters")
        self.tabs.addTab(self.encounter_builder, "Encounter Builder")
        self.tabs.addTab(self.monster_editor, "Monsters")
        self.tabs.addTab(self.spell_editor, "Spell Editor")

        # Keep reference so it doesn’t get GC’d
        self.map_window = None

        # signals
        self.textScaleChanged.connect(self.character_editor.applyFonts)
        self.textScaleChanged.connect(self.encounter_builder.applyFonts)
        self.textScaleChanged.connect(self.monster_editor.applyFonts)
        self.textScaleChanged.connect(self.spell_editor.applyFonts)
        self.spell_editor.spellsChanged.connect(self.character_editor.refresh_spells)

        # Install event filter so the main window can capture Ctrl+Wheel
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        self.setTheme("dark")  # default (overridden by _restore_state if settings exist)

        self.setTextScale(self.text_scale)

        # ---- Status bar ----
        self._status_bar = self.statusBar()
        self._status_bar.showMessage("Ready", 3000)

        # ---- Keyboard shortcuts ----
        QShortcut(QKeySequence("Ctrl+="), self, lambda: self._adjust_text_scale(1))
        QShortcut(QKeySequence("Ctrl++"), self, lambda: self._adjust_text_scale(1))
        QShortcut(QKeySequence("Ctrl+-"), self, lambda: self._adjust_text_scale(-1))
        QShortcut(QKeySequence("Ctrl+0"), self, lambda: self.setTextScale(TextScale.MD))
        QShortcut(QKeySequence("Ctrl+T"), self,
                  lambda: self.setTheme("light" if self.current_theme == "dark" else "dark"))

        # ---- Restore persisted window state (geometry, theme, scale, tab) ----
        self._settings = QSettings("DMSim", "DMSim")
        self._restore_state()

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
            self.tabs.setStyleSheet(self._tab_base_style.format(
                sel_bg="#2a2a4a", sel_fg="#d0d4e0", accent="#4a9eff"
            ))
        else:
            app.setStyleSheet(AppThemes.LIGHT)
            self.light_action.setChecked(True)
            self.tabs.setStyleSheet(self._tab_base_style.format(
                sel_bg="#ccd8f0", sel_fg="#1a1a2e", accent="#1a6bb0"
            ))

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


    def _adjust_text_scale(self, delta: int):
        scale_values = [TextScale.XS, TextScale.SM, TextScale.MD, TextScale.LG, TextScale.XL]
        idx = scale_values.index(self.text_scale) if self.text_scale in scale_values else 2
        new_idx = max(0, min(len(scale_values) - 1, idx + delta))
        self.setTextScale(scale_values[new_idx])

    def _restore_state(self):
        s = self._settings
        geom = s.value("geometry")
        if geom:
            self.restoreGeometry(geom)
        theme = s.value("theme", "dark")
        self.setTheme(theme)
        tab = s.value("lastTab", 0, type=int)
        if 0 <= tab < self.tabs.count():
            self.tabs.setCurrentIndex(tab)

    def closeEvent(self, event):
        s = self._settings
        s.setValue("geometry", self.saveGeometry())
        s.setValue("theme", self.current_theme)
        s.setValue("textScale", self.text_scale)
        s.setValue("lastTab", self.tabs.currentIndex())
        super().closeEvent(event)

    def show_status(self, message: str, timeout: int = 4000):
        """Show a message in the main window status bar."""
        self._status_bar.showMessage(message, timeout)

    def startEncounter(self, controller=None, save_data=None):
        if controller is None:
            QMessageBox.warning(self, "Error", "Invalid encounter setup")
            return

        # Close old map window if it exists
        if self.map_window:
            self.map_window.close()

        self.map_window = MapWidget(controller)
        if save_data is not None:
            self.map_window.restore_from_save(save_data)
        self.map_window.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DMSim — D&D Combat Simulator")
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable verbose debug output from the engine during a run"
    )
    args, qt_args = parser.parse_known_args()

    if args.debug:
        _engine_utils.set_debug(True)

    app = QApplication(qt_args or sys.argv[:1])

    window = MainWindow()
    if args.debug:
        window.debug_action.setChecked(True)
    window.setWindowIcon(QtGui.QIcon(str(_root / 'DM_Sim_Icon.png')))
    window.show()

    app.exec()


