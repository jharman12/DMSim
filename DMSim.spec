# -*- mode: python ; coding: utf-8 -*-
"""
DMSim PyInstaller spec — one-directory build.

Output: dist/DMSim/
  DMSim.exe            — launcher
  _internal/           — Python runtime + all bundled modules + data files

Run:
    pyinstaller DMSim.spec
"""
from pathlib import Path
import os

root = Path(SPECPATH)          # repo root (same directory as this .spec file)
app  = root / 'App'


# ---------------------------------------------------------------------------
# Data files to bundle (source, destination-inside-_internal)
# ---------------------------------------------------------------------------
datas = [
    # Application icon
    (str(root / 'DM_Sim_Icon.png'),  '.'),
    (str(root / 'download.png'),      '.'),

    # App assets
    (str(app / 'unknown.jpg'),        'App'),
    (str(app / 'Maps'),               'App/Maps'),
    (str(app / 'Monsters'),           'App/Monsters'),
    (str(app / 'Characters'),         'App/Characters'),

    # Actor / spell JSON data
    (str(root / 'actors' / 'savedObjs' / 'monsters.json'),   'actors/savedObjs'),
    (str(root / 'actors' / 'savedObjs' / 'newChars.json'),   'actors/savedObjs'),
    (str(root / 'actors' / 'savedObjs' / 'encounters.json'), 'actors/savedObjs'),
    (str(root / 'actors' / 'savedObjs' / 'characters.json'), 'actors/savedObjs'),
    (str(root / 'spells' / 'spellList.json'),                 'spells'),
]


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    [str(app / 'main.py')],
    pathex=[str(root), str(app)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'scipy.spatial',
        'scipy.spatial.transform',
        'scipy._lib.messagestream',
        'scipy._lib._util',
        'numpy',
        'numpy.core',
        'PyQt5',
        'PyQt5.QtWidgets',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtPrintSupport',
        'PyQt5.sip',
        # Our own modules imported via sys.path tricks
        'app_paths',
        'model.map',
        'model.player',
        'model.monster',
        'model.actor',
        'model.weapon',
        'model.Interactive.interactiveEncounter',
        'model.Simulation.encounterSim',
        'model.Simulation.encounterMain',
        'engine.combat',
        'engine.targeting',
        'engine.dice',
        'engine.utils',
        'engine.persistent',
        'engine.size_utils',
        'engine.difficulty',
        'controller',
        'dialogs',
        'newCharWindow',
        'monsterWindow',
        'spellEditor',
        'TestingMap',
    ],
    excludes=['matplotlib', 'pandas', 'tkinter'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DMSim',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(root / 'DM_Sim_Icon.png'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DMSim',
)
