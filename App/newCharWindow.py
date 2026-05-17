import json
import pathlib
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QSpinBox, QComboBox, QCompleter,
    QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QListWidget, QListWidgetItem,
    QScrollArea, QApplication, QTabWidget, QMessageBox,
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, QEvent
from pathlib import Path

_root = pathlib.Path(__file__).parent.parent

class AutocompleteLineEdit(QLineEdit):
    """QLineEdit that accepts Tab to autocomplete with the closest match."""
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Tab:
            completer = self.completer()
            if completer and completer.completionCount() > 0:
                completer.setCurrentRow(0)
                completion = completer.currentCompletion()
                self.setText(completion)
            event.accept()
            return
        super().keyPressEvent(event)

class CharacterStore:
    def __init__(self, file_path=None):
        if file_path is None:
            file_path = _root / "actors" / "savedObjs" / "newChars.json"
        self.file_path = Path(file_path)
        self.characters = {}  # name -> data
        self.load()

    def load(self):
        if self.file_path.exists():
            with open(self.file_path, "r") as f:
                data = json.load(f)
            self.characters = data
        else:
            self.characters = {}

    def upsert(self, name, data):
        self.characters[name] = data
        self.save()

    def save(self):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, "w") as f:
            json.dump(self.characters, f, indent=2)

    def get_names(self):
        return sorted(self.characters.keys())

    def get(self, name):
        return self.characters.get(name)

    def delete(self, name):
        if name in self.characters:
            del self.characters[name]
            self.save()

def set_font(widget, size, weight=QFont.Normal, monospace=False):
    if monospace:
        font = QFont("Consolas")
    else:
        font = widget.font()

    font.setPointSize(size)
    font.setWeight(weight)
    widget.setFont(font)

