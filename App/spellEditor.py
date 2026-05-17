"""
Spell Creation / Editor tab for DMSim.
Allows creating, editing, and deleting spells that are saved to spellList.json.
"""
import json
import pathlib
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QSpinBox,
    QScrollArea, QSizePolicy, QFrame,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

_SPELL_PATH = pathlib.Path(__file__).parent.parent / "spells" / "spellList.json"

# ── Enum-style constants mirroring existing spell data ────────────────────────

SPELL_LEVELS = [str(i) for i in range(10)]   # 0 = cantrip

CAST_TIMES = [
    "1 Action", "1 Bonus Action", "1 Reaction *",
    "1 Minute", "10 Minutes", "1 Hour",
    "8 Hours", "12 Hours", "24 Hours", "Special",
]

DURATIONS = [
    "Instantaneous", "1 Round", "1 Minute", "10 Minutes",
    "1 Hour", "2 Hours", "8 Hours", "1 Day", "7 Days",
    "10 Days", "24 Hours", "30 Days", "Until Dispelled",
    "Until Dispelled or Triggered", "Special",
]

AREA_TYPES = ["", "sphere", "cone", "line", "square"]

ATTACK_TYPES = ["", "Melee", "Ranged"]

SAVES = [
    "", "Strength Save", "Dexterity Save", "Constitution Save",
    "Intelligence Save", "Wisdom Save", "Charisma Save",
]

DAMAGE_EFFECTS = [
    "Acid", "Bludgeoning", "Cold", "Fire", "Force",
    "Lightning", "Necrotic", "Piercing", "Poison",
    "Psychic", "Radiant", "Slashing", "Thunder",
]

CC_EFFECTS = [
    "Banishment", "Blinded", "Charmed", "Deafened",
    "Frightened", "Incapacitated", "Invisible",
    "Paralyzed", "Petrified", "Prone", "Restrained",
    "Stunned", "Unconscious",
]

OTHER_EFFECTS = [
    "Buff", "Communication", "Control", "Creation", "Debuff",
    "Deception", "Detection", "Environment", "Exploration",
    "Foreknowledge", "Healing", "Movement", "Negation",
    "Shapechanging", "Social", "Summoning", "Teleportation",
    "Utility", "Warding",
]

# Flat list of all selectable effect values (no headers) used for load/save lookups
EFFECTS = [""] + DAMAGE_EFFECTS + CC_EFFECTS + OTHER_EFFECTS

CLASSES = [
    "Artificer", "Bard", "Cleric", "Druid",
    "Paladin", "Ranger", "Sorcerer", "Warlock", "Wizard",
]

DICE_SIZES = ["", "d4", "d6", "d8", "d10", "d12", "d20", "d100"]


def _load_spells() -> dict:
    if _SPELL_PATH.exists():
        with open(_SPELL_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_spells(spells: dict):
    with open(_SPELL_PATH, "w", encoding="utf-8") as f:
        json.dump(spells, f, indent=4)


# ── Dice entry row ────────────────────────────────────────────────────────────

class DiceRow(QWidget):
    """One damage-dice entry: [count] d [size]  [remove]"""
    def __init__(self, count=1, size="d6", parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 20)
        self.count_spin.setValue(count)
        self.count_spin.setFixedWidth(48)

        self.size_combo = QComboBox()
        self.size_combo.addItems(DICE_SIZES)
        idx = self.size_combo.findText(size)
        if idx >= 0:
            self.size_combo.setCurrentIndex(idx)

        self.remove_btn = QPushButton("✕")
        self.remove_btn.setFixedSize(24, 24)
        self.remove_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #c00; border: none; }"
            "QPushButton:hover { color: #f44; }"
        )

        row.addWidget(self.count_spin)
        row.addWidget(QLabel("d"), alignment=Qt.AlignVCenter)
        # replace "d" prefix in size combo since label already has it
        row.addWidget(self.size_combo)
        row.addWidget(self.remove_btn)
        row.addStretch()

    def dice_str(self) -> str:
        sz = self.size_combo.currentText()
        if not sz:
            return ""
        return f"{self.count_spin.value()}{sz}"


# ── Main SpellEditorTab ────────────────────────────────────────────────────────

class SpellEditorTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._spells: dict = _load_spells()
        self._editing: str | None = None   # name of spell being edited

        main = QHBoxLayout(self)
        main.setSpacing(12)

        # ── Left: spell list ──────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(6)

        search_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search spells…")
        self._search.textChanged.connect(self._filter_list)
        search_row.addWidget(self._search)
        left.addLayout(search_row)

        self._list = QListWidget()
        self._list.setMinimumWidth(200)
        self._list.currentTextChanged.connect(self._on_select)
        left.addWidget(self._list, stretch=1)

        btn_row = QHBoxLayout()
        self._new_btn = QPushButton("New")
        self._new_btn.clicked.connect(self._new_spell)
        self._del_btn = QPushButton("Delete")
        self._del_btn.clicked.connect(self._delete_spell)
        btn_row.addWidget(self._new_btn)
        btn_row.addWidget(self._del_btn)
        left.addLayout(btn_row)

        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setFixedWidth(230)
        main.addWidget(left_widget)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.VLine)
        div.setFrameShadow(QFrame.Sunken)
        main.addWidget(div)

        # ── Right: editor form ────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        form_widget = QWidget()
        self._form_layout = QVBoxLayout(form_widget)
        self._form_layout.setSpacing(10)
        self._form_layout.setContentsMargins(8, 8, 8, 8)

        self._build_form()

        scroll.setWidget(form_widget)
        main.addWidget(scroll, stretch=1)

        self._refresh_list()

    # ── Form construction ─────────────────────────────────────────────────

    def _build_form(self):
        fl = self._form_layout

        # -- Basic info --
        basic_box = QGroupBox("Basic Info")
        basic_form = QFormLayout()
        basic_form.setSpacing(8)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Spell name…")
        basic_form.addRow(_lbl("Name *",
            "The spell's name as it will appear in character spell lists and the combat log. "
            "Must be unique — you cannot have two spells with the same name."),
            self._name_edit)

        self._level_combo = QComboBox()
        self._level_combo.addItems(["0 (Cantrip)"] + [str(i) for i in range(1, 10)])
        basic_form.addRow(_lbl("Level",
            "Spell level from 0 (cantrip) to 9.\n"
            "Cantrips (level 0) can be cast freely without using a spell slot.\n"
            "Higher-level spells are more powerful and consume higher-level spell slots."),
            self._level_combo)

        self._time_combo = QComboBox()
        self._time_combo.setEditable(True)
        self._time_combo.addItems(CAST_TIMES)
        basic_form.addRow(_lbl("Casting Time",
            "How long it takes to cast the spell.\n"
            "'1 Action' uses the caster's main action for the turn.\n"
            "'1 Bonus Action' uses the bonus action — useful for quick buffs or follow-up attacks.\n"
            "Spells that take 1 Minute or longer generally cannot be cast during combat."),
            self._time_combo)

        self._duration_combo = QComboBox()
        self._duration_combo.setEditable(True)
        self._duration_combo.addItems(DURATIONS)
        basic_form.addRow(_lbl("Duration",
            "How long the spell's effect lasts after being cast.\n"
            "'Instantaneous' means the effect happens and ends immediately (e.g. a fireball).\n"
            "Longer durations keep the effect active until the time expires or the caster loses concentration.\n"
            "Concentration spells end early if the caster is knocked out, casts another concentration spell, or fails a concentration check."),
            self._duration_combo)

        # Range: special combo + numeric spinbox + "ft" label
        range_row = QHBoxLayout()
        range_row.setSpacing(6)
        self._range_special_combo = QComboBox()
        self._range_special_combo.addItems(["ft", "Self", "Touch", "0", "Special"])
        self._range_special_combo.setFixedWidth(80)
        self._range_special_combo.currentTextChanged.connect(self._on_range_type_changed)
        self._range_spin = QSpinBox()
        self._range_spin.setRange(0, 10000)
        self._range_spin.setSingleStep(5)
        self._range_spin.setValue(60)
        self._range_spin.setFixedWidth(72)
        self._range_ft_label = QLabel("ft")
        range_row.addWidget(self._range_special_combo)
        range_row.addWidget(self._range_spin)
        range_row.addWidget(self._range_ft_label)
        range_row.addStretch()
        range_widget = QWidget()
        range_widget.setLayout(range_row)
        basic_form.addRow(_lbl("Range",
            "The maximum distance from the caster to the spell's target or point of origin.\n"
            "'Self' — the spell only affects the caster (e.g. Mage Armor).\n"
            "'Touch' — the caster must be adjacent to the target (e.g. Cure Wounds).\n"
            "'0' — the spell originates from the caster's space but may extend outward.\n"
            "'Special' — range is described in the spell text and varies.\n"
            "For numbered ranges, enter the distance in feet (e.g. 60 for a 60 ft spell)."),
            range_widget)

        self._conc_check = QCheckBox("Requires Concentration")
        self._conc_check.setToolTip(
            "If checked, the caster must actively concentrate to keep this spell active.\n"
            "Only one concentration spell can be maintained at a time — casting another cancels the first.\n"
            "Taking damage forces a Constitution saving throw (DC 10 or half damage taken) to maintain it.\n"
            "Being knocked unconscious or killed automatically ends concentration.")
        basic_form.addRow("", self._conc_check)

        self._combat_check = QCheckBox("Used in Combat (AI considers this spell)")
        self._combat_check.setToolTip(
            "If checked, enemy and allied AI will include this spell when deciding what to do on their turn.\n"
            "Uncheck for spells that are purely utility outside of combat — rituals, social spells, exploration tools — "
            "so they don't clutter the AI's combat decision-making.")
        self._combat_check.setChecked(True)
        basic_form.addRow("", self._combat_check)

        basic_box.setLayout(basic_form)
        fl.addWidget(basic_box)

        # -- Area --
        area_box = QGroupBox("Area of Effect")
        area_form = QFormLayout()
        area_form.setSpacing(8)

        area_type_row = QHBoxLayout()
        self._area_type_combo = QComboBox()
        self._area_type_combo.addItems(AREA_TYPES)
        self._area_type_combo.currentTextChanged.connect(self._on_area_type_changed)
        area_type_row.addWidget(self._area_type_combo)
        area_form.addRow(_lbl("Shape",
            "The shape of the spell's area of effect.\n"
            "'Sphere' — radiates outward from a central point (e.g. Fireball, 20 ft radius).\n"
            "'Cone' — fans out in a direction the caster chooses (e.g. Burning Hands).\n"
            "'Line' — a narrow beam or streak in a straight line (e.g. Lightning Bolt).\n"
            "'Square' — covers a flat grid area (e.g. Grease, Silence).\n"
            "Leave blank for single-target spells that don't have an area."),
            area_type_row)

        self._area_size_spin = QSpinBox()
        self._area_size_spin.setRange(0, 10000)
        self._area_size_spin.setSingleStep(5)
        self._area_size_spin.setSuffix(" ft")
        area_form.addRow(_lbl("Size",
            "The radius or length of the area in feet, as written in the spell's description.\n"
            "For spheres this is the radius (e.g. Fireball = 20 ft). "
            "For cones and lines this is the length (e.g. Burning Hands = 15 ft cone).\n"
            "The engine uses this to determine which hexes on the map fall inside the effect."),
            self._area_size_spin)

        area_box.setLayout(area_form)
        fl.addWidget(area_box)

        # -- Mechanics --
        mech_box = QGroupBox("Mechanics")
        mech_form = QFormLayout()
        mech_form.setSpacing(8)

        self._attack_combo = QComboBox()
        self._attack_combo.addItems(ATTACK_TYPES)
        mech_form.addRow(_lbl("Attack Type",
            "Whether the spell requires an attack roll to hit.\n"
            "'Ranged' — uses the caster's ranged spell attack modifier (e.g. Fire Bolt, Eldritch Blast).\n"
            "'Melee' — uses the melee spell attack modifier, requires being adjacent to the target (e.g. Shocking Grasp).\n"
            "Leave blank if the spell automatically hits, forces a saving throw, or has no attack roll."),
            self._attack_combo)

        self._save_combo = QComboBox()
        self._save_combo.addItems(SAVES)
        mech_form.addRow(_lbl("Saving Throw",
            "The ability saving throw targets must make against this spell.\n"
            "On a failed save the target takes full effect; on a success they typically take half damage or avoid the condition.\n"
            "Leave blank if the spell uses an attack roll or automatically affects the target with no roll.\n"
            "Common examples: Fireball → Dexterity, Hold Person → Wisdom, Ray of Enfeeblement → Constitution."),
            self._save_combo)

        self._effect_combo = QComboBox()
        _populate_effect_combo(self._effect_combo)
        mech_form.addRow(_lbl("Effect",
            "The primary damage type or condition this spell delivers.\n"
            "Damage types (Fire, Cold, Lightning, etc.) are checked against creature resistances and immunities.\n"
            "Conditions (Incapacitated, Restrained, Stunned, etc.) are applied to the target and affect their actions.\n"
            "Utility categories like Buff, Debuff, Healing, or Control describe non-damaging spells — "
            "the engine uses these for AI priority decisions."),
            self._effect_combo)

        mech_box.setLayout(mech_form)
        fl.addWidget(mech_box)

        # -- Damage Dice --
        dice_box = QGroupBox("Damage Dice")
        dice_box.setToolTip(
            "The dice rolled to calculate damage or healing when this spell is cast.\n"
            "Add one row per dice group — for example, Fireball uses 8d6, so add one row: 8 × d6.\n"
            "Some spells with multiple separate damage rolls (e.g. Scorching Ray) may list multiple rows.\n"
            "Leave empty for spells that deal no damage (buffs, debuffs, utility, etc.).")
        dice_layout = QVBoxLayout()
        dice_layout.setSpacing(4)

        self._dice_container = QVBoxLayout()
        self._dice_container.setSpacing(4)
        self._dice_rows: list[DiceRow] = []
        dice_layout.addLayout(self._dice_container)

        add_dice_btn = QPushButton("+ Add Dice")
        add_dice_btn.clicked.connect(self._add_dice_row)
        dice_layout.addWidget(add_dice_btn, alignment=Qt.AlignLeft)
        dice_box.setLayout(dice_layout)
        fl.addWidget(dice_box)

        # -- Classes --
        class_box = QGroupBox("Available To")
        class_box.setToolTip(
            "The character classes that have access to this spell on their official spell list.\n"
            "This is used to populate spell dropdowns when building characters and to validate spellcasting.\n"
            "Check every class that can learn or prepare this spell (a spell can belong to multiple classes).")
        class_layout = QVBoxLayout()
        class_layout.setSpacing(4)
        self._class_checks: dict[str, QCheckBox] = {}
        class_grid = QHBoxLayout()
        class_grid.setSpacing(8)
        for cls in CLASSES:
            cb = QCheckBox(cls)
            self._class_checks[cls] = cb
            class_grid.addWidget(cb)
        class_layout.addLayout(class_grid)
        class_box.setLayout(class_layout)
        fl.addWidget(class_box)

        # -- Save / Cancel --
        save_row = QHBoxLayout()
        self._save_btn = QPushButton("💾  Save Spell")
        self._save_btn.setStyleSheet(
            "QPushButton { background: #1a5a1a; color: #fff; border-radius: 4px; padding: 6px 16px; }"
            "QPushButton:hover { background: #2a7a2a; }"
        )
        self._save_btn.clicked.connect(self._save_spell)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self._cancel_edit)

        save_row.addWidget(self._save_btn)
        save_row.addWidget(self._cancel_btn)
        save_row.addStretch()
        fl.addLayout(save_row)

        fl.addStretch()

        self._on_area_type_changed(self._area_type_combo.currentText())
        self._on_range_type_changed(self._range_special_combo.currentText())

    # ── Dice row helpers ──────────────────────────────────────────────────

    def _add_dice_row(self, count=1, size="d6"):
        row = DiceRow(count, size)
        row.remove_btn.clicked.connect(lambda: self._remove_dice_row(row))
        self._dice_rows.append(row)
        self._dice_container.addWidget(row)

    def _remove_dice_row(self, row: DiceRow):
        if row in self._dice_rows:
            self._dice_rows.remove(row)
        row.setParent(None)
        row.deleteLater()

    def _clear_dice_rows(self):
        for row in list(self._dice_rows):
            row.setParent(None)
            row.deleteLater()
        self._dice_rows.clear()

    # ── Range type changed ────────────────────────────────────────────────

    def _on_range_type_changed(self, range_type: str):
        numeric = (range_type == "ft")
        self._range_spin.setVisible(numeric)
        self._range_ft_label.setVisible(numeric)

    # ── Area type changed ─────────────────────────────────────────────────

    def _on_area_type_changed(self, area_type: str):
        has_area = bool(area_type)
        # Find the size row label/widget — show only when an area type is chosen
        form = self._area_type_combo.parentWidget().layout() if self._area_type_combo.parentWidget() else None
        # Simpler: just enable/disable the size spin
        self._area_size_spin.setEnabled(has_area)
        if not has_area:
            self._area_size_spin.setValue(0)

    # ── List management ───────────────────────────────────────────────────

    def _refresh_list(self, keep_selection: str | None = None):
        self._list.blockSignals(True)
        self._list.clear()
        query = self._search.text().lower()
        for name in sorted(self._spells.keys()):
            if query and query not in name.lower():
                continue
            item = QListWidgetItem(name)
            self._list.addItem(item)
            if name == keep_selection:
                self._list.setCurrentItem(item)
        self._list.blockSignals(False)

    def _filter_list(self, _text):
        self._refresh_list(keep_selection=self._editing)

    # ── Selection ─────────────────────────────────────────────────────────

    def _on_select(self, name: str):
        if not name or name not in self._spells:
            return
        self._editing = name
        self._populate_form(name, self._spells[name])

    def _populate_form(self, name: str, data: dict):
        self._name_edit.setText(name)

        lvl = str(data.get("lvl", 0))
        idx = self._level_combo.findText("0 (Cantrip)") if lvl == "0" else self._level_combo.findText(lvl)
        if idx >= 0:
            self._level_combo.setCurrentIndex(idx)

        _set_combo(self._time_combo, data.get("time", "1 Action"))
        _set_combo(self._duration_combo, data.get("duration", "Instantaneous"))

        # Range
        range_str = data.get("range", "")
        if range_str.endswith(" ft"):
            try:
                val = int(range_str[:-3])
                _set_combo(self._range_special_combo, "ft")
                self._range_spin.setValue(val)
            except ValueError:
                _set_combo(self._range_special_combo, "Special")
        elif range_str in ("Self", "Touch", "0", "Special"):
            _set_combo(self._range_special_combo, range_str)
        else:
            # Fallback: show as numeric if parseable, else Special
            try:
                _set_combo(self._range_special_combo, "ft")
                self._range_spin.setValue(int(range_str))
            except ValueError:
                _set_combo(self._range_special_combo, "Special")

        self._conc_check.setChecked(bool(data.get("concentration", "")))
        self._combat_check.setChecked(data.get("combat", "y") == "y")

        # Area
        area = data.get("area", "")
        area_parts = area.split() if area else []
        area_type = area_parts[0] if area_parts else ""
        area_size = 0
        if len(area_parts) >= 2:
            try:
                area_size = int(area_parts[1])
            except ValueError:
                area_size = 0
        _set_combo(self._area_type_combo, area_type)
        self._area_size_spin.setValue(area_size)

        _set_combo(self._attack_combo, data.get("attack", ""))
        _set_combo(self._save_combo, data.get("save", ""))
        _set_combo(self._effect_combo, data.get("effect", ""))

        # Dice
        self._clear_dice_rows()
        for d in data.get("dice", []):
            if not d:
                continue
            # parse e.g. "2d6"
            if "d" in d:
                parts = d.split("d")
                try:
                    count = int(parts[0])
                    size = "d" + parts[1]
                except (ValueError, IndexError):
                    count, size = 1, "d6"
            else:
                count, size = 1, "d6"
            self._add_dice_row(count, size)

        # Classes
        classes_str = data.get("classes", "")
        spell_classes = {c.strip() for c in classes_str.split(",")}
        for cls, cb in self._class_checks.items():
            cb.setChecked(cls in spell_classes)

    # ── CRUD ──────────────────────────────────────────────────────────────

    def _new_spell(self):
        self._editing = None
        self._list.clearSelection()
        self._clear_form()

    def _clear_form(self):
        self._name_edit.clear()
        self._level_combo.setCurrentIndex(0)
        _set_combo(self._time_combo, "1 Action")
        _set_combo(self._duration_combo, "Instantaneous")
        _set_combo(self._range_special_combo, "ft")
        self._range_spin.setValue(60)
        self._conc_check.setChecked(False)
        self._combat_check.setChecked(True)
        self._area_type_combo.setCurrentIndex(0)
        self._area_size_spin.setValue(0)
        self._attack_combo.setCurrentIndex(0)
        self._save_combo.setCurrentIndex(0)
        self._effect_combo.setCurrentIndex(0)
        self._clear_dice_rows()
        for cb in self._class_checks.values():
            cb.setChecked(False)

    def _save_spell(self):
        name = self._name_edit.text().strip()

        # ── Build all values first ────────────────────────────────────────
        lvl_text = self._level_combo.currentText()
        lvl = 0 if lvl_text.startswith("0") else int(lvl_text)

        area_type = self._area_type_combo.currentText()
        area_size = self._area_size_spin.value()
        area = f"{area_type} {area_size} ft" if area_type else ""

        range_type = self._range_special_combo.currentText()
        spell_range = (f"{self._range_spin.value()} ft" if range_type == "ft" else range_type)

        attack = self._attack_combo.currentText()
        save = self._save_combo.currentText()
        effect = self._effect_combo.currentText()
        combat = "y" if self._combat_check.isChecked() else "n"

        dice = [r.dice_str() for r in self._dice_rows if r.dice_str()]
        if not dice:
            dice = [""]

        selected_classes = [cls for cls, cb in self._class_checks.items() if cb.isChecked()]
        classes_str = ", ".join(selected_classes)

        # ── Hard errors (will crash the engine) ──────────────────────────
        hard_errors = []

        if not name:
            hard_errors.append("• Spell name is required.")

        # Range must not be empty — engine does int(re.findall(r'\\d+', range)[0])
        if spell_range in ("", "Special") and combat == "y":
            pass  # Special is fine for non-targeted utilities
        elif spell_range == "" :
            hard_errors.append(
                "• Range cannot be empty. Choose 'ft' with a number, Self, Touch, or 0.")

        # Area shape with size=0 would produce "sphere 0 ft" — engine won't find targets
        if area_type and area_size == 0:
            hard_errors.append(
                f"• Area shape '{area_type}' requires a size greater than 0 ft.")

        # Dice validation — engine parses with re.findall(r'\\d+', di); if only one number
        # is found (e.g. "d6") it crashes on index [1].
        import re as _re
        for di in dice:
            if not di:
                continue
            if "d" not in di:
                hard_errors.append(
                    f"• Dice entry '{di}' has no 'd' — use the format NdS (e.g. 2d6).")
            else:
                nums = _re.findall(r'\d+', di)
                if len(nums) < 2:
                    hard_errors.append(
                        f"• Dice entry '{di}' is missing the die count before 'd' — "
                        f"use the format NdS (e.g. 1d{nums[0] if nums else '6'}).")
                elif int(nums[0]) < 1:
                    hard_errors.append(
                        f"• Dice entry '{di}' has a count of 0 — must be at least 1.")

        if hard_errors:
            QMessageBox.critical(
                self, "Cannot Save — Spell Would Crash the Engine",
                "Fix the following before saving:\n\n" + "\n".join(hard_errors),
            )
            return

        # ── Soft warnings (won't crash but will behave incorrectly in combat) ──
        warnings = []

        if combat == "y":
            # Combat spell with no effect set — AI can't categorise it
            if not effect:
                warnings.append(
                    "• No Effect is set. The combat AI won't know what this spell does "
                    "and may skip it.")

            # Attack roll spells with no damage — will roll to hit but deal nothing
            if attack and dice == [""]:
                warnings.append(
                    "• Attack type is set but no Damage Dice are defined. "
                    "The spell will make an attack roll but deal 0 damage.")

            # Damage/healing effect with no dice
            if effect in (DAMAGE_EFFECTS + ["Healing"]) and dice == [""]:
                warnings.append(
                    f"• Effect is '{effect}' but no Damage Dice are defined. "
                    f"The spell will deal 0 damage.")

            # Both attack and save set — save is silently ignored by the engine
            if attack and save:
                warnings.append(
                    f"• Both Attack Type ('{attack}') and Saving Throw ('{save}') are set. "
                    f"The engine only uses the attack roll and will ignore the saving throw.")

            # AoE spell with no attack and no save — engine falls back to attack-roll logic
            if area and not attack and not save and effect not in ("Healing",):
                warnings.append(
                    "• This spell has an Area of Effect but no Attack Type or Saving Throw. "
                    "In combat the engine will try an attack roll against each target's AC, "
                    "which is probably not intended.")

            # Condition CC effect with no save and no attack — same as above
            if effect in CC_EFFECTS and not save and not attack:
                warnings.append(
                    f"• Effect '{effect}' is a condition (crowd control) but no Saving Throw "
                    f"or Attack Type is set. Targets will only be affected if an AC-based "
                    f"attack roll succeeds, which is probably not intended.")

        if warnings:
            msg = ("The spell will be saved, but the following issues may cause it "
                   "to behave incorrectly during combat:\n\n" + "\n".join(warnings)
                   + "\n\nSave anyway?")
            resp = QMessageBox.warning(
                self, "Spell Has Potential Issues",
                msg,
                QMessageBox.Yes | QMessageBox.No,
            )
            if resp != QMessageBox.Yes:
                return

        # ── Overwrite check when renaming ─────────────────────────────────
        if self._editing and self._editing != name:
            if name in self._spells:
                resp = QMessageBox.question(
                    self, "Overwrite?",
                    f"A spell named '{name}' already exists. Overwrite it?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if resp != QMessageBox.Yes:
                    return
            del self._spells[self._editing]
        elif not self._editing and name in self._spells:
            resp = QMessageBox.question(
                self, "Overwrite?",
                f"A spell named '{name}' already exists. Overwrite it?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if resp != QMessageBox.Yes:
                return

        spell_data = {
            "lvl": lvl,
            "time": self._time_combo.currentText(),
            "duration": self._duration_combo.currentText(),
            "range": spell_range,
            "area": area,
            "attack": attack,
            "save": save,
            "effect": effect,
            "concentration": "Y" if self._conc_check.isChecked() else "",
            "classes": classes_str,
            "dice": dice,
            "uniqueDice": "n",
            "combat": combat,
        }

        self._spells[name] = spell_data
        _save_spells(self._spells)

        self._editing = name
        self._refresh_list(keep_selection=name)
        QMessageBox.information(self, "Saved", f"Spell '{name}' saved successfully.")

    def _cancel_edit(self):
        if self._editing:
            self._populate_form(self._editing, self._spells[self._editing])
        else:
            self._clear_form()

    def _delete_spell(self):
        selected = self._list.currentItem()
        if not selected:
            QMessageBox.information(self, "Delete", "Select a spell to delete.")
            return
        name = selected.text()
        resp = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete spell '{name}'? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
        del self._spells[name]
        _save_spells(self._spells)
        self._editing = None
        self._clear_form()
        self._refresh_list()

    # ── Font scaling (called by MainWindow) ───────────────────────────────

    def applyFonts(self):
        pass   # scaling handled at app level


# ── Helpers ───────────────────────────────────────────────────────────────────

def _set_combo(combo: QComboBox, value: str):
    idx = combo.findText(value)
    if idx >= 0:
        combo.setCurrentIndex(idx)
    else:
        combo.setCurrentIndex(0)


def _lbl(text: str, tip: str) -> QLabel:
    """Create a form-row label with a hover tooltip."""
    label = QLabel(text)
    label.setToolTip(tip)
    label.setCursor(Qt.WhatsThisCursor)
    return label


def _populate_effect_combo(combo: QComboBox):
    """Add effect items to *combo* with disabled section-header separators."""
    from PyQt5.QtGui import QStandardItem
    from PyQt5.QtWidgets import QSizePolicy

    combo.addItem("")   # blank / none

    def _add_header(label: str):
        combo.addItem(label)
        model = combo.model()
        item: QStandardItem = model.item(combo.count() - 1)
        item.setEnabled(False)
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        # Slight indent via foreground color to visually distinguish
        from PyQt5.QtGui import QColor
        item.setForeground(QColor("#888888"))

    _add_header("── Damage ──")
    for eff in DAMAGE_EFFECTS:
        combo.addItem(eff)

    _add_header("── Conditions (CC) ──")
    for eff in CC_EFFECTS:
        combo.addItem(eff)

    _add_header("── Other ──")
    for eff in OTHER_EFFECTS:
        combo.addItem(eff)
