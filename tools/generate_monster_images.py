"""
Generate simple geometric placeholder icons for monsters that have no image.

Each icon is a 128×128 PNG with:
  - A category-color background hex shape
  - The monster's initial letter centered in bold white
  - A small category symbol in the bottom-right corner

No copyrighted art is used — all imagery is procedurally generated geometry.
"""
from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent
_MONSTERS_JSON = _ROOT / "actors" / "savedObjs" / "monsters.json"
_OUTPUT_DIR = _ROOT / "App" / "Monsters"
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Category detection (keyword → category)
# ---------------------------------------------------------------------------
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "dragon":     ["dragon", "wyvern", "drake", "dragonborn", "sphinx"],
    "undead":     ["zombie", "skeleton", "ghost", "vampire", "wraith", "specter",
                   "specter", "lich", "mummy", "ghoul", "ghast", "wight", "revenant",
                   "banshee", "shadow"],
    "humanoid":   ["goblin", "orc", "gnoll", "kobold", "hobgoblin", "bugbear",
                   "troll", "giant", "ogre", "acolyte", "bandit", "cultist",
                   "guard", "knight", "mage", "priest", "thug", "wizard",
                   "warrior", "archer", "spy"],
    "beast":      ["wolf", "bear", "boar", "eagle", "lion", "tiger", "ape",
                   "crocodile", "spider", "rat", "snake", "shark", "bat",
                   "panther", "elephant", "rhinoceros", "mammoth", "horse",
                   "frog", "toad", "scorpion", "crab", "octopus", "quipper",
                   "giant", "dire"],
    "monstrosity":["minotaur", "manticore", "basilisk", "gorgon", "harpy",
                   "hydra", "roper", "rust", "ankheg", "behir", "chimera",
                   "bulette", "hook", "kraken", "medusa", "owlbear", "peryton",
                   "phase", "purple", "remorhaz", "tarrasque", "umber"],
    "elemental":  ["elemental", "djinni", "efreeti", "dao", "marid", "gargoyle",
                   "galeb", "xorn", "mephit", "salamander", "invisible"],
    "fiend":      ["devil", "demon", "imp", "quasit", "balor", "pit fiend",
                   "succubus", "incubus", "vrock", "hezrou", "glabrezu",
                   "nalfeshnee", "marilith", "cambion", "rakshasa", "barbed",
                   "bearded", "bone", "chain", "erinyes", "horned", "ice",
                   "lemure", "merregon", "narzugon", "nupperibo"],
    "fey":        ["pixie", "sprite", "satyr", "dryad", "green hag", "night hag",
                   "sea hag", "hag", "blink dog", "displacer"],
    "construct":  ["golem", "animated", "shield guardian", "homunculus",
                   "modron", "quadrone", "pentadrone", "clockwork", "scarecrow"],
    "plant":      ["shambling mound", "vine blight", "needle blight", "twig blight",
                   "violet fungus", "gas spore", "myconid"],
    "celestial":  ["angel", "deva", "planetar", "solar", "couatl", "pegasus",
                   "unicorn", "ki-rin"],
    "aberration": ["mind flayer", "intellect devourer", "aboleth", "beholder",
                   "grell", "chuul", "slaad", "otyugh", "gibbering",
                   "nothic", "flumph", "death kiss", "eye of the deep",
                   "spectator", "gazebo"],
    "ooze":       ["ooze", "slime", "pudding", "cube", "jelly"],
}

# category → (background RGB, symbol char)
_CATEGORY_STYLE: dict[str, tuple[tuple[int, int, int], str]] = {
    "dragon":      ((120, 30,  10),  "🐉"),
    "undead":      ((50,  50,  80),  "💀"),
    "humanoid":    ((60,  90,  130), "👤"),
    "beast":       ((80,  110, 40),  "🐾"),
    "monstrosity": ((100, 50,  110), "👁"),
    "elemental":   ((30,  120, 130), "✦"),
    "fiend":       ((120, 20,  20),  "⛧"),
    "fey":         ((100, 60,  140), "✿"),
    "construct":   ((90,  90,  90),  "⚙"),
    "plant":       ((30,  100, 30),  "🌿"),
    "celestial":   ((140, 120, 30),  "★"),
    "aberration":  ((50,  80,  50),  "⊗"),
    "ooze":        ((60,  120, 80),  "~"),
    "unknown":     ((70,  70,  90),  "?"),
}


