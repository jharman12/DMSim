from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QHBoxLayout, QTabBar,
    QPushButton, QMessageBox, QLabel, QApplication, QAction, QActionGroup
)
from PyQt5.QtCore import Qt, pyqtSignal, QEvent

from newCharWindow import CharacterEditor, CharacterStore
from monsterWindow import MonsterEditor, MonsterStore
from TestingMap import MapWidget
import pathlib
dmSimPath = str(pathlib.Path(__file__).parent.resolve())[0:-4]
from player import createPartyList
from monster import createMonsterList
from interactiveEncounter import interactiveEncounter

class TextScale:
    XS = 0
    SM = 1
    MD = 2
    LG = 3
    XL = 4

    BASE = 11  # default font size

    SCALE_MAP = {
        XS: 0.85,
        SM: 0.95,
        MD: 1.00,
        LG: 1.15,
        XL: 1.30,
    }

    
    max_BASE = 24
    min_BASE = 6

    @classmethod
    def size(cls, scale):
        return int(cls.BASE * cls.SCALE_MAP[scale])
    
    @classmethod
    def increase(self):
        self.BASE = min(self.BASE + .2, self.max_BASE)

    @classmethod
    def decrease(self):
        self.BASE = max(self.BASE - .2, self.min_BASE)

from PyQt5.QtGui import QFont

def set_font(widget, size, weight=QFont.Normal, monospace=False):
    if monospace:
        font = QFont("Consolas")
    else:
        font = widget.font()

    font.setPointSize(size)
    font.setWeight(weight)
    widget.setFont(font)

class EncounterBuilderTab(QWidget):
    
    def __init__(self, start_callback):
        super().__init__()

        self.start_callback = start_callback

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Encounter Builder"))

        self.start_button = QPushButton("Start Encounter")
        self.start_button.clicked.connect(self.start_callback)

        layout.addWidget(self.start_button)
        layout.addStretch()
    def buildEncounter(self):
        path = dmSimPath + '\\actors\\savedObjs\\'
        myPlayers = createPartyList(['Arabella', 'Root', 'Ephraim',  'Darian'], path = path)
        myPlayers = createPartyList(['Aldric',  'Galleus', 'Adrel', 'VV', 'Cobo'], path = path)
        #badGuys = createMonsterList(["Quenth"] + ["Demogorgon" for i in range(1)], path = path)
        badGuys = createMonsterList(["Myconid Sovereign" for i in range(2)] + ["Myconid Adult" for i in range(6)], path = path)
        myEncounter = interactiveEncounter(myPlayers, [], badGuys, 20, dmSimPath + "\\App\\Maps\\maze Engine.webp")
        return myEncounter
    
    def applyFonts(self):
        mw = self.window()
        if mw is None:
            return

        base = mw.TextScale.size(mw.text_scale)
        set_font(self.start_button, base)

from PyQt5 import QtCore, QtGui, QtWidgets


class TabBar(QtWidgets.QTabBar):
    def tabSizeHint(self, index):
        s = QtWidgets.QTabBar.tabSizeHint(self, index)
        s.transpose()
        return s

    def paintEvent(self, event):
        painter = QtWidgets.QStylePainter(self)
        opt = QtWidgets.QStyleOptionTab()

        for i in range(self.count()):
            self.initStyleOption(opt, i)
            painter.drawControl(QtWidgets.QStyle.CE_TabBarTabShape, opt)
            painter.save()

            s = opt.rect.size()
            s.transpose()
            r = QtCore.QRect(QtCore.QPoint(), s)
            r.moveCenter(opt.rect.center())
            opt.rect = r

            c = self.tabRect(i).center()
            painter.translate(c)
            painter.rotate(90)
            painter.translate(-c)
            painter.drawControl(QtWidgets.QStyle.CE_TabBarTabLabel, opt);
            painter.restore()


class TabWidget(QtWidgets.QTabWidget):
    def __init__(self, *args, **kwargs):
        QtWidgets.QTabWidget.__init__(self, *args, **kwargs)
        self.setTabBar(TabBar(self))
        self.setTabPosition(QtWidgets.QTabWidget.West)


