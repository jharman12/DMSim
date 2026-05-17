"""
Shared dialogs for DMSim App layer.
No engine imports — pure PyQt5.
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QListWidget, QListWidgetItem, QGroupBox, QDialogButtonBox,
    QPushButton,
)
from PyQt5.QtCore import Qt


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
