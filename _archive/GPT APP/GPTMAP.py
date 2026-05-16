import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea, QFrame
)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QSize

# Import your CustomGraphicsView
# from your_file import CustomGraphicsView


class TurnOrderWidget(QWidget):
    def __init__(self):
        super().__init__()

        layout = QHBoxLayout()
        layout.setSpacing(10)

        # Placeholder icons
        placeholder_pix = QPixmap(50, 50)
        placeholder_pix.fill(Qt.darkGray)

        # Current turn icon
        self.current_icon = QLabel()
        self.current_icon.setPixmap(placeholder_pix)
        self.current_icon.setFixedSize(50, 50)

        layout.addWidget(self.current_icon)

        # Next 5 turn icons
        self.next_icons = []
        for _ in range(5):
            lbl = QLabel()
            lbl.setPixmap(placeholder_pix)
            lbl.setFixedSize(40, 40)
            layout.addWidget(lbl)
            self.next_icons.append(lbl)

        layout.addStretch()
        self.setLayout(layout)


class TurnActionPanel(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Action input
        self.action_input = QLineEdit()
        self.action_input.setPlaceholderText("Action")
        layout.addWidget(self.action_input)

        # Targets input
        self.targets_input = QLineEdit()
        self.targets_input.setPlaceholderText("Targets")
        layout.addWidget(self.targets_input)

        # Move coords input
        self.move_input = QLineEdit()
        self.move_input.setPlaceholderText("Move Coords")
        layout.addWidget(self.move_input)

        # Take Turn button
        self.take_turn_button = QPushButton("Take Turn")
        layout.addWidget(self.take_turn_button)

        layout.addStretch()

        self.setLayout(layout)


class EncounterUI(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)

        # ---- Top: Turn Order Indicator ----
        self.turn_order_widget = TurnOrderWidget()
        main_layout.addWidget(self.turn_order_widget)

        # ---- Middle: Map + Right Panel ----
        mid_layout = QHBoxLayout()

        # Map widget
        self.map_view = CustomGraphicsView()
        self.map_view.setFrameShape(QFrame.Box)
        self.map_view.setMinimumSize(900, 700)
        mid_layout.addWidget(self.map_view, 3)

        # Right-side panel
        self.turn_action_panel = TurnActionPanel()
        self.turn_action_panel.setFixedWidth(250)
        mid_layout.addWidget(self.turn_action_panel, 1)

        main_layout.addLayout(mid_layout)

        # ---- Bottom: Start Encounter Button ----
        self.start_button = QPushButton("Start Encounter")
        self.start_button.setFixedHeight(40)
        main_layout.addWidget(self.start_button)

        self.setLayout(main_layout)


# ---------------------------------------
# Testing the UI
# ---------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Dummy map viewer for this test
    #class CustomGraphicsView(QFrame):
    #    pass

    window = EncounterUI()
    window.setWindowTitle("D&D Encounter Manager")
    window.resize(1200, 900)
    window.show()

    sys.exit(app.exec_())
