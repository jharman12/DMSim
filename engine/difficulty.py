"""
D&D 5e encounter difficulty calculator.

All logic here is pure Python — no Qt, no model dependencies.
"""

# CR → approximate XP value (SRD table)
_CR_TO_XP = {
    0: 10, 0.125: 25, 0.25: 50, 0.5: 100,
    1: 200, 2: 450, 3: 700, 4: 1100, 5: 1800,
    6: 2300, 7: 2900, 8: 3900, 9: 5000, 10: 5900,
    11: 7200, 12: 8400, 13: 10000, 14: 11500, 15: 13000,
    16: 15000, 17: 18000, 18: 20000, 19: 22000, 20: 25000,
    21: 33000, 22: 41000, 23: 50000, 24: 62000, 30: 155000,
}

# XP thresholds per character per level (Easy, Medium, Hard, Deadly)
_XP_THRESHOLDS_PER_LEVEL = {
    1:  (25,  50,  75,  100),
    2:  (50,  100, 150, 200),
    3:  (75,  150, 225, 400),
    4:  (125, 250, 375, 500),
    5:  (250, 500, 750, 1100),
    6:  (300, 600, 900, 1400),
    7:  (350, 750, 1100, 1700),
    8:  (450, 900, 1400, 2100),
    9:  (550, 1100, 1600, 2400),
    10: (600, 1200, 1900, 2800),
    11: (800, 1600, 2400, 3600),
    12: (1000, 2000, 3000, 4500),
    13: (1100, 2200, 3400, 5100),
    14: (1250, 2500, 3800, 5700),
    15: (1400, 2800, 4300, 6400),
    16: (1600, 3200, 4800, 7200),
    17: (2000, 3900, 5900, 8800),
    18: (2100, 4200, 6300, 9500),
    19: (2400, 4900, 7300, 10900),
    20: (2800, 5700, 8500, 12700),
}

# Enemy-count multipliers for action-economy advantage
_COUNT_MULTIPLIERS = [
    (1,   1.0),
    (2,   1.5),
    (6,   2.0),
    (10,  2.5),
    (14,  3.0),
    (float("inf"), 4.0),
]


def parse_cr(cr_str) -> float:
    """Convert a CR string like '1/4' or '5' to a float."""
    s = str(cr_str).strip()
    if "/" in s:
        parts = s.split("/")
        try:
            return float(parts[0]) / float(parts[1])
        except (ValueError, ZeroDivisionError):
            return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def enemy_count_multiplier(enemy_count: int, party_size: int) -> float:
    """Return the action-economy multiplier for *enemy_count* vs *party_size*."""
    # SRD adjusts the bracket upward for small or large parties
    adjusted = enemy_count
    if party_size < 3:
        # Bump up one bracket
        adjusted = max(adjusted, 2)
    elif party_size > 5:
        # Bump down one bracket (but never below 1 enemy)
        adjusted = max(adjusted - 1, 1)

    for threshold, mult in _COUNT_MULTIPLIERS:
        if adjusted <= threshold:
            return mult
    return 4.0


def xp_thresholds(party_size: int, avg_level: int) -> tuple:
    """
    Return (easy, medium, hard, deadly) total XP thresholds for the party.
    """
    level = max(1, min(20, avg_level))
    per_char = _XP_THRESHOLDS_PER_LEVEL.get(level, _XP_THRESHOLDS_PER_LEVEL[20])
    return tuple(v * party_size for v in per_char)


def calculate_difficulty(party_size: int, avg_level: int, enemy_crs: list) -> str:
    """
    Return a difficulty string: 'Trivial', 'Easy', 'Medium', 'Hard', or 'Deadly'.

    Parameters
    ----------
    party_size : int
    avg_level  : int   average party level
    enemy_crs  : list  list of CR values (float or parseable strings)
    """
    if party_size == 0:
        return "—"
    if not enemy_crs:
        return "None"

    total_xp = sum(_CR_TO_XP.get(round(parse_cr(cr) * 8) / 8, 0) for cr in enemy_crs)
    mult = enemy_count_multiplier(len(enemy_crs), party_size)
    adjusted_xp = total_xp * mult

    easy, medium, hard, deadly = xp_thresholds(party_size, avg_level)

    if adjusted_xp >= deadly:
        return "Deadly"
    if adjusted_xp >= hard:
        return "Hard"
    if adjusted_xp >= medium:
        return "Medium"
    if adjusted_xp >= easy:
        return "Easy"
    return "Trivial"
