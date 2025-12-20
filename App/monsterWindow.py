import json
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QSpinBox, QPushButton,
    QFileDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QListWidget,
    QMessageBox, QDoubleSpinBox, QTextEdit, QGridLayout, QComboBox, QScrollArea, QMessageBox
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt
import pathlib
dmSimPath = str(pathlib.Path(__file__).parent.resolve())[0:-4]
import sys
sys.path.insert(1, dmSimPath + '/model/')
from monster import Monster


class MonsterStore:
    def __init__(self, file_path=None):
        if file_path is None:
            # file is at workspace_root/actors/savedObjs/monsters.json
            file_path = Path(__file__).parent.parent / "actors" / "savedObjs" / "monsters.json"

        self.file_path = Path(file_path)
        self.monsters = {}
        self.load()

    def load(self):
        if self.file_path.exists():
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Expecting { "monsters": {name: data, ...} } or list
            if isinstance(data, dict) and "monsters" in data:
                val = data["monsters"]
                if isinstance(val, dict):
                    self.monsters = val
                elif isinstance(val, list):
                    # convert list to dict keyed by name
                    self.monsters = {m.get("name", f"monster_{i}"): m for i, m in enumerate(val)}
                else:
                    self.monsters = {}
            else:
                # try list-of-monsters
                if isinstance(data, list):
                    self.monsters = {m.get("name", f"monster_{i}"): m for i, m in enumerate(data)}
                else:
                    self.monsters = {}
        else:
            self.monsters = {}

    def save(self):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump({"monsters": self.monsters}, f, indent=2)

    def get_names(self):
        return sorted(self.monsters.keys())

    def get(self, name):
        return self.monsters.get(name)

    def upsert(self, name, data):
        self.monsters[name] = data
        self.save()

    def delete(self, name):
        if name in self.monsters:
            del self.monsters[name]
            self.save()


def set_font(widget, size, weight=QFont.Normal, monospace=False):
    if monospace:
        font = QFont("Consolas")
    else:
        font = widget.font()

    font.setPointSize(size)
    font.setWeight(weight)
    widget.setFont(font)


