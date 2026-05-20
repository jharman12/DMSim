"""
Shared dialogs for DMSim App layer.
No engine imports — pure PyQt5.
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QListWidget, QListWidgetItem, QGroupBox, QDialogButtonBox,
    QPushButton, QFrame, QCheckBox, QScrollArea, QWidget,
    QSizePolicy, QAbstractSpinBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


def _make_checkable_list(actors: list, checked_names: set) -> QListWidget:
    """Build a QListWidget whose items toggle when either the checkbox or the name is clicked."""
    lst = QListWidget()
    for actor in actors:
        item = QListWidgetItem(actor.name)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(
            Qt.Checked if actor.name in checked_names else Qt.Unchecked
        )
        lst.addItem(item)

    def _toggle_item(clicked_item):
        new_state = Qt.Unchecked if clicked_item.checkState() == Qt.Checked else Qt.Checked
        clicked_item.setCheckState(new_state)

    lst.itemClicked.connect(_toggle_item)
    return lst


def _make_actor_group(title: str, actors: list, checked_names: set, all_items: list) -> QGroupBox:
    """Return a QGroupBox containing a Select All button and a checkable actor list.

    Appends the list's QListWidgetItems into all_items for later retrieval.
    """
    box = QGroupBox(title)
    box_layout = QVBoxLayout(box)

    lst = _make_checkable_list(actors, checked_names)
    for i in range(lst.count()):
        all_items.append(lst.item(i))

    # --- Select All / Deselect All toggle button ---
    select_btn = QPushButton("Select All")

    def _update_btn_label():
        all_checked = all(lst.item(i).checkState() == Qt.Checked for i in range(lst.count()))
        select_btn.setText("Deselect All" if all_checked else "Select All")

    def _on_select_all():
        all_checked = all(lst.item(i).checkState() == Qt.Checked for i in range(lst.count()))
        new_state = Qt.Unchecked if all_checked else Qt.Checked
        for i in range(lst.count()):
            lst.item(i).setCheckState(new_state)
        _update_btn_label()

    # Keep button label in sync when individual items are toggled too
    lst.itemClicked.connect(lambda _: _update_btn_label())

    select_btn.clicked.connect(_on_select_all)
    _update_btn_label()   # set correct initial label

    box_layout.addWidget(select_btn)
    box_layout.addWidget(lst)
    return box


class ManualRollDialog(QDialog):
    """
    Modal dialog that prompts a player to physically roll dice and enter the results.

    Parameters
    ----------
    actor_name : str
    context    : str   description of what is being rolled, e.g. 'Dex save (DC 15)'
    n          : int   number of dice
    sides      : int   die size (e.g. 20, 6, 8)
    """

    def __init__(self, actor_name: str, context: str, n: int, sides: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Manual Roll - {actor_name}")
        self.setMinimumWidth(320)
        self.setWindowFlag(Qt.WindowStaysOnTopHint)

        # d20 rolls (attack checks, saves) need individual values for
        # advantage/disadvantage; everything else just needs the total.
        self._per_die = (sides == 20)

        layout = QVBoxLayout(self)

        header = QLabel(f"<b>{actor_name}</b>")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        ctx_label = QLabel(context)
        ctx_label.setAlignment(Qt.AlignCenter)
        ctx_label.setWordWrap(True)
        layout.addWidget(ctx_label)

        dice_box = QGroupBox()
        dice_layout = QHBoxLayout(dice_box)
        self._spins = []

        if self._per_die:
            instr = QLabel(f"Roll <b>{n}d{sides}</b> and enter each result:")
            instr.setAlignment(Qt.AlignCenter)
            layout.addWidget(instr)
            for i in range(n):
                col = QVBoxLayout()
                lbl = QLabel(f"d{sides}" if n == 1 else f"Die {i + 1}")
                lbl.setAlignment(Qt.AlignCenter)
                spin = QSpinBox()
                spin.setMinimum(1)
                spin.setMaximum(sides)
                spin.setValue(1)
                spin.setMinimumWidth(60)
                col.addWidget(lbl)
                col.addWidget(spin)
                dice_layout.addLayout(col)
                self._spins.append(spin)
        else:
            instr = QLabel(f"Roll <b>{n}d{sides}</b> and enter the total:")
            instr.setAlignment(Qt.AlignCenter)
            layout.addWidget(instr)
            spin = QSpinBox()
            spin.setMinimum(n)           # minimum 1 per die
            spin.setMaximum(n * sides)
            spin.setValue(n)
            spin.setMinimumWidth(80)
            col = QVBoxLayout()
            lbl = QLabel("Total")
            lbl.setAlignment(Qt.AlignCenter)
            col.addWidget(lbl)
            col.addWidget(spin)
            dice_layout.addLayout(col)
            self._spins.append(spin)

        layout.addWidget(dice_box)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_rolls(self) -> list:
        """Return list of int results entered by the user.
        For per-die mode (d20): one value per die.
        For total mode (non-d20): a single-element list containing the total,
        which is correct when the caller sums the result.
        """
        return [spin.value() for spin in self._spins]


class ManualRollersDialog(QDialog):
    """
    Dialog for selecting which actors roll dice manually.
    Actors are shown in two side-by-side columns: Players and Monsters / NPCs.

    Parameters
    ----------
    all_actors    : list[Actor]   all actors in the encounter
    manual_actors : set[str]      names of currently manual actors
    """

    def __init__(self, all_actors: list, manual_actors: set, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manual Dice Rollers")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        info = QLabel(
            "Check the actors whose dice rolls you want to enter manually.\n"
            "When it's their turn the game will pause and ask for each roll."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        players  = [a for a in all_actors if getattr(a, 'is_player', False)]
        monsters = [a for a in all_actors if not getattr(a, 'is_player', False)]

        self._all_items = []

        outer = QHBoxLayout()

        if players:
            outer.addWidget(_make_actor_group("Players", players, manual_actors, self._all_items))
        if monsters:
            outer.addWidget(_make_actor_group("Monsters / NPCs", monsters, manual_actors, self._all_items))
        layout.addLayout(outer)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_selected(self) -> set:
        """Return set of actor names that should roll manually."""
        return {
            item.text()
            for item in self._all_items
            if item.checkState() == Qt.Checked
        }


class ManualActionsDialog(QDialog):
    """
    Dialog for selecting which actors have their action choices made by the user.
    Actors in this list will show the interactive turn panel (move, pick action, pick target)
    instead of having the AI engine decide automatically.

    Players are checked by default; monsters are unchecked by default.
    """

    def __init__(self, all_actors: list, interactive_actors: set, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manual Action Control")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        info = QLabel(
            "Check the actors whose actions you want to control manually.\n"
            "Checked actors will show the action panel during their turn.\n"
            "Unchecked actors will have their actions decided by the AI."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        players  = [a for a in all_actors if getattr(a, 'is_player', False)]
        monsters = [a for a in all_actors if not getattr(a, 'is_player', False)]

        self._all_items = []

        outer = QHBoxLayout()

        if players:
            outer.addWidget(_make_actor_group("Players", players, interactive_actors, self._all_items))
        if monsters:
            outer.addWidget(_make_actor_group("Monsters / NPCs", monsters, interactive_actors, self._all_items))
        layout.addLayout(outer)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_selected(self) -> set:
        """Return set of actor names whose actions should be user-controlled."""
        return {
            item.text()
            for item in self._all_items
            if item.checkState() == Qt.Checked
        }


class SetStatsDialog(QDialog):
    """
    Dark-themed stat editor dialog styled to match the right-click character popup.
    Sections: Health (with live bar), Combat Stats, Ability Scores, Conditions.
    """

    _ABILITIES = ["Strength", "Dexterity", "Constitution",
                  "Intelligence", "Wisdom", "Charisma"]

    _CONDITIONS = [
        "Blinded", "Charmed", "Deafened", "Exhausted", "Frightened",
        "Grappled", "Incapacitated", "Invisible", "Paralyzed", "Petrified",
        "Poisoned", "Prone", "Restrained", "Stunned", "Unconscious",
    ]

    # ── Shared popup stylesheet ──────────────────────────────────────────
    _SHEET = """
        QDialog {
            background-color: #1e1e2e;
            border: 1px solid #444;
            border-radius: 8px;
        }
        QLabel        { background: transparent; color: #eee; }
        QFrame#divider { background: #444; max-height: 1px; border: none; }
        QSpinBox {
            background: #2a2a3a; color: #eee;
            border: 1px solid #555; border-radius: 4px;
            padding: 2px 6px; font-size: 14px;
        }
        QSpinBox:focus { border: 1px solid #8899cc; }
        QCheckBox { color: #eee; font-size: 14px; }
        QCheckBox::indicator {
            width: 14px; height: 14px;
            border: 1px solid #555; border-radius: 3px;
            background: #2a2a3a;
        }
        QCheckBox::indicator:checked {
            background: #5577cc; border: 1px solid #8899cc;
        }
        QPushButton#saveBtn {
            background: #2a3a5a; color: #aaddff;
            border: 1px solid #446688; border-radius: 4px;
            padding: 6px 14px; font-size: 14px;
        }
        QPushButton#saveBtn:hover { background: #2a4a6a; }
        QPushButton#cancelBtn {
            background: #2a2a3a; color: #888;
            border: 1px solid #444; border-radius: 4px;
            padding: 6px 14px; font-size: 14px;
        }
        QPushButton#cancelBtn:hover { color: #ccc; }
        QPushButton#condToggle {
            background: transparent; color: #aaa;
            border: none; font-size: 14px;
            text-align: left; padding: 2px 0;
        }
        QPushButton#condToggle:hover { color: #fff; }
    """

    def __init__(self, actor, parent=None):
        super().__init__(parent)
        self.actor = actor
        self.setWindowTitle(f"Set Stats — {actor.name}")
        self.setMinimumWidth(340)
        self.setStyleSheet(self._SHEET)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)

        self._spins = {}
        self._cond_checks = {}
        self._conds_visible = False

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 14)
        root.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        name_lbl = QLabel(f"<b>{actor.name}</b>")
        name_lbl.setStyleSheet("color: #ffffff; font-size: 18px;")
        hdr.addWidget(name_lbl, stretch=1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #aaa;
                          border: none; font-size: 16px; }
            QPushButton:hover { color: #fff; }
        """)
        close_btn.clicked.connect(self.reject)
        hdr.addWidget(close_btn)
        root.addLayout(hdr)

        root.addSpacing(6)
        root.addWidget(self._divider())
        root.addSpacing(6)

        # ── Health ──────────────────────────────────────────────────────
        hp_row = QHBoxLayout()
        hp_lbl = QLabel("HP")
        hp_lbl.setStyleSheet("color: #aaa; font-size: 16px;")
        hp_row.addWidget(hp_lbl)
        hp_row.addStretch()

        self._spins["health"] = self._spin(int(actor.health), 0, int(actor.maxHealth))
        slash = QLabel("/")
        slash.setStyleSheet("color: #666; font-size: 16px;")
        self._spins["maxHealth"] = self._spin(int(actor.maxHealth), 1, 9999)
        for w in (self._spins["health"], slash, self._spins["maxHealth"]):
            hp_row.addWidget(w)
        root.addLayout(hp_row)

        root.addSpacing(4)
        self._bar_bg = QFrame()
        self._bar_bg.setFixedHeight(10)
        self._bar_bg.setStyleSheet("QFrame { background: #333; border-radius: 5px; }")
        bar_inner = QHBoxLayout(self._bar_bg)
        bar_inner.setContentsMargins(0, 0, 0, 0)
        bar_inner.setSpacing(0)
        self._bar_fill = QFrame()
        self._bar_fill.setFixedHeight(10)
        self._bar_spacer = QFrame()
        self._bar_spacer.setStyleSheet("background: transparent;")
        bar_inner.addWidget(self._bar_fill)
        bar_inner.addWidget(self._bar_spacer)
        root.addWidget(self._bar_bg)

        self._spins["health"].valueChanged.connect(self._refresh_bar)
        self._spins["maxHealth"].valueChanged.connect(self._on_maxhp_change)
        self._refresh_bar()

        root.addSpacing(8)
        root.addWidget(self._divider())
        root.addSpacing(8)

        # ── Combat stats: AC + Speed ─────────────────────────────────────
        stat_row = QHBoxLayout()
        stat_row.setSpacing(16)
        for label, key, val, lo, hi in [
            ("Armour Class", "ac",    int(actor.ac),    1,  30),
            ("Speed (ft)",   "speed", int(actor.speed), 0, 120),
        ]:
            col = QVBoxLayout()
            col.setSpacing(2)
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #888; font-size: 13px;")
            lbl.setAlignment(Qt.AlignCenter)
            spin = self._spin(val, lo, hi)
            spin.setFixedWidth(80)
            spin.setAlignment(Qt.AlignCenter)
            col.addWidget(lbl)
            col.addWidget(spin, alignment=Qt.AlignHCenter)
            stat_row.addLayout(col)
            self._spins[key] = spin
        root.addLayout(stat_row)

        root.addSpacing(8)
        root.addWidget(self._divider())
        root.addSpacing(8)

        # ── Ability scores ───────────────────────────────────────────────
        mods = getattr(actor, 'modDict', {})
        if mods:
            ab_lbl = QLabel("Ability Scores")
            ab_lbl.setStyleSheet("color: #aaa; font-size: 13px;")
            root.addWidget(ab_lbl)
            root.addSpacing(4)

            for row_start in (0, 3):
                row = QHBoxLayout()
                row.setSpacing(8)
                for ability in self._ABILITIES[row_start:row_start + 3]:
                    score = int(mods.get(ability, 10))
                    mod_val = (score - 10) // 2
                    col = QVBoxLayout()
                    col.setSpacing(1)

                    a_lbl = QLabel(ability[:3].upper())
                    a_lbl.setStyleSheet("color: #777; font-size: 12px;")
                    a_lbl.setAlignment(Qt.AlignCenter)

                    spin = self._spin(score, 1, 30)
                    spin.setFixedWidth(64)
                    spin.setAlignment(Qt.AlignCenter)

                    self._mod_lbl = QLabel(f"{'+' if mod_val >= 0 else ''}{mod_val}")
                    self._mod_lbl.setStyleSheet("color: #aaa; font-size: 12px;")
                    self._mod_lbl.setAlignment(Qt.AlignCenter)
                    mod_display = self._mod_lbl  # capture for closure

                    def _update_mod(val, lbl=mod_display):
                        m = (val - 10) // 2
                        lbl.setText(f"{'+' if m >= 0 else ''}{m}")
                    spin.valueChanged.connect(_update_mod)

                    col.addWidget(a_lbl)
                    col.addWidget(spin, alignment=Qt.AlignHCenter)
                    col.addWidget(mod_display)
                    row.addLayout(col)
                    self._spins[f"mod_{ability}"] = spin

                root.addLayout(row)
                root.addSpacing(4)

            root.addWidget(self._divider())
            root.addSpacing(4)

        # ── Conditions (collapsible) ─────────────────────────────────────
        active = getattr(actor, 'active_conditions', set())

        cond_toggle = QPushButton("▶  Conditions")
        cond_toggle.setObjectName("condToggle")
        cond_toggle.setCursor(Qt.PointingHandCursor)
        root.addWidget(cond_toggle)

        self._cond_panel = QFrame()
        self._cond_panel.setVisible(False)
        cond_layout = QVBoxLayout(self._cond_panel)
        cond_layout.setContentsMargins(4, 4, 4, 4)
        cond_layout.setSpacing(4)

        # Two-column grid
        cond_grid = QHBoxLayout()
        left_col  = QVBoxLayout()
        right_col = QVBoxLayout()
        for i, cond in enumerate(self._CONDITIONS):
            cb = QCheckBox(cond)
            cb.setChecked(cond in active)
            self._cond_checks[cond] = cb
            (left_col if i % 2 == 0 else right_col).addWidget(cb)
        cond_grid.addLayout(left_col)
        cond_grid.addLayout(right_col)
        cond_layout.addLayout(cond_grid)
        root.addWidget(self._cond_panel)

        def _toggle_conds():
            self._conds_visible = not self._conds_visible
            self._cond_panel.setVisible(self._conds_visible)
            cond_toggle.setText(
                ("▼" if self._conds_visible else "▶") + "  Conditions"
            )
            self.adjustSize()
        cond_toggle.clicked.connect(_toggle_conds)

        root.addSpacing(10)

        # ── Footer buttons ───────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("cancelBtn")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.setObjectName("saveBtn")
        save.clicked.connect(self.accept)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        root.addLayout(btn_row)

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _divider():
        f = QFrame()
        f.setObjectName("divider")
        f.setFrameShape(QFrame.HLine)
        f.setFixedHeight(1)
        return f

    @staticmethod
    def _spin(value: int, lo: int, hi: int) -> QSpinBox:
        s = QSpinBox()
        s.setMinimum(lo)
        s.setMaximum(hi)
        s.setValue(value)
        s.setButtonSymbols(QAbstractSpinBox.NoButtons)
        return s

    def _on_maxhp_change(self, val):
        self._spins["health"].setMaximum(val)
        self._refresh_bar()

    def _refresh_bar(self):
        hp  = self._spins["health"].value()
        mhp = self._spins["maxHealth"].value()
        pct = max(hp / max(mhp, 1), 0.0)
        fill = max(int(pct * 100), 0)
        if pct > 0.5:
            color = "#4caf50"
        elif pct > 0.25:
            color = "#ff9800"
        else:
            color = "#f44336"
        self._bar_fill.setStyleSheet(
            f"QFrame {{ background: {color}; border-radius: 5px; }}"
        )
        lay = self._bar_bg.layout()
        lay.setStretch(0, fill)
        lay.setStretch(1, max(100 - fill, 0))

    # ── Apply ────────────────────────────────────────────────────────────

    def apply(self):
        """Write dialog values back onto the actor."""
        self.actor.health    = self._spins["health"].value()
        self.actor.maxHealth = self._spins["maxHealth"].value()
        self.actor.ac        = self._spins["ac"].value()
        self.actor.speed     = self._spins["speed"].value()
        if hasattr(self.actor, 'maxSpeed'):
            self.actor.maxSpeed = max(self.actor.maxSpeed, self.actor.speed)

        mods = getattr(self.actor, 'modDict', {})
        for ability in self._ABILITIES:
            key = f"mod_{ability}"
            if key in self._spins and ability in mods:
                mods[ability] = self._spins[key].value()

        active = getattr(self.actor, 'active_conditions', None)
        if active is not None:
            for cond, cb in self._cond_checks.items():
                if cb.isChecked():
                    active.add(cond)
                else:
                    active.discard(cond)


