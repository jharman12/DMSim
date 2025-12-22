import json
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QSpinBox, QPushButton,
    QFileDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QListWidget,
    QMessageBox, QDoubleSpinBox, QTextEdit, QGridLayout, QComboBox, QScrollArea, QDialog
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt
import pathlib
dmSimPath = str(pathlib.Path(__file__).parent.resolve())[0:-4]
import sys
sys.path.insert(1, dmSimPath + '/model/')
from monster import Monster

sys.path.insert(1, dmSimPath + '/actors/statReader')
from textReader import buildMonsterFromString


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

            if isinstance(data, dict):
                if "monsters" in data:
                    val = data["monsters"]
                    if isinstance(val, dict):
                        self.monsters = val
                    elif isinstance(val, list):
                        # convert list to dict keyed by name
                        self.monsters = {m.get("name", f"monster_{i}"): m for i, m in enumerate(val)}
                    else:
                        self.monsters = {}
                else:
                    # assume direct dict of monsters
                    self.monsters = data
            elif isinstance(data, list):
                self.monsters = {m.get("name", f"monster_{i}"): m for i, m in enumerate(data)}
            else:
                self.monsters = {}
        else:
            self.monsters = {}

    def save(self):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.monsters, f, indent=2)

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

    def dump_monster(self, monster_obj):
        """Convert a Monster object to dict and save it, similar to MonsterDump."""
        # Convert weaponList to dicts
        newList = []
        for weap in monster_obj.weaponList:
            newList.append(weap.__dict__)
        
        # Convert legActionWeapon to dicts
        legList = []
        for weap in monster_obj.legActionWeapon:
            legList.append(weap.__dict__)

        # Temporarily modify the object for serialization
        original_weaponList = monster_obj.weaponList
        original_legActionWeapon = monster_obj.legActionWeapon
        monster_obj.weaponList = newList
        monster_obj.legActionWeapon = legList
        
        # Serialize to dict
        jsonObj = json.dumps(monster_obj.__dict__)
        test = json.loads(jsonObj)
        
        # Remove unwanted keys
        keys_to_delete = ["maxLegActions", "initTF", "initSpells", "cc", "initMod", "spellDC", "maxLegRes", "reaction", "optRange"]
        for key in keys_to_delete:
            test.pop(key, None)
        
        # Restructure legActions
        test["legActions"] = [test["legActions"], test["legActionWeapon"]]
        del test["legActionWeapon"]
        
        # Get name and remove from dict
        name = test.pop('name')
        
        # Restore original object
        monster_obj.weaponList = original_weaponList
        monster_obj.legActionWeapon = original_legActionWeapon
        
        # Upsert to store
        self.upsert(name, test)


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
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(self.delete_selected)
        read_btn = QPushButton("Read Monster from Text")
        read_btn.clicked.connect(self.read_monster_from_text)

        btn_col.addWidget(refresh_btn)
        btn_col.addWidget(del_btn)
        btn_col.addWidget(read_btn)
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
        leg_layout = QVBoxLayout()

        # Top row: Leg Res, Leg Actions, Leg Action Weapon label
        top_layout = QHBoxLayout()
        self.leg_res_input = QSpinBox()
        self.leg_res_input.setRange(0, 10)
        self.leg_actions_input = QSpinBox()
        self.leg_actions_input.setRange(0, 10)
        top_layout.addWidget(QLabel("Leg Res"))
        top_layout.addWidget(self.leg_res_input)
        top_layout.addWidget(QLabel("Leg Actions"))
        top_layout.addWidget(self.leg_actions_input)
        top_layout.addStretch()
        leg_layout.addLayout(top_layout)

        # Leg Action Weapons container
        self.leg_weapon_container = QVBoxLayout()
        leg_layout.addLayout(self.leg_weapon_container)

        # Add button
        add_leg_weapon_btn = QPushButton("+ Add Legendary Weapon")
        add_leg_weapon_btn.clicked.connect(self.add_leg_action_weapon)
        leg_layout.addWidget(add_leg_weapon_btn)

        leg_box.setLayout(leg_layout)
        main.addWidget(leg_box)

        self.leg_action_weapon_inputs = []

        self.update_leg_weapon_combo()

        # Load spell names
        spell_file = Path(__file__).parent.parent / "spells" / "spellList.json"
        with open(spell_file, "r", encoding="utf-8") as f:
            self.spell_names = sorted(json.load(f).keys())

        spells_box = QGroupBox("Spells")
        spells_layout = QVBoxLayout()
        self.spell_container = QVBoxLayout()
        spells_layout.addLayout(self.spell_container)
        add_spell_btn = QPushButton("+ Add Spell")
        add_spell_btn.clicked.connect(self.add_spell)
        spells_layout.addWidget(add_spell_btn)
        spells_box.setLayout(spells_layout)
        main.addWidget(spells_box)

        self.spell_entries = []

        multi_box = QGroupBox("MultiAttack")
        multi_layout = QVBoxLayout()
        self.multi_container = QVBoxLayout()
        multi_layout.addLayout(self.multi_container)
        add_multi_btn = QPushButton("+ Add Multiattack")
        add_multi_btn.clicked.connect(self.add_multiattack)
        multi_layout.addWidget(add_multi_btn)
        multi_box.setLayout(multi_layout)
        main.addWidget(multi_box)

        self.multi_entries = []

        # image picker
        image_box = QGroupBox("Monster Image")
        image_layout = QHBoxLayout()
        self.image_label = QLabel("No Image")
        self.image_label.setFixedSize(100, 100)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid #666;")
        img_btn = QPushButton("Choose Image")
        img_btn.clicked.connect(self.pick_image)
        image_layout.addWidget(self.image_label)
        image_layout.addWidget(img_btn)
        image_box.setLayout(image_layout)
        main.addWidget(image_box)

        # save button
        save_btn = QPushButton("Save Monster")
        save_btn.clicked.connect(self.save_monster)
        main.addWidget(save_btn)

        self.refresh()

        self.scroll_area.setWidget(self.container)
        self.scroll_area.setWidgetResizable(True)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.scroll_area)

    def update_leg_weapon_combo(self):
        for item in self.leg_action_weapon_inputs:
            combo = item["combo"]
            combo.clear()
            combo.addItem("None")
            for w in self.weapon_widgets:
                name = w["name"].text().strip()
                if name:
                    combo.addItem(name)

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

        self.update_leg_weapon_combo()
        self.update_multi_combos()

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

        self.update_leg_weapon_combo()
        self.update_multi_combos()

    def add_leg_action_weapon(self):
        row = QHBoxLayout()

        combo = QComboBox()
        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(lambda: self.delete_leg_action_weapon(row))

        row.addWidget(QLabel("Leg Action Weapon"))
        row.addWidget(combo)
        row.addWidget(del_btn)

        self.leg_weapon_container.addLayout(row)

        self.leg_action_weapon_inputs.append({
            "combo": combo,
            "layout": row,
            "delete_btn": del_btn
        })

        self.update_leg_weapon_combo()

    def delete_leg_action_weapon(self, layout):
        # Find and remove
        for i, item in enumerate(self.leg_action_weapon_inputs):
            if item["layout"] == layout:
                # Remove from container
                for j in range(self.leg_weapon_container.count()):
                    if self.leg_weapon_container.itemAt(j).layout() == layout:
                        self.leg_weapon_container.takeAt(j)
                        break
                # Delete widgets
                self._clear_layout(layout)
                del self.leg_action_weapon_inputs[i]
                break

    def clear_leg_action_weapons(self):
        while self.leg_weapon_container.count():
            item = self.leg_weapon_container.takeAt(0)
            if item.layout():
                self._clear_layout(item.layout())
        self.leg_action_weapon_inputs.clear()

    def add_spell(self):
        row = QHBoxLayout()

        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems(self.spell_names)

        count_spin = QSpinBox()
        count_spin.setRange(0, 100)

        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(lambda: self.delete_spell(row))

        row.addWidget(combo)
        row.addWidget(count_spin)
        row.addWidget(del_btn)

        self.spell_container.addLayout(row)

        self.spell_entries.append({
            "combo": combo,
            "count": count_spin,
            "layout": row,
            "delete_btn": del_btn
        })

    def delete_spell(self, layout):
        for i, entry in enumerate(self.spell_entries):
            if entry["layout"] == layout:
                for j in range(self.spell_container.count()):
                    if self.spell_container.itemAt(j).layout() == layout:
                        self.spell_container.takeAt(j)
                        break
                self._clear_layout(layout)
                del self.spell_entries[i]
                break

    def clear_spells(self):
        while self.spell_container.count():
            item = self.spell_container.takeAt(0)
            if item.layout():
                self._clear_layout(item.layout())
        self.spell_entries.clear()

    def update_multi_combos(self):
        weapon_names = [w["name"].text().strip() for w in self.weapon_widgets if w["name"].text().strip()]
        for entry in self.multi_entries:
            combo = entry["combo"]
            current = combo.currentText()
            combo.clear()
            combo.addItems(weapon_names)
            if current in weapon_names:
                combo.setCurrentText(current)

    def add_multiattack(self):
        row = QHBoxLayout()

        combo = QComboBox()
        weapon_names = [w["name"].text().strip() for w in self.weapon_widgets if w["name"].text().strip()]
        combo.addItems(weapon_names)

        count_spin = QSpinBox()
        count_spin.setRange(1, 10)

        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(lambda: self.delete_multiattack(row))

        row.addWidget(combo)
        row.addWidget(count_spin)
        row.addWidget(del_btn)

        self.multi_container.addLayout(row)

        self.multi_entries.append({
            "combo": combo,
            "count": count_spin,
            "layout": row,
            "delete_btn": del_btn
        })

    def delete_multiattack(self, layout):
        for i, entry in enumerate(self.multi_entries):
            if entry["layout"] == layout:
                for j in range(self.multi_container.count()):
                    if self.multi_container.itemAt(j).layout() == layout:
                        self.multi_container.takeAt(j)
                        break
                self._clear_layout(layout)
                del self.multi_entries[i]
                break

    def clear_multiattacks(self):
        while self.multi_container.count():
            item = self.multi_container.takeAt(0)
            if item.layout():
                self._clear_layout(item.layout())
        self.multi_entries.clear()
        while self.leg_weapon_container.count():
            item = self.leg_weapon_container.takeAt(0)
            if item.layout():
                self._clear_layout(item.layout())
        self.leg_action_weapon_inputs.clear()

    def clear_weapons(self):
        while self.weapon_container.count():
            item = self.weapon_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
        self.weapon_widgets.clear()
        self.update_leg_weapon_combo()
        self.update_multi_combos()

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
                  self.leg_actions_input):
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

        # leg action weapon combos
        for item in self.leg_action_weapon_inputs:
            try:
                set_font(item["combo"], base)
            except Exception:
                pass
            try:
                set_font(item["delete_btn"], base)
            except Exception:
                pass

        # spell entries
        for entry in self.spell_entries:
            try:
                set_font(entry["combo"], base)
            except Exception:
                pass
            try:
                set_font(entry["count"], base)
            except Exception:
                pass
            try:
                set_font(entry["delete_btn"], base)
            except Exception:
                pass

        # multi entries
        for entry in self.multi_entries:
            try:
                set_font(entry["combo"], base)
            except Exception:
                pass
            try:
                set_font(entry["count"], base)
            except Exception:
                pass
            try:
                set_font(entry["delete_btn"], base)
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
        img = m.get("image")
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
        # self.leg_action_weapon_input.setText(str(m.get("legActions", [0, []])[1]))  # old line, removed

        # spells
        self.clear_spells()
        spells = m.get("spells", {})
        if isinstance(spells, dict):
            for spell, data in spells.items():
                if isinstance(data, list) and len(data) > 0:
                    count = int(data[0])
                elif isinstance(data, int):
                    count = data
                else:
                    count = 1
                self.add_spell()
                entry = self.spell_entries[-1]
                entry["combo"].setCurrentText(spell)
                entry["count"].setValue(count)

        # multi
        self.clear_multiattacks()
        multi = m.get("multiAttack", {})
        if isinstance(multi, dict):
            for weapon, count in multi.items():
                self.add_multiattack()
                entry = self.multi_entries[-1]
                entry["combo"].setCurrentText(weapon)
                entry["count"].setValue(int(count))

        # weapons
        self.clear_weapons()
        weapons = m.get("weaponList", [])
        for weap in weapons:
            self.add_weapon()
            w = self.weapon_widgets[-1]
            w["name"].setText(weap.get("name", ""))
            w["type"].setCurrentText(weap.get("attackType", "Melee"))
            w["range"].setValue(int(weap.get("range", 5)))
            w["attack_mod"].setValue(int(weap.get("attackMod", 0)))
            w["dice_count"].setValue(int(weap.get("diceCount", [1])[0]))
            w["dice_type"].setCurrentText(str(weap.get("diceType", [0])[0]))
            w["damage_mod"].setValue(int(weap.get("dmgMod", 0)))

        # leg action weapons
        self.clear_leg_action_weapons()
        leg_weapons = m.get("legActions", [0, []])[1]
        if isinstance(leg_weapons, list):
            for weapon_name in leg_weapons:
                self.add_leg_action_weapon()
                combo = self.leg_action_weapon_inputs[-1]["combo"]
                combo.setCurrentText(weapon_name["name"] if weapon_name else "None")
        elif isinstance(leg_weapons, str) and leg_weapons:
            self.add_leg_action_weapon()
            combo = self.leg_action_weapon_inputs[-1]["combo"]
            combo.setCurrentText(leg_weapons)
        else:
            # add one empty
            self.add_leg_action_weapon()
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

        spells = {}
        for entry in self.spell_entries:
            spell = entry["combo"].currentText().strip()
            if spell:
                count = entry["count"].value()
                spells[spell] = count

        multiAttack = {}
        for entry in self.multi_entries:
            weapon = entry["combo"].currentText().strip()
            if weapon:
                count = entry["count"].value()
                multiAttack[weapon] = count

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
        leg_action = [self.leg_actions_input.value(), [combo["combo"].currentText() for combo in self.leg_action_weapon_inputs if combo["combo"].currentText() != "None"]]

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

    def read_monster_from_text(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Read Monster from Text")
        layout = QVBoxLayout()
        text_edit = QTextEdit()
        layout.addWidget(text_edit)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(lambda: self.save_monster_text(dialog, text_edit))
        layout.addWidget(save_btn)
        dialog.setLayout(layout)
        dialog.exec_()

    def save_monster_text(self, dialog, text_edit):
        text = text_edit.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "Error", "Text is empty")
            return
        try:
            print('trying to build monster from string')
            monster_obj = buildMonsterFromString(text)
            print('built monster from string', monster_obj.name)
            self.store.dump_monster(monster_obj.monster)
            print('dumped monster to store')
            QMessageBox.information(self, "Success", f"Monster '{monster_obj.monster.name}' saved.")
            self.refresh()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to parse monster: {str(e)}")
        dialog.accept()