class AppThemes:
    LIGHT = """
    QWidget {
        background-color: #f4f4f4;
        color: #111;
        font-family: Segoe UI;
    }

    QLineEdit, QTextEdit, QComboBox {
        background-color: #ffffff;
        border: 1px solid #bbb;
        padding: 4px;
    }

    QPushButton {
        background-color: #e0e0e0;
        border: 1px solid #999;
        padding: 6px;
    }

    QPushButton:hover {
        background-color: #d6d6d6;
    }

    QProgressBar {
        border: 1px solid #aaa;
        background: #ddd;
    }

    QProgressBar::chunk {
        background: #4caf50;
    }
    """

    DARK = """
    QWidget {
        background-color: #1e1e1e;
        color: #ddd;
        font-family: Segoe UI;
    }

    QLineEdit, QTextEdit, QComboBox {
        background-color: #2a2a2a;
        border: 1px solid #555;
        color: #ddd;
        padding: 4px;
    }

    QPushButton {
        background-color: #333;
        border: 1px solid #555;
        padding: 6px;
        color: #ddd;
    }

    QPushButton:hover {
        background-color: #444;
    }

    QProgressBar {
        border: 1px solid #555;
        background: #2a2a2a;
    }

    QProgressBar::chunk {
        background: #66ccff;
    }
    """


class MainWindow(QMainWindow):
    textScaleChanged = pyqtSignal()
    def __init__(self):
        
        super().__init__()

        self.TextScale = TextScale()
        self.text_scale = TextScale.MD
        self.setTextScale(self.text_scale)

        menubar = self.menuBar()

        view_menu = menubar.addMenu("View")
        theme_menu = view_menu.addMenu("Theme")

        self.light_action = QAction("Light", self, checkable=True)
        self.dark_action = QAction("Dark", self, checkable=True)

        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)

        theme_group.addAction(self.light_action)
        theme_group.addAction(self.dark_action)

        theme_menu.addAction(self.light_action)
        theme_menu.addAction(self.dark_action)

        self.light_action.triggered.connect(lambda: self.setTheme("light"))
        self.dark_action.triggered.connect(lambda: self.setTheme("dark"))


        self.setWindowTitle("DnD Encounter Manager")
        self.resize(1400, 900)

        # ---- Central widget ----
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # ---- Tabs ----
        self.tabs = TabWidget()
        #self.tabs.setTabPosition(QTabWidget.West)
        #self.tabs.tabBar().setShape(QTabBar.RoundedWest)


        #self.tabs.setMovable(False)
        #self.tabs.setUsesScrollButtons(True)
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                padding: 8px 14px;
                min-width: 130px;
                text-align: left;
                transform: rotate(-180deg);   
            }
            QTabBar::tab:selected {
                background: #2a2a2a;
            }
            
            """)

        layout.addWidget(self.tabs)

        # ---- Tabs ----
        store = CharacterStore()
        self.character_editor = CharacterEditor(store)
        self.encounter_builder = EncounterBuilderTab(self.startEncounter)

        self.tabs.addTab(self.character_editor, "Characters")
        self.tabs.addTab(self.encounter_builder, "Encounter Builder")

        # ---- Monsters tab ----
        self.monster_store = MonsterStore()
        self.monster_editor = MonsterEditor(self.monster_store)
        self.tabs.addTab(self.monster_editor, "Monsters")

        # Keep reference so it doesn’t get GC’d
        self.map_window = None

        # signals
        self.textScaleChanged.connect(self.character_editor.applyFonts)
        self.textScaleChanged.connect(self.encounter_builder.applyFonts)
        self.textScaleChanged.connect(self.monster_editor.applyFonts)

        # Install event filter so the main window can capture Ctrl+Wheel
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        self.setTheme("dark")  # default

    def setTextScale(self, scale):
        self.text_scale = scale
        base_size = TextScale.size(scale)

        def apply(widget):
            font = widget.font()
            font.setPointSize(base_size)
            widget.setFont(font)

            for child in widget.findChildren(QWidget):
                apply(child)

        apply(self)

        # notify child widgets that care about more targeted font application
        try:
            self.textScaleChanged.emit()
        except Exception:
            pass

    def setTheme(self, theme_name):
        app = QApplication.instance()

        if theme_name == "dark":
            app.setStyleSheet(AppThemes.DARK)
            self.dark_action.setChecked(True)
        else:
            app.setStyleSheet(AppThemes.LIGHT)
            self.light_action.setChecked(True)

        self.current_theme = theme_name

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            if QApplication.keyboardModifiers() & Qt.ControlModifier:
                delta = event.angleDelta().y()

                if delta > 0:
                    self.TextScale.increase()
                else:
                    self.TextScale.decrease()

                # Re-apply the current scale (uses TextScale.BASE internally)
                self.setTextScale(self.text_scale)
                return True  # stop normal scrolling

        return False


    def startEncounter(self):
        encounter = self.encounter_builder.buildEncounter()
        if not encounter:
            QMessageBox.warning(self, "Error", "Invalid encounter setup")
            return

        # Close old map window if it exists
        if self.map_window:
            self.map_window.close()

        self.map_window = MapWidget(encounter)
        self.map_window.show()

app = QApplication([])

window = MainWindow()
window.show()

app.exec()


