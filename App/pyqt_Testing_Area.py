from PyQt5.QtWidgets import QApplication, QPushButton, QMainWindow
from PyQt5.QtCore import QSize, Qt

import sys

class mainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("My App")

        self.buttonIsChecked = True
        self.button = QPushButton("Press Me")
        self.button.setCheckable(True)
        self.button.clicked.connect(self.theButtonWasClicked)
        #button.clicked.connect(self.theButtonWasToggled)
        self.button.setChecked(self.buttonIsChecked)
        self.button.released.connect(self.theButtonWasReleased)


        self.setFixedSize(QSize(400, 300))
        self.setCentralWidget(self.button)

    def theButtonWasReleased(self):
        self.buttonIsChecked = self.button.isChecked()
        print(self.buttonIsChecked)
    def theButtonWasClicked(self):
        self.button.setText("You already clicked me.")
        self.button.setEnabled(False)

        self.setWindowTitle("A new window title")

    #def theButtonWasToggled(self, checked):
    #   self.buttonIsChecked = checked
    #    print("Checked?", checked)
        

app = QApplication(sys.argv)

window = mainWindow()
window.show()


app.exec()