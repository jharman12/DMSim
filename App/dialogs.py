"""
Shared dialogs for DMSim App layer.
No engine imports — pure PyQt5.
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QListWidget, QListWidgetItem, QGroupBox, QDialogButtonBox,
)
from PyQt5.QtCore import Qt


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

        def _make_group(title: str, actors: list) -> QGroupBox:
            box = QGroupBox(title)
            box_layout = QVBoxLayout(box)
            lst = QListWidget()
            for actor in actors:
                item = QListWidgetItem(actor.name)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(
                    Qt.Checked if actor.name in manual_actors else Qt.Unchecked
                )
                lst.addItem(item)
                self._all_items.append(item)
            box_layout.addWidget(lst)
            return box

        if players:
            outer.addWidget(_make_group("Players", players))
        if monsters:
            outer.addWidget(_make_group("Monsters / NPCs", monsters))
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