def _infer_category(name: str, json_type: str | None) -> str:
    """Infer creature category from monster name keywords or JSON type field."""
    lower = name.lower()

    # JSON type overrides keyword guessing when available
    if json_type:
        t = json_type.lower()
        if t in _CATEGORY_STYLE:
            return t
        for cat, keywords in _CATEGORY_KEYWORDS.items():
            if any(kw in t for kw in keywords):
                return cat

    # Fall back to name keywords
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return cat
    return "unknown"


def _safe_filename(name: str) -> str:
    """Convert monster name to a safe filename (no special chars)."""
    s = re.sub(r"[^\w\s-]", "", name).strip()
    return re.sub(r"\s+", "_", s) + ".png"


def _hex_polygon(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int,
                 fill: tuple, outline: tuple):
    """Draw a flat-top hexagon."""
    pts = [
        (cx + int(r * math.cos(math.radians(30 + 60 * i))),
         cy + int(r * math.sin(math.radians(30 + 60 * i))))
        for i in range(6)
    ]
    draw.polygon(pts, fill=fill, outline=outline)


def _brighten(color: tuple[int, int, int], amount: int = 40) -> tuple[int, int, int]:
    return tuple(min(255, c + amount) for c in color)  # type: ignore[return-value]


def _make_icon(name: str, category: str, size: int = 128) -> Image.Image:
    bg_color, _symbol = _CATEGORY_STYLE.get(category, _CATEGORY_STYLE["unknown"])
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Outer hexagon fill
    _hex_polygon(draw, size // 2, size // 2, size // 2 - 2, bg_color, _brighten(bg_color, 60))

    # Inner lighter hex to give depth
    _hex_polygon(draw, size // 2, size // 2, size // 2 - 12,
                 _brighten(bg_color, 20), _brighten(bg_color, 80))

    # Monster initial letter — large, centered, bold white
    initial = name.strip()[0].upper() if name.strip() else "?"
    # Try a truetype font, fall back to default
    font_size = int(size * 0.52)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

    # Draw with slight shadow
    bbox = draw.textbbox((0, 0), initial, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) // 2 - bbox[0]
    ty = (size - th) // 2 - bbox[1] - 4
    draw.text((tx + 2, ty + 2), initial, fill=(0, 0, 0, 140), font=font)
    draw.text((tx, ty), initial, fill=(255, 255, 255, 230), font=font)

    # Small category abbreviation in bottom-right (ASCII only for compatibility)
    cat_abbrev = category[:3].upper()
    try:
        small_font = ImageFont.truetype("arial.ttf", max(10, int(size * 0.14)))
    except OSError:
        small_font = ImageFont.load_default()
    lbl_bbox = draw.textbbox((0, 0), cat_abbrev, font=small_font)
    lw = lbl_bbox[2] - lbl_bbox[0]
    lh = lbl_bbox[3] - lbl_bbox[1]
    lx = size - lw - 10 - lbl_bbox[0]
    ly = size - lh - 8 - lbl_bbox[1]
    draw.text((lx + 1, ly + 1), cat_abbrev, fill=(0, 0, 0, 120), font=small_font)
    draw.text((lx, ly), cat_abbrev, fill=(220, 220, 220, 200), font=small_font)

    return img


def generate_all():
    with open(_MONSTERS_JSON, encoding="utf-8") as f:
        data: dict = json.load(f)

    updated = 0
    skipped = 0

    for name, monster in data.items():
        existing_img = monster.get("image")
        if existing_img:
            skipped += 1
            continue

        category = _infer_category(name, monster.get("type"))
        filename = _safe_filename(name)
        out_path = _OUTPUT_DIR / filename
        rel_path = f"/App/Monsters/{filename}"

        if not out_path.exists():
            icon = _make_icon(name, category)
            icon.save(str(out_path))

        monster["image"] = rel_path
        updated += 1

    with open(_MONSTERS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Done. Generated/updated: {updated}, Skipped (already had image): {skipped}")
    print(f"Icons saved to: {_OUTPUT_DIR}")


if __name__ == "__main__":
    generate_all()
