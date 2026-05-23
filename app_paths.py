"""
Central path resolution for DMSim.

Works in both development mode and as a PyInstaller frozen bundle.

Usage in any module:
    from app_paths import APP_ROOT

APP_ROOT is always the DMSim project root directory — the folder that contains
`actors/`, `spells/`, `App/`, `model/`, etc.
"""
import sys
from pathlib import Path


def _compute_app_root() -> Path:
    if getattr(sys, 'frozen', False):
        # PyInstaller: all bundled files are extracted to sys._MEIPASS
        return Path(sys._MEIPASS)
    # Development: this file lives at <repo_root>/app_paths.py
    return Path(__file__).resolve().parent


APP_ROOT = _compute_app_root()