class CharacterEditor(QWidget):
    def __init__(self, character_store):
        super().__init__()
        self.store = character_store
        
        self.setWindowTitle("Character Sheet")
        self.weapon_widgets = []
        self.class_widgets = []  # Track class entries
        self.image_path = None
        self.spell_list = None
        self.spell_input = None
        self.spell_group = None
        self.spell_add_btn = None
        self.spell_remove_btn = None
        self.all_spells = self._load_spell_names()

        self.scroll_area = QScrollArea(self)
        self.container = QWidget()
        main_layout = QVBoxLayout(self.container)
        main_layout.setSpacing(12)

        main_layout.addWidget(self._buildCharacterLoader())

        main_layout.addWidget(self._buildCoreInfo())
        main_layout.addWidget(self._buildClasses())
        main_layout.addWidget(self._buildSpells())
        main_layout.addWidget(self._buildAbilityScores())
        main_layout.addWidget(self._buildWeapons())
        main_layout.addWidget(self._buildImagePicker())

        save_btn = QPushButton("Save Character")
        save_btn.clicked.connect(self.saveCharacter)
        main_layout.addWidget(save_btn)

        self.scroll_area.setWidget(self.container)
        self.scroll_area.setWidgetResizable(True)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.scroll_area)

        self.character_db = {}
        self.current_db_path = None
        self.current_character = None

        self._loadCharacterList()

    def applyFonts(self):
        mw = self.window()
        if mw is None:
            return

        base = mw.TextScale.size(mw.text_scale)

        try:
            set_font(self.character_selector, base)
        except Exception:
            pass

        # core inputs
        for w in (self.name_input, self.level_input, self.ac_input, self.hp_input):
            try:
                set_font(w, base)
            except Exception:
                pass

        # class widgets
        for c in self.class_widgets:
            for widget in c.values():
                try:
                    set_font(widget, base)
                except Exception:
                    pass

        # spells widgets
        for w in (self.spell_input, self.spell_list, getattr(self, 'spell_add_btn', None), getattr(self, 'spell_remove_btn', None)):
            if w is None:
                continue
            try:
                set_font(w, base)
            except Exception:
                pass

        for spin in self.mods.values():
            try:
                set_font(spin, base)
            except Exception:
                pass

        # weapon widgets
        for weap in self.weapon_widgets:
            for widget in weap.values():
                try:
                    set_font(widget, base)
                except Exception:
                    pass

        
    def _loadCharacterList(self):
        self.character_selector.blockSignals(True)
        self.character_selector.clear()
        self.character_selector.addItem("New Character")
        self.character_selector.addItems(self.store.get_names())
        self.character_selector.blockSignals(False)


    def addWeaponFromData(self, data):
        self.addWeapon()
        w = self.weapon_widgets[-1]

        w["name"].setText(data["name"])
        w["type"].setCurrentText(data["type"])
        w["range"].setValue(data["range"])
        w["attack_mod"].setValue(data["attack_mod"])
        w["dice_count"].setValue(data["dice_count"])
        w["dice_type"].setCurrentText(data["dice_type"])
        w["damage_mod"].setValue(data["damage_mod"])

    def clearWeapons(self):
        """Remove all weapon widgets from the UI and reset tracking."""
        
        # Remove widgets from layout
        while self.weapon_container.count():
            item = self.weapon_container.takeAt(0)

            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

            # If it's a nested layout (rare but safe to handle)
            layout = item.layout()
            if layout is not None:
                self._clearLayout(layout)

        self.weapon_widgets.clear()

    def _clearLayout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clearLayout(item.layout())

    def _load_spell_names(self):
        """Load spell names from spellList.json for completer; fallback to empty list on error."""
        try:
            spell_path = Path(__file__).resolve().parent.parent / "spells" / "spellList.json"
            with open(spell_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return sorted(list(data.keys()))
        except Exception:
            return []


    def loadCharacterDatabase(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Character Database", "", "JSON Files (*.json)"
        )
        if not path:
            return

        with open(path, "r") as f:
            data = json.load(f)

        self.character_db = data.get("characters", {})
        self.current_db_path = path

        self.character_selector.clear()
        self.character_selector.addItem("— New Character —")
        self.character_selector.addItems(self.character_db.keys())

    def clearEditor(self):
        self.clearForm()

    def clearForm(self):
        self.name_input.clear()
        self.level_input.setValue(1)
        self.ac_input.setValue(10)
        self.hp_input.setValue(1)
        self.image_label.setText("No Image")
        self.image_path = None

        self.clearClasses()
        self.clearSpells()

        for spin in self.mods.values():
            spin.setValue(0)

        self.clearWeapons()

    def _update_total_level(self):
        """Recalculate total level from all class level spinboxes and display it."""
        total = sum(c["level_spin"].value() for c in self.class_widgets)
        self.level_input.setValue(max(total, 1))

    def _buildCharacterLoader(self):
        box = QGroupBox("Character Database")
        layout = QHBoxLayout()

        self.character_selector = QComboBox()
        self.character_selector.currentTextChanged.connect(self.loadCharacter)

        layout.addWidget(self.character_selector)

        box.setLayout(layout)
        return box

    def loadCharacter(self, name):
        if name == "New Character":
            self.clearForm()
            return

        data = self.store.get(name)
        if not data:
            return

        self.name_input.setText(name)
        
        # Handle both single-class and multiclass formats
        class_data = data.get("class")
        self.clearClasses()
        if isinstance(class_data, dict):
            for class_name, level in sorted(class_data.items()):
                self.addClassFromData({"name": class_name, "level": level})
        else:
            self.addClassFromData({"name": class_data, "level": data.get("level", 1)})
        
        self._update_total_level()
        self.ac_input.setValue(data.get("ac", 10))
        self.hp_input.setValue(data.get("hp", 1))

        self.loadModifiers(data.get("mods", {}))

        image_path = data.get("image")
        if image_path and Path(image_path).exists():
            self.image_path = image_path
            px = QPixmap(image_path).scaled(100, 100, Qt.KeepAspectRatio)
            self.image_label.setPixmap(px)
        else:
            self.image_path = None
            self.image_label.setText("No Image")

        # Spells (optional known list)
        self.clearSpells()
        known_spells = data.get("known_spells")
        if known_spells:
            self.spell_group.setChecked(True)
            self._set_spell_widgets_enabled(True)
            for spell in known_spells:
                self.addSpellFromData(spell)

        self.clearWeapons()
        for weapon in data.get("weapons", []):
            self.addWeaponFromData(weapon)


    def _buildCoreInfo(self):
        box = QGroupBox("Character Info")
        grid = QGridLayout()

        self.name_input = QLineEdit()

        self.level_input = QSpinBox()
        self.level_input.setRange(1, 20)
        self.level_input.setReadOnly(True)
        self.level_input.setToolTip("Total level (auto-calculated from classes)")

        self.ac_input = QSpinBox()
        self.ac_input.setRange(0, 40)

        self.hp_input = QSpinBox()
        self.hp_input.setRange(0, 500)

        grid.addWidget(QLabel("Name"), 0, 0)
        grid.addWidget(self.name_input, 0, 1)

        grid.addWidget(QLabel("Level"), 0, 2)
        grid.addWidget(self.level_input, 0, 3)

        grid.addWidget(QLabel("AC"), 1, 2)
        grid.addWidget(self.ac_input, 1, 3)

        grid.addWidget(QLabel("Health"), 2, 0)
        grid.addWidget(self.hp_input, 2, 1)

        box.setLayout(grid)
        return box

    def _buildClasses(self):
        """Build the classes UI similar to weapons."""
        box = QGroupBox("Classes")
        layout = QVBoxLayout()

        self.class_container = QVBoxLayout()
        layout.addLayout(self.class_container)

        add_btn = QPushButton("+ Add Class")
        add_btn.clicked.connect(self.addClass)
        layout.addWidget(add_btn)

        box.setLayout(layout)
        return box

    def _buildSpells(self):
        """Optional known-spells section; when unchecked, uses full spell list."""
        box = QGroupBox("Known Spells (optional)")
        box.setCheckable(True)
        box.setChecked(False)
        layout = QVBoxLayout()

        # Searchable input with completer
        input_row = QHBoxLayout()
        self.spell_input = AutocompleteLineEdit()
        self.spell_input.setPlaceholderText("Type to search spells (Tab to autocomplete)")
        if self.all_spells:
            completer = QCompleter(self.all_spells)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setFilterMode(Qt.MatchContains)
            self.spell_input.setCompleter(completer)
        self.spell_input.returnPressed.connect(self.addSpell)
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.addSpell)
        self.spell_add_btn = add_btn
        input_row.addWidget(self.spell_input)
        input_row.addWidget(add_btn)
        layout.addLayout(input_row)

        # List of selected spells
        self.spell_list = QListWidget()
        self.spell_list.setMaximumHeight(150)
        layout.addWidget(self.spell_list)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.removeSelectedSpell)
        self.spell_remove_btn = remove_btn
        layout.addWidget(remove_btn)

        box.setLayout(layout)
        self.spell_group = box
        box.toggled.connect(self._set_spell_widgets_enabled)
        self._set_spell_widgets_enabled(False)
        return box

    def _set_spell_widgets_enabled(self, enabled):
        if not self.spell_group:
            return
        for widget in (self.spell_input, self.spell_list):
            if widget is not None:
                widget.setEnabled(enabled)
        # Buttons are children of layout; enable/disable by traversing
        if self.spell_group.layout():
            for i in range(self.spell_group.layout().count()):
                item = self.spell_group.layout().itemAt(i)
                w = item.widget()
                if w is not None:
                    w.setEnabled(enabled)
                elif item.layout():
                    for j in range(item.layout().count()):
                        sub = item.layout().itemAt(j).widget()
                        if sub is not None:
                            sub.setEnabled(enabled)

    def addSpell(self):
        if not self.spell_group.isChecked():
            self.spell_group.setChecked(True)
        name = self.spell_input.text().strip()
        if not name:
            return
        # Avoid duplicates
        for i in range(self.spell_list.count()):
            if self.spell_list.item(i).text().lower() == name.lower():
                self.spell_input.clear()
                return
        self.spell_list.addItem(name)
        self.spell_input.clear()

    def removeSelectedSpell(self):
        item = self.spell_list.currentItem()
        if item:
            self.spell_list.takeItem(self.spell_list.row(item))

    def addSpellFromData(self, spell_name):
        if not self.spell_group.isChecked():
            self.spell_group.setChecked(True)
        # Avoid duplicates
        for i in range(self.spell_list.count()):
            if self.spell_list.item(i).text().lower() == spell_name.lower():
                return
        self.spell_list.addItem(spell_name)

    def clearSpells(self):
        if self.spell_list:
            self.spell_list.clear()
        if self.spell_group:
            self.spell_group.setChecked(False)
        self._set_spell_widgets_enabled(False)

    def addClass(self):
        """Add a new class entry."""
        row = QHBoxLayout()

        class_combo = QComboBox()
        class_combo.addItems([
            "Barbarian", "Bard", "Cleric", "Druid", "Fighter", "Monk",
            "Paladin", "Ranger", "Rogue", "Sorcerer", "Warlock", "Wizard", "Artificer"
        ])

        level_spin = QSpinBox()
        level_spin.setRange(1, 20)
        level_spin.setValue(1)
        level_spin.valueChanged.connect(self._update_total_level)

        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(lambda: self.deleteClass(row))

        row.addWidget(QLabel("Class:"))
        row.addWidget(class_combo)
        row.addWidget(QLabel("Level:"))
        row.addWidget(level_spin)
        row.addWidget(del_btn)

        self.class_container.addLayout(row)

        self.class_widgets.append({
            "class_combo": class_combo,
            "level_spin": level_spin,
            "delete_btn": del_btn,
            "layout": row
        })

        # Apply current font size to new widgets
        mw = self.window()
        if mw is not None:
            try:
                base = mw.TextScale.size(mw.text_scale)
                for widget in [class_combo, level_spin, del_btn]:
                    try:
                        set_font(widget, base)
                    except Exception:
                        pass
            except Exception:
                pass

    def deleteClass(self, layout):
        """Delete a class entry."""
        for i in range(self.class_container.count()):
            item = self.class_container.itemAt(i)
            if item.layout() == layout:
                self.class_container.takeAt(i)
                self._clearLayout(layout)
                for j, c in enumerate(self.class_widgets):
                    if c["layout"] == layout:
                        del self.class_widgets[j]
                        break
                break

    def addClassFromData(self, data):
        """Add a class entry from character data."""
        self.addClass()
        c = self.class_widgets[-1]
        c["class_combo"].setCurrentText(data["name"])
        c["level_spin"].setValue(data["level"])

    def clearClasses(self):
        """Clear all class entries."""
        while self.class_container.count() > 0:
            item = self.class_container.takeAt(0)
            if item.layout():
                self._clearLayout(item.layout())
        self.class_widgets.clear()
    def loadModifiers(self, modifiers: dict):
        """
        Load ability modifiers into UI inputs.

        Expected format:
        {
            "str": int,
            "dex": int,
            "con": int,
            "int": int,
            "wis": int,
            "cha": int
        }
        """

        if not modifiers:
            modifiers = {}

        for key, spinbox in self.mods.items():
            value = modifiers.get(key, 0)
            spinbox.blockSignals(True)
            spinbox.setValue(value)
            spinbox.blockSignals(False)

    def _buildAbilityScores(self):
        box = QGroupBox("Ability Modifiers")
        grid = QGridLayout()

        self.mods = {}
        abilities = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]

        for i, abil in enumerate(abilities):
            lbl = QLabel(abil)
            spin = QSpinBox()
            spin.setRange(-5, 30)
            self.mods[abil.lower()] = spin

            grid.addWidget(lbl, 0, i)
            grid.addWidget(spin, 1, i)

        box.setLayout(grid)
        return box
    
    def _buildWeapons(self):
        box = QGroupBox("Weapons")
        layout = QVBoxLayout()

        self.weapon_container = QVBoxLayout()
        layout.addLayout(self.weapon_container)

        add_btn = QPushButton("+ Add Weapon")
        add_btn.clicked.connect(self.addWeapon)
        layout.addWidget(add_btn)

        box.setLayout(layout)
        return box

    def addWeapon(self):
        row = QHBoxLayout()

        name = QLineEdit()
        name.setPlaceholderText("Name")

        atk_type = QComboBox()
        atk_type.addItems(["Melee", "Ranged"])

        rng = QSpinBox()
        rng.setRange(0, 500)

        atk_mod = QSpinBox()
        atk_mod.setRange(-10, 20)

        dice_count = QSpinBox()
        dice_count.setRange(1, 10)

        dice_type = QComboBox()
        dice_type.addItems(["d4", "d6", "d8", "d10", "d12"])

        dmg_mod = QSpinBox()
        dmg_mod.setRange(-10, 20)

        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(lambda: self.delete_weapon(row))

        for w in [name, atk_type, rng, atk_mod, dice_count, dice_type, dmg_mod, del_btn]:
            row.addWidget(w)

        self.weapon_container.addLayout(row)

        self.weapon_widgets.append({
            "name": name,
            "type": atk_type,
            "range": rng,
            "attack_mod": atk_mod,
            "dice_count": dice_count,
            "dice_type": dice_type,
            "damage_mod": dmg_mod,
            "delete_btn": del_btn,
            "layout": row
        })

        # Apply current font size to new widgets
        mw = self.window()
        if mw is not None:
            try:
                base = mw.TextScale.size(mw.text_scale)
                for widget in [name, atk_type, rng, atk_mod, dice_count, dice_type, dmg_mod, del_btn]:
                    try:
                        set_font(widget, base)
                    except Exception:
                        pass
            except Exception:
                pass

    def delete_weapon(self, layout):
        # Find the index of the layout in weapon_container
        for i in range(self.weapon_container.count()):
            item = self.weapon_container.itemAt(i)
            if item.layout() == layout:
                # Remove from container
                self.weapon_container.takeAt(i)
                # Delete the layout and its widgets
                self._clearLayout(layout)
                # Remove from weapon_widgets
                for j, w in enumerate(self.weapon_widgets):
                    if w["layout"] == layout:
                        del self.weapon_widgets[j]
                        break
                break

    def _buildImagePicker(self):
        box = QGroupBox("Character Image")
        layout = QHBoxLayout()

        self.image_label = QLabel("No Image")
        self.image_label.setFixedSize(100, 100)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid #666;")

        btn = QPushButton("Choose Image")
        btn.clicked.connect(self.pickImage)

        layout.addWidget(self.image_label)
        layout.addWidget(btn)

        box.setLayout(layout)
        return box

    def pickImage(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg)")
        if path:
            self.image_path = path
            px = QPixmap(path).scaled(100, 100, Qt.KeepAspectRatio)
            self.image_label.setPixmap(px)

    def getWeapons(self):
        data = {"weapons": []}
        for w in self.weapon_widgets:
            data["weapons"].append({
                "name": w["name"].text(),
                "type": w["type"].currentText(),
                "range": w["range"].value(),
                "attack_mod": w["attack_mod"].value(),
                "dice_count": w["dice_count"].value(),
                "dice_type": w["dice_type"].currentText(),
                "damage_mod": w["damage_mod"].value()
            })
        return data
    
    def refreshCharacters(self):
        self.store.load()
        self._loadCharacterList()


    def saveCharacter(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Please enter a character name")
            return

        # Validate we have at least one class
        if len(self.class_widgets) == 0:
            QMessageBox.warning(self, "Warning", "Please add at least one class")
            return

        # Build class data from class widgets
        class_data = {}
        total_level = 0
        for c in self.class_widgets:
            class_name = c["class_combo"].currentText()
            class_level = c["level_spin"].value()
            class_data[class_name] = class_level
            total_level += class_level

        # If only one class, save as string for backward compatibility
        if len(class_data) == 1:
            class_data = list(class_data.keys())[0]

        data = {
            "name": name,
            "class": class_data,
            "level": total_level,
            "ac": self.ac_input.value(),
            "hp": self.hp_input.value(),
            "image": self.image_path,
            "mods": {k: v.value() for k, v in self.mods.items()},
            "weapons": []
        }

        # Optional known spells
        if self.spell_group.isChecked():
            known = [self.spell_list.item(i).text() for i in range(self.spell_list.count())]
            data["known_spells"] = known

        for w in self.weapon_widgets:
            data["weapons"].append({
                "name": w["name"].text(),
                "type": w["type"].currentText(),
                "range": w["range"].value(),
                "attack_mod": w["attack_mod"].value(),
                "dice_count": w["dice_count"].value(),
                "dice_type": w["dice_type"].currentText(),
                "damage_mod": w["damage_mod"].value()
            })

        self.store.upsert(name, data)
        self.refreshCharacters()
        QMessageBox.information(self, "Success", f"Character '{name}' saved successfully!")



