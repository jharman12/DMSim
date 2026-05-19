"""
D&D 5e actor size helpers for the hex map.

Size → hex footprint count:
  Tiny / Small / Medium  → 1 hex
  Large                  → 3 hexes  (triangle)
  Huge                   → 7 hexes  (center + ring-1)
  Gargantuan             → 12 hexes (center + ring-1 + partial ring-2)
"""
from __future__ import annotations
from collections import deque

SIZE_HEX_COUNT: dict[str, int] = {
    'Tiny':       1,
    'Small':      1,
    'Medium':     1,
    'Large':      3,
    'Huge':       7,
    'Gargantuan': 12,
}

# Legacy int size values (size=25 was used for all actors previously)
_INT_TO_CAT: list[tuple[int, str]] = [
    (25,  'Medium'),
    (50,  'Large'),
    (100, 'Huge'),
    (200, 'Gargantuan'),
]


def get_size_cat(actor) -> str:
    """Return the D&D 5e size-category string for an actor."""
    s = getattr(actor, 'size', 25)
    if isinstance(s, str) and s in SIZE_HEX_COUNT:
        return s
    if isinstance(s, (int, float)):
        for threshold, cat in _INT_TO_CAT:
            if s <= threshold:
                return cat
    return 'Medium'


def hex_count(actor) -> int:
    """How many hexes this actor's footprint occupies."""
    return SIZE_HEX_COUNT.get(get_size_cat(actor), 1)


def _hex_dist(a: tuple, b: tuple) -> float:
    """Doubled-height hex distance."""
    drow = abs(a[1] - b[1])
    dcol = abs(a[0] - b[0])
    return dcol + max(0.0, (drow - dcol) / 2)


def compute_footprint(anchor_coord: tuple, size_cat: str, map_obj) -> list:
    """
    Return the list of map coords forming the actor's footprint, anchor first.
    Uses BFS outward from anchor, taking the nearest available hexes.
    Only returns hexes that exist in map_obj.arrayCenters.
    """
    n = SIZE_HEX_COUNT.get(size_cat, 1)
    if n == 1:
        return [anchor_coord]

    all_coords = list(map_obj.arrayCenters)
    coord_set = set(all_coords)

    included = [anchor_coord]
    visited = {anchor_coord}
    queue = deque([anchor_coord])

    while queue and len(included) < n:
        cur = queue.popleft()
        candidates = sorted(
            [c for c in all_coords if _hex_dist(cur, c) == 1 and c not in visited],
            key=lambda c: (_hex_dist(anchor_coord, c), c)
        )
        for nb in candidates:
            if len(included) >= n:
                break
            visited.add(nb)
            included.append(nb)
            queue.append(nb)

    return included


def get_actor_anchor(actor, map_obj):
    """Return the anchor coord for this actor (primary hex)."""
    anchor = getattr(actor, '_anchor_coord', None)
    if anchor is not None and map_obj.arrayCenters.get(anchor) is actor:
        return anchor
    # Fallback: first coord found
    for coord, val in map_obj.arrayCenters.items():
        if val is actor:
            actor._anchor_coord = coord
            return coord
    return None


def get_actor_anchor_index(actor, map_obj) -> int | None:
    """Return the index of the actor's anchor coord in arrayCenters."""
    anchor = get_actor_anchor(actor, map_obj)
    if anchor is None:
        return None
    return list(map_obj.arrayCenters).index(anchor)


def get_actor_footprint_coords(actor, map_obj) -> list:
    """Return all coords currently occupied by this actor."""
    return [c for c, v in map_obj.arrayCenters.items() if v is actor]


def can_place_footprint(anchor_coord: tuple, size_cat: str, map_obj, actor=None) -> bool:
    """
    Return True if the footprint rooted at anchor_coord is entirely free
    (empty or already owned by `actor`).
    """
    for c in compute_footprint(anchor_coord, size_cat, map_obj):
        val = map_obj.arrayCenters.get(c)
        if val is None:
            return False
        if val != '' and val is not actor:
            return False
    return True


def actor_min_distance(from_index: int, target_actor, map_obj) -> float:
    """
    Minimum hex distance from `from_index` to any hex occupied by `target_actor`.
    Use this for range checks against large targets.
    """
    coords = list(map_obj.arrayCenters)
    footprint = get_actor_footprint_coords(target_actor, map_obj)
    if not footprint:
        return 999
    return min(map_obj.distanceCalc(from_index, coords.index(c)) for c in footprint)


def actor_to_actor_distance(attacker, target, map_obj) -> float:
    """
    Minimum hex distance between any hex of `attacker` and any hex of `target`.
    Handles both single-hex and multi-hex actors correctly.
    """
    coords = list(map_obj.arrayCenters)
    attacker_fp = get_actor_footprint_coords(attacker, map_obj)
    target_fp = get_actor_footprint_coords(target, map_obj)
    if not attacker_fp or not target_fp:
        return 999
    return min(
        map_obj.distanceCalc(coords.index(ac), coords.index(tc))
        for ac in attacker_fp
        for tc in target_fp
    )


def nearest_footprint_index(actor_anchor_idx: int, target_actor, map_obj) -> int:
    """
    Return the index of the footprint hex of target_actor that is nearest to actor_anchor_idx.
    """
    coords = list(map_obj.arrayCenters)
    footprint = get_actor_footprint_coords(target_actor, map_obj)
    if not footprint:
        return actor_anchor_idx
    return min(
        (coords.index(c) for c in footprint),
        key=lambda i: map_obj.distanceCalc(actor_anchor_idx, i)
    )


def dedup_actor_list(index_list: list, map_obj) -> list:
    """
    Given a list of hex indices potentially containing multiple hexes of the
    same large actor, return a deduplicated list keeping only the anchor index
    for each actor.
    """
    seen_ids: set[int] = set()
    result: list[int] = []
    coords = list(map_obj.arrayCenters)
    for idx in index_list:
        actor = map_obj.arrayCenters[coords[idx]]
        if actor == '' or id(actor) in seen_ids:
            continue
        seen_ids.add(id(actor))
        # Use anchor index
        anchor = get_actor_anchor(actor, map_obj)
        anchor_idx = coords.index(anchor) if anchor else idx
        result.append(anchor_idx)
    return result
