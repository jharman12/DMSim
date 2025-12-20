import json
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QSpinBox, QComboBox,
    QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QListWidget, QListWidgetItem,
    QScrollArea, QApplication, QTabWidget, QMessageBox
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from pathlib import Path

class CharacterStore:
    def __init__(self, file_path="A:\\Code\\Python\\Git Repo\\DMSim\\actors\\savedObjs\\newChars.json"):
        self.file_path = Path(file_path)
        self.characters = {}  # name -> data
        self.load()

    def load(self):
        if self.file_path.exists():
            with open(self.file_path, "r") as f:
                data = json.load(f)

            # 🔥 FIX HERE
            self.characters = data.get("characters", {})
        else:
            self.characters = {}


    def save(self):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, "w") as f:
            json.dump(self.characters, f, indent=2)

    def get_names(self):
        return sorted(self.characters.keys())

    def get(self, name):
        return self.characters.get(name)

    def upsert(self, name, data):
        self.characters[name] = data
        self.save()

    def delete(self, name):
        if name in self.characters:
            del self.characters[name]
            self.save()



class CharacterEditor(QWidget):
    def __init__(self, character_store):
        super().__init__()
        self.store = character_store
        

        self.setWindowTitle("Character Sheet")
        self.weapon_widgets = []
        self.image_path = None

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        main_layout.addWidget(self._buildCharacterLoader())

        main_layout.addWidget(self._buildCoreInfo())
        main_layout.addWidget(self._buildAbilityScores())
        main_layout.addWidget(self._buildWeapons())
        main_layout.addWidget(self._buildImagePicker())

        save_btn = QPushButton("Save Character")
        save_btn.clicked.connect(self.saveCharacter)
        main_layout.addWidget(save_btn)

        self.character_db = {}
        self.current_db_path = None
        self.current_character = None

        self._loadCharacterList()

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
        self.name_input.clear()
        self.class_input.clear()
        self.level_input.setValue(1)
        self.ac_input.setValue(10)
        self.hp_input.setValue(1)
        self.image_label.setText("No Image")
        self.image_path = None

        for spin in self.mods.values():
            spin.setValue(0)

        self.clearWeapons()

    def addWeaponFromData(self, data):
        

        for weap in data: # data here is list of dictionaries
            self.addWeapon()
            w = self.weapon_widgets[-1]
            print(weap)
            w["name"].setText(weap["name"])
            w["type"].setCurrentText(weap["type"])
            w["range"].setValue(weap["range"])
            w["attack_mod"].setValue(weap["attack_mod"])
            w["dice_count"].setValue(weap["dice_count"])
            w["dice_type"].setCurrentText(weap["dice_type"])
            w["damage_mod"].setValue(weap["damage_mod"])

    def loadSelectedCharacter(self, name):
        if name == "— New Character —" or name not in self.character_db:
            self.clearEditor()
            self.current_character = None
            return

        char = self.character_db[name]
        self.current_character = name

        self.name_input.setText(char["name"])
        self.class_input.setText(char["class"])
        self.level_input.setValue(char["level"])
        self.ac_input.setValue(char["ac"])
        self.hp_input.setValue(char["hp"])

        self.image_path = char.get("image")
        if self.image_path:
            px = QPixmap(self.image_path).scaled(100, 100, Qt.KeepAspectRatio)
            self.image_label.setPixmap(px)

        for k, spin in self.mods.items():
            spin.setValue(char["mods"].get(k, 0))

        self.clearWeapons()
        for weapon in char["weapons"]:
            self.addWeaponFromData(weapon)


    def _buildCharacterLoader(self):
        box = QGroupBox("Character Database")
        layout = QHBoxLayout()

        self.character_selector = QComboBox()
        self.character_selector.currentTextChanged.connect(self.loadCharacter)

        load_btn = QPushButton("Load JSON")
        load_btn.clicked.connect(self.loadCharacterDatabase)

        layout.addWidget(self.character_selector)
        layout.addWidget(load_btn)

        box.setLayout(layout)
        return box

    def loadCharacter(self, name):
        if name == "New Character":
            self.clearForm()
            return

        data = self.store.get(name)
        print(data)
        if not data:
            return

        self.name_input.setText(name)
        self.level_input.setValue(data["level"])
        self.ac_input.setValue(data["ac"])
        self.hp_input.setValue(data["hp"])

        self.loadModifiers(data["mods"])
        self.addWeaponFromData(data["weapons"])


    def _buildCoreInfo(self):
        box = QGroupBox("Character Info")
        grid = QGridLayout()

        self.name_input = QLineEdit()
        self.class_input = QLineEdit()

        self.level_input = QSpinBox()
        self.level_input.setRange(1, 20)

        self.ac_input = QSpinBox()
        self.ac_input.setRange(0, 40)

        self.hp_input = QSpinBox()
        self.hp_input.setRange(0, 500)

        grid.addWidget(QLabel("Name"), 0, 0)
        grid.addWidget(self.name_input, 0, 1)

        grid.addWidget(QLabel("Class"), 1, 0)
        grid.addWidget(self.class_input, 1, 1)

        grid.addWidget(QLabel("Level"), 0, 2)
        grid.addWidget(self.level_input, 0, 3)

        grid.addWidget(QLabel("AC"), 1, 2)
        grid.addWidget(self.ac_input, 1, 3)

        grid.addWidget(QLabel("Health"), 2, 0)
        grid.addWidget(self.hp_input, 2, 1)

        box.setLayout(grid)
        return box
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
            spin.setRange(0, 30)
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

        for w in [name, atk_type, rng, atk_mod, dice_count, dice_type, dmg_mod]:
            row.addWidget(w)

        self.weapon_container.addLayout(row)

        self.weapon_widgets.append({
            "name": name,
            "type": atk_type,
            "range": rng,
            "attack_mod": atk_mod,
            "dice_count": dice_count,
            "dice_type": dice_type,
            "damage_mod": dmg_mod
        })

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
            return

        data = {
            "name": name,
            "class": self.class_input.text(),
            "level": self.level_input.value(),
            "ac": self.ac_input.value(),
            "hp": self.hp_input.value(),
            "image": self.image_path,
            "mods": {k: v.value() for k, v in self.mods.items()},
            "weapons": []
        }

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

        self.character_db[name] = data

        if not self.current_db_path:
            self.current_db_path, _ = QFileDialog.getSaveFileName(
                self, "Save Character Database", "", "JSON Files (*.json)"
            )
            if not self.current_db_path:
                return

        with open(self.current_db_path, "w") as f:
            json.dump({"characters": self.character_db}, f, indent=4)

        if self.character_selector.findText(name) == -1:
            self.character_selector.addItem(name)

        self.character_selector.setCurrentText(name)