class MonsterEditor(QWidget):
    """Simple editor for monsters stored in actors/savedObjs/monsters.json

    Data is stored as a dict keyed by monster name. Each monster is a dict
    containing at least: name, cr, ac, hp, image
    """

    def __init__(self, store: MonsterStore = None):
        super().__init__()
        self.store = store or MonsterStore()

        self.setWindowTitle("Monster Editor")

        self.scroll_area = QScrollArea(self)
        self.container = QWidget()
        main = QVBoxLayout(self.container)

        # DB list
        db_box = QGroupBox("Monster Database")
        db_layout = QHBoxLayout()

        self.list_widget = QListWidget()
        self.list_widget.currentTextChanged.connect(self.load_monster)

        btn_col = QVBoxLayout()
        load_btn = QPushButton("Load JSON")
        load_btn.clicked.connect(self.load_json_file)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(self.delete_selected)

        btn_col.addWidget(load_btn)
        btn_col.addWidget(refresh_btn)
        btn_col.addWidget(del_btn)
        btn_col.addStretch()

        db_layout.addWidget(self.list_widget)
        db_layout.addLayout(btn_col)
        db_box.setLayout(db_layout)

        main.addWidget(db_box)

        # Core info
        info_box = QGroupBox("Monster Info")
        info_layout = QHBoxLayout()

        left_col = QVBoxLayout()
        right_col = QVBoxLayout()

        self.name_input = QLineEdit()
        self.cr_input = QLineEdit()
        self.ac_input = QSpinBox()
        self.ac_input.setRange(0, 100)
        self.hp_input = QSpinBox()
        self.hp_input.setRange(0, 9999)

        left_col.addWidget(QLabel("Name"))
        left_col.addWidget(self.name_input)
        left_col.addWidget(QLabel("CR"))
        left_col.addWidget(self.cr_input)

        right_col.addWidget(QLabel("AC"))
        right_col.addWidget(self.ac_input)
        right_col.addWidget(QLabel("HP"))
        right_col.addWidget(self.hp_input)

        info_layout.addLayout(left_col)
        info_layout.addLayout(right_col)
        info_box.setLayout(info_layout)

        main.addWidget(info_box)

        # Weapons
        weapons_box = QGroupBox("Weapons")
        weapons_layout = QVBoxLayout()
        self.weapon_container = QVBoxLayout()
        weapons_layout.addLayout(self.weapon_container)
        add_weapon_btn = QPushButton("+ Add Weapon")
        add_weapon_btn.clicked.connect(self.add_weapon)
        weapons_layout.addWidget(add_weapon_btn)
        weapons_box.setLayout(weapons_layout)
        main.addWidget(weapons_box)

        self.weapon_widgets = []

        # Speed and Size
        speed_size_box = QGroupBox("Speed and Size")
        speed_size_layout = QHBoxLayout()
        self.speed_input = QSpinBox()
        self.speed_input.setRange(0, 200)
        self.size_input = QSpinBox()
        self.size_input.setRange(1, 1000)
        speed_size_layout.addWidget(QLabel("Speed"))
        speed_size_layout.addWidget(self.speed_input)
        speed_size_layout.addWidget(QLabel("Size"))
        speed_size_layout.addWidget(self.size_input)
        speed_size_box.setLayout(speed_size_layout)
        main.addWidget(speed_size_box)

        # Ability Modifiers
        mods_box = QGroupBox("Ability Modifiers")
        mods_layout = QGridLayout()
        self.mods = {}
        abilities = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
        for i, abil in enumerate(abilities):
            lbl = QLabel(abil)
            spin = QSpinBox()
            spin.setRange(-10, 30)
            self.mods[abil.lower()] = spin
            mods_layout.addWidget(lbl, 0, i)
            mods_layout.addWidget(spin, 1, i)
        mods_box.setLayout(mods_layout)
        main.addWidget(mods_box)

        # Turn Factors
        tf_box = QGroupBox("Turn Factors")
        tf_layout = QGridLayout()
        self.tf_inputs = {}
        tf_keys = ["Melee", "Ranged", "Ranged Spell", "Spell CC"]
        for i, key in enumerate(tf_keys):
            lbl = QLabel(key)
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 10.0)
            spin.setSingleStep(0.1)
            self.tf_inputs[key] = spin
            tf_layout.addWidget(lbl, 0, i)
            tf_layout.addWidget(spin, 1, i)
        tf_box.setLayout(tf_layout)
        main.addWidget(tf_box)

        # Spell Attack Mod
        spell_mod_box = QGroupBox("Spell Attack Mod")
        spell_mod_layout = QHBoxLayout()
        self.spell_mod_input = QSpinBox()
        self.spell_mod_input.setRange(-10, 20)
        spell_mod_layout.addWidget(QLabel("Spell Attack Mod"))
        spell_mod_layout.addWidget(self.spell_mod_input)
        spell_mod_box.setLayout(spell_mod_layout)
        main.addWidget(spell_mod_box)

        # Legendary Resistance and Actions
        leg_box = QGroupBox("Legendary")
        leg_layout = QHBoxLayout()
        self.leg_res_input = QSpinBox()
        self.leg_res_input.setRange(0, 10)
        self.leg_actions_input = QSpinBox()
        self.leg_actions_input.setRange(0, 10)
        self.leg_action_weapon_input = QLineEdit()
        leg_layout.addWidget(QLabel("Leg Res"))
        leg_layout.addWidget(self.leg_res_input)
        leg_layout.addWidget(QLabel("Leg Actions"))
        leg_layout.addWidget(self.leg_actions_input)
        leg_layout.addWidget(QLabel("Leg Action Weapon"))
        leg_layout.addWidget(self.leg_action_weapon_input)
        leg_box.setLayout(leg_layout)
        main.addWidget(leg_box)

        # Spells and MultiAttack as JSON text
        spells_box = QGroupBox("Spells (JSON)")
        spells_layout = QVBoxLayout()
        self.spells_text = QTextEdit()
        self.spells_text.setPlaceholderText('{"spell_name": [count, {...}]}')
        spells_layout.addWidget(self.spells_text)
        spells_box.setLayout(spells_layout)
        main.addWidget(spells_box)

        multi_box = QGroupBox("MultiAttack (JSON)")
        multi_layout = QVBoxLayout()
        self.multi_text = QTextEdit()
        self.multi_text.setPlaceholderText('{}')
        multi_layout.addWidget(self.multi_text)
        multi_box.setLayout(multi_layout)
        main.addWidget(multi_box)

        self.current_monster = None

        self.refresh()

        self.scroll_area.setWidget(self.container)
        self.scroll_area.setWidgetResizable(True)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.scroll_area)

    def add_weapon(self):
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

    def delete_weapon(self, layout):
        # Find the index of the layout in weapon_container
        for i in range(self.weapon_container.count()):
            item = self.weapon_container.itemAt(i)
            if item.layout() == layout:
                # Remove from container
                self.weapon_container.takeAt(i)
                # Delete the layout and its widgets
                self._clear_layout(layout)
                # Remove from weapon_widgets
                for j, w in enumerate(self.weapon_widgets):
                    if w["layout"] == layout:
                        del self.weapon_widgets[j]
                        break
                break

    def clear_weapons(self):
        while self.weapon_container.count():
            item = self.weapon_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
        self.weapon_widgets.clear()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def applyFonts(self):
        mw = self.window()
        if mw is None:
            return

        try:
            base = mw.TextScale.size(mw.text_scale)
        except Exception:
            base = 11

        for w in (self.list_widget, self.name_input, self.cr_input, self.ac_input, self.hp_input,
                  self.speed_input, self.size_input, self.spell_mod_input, self.leg_res_input,
                  self.leg_actions_input, self.leg_action_weapon_input, self.spells_text, self.multi_text):
            try:
                set_font(w, base)
            except Exception:
                pass

        for spin in self.mods.values():
            try:
                set_font(spin, base)
            except Exception:
                pass

        for spin in self.tf_inputs.values():
            try:
                set_font(spin, base)
            except Exception:
                pass

        # weapon widgets
        for weap in self.weapon_widgets:
            for widget in weap.values():
                if isinstance(widget, QWidget):
                    try:
                        set_font(widget, base)
                    except Exception:
                        pass

    def refresh(self):
        self.store.load()
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        self.list_widget.addItems(self.store.get_names())
        self.list_widget.blockSignals(False)

    def load_json_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Monster JSON", "", "JSON Files (*.json)")
        if not path:
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # accept either top-level dict or dict with 'monsters'
        if isinstance(data, dict) and "monsters" in data:
            val = data["monsters"]
            if isinstance(val, dict):
                self.store.monsters = val
            elif isinstance(val, list):
                self.store.monsters = {m.get("name", f"m{i}"): m for i, m in enumerate(val)}
        elif isinstance(data, list):
            self.store.monsters = {m.get("name", f"m{i}"): m for i, m in enumerate(data)}
        else:
            QMessageBox.warning(self, "Error", "Unexpected JSON format")
            return

        self.store.save()
        self.refresh()

    def pick_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.webp)")
        if path:
            px = QPixmap(path).scaled(100, 100, Qt.KeepAspectRatio)
            self.image_label.setPixmap(px)
            self.image_path = path

    def load_monster(self, name):
        if not name:
            return
        m = self.store.get(name)
        if not m:
            return

        self.current_monster = name
        self.name_input.setText(m.get("name", name))
        self.cr_input.setText(str(m.get("cr", "")))
        self.ac_input.setValue(int(m.get("ac", 0)))
        self.hp_input.setValue(int(m.get("hp", 0)))
        self.speed_input.setValue(int(m.get("speed", 30)))
        self.size_input.setValue(int(m.get("size", 25)))

        # mods
        for key, spin in self.mods.items():
            spin.setValue(int(m.get("modDict", {}).get(key.capitalize(), 10)))

        # turn factors
        for key, spin in self.tf_inputs.items():
            spin.setValue(float(m.get("turnFactors", {}).get(key, 1.0)))

        self.spell_mod_input.setValue(int(m.get("spellAttackMod", 0)))
        self.leg_res_input.setValue(int(m.get("legRes", 0)))
        self.leg_actions_input.setValue(int(m.get("legActions", [0, []])[0]))
        self.leg_action_weapon_input.setText(str(m.get("legActions", [0, []])[1]))

        # spells
        spells = m.get("spells", {})
        self.spells_text.setPlainText(json.dumps(spells, indent=2))

        # multi
        multi = m.get("multiAttack", {})
        self.multi_text.setPlainText(json.dumps(multi, indent=2))

        # weapons
        self.clear_weapons()
        weapons = m.get("weaponList", [])
        for weap in weapons:
            self.add_weapon()
            w = self.weapon_widgets[-1]
            w["name"].setText(weap.get("name", ""))
            w["type"].setCurrentText(weap.get("attackType", "Melee"))
            w["range"].setValue(weap.get("range", 5))
            w["attack_mod"].setValue(weap.get("attackMod", 0))
            w["dice_count"].setValue(weap.get("diceCount", [1])[0])
            w["dice_type"].setCurrentText(weap.get("diceType", ["d6"])[0])
            w["damage_mod"].setValue(weap.get("dmgMod", 0))

        img = m.get("image") or m.get("Image")
        if img:
            px = QPixmap(img).scaled(100, 100, Qt.KeepAspectRatio)
            self.image_label.setPixmap(px)
            self.image_path = img
        else:
            self.image_label.setText("No Image")
            self.image_path = None

    def save_monster(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Name required")
            return

        try:
            spells = json.loads(self.spells_text.toPlainText() or "{}")
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Error", "Invalid Spells JSON")
            return

        try:
            multi = json.loads(self.multi_text.toPlainText() or "{}")
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Error", "Invalid MultiAttack JSON")
            return

        mod_dict = {k.capitalize(): v.value() for k, v in self.mods.items()}
        turn_factors = {k: v.value() for k, v in self.tf_inputs.items()}
        weapon_list = []
        for w in self.weapon_widgets:
            weapon_list.append({
                "name": w["name"].text(),
                "attackType": w["type"].currentText(),
                "range": w["range"].value(),
                "attackMod": w["attack_mod"].value(),
                "diceType": [w["dice_type"].currentText()],
                "diceCount": [w["dice_count"].value()],
                "dmgMod": w["damage_mod"].value()
            })
        leg_action = [self.leg_actions_input.value(), self.leg_action_weapon_input.text()]

        data = {
            "name": name,
            "cr": self.cr_input.text().strip(),
            "ac": self.ac_input.value(),
            "hp": self.hp_input.value(),
            "speed": self.speed_input.value(),
            "modDict": mod_dict,
            "turnFactors": turn_factors,
            "weaponList": weapon_list,
            "size": self.size_input.value(),
            "spells": spells,
            "spellAttackMod": self.spell_mod_input.value(),
            "multiAttack": multi,
            "legRes": self.leg_res_input.value(),
            "legActions": leg_action,
            "image": getattr(self, "image_path", None)
        }

        # if renaming, remove old key
        if self.current_monster and self.current_monster != name:
            try:
                self.store.delete(self.current_monster)
            except Exception:
                pass

        self.store.upsert(name, data)
        self.refresh()
        self.list_widget.setCurrentText(name)

        # Create Monster object
        try:
            monster_obj = Monster(
                name=name,
                ac=data["ac"],
                health=data["hp"],
                speed=data["speed"],
                modDict=mod_dict,
                turnFactors=turn_factors,
                weaponList=weapon_list,
                size=data["size"],
                spells=spells,
                spellMod=data["spellAttackMod"],
                multiAttack=multi,
                legRes=data["legRes"],
                legAction=leg_action,
                Image=data["image"]
            )
            QMessageBox.information(self, "Success", f"Monster '{name}' saved and object created.")
            # Optionally, store the object somewhere, e.g., self.current_monster_obj = monster_obj
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to create Monster object: {str(e)}")

    def delete_selected(self):
        name = self.list_widget.currentItem().text() if self.list_widget.currentItem() else None
        if not name:
            return

        if QMessageBox.question(self, "Delete", f"Delete '{name}'?") != QMessageBox.StandardButton.Yes:
            return

        self.store.delete(name)
        self.refresh()
