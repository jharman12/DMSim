# encounter_widget.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel


class EncounterWidget(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        label = QLabel("Encounter Window")
        layout.addWidget(label)
        self.setLayout(layout)