class DamageTrackerDialog(QDialog):
    """Non-modal popup showing cumulative damage dealt per player actor this combat."""

    _BAR_MAX_WIDTH = 180

    def __init__(self, party: list, parent=None):
        super().__init__(parent, Qt.Window | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("📊 Damage Tracker")
        self.setMinimumWidth(340)
        self._party = party  # live list; entries never change, only _damage_dealt attr does

        self._rows: list[dict] = []   # one entry per player: {name_lbl, dmg_lbl, bar_fill, bar_bg}

        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(12, 10, 12, 10)

        title = QLabel("Damage Dealt — This Combat")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #e0e0e0;")
        root.addWidget(title)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color: #555;")
        root.addWidget(divider)

        self._rows_container = QVBoxLayout()
        self._rows_container.setSpacing(4)
        root.addLayout(self._rows_container)

        self._build_rows()

        root.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.hide)
        close_btn.setFixedHeight(28)
        root.addWidget(close_btn, alignment=Qt.AlignRight)

        self.setStyleSheet("""
            QDialog { background: #2b2b2b; }
            QLabel  { color: #e0e0e0; font-size: 13px; }
        """)

    def _build_rows(self):
        """Create one row widget per player."""
        for actor in self._party:
            if not getattr(actor, 'is_player', False):
                continue

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 2, 0, 2)
            row_layout.setSpacing(8)

            # Name label (fixed width so damage column aligns)
            name_lbl = QLabel(actor.name)
            name_lbl.setMinimumWidth(110)
            name_lbl.setStyleSheet("font-weight: bold; color: #c8d8f0;")
            row_layout.addWidget(name_lbl)

            # Damage number
            dmg_lbl = QLabel("0")
            dmg_lbl.setMinimumWidth(48)
            dmg_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            dmg_lbl.setStyleSheet("font-family: monospace; color: #ff9966;")
            row_layout.addWidget(dmg_lbl)

            # Bar background
            bar_bg = QFrame()
            bar_bg.setFixedHeight(14)
            bar_bg.setFixedWidth(self._BAR_MAX_WIDTH)
            bar_bg.setStyleSheet("background: #444; border-radius: 4px;")
            bar_layout = QHBoxLayout(bar_bg)
            bar_layout.setContentsMargins(0, 0, 0, 0)
            bar_layout.setSpacing(0)

            bar_fill = QFrame()
            bar_fill.setFixedHeight(14)
            bar_fill.setFixedWidth(0)
            bar_fill.setStyleSheet("background: #e05030; border-radius: 4px;")
            bar_layout.addWidget(bar_fill)
            bar_layout.addStretch()

            row_layout.addWidget(bar_bg)
            row_layout.addStretch()

            self._rows_container.addWidget(row_widget)
            self._rows.append({
                'actor': actor,
                'dmg_lbl': dmg_lbl,
                'bar_fill': bar_fill,
            })

    def refresh(self):
        """Update all rows from the actors' current _damage_dealt values."""
        if not self._rows:
            return
        max_dmg = max((r['actor']._damage_dealt for r in self._rows), default=0)
        max_dmg = max(max_dmg, 1)
        for row in self._rows:
            dmg = getattr(row['actor'], '_damage_dealt', 0)
            row['dmg_lbl'].setText(str(int(dmg)))
            fill_w = int((dmg / max_dmg) * self._BAR_MAX_WIDTH)
            row['bar_fill'].setFixedWidth(fill_w)

