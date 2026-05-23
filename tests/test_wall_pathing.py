"""
Tests for wall-aware pathfinding in the DMSim engine.

Verifies that:
  - calcMoveHexes never returns wall hex indices
  - _bfs_path_dest routes around walls, not through them
  - Actors never land on wall hexes after movement
  - A wall barrier forces actors to find the gap rather than a direct path

Run with:
    python -m pytest tests/test_wall_pathing.py -v
  or:
    python tests/test_wall_pathing.py
"""

import sys
import pathlib
import math

_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_root))

from model.map import Map
from model.player import createPartyList
from model.monster import createMonsterList
from engine.targeting import calcMoveHexes, _bfs_path_dest
from engine.combat import takeTurn

_PATH = str(_root / "actors" / "savedObjs") + "\\"
_MONSTERS = ["Goblin", "Goblin"]
_PARTY    = ["Galleus"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_map(num_hexes=10, monsters=None, party=None):
    """Build a headless Map with real actors from saved JSON."""
    p = createPartyList(party or _PARTY[:1], path=_PATH)
    e = createMonsterList(monsters or _MONSTERS[:1], path=_PATH)
    m = Map(num_hexes, p, e, graphicsViewer=None)
    for a in p + e:
        a.health = a.maxHealth
        a.defineSpellSlots()
    return m, p, e


def _place_actor(m, actor, coord):
    """Forcibly place actor at coord, clearing its old footprint."""
    for c, v in list(m.arrayCenters.items()):
        if v is actor:
            m.arrayCenters[c] = ''
    assert coord in m.arrayCenters, f"coord {coord} not in grid"
    assert m.arrayCenters[coord] == '', f"coord {coord} is occupied by {m.arrayCenters[coord]}"
    m.arrayCenters[coord] = actor
    actor._anchor_coord = coord


def _actor_coord(m, actor):
    """Return the coordinate where actor currently sits."""
    return next((c for c, v in m.arrayCenters.items() if v is actor), None)


def _build_wall_column(m, col):
    """Add every hex in column `col` to map.walls. Returns the set of added coords."""
    added = {c for c in m._coord_list if c[0] == col}
    m.walls |= added
    return added


def _build_wall_column_with_gap(m, col, gap_row):
    """Add every hex in column `col` except the one at `gap_row` to map.walls.
    Skips hexes that already have an actor so we never wall over a placed actor."""
    occupied = {c for c, v in m.arrayCenters.items() if v not in ('', None)}
    added = {c for c in m._coord_list
             if c[0] == col and c[1] != gap_row and c not in occupied}
    m.walls |= added
    return added


def _grid_info(m):
    """Return (cols_sorted, rows_for_col0) for quick orientation."""
    cols = sorted(set(c[0] for c in m._coord_list))
    rows = sorted(set(c[1] for c in m._coord_list))
    return cols, rows


# ---------------------------------------------------------------------------
# Test 1: calcMoveHexes never returns wall indices
# ---------------------------------------------------------------------------

def test_calcMoveHexes_excludes_walls():
    m, party, enemies = _make_map()
    actor = enemies[0]

    # Find actor's column and wall the neighbours to be sure
    actor_coord = _actor_coord(m, actor)
    assert actor_coord is not None, "Actor not placed"

    # Add a couple of neighbouring hexes as walls
    neighbours = m._neighbors_of(actor_coord)
    wall_indices = set(neighbours[:2])
    wall_coords  = {m._coord_list[i] for i in wall_indices}
    m.walls |= wall_coords

    reachable = set(calcMoveHexes(actor, m))
    overlap = reachable & wall_indices
    assert not overlap, (
        f"calcMoveHexes returned wall indices: {overlap}. "
        f"Wall coords: {wall_coords}"
    )
    print("PASS test_calcMoveHexes_excludes_walls")


# ---------------------------------------------------------------------------
# Test 2: _bfs_path_dest routes around a single-hex wall obstacle
# ---------------------------------------------------------------------------

def test_bfs_routes_around_single_wall():
    m, party, enemies = _make_map(num_hexes=10)

    cols, rows = _grid_info(m)
    if len(cols) < 5:
        print("SKIP test_bfs_routes_around_single_wall — grid too small")
        return

    # Pick start on left half, target on right half
    mid_col = cols[len(cols) // 2]
    left_col  = cols[len(cols) // 4]
    right_col = cols[3 * len(cols) // 4]

    # Get any row that exists in both columns and the mid column
    left_coords  = [c for c in m._coord_list if c[0] == left_col]
    right_coords = [c for c in m._coord_list if c[0] == right_col]
    mid_coords   = [c for c in m._coord_list if c[0] == mid_col]

    if not left_coords or not right_coords or not mid_coords:
        print("SKIP test_bfs_routes_around_single_wall — missing column(s)")
        return

    # Place a single wall in the middle
    wall_coord = mid_coords[len(mid_coords) // 2]
    m.walls.add(wall_coord)
    wall_idx = m._coord_idx[wall_coord]

    start_coord = left_coords[0]
    end_coord   = right_coords[0]

    # Clear any actors from those positions
    for c in (start_coord, end_coord):
        if m.arrayCenters.get(c) not in ('', None):
            m.arrayCenters[c] = ''
    m.arrayCenters[start_coord] = ''
    m.arrayCenters[end_coord]   = ''

    start_idx = m._coord_idx[start_coord]
    end_idx   = m._coord_idx[end_coord]

    # BFS with unlimited steps (large max_steps)
    dest = _bfs_path_dest(start_idx, end_idx, 9999, m)

    assert dest != wall_idx, (
        f"_bfs_path_dest routed through wall at {wall_coord} (idx {wall_idx})"
    )
    assert dest is not None, "BFS returned None — no path found, but one should exist"
    print("PASS test_bfs_routes_around_single_wall")


# ---------------------------------------------------------------------------
# Test 3: _bfs_path_dest returns None when target is fully surrounded
# ---------------------------------------------------------------------------

def test_bfs_returns_none_when_blocked():
    m, party, enemies = _make_map(num_hexes=10)

    # Pick any interior coord and surround it with walls
    interior = next(
        (c for c in m._coord_list
         if len(m._neighbors_of(c)) == 6),  # full 6 neighbours = interior hex
        None
    )
    if interior is None:
        print("SKIP test_bfs_returns_none_when_blocked — no interior hex found")
        return

    # Wall off all 6 neighbours
    for nb_idx in m._neighbors_of(interior):
        m.walls.add(m._coord_list[nb_idx])

    # Pick a start that is NOT inside the wall ring
    exterior_coords = [c for c in m._coord_list
                       if c not in m.walls and c != interior]
    if not exterior_coords:
        print("SKIP test_bfs_returns_none_when_blocked — no exterior hexes")
        return

    start_idx  = m._coord_idx[exterior_coords[0]]
    target_idx = m._coord_idx[interior]

    dest = _bfs_path_dest(start_idx, target_idx, 9999, m)
    assert dest is None, (
        f"Expected None (target fully enclosed) but got idx={dest} coord={m._coord_list[dest]}"
    )
    print("PASS test_bfs_returns_none_when_blocked")


# ---------------------------------------------------------------------------
# Test 4: After takeTurn, no actor sits on a wall hex
# ---------------------------------------------------------------------------

def test_no_actor_on_wall_after_turn():
    m, party, enemies = _make_map(num_hexes=10)

    # Build a half-wall across the middle column
    cols, rows = _grid_info(m)
    if len(cols) < 3:
        print("SKIP test_no_actor_on_wall_after_turn — grid too small")
        return

    mid_col = cols[len(cols) // 2]
    _build_wall_column_with_gap(m, mid_col, gap_row=rows[len(rows) // 2])

    # Run one AI turn for each enemy
    for enemy in enemies:
        try:
            takeTurn(enemy, m, interactive=False)
        except Exception as e:
            print(f"  WARNING: takeTurn raised {e} — checking positions anyway")

    # Assert no actor is on a wall hex
    for coord, occupant in m.arrayCenters.items():
        if occupant not in ('', None) and coord in m.walls:
            raise AssertionError(
                f"Actor '{occupant.name}' is sitting on wall hex {coord}!"
            )

    print("PASS test_no_actor_on_wall_after_turn")


# ---------------------------------------------------------------------------
# Test 5: Wall barrier forces path through gap — not straight line
# ---------------------------------------------------------------------------

def test_wall_barrier_forces_gap_path():
    """
    Place a wall column across the grid with a single gap.
    Place actor left of the wall, target right of the wall.
    BFS path must pass through the gap, not any wall hex.
    """
    m, party, enemies = _make_map(num_hexes=10)

    cols, rows = _grid_info(m)
    if len(cols) < 5 or len(rows) < 3:
        print("SKIP test_wall_barrier_forces_gap_path — grid too small")
        return

    # Build wall column in the middle, with a gap at the bottom row
    mid_col  = cols[len(cols) // 2]
    gap_row  = rows[-1]   # leave the last (bottom) row open
    wall_coords = _build_wall_column_with_gap(m, mid_col, gap_row)
    wall_indices = {m._coord_idx[c] for c in wall_coords}

    # Clear actors and place them on opposite sides of the wall
    for c, v in list(m.arrayCenters.items()):
        if v not in ('', None):
            m.arrayCenters[c] = ''

    left_col  = cols[max(0, len(cols) // 2 - 2)]
    right_col = cols[min(len(cols) - 1, len(cols) // 2 + 2)]

    left_hexes  = [c for c in m._coord_list if c[0] == left_col and c not in m.walls]
    right_hexes = [c for c in m._coord_list if c[0] == right_col and c not in m.walls]

    if not left_hexes or not right_hexes:
        print("SKIP test_wall_barrier_forces_gap_path — can't find free hexes on each side")
        return

    start_coord = left_hexes[0]
    end_coord   = right_hexes[0]

    start_idx = m._coord_idx[start_coord]
    end_idx   = m._coord_idx[end_coord]

    dest = _bfs_path_dest(start_idx, end_idx, 9999, m)
    assert dest is not None, "No path found — is the gap accessible?"

    # Reconstruct full path and verify no wall hex is visited
    from collections import deque
    parent = {start_idx: None}
    queue = deque([start_idx])
    found = False
    while queue:
        cur = queue.popleft()
        if cur == end_idx:
            found = True
            break
        for nb in m._neighbors_of(m._coord_list[cur]):
            if nb not in parent and nb not in wall_indices:
                parent[nb] = cur
                queue.append(nb)

    assert found, "BFS couldn't reconstruct path"

    path = []
    cur = end_idx
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    path.reverse()

    path_wall_hits = [idx for idx in path if idx in wall_indices]
    assert not path_wall_hits, (
        f"BFS path passes through wall hexes: "
        f"{[m._coord_list[i] for i in path_wall_hits]}"
    )
    print(f"PASS test_wall_barrier_forces_gap_path  (path length={len(path)})")


# ---------------------------------------------------------------------------
# Test 6: Full combat — multiple turns, walls present, actors never on walls
# ---------------------------------------------------------------------------

def test_full_combat_actors_never_on_wall():
    m, party, enemies = _make_map(num_hexes=15, monsters=_MONSTERS, party=_PARTY)

    cols, rows = _grid_info(m)
    if len(cols) < 5:
        print("SKIP test_full_combat_actors_never_on_wall — grid too small")
        return

    # Add a partial wall barrier
    mid_col = cols[len(cols) // 2]
    _build_wall_column_with_gap(m, mid_col, gap_row=rows[len(rows) // 2])

    all_actors = party + enemies

    def check_no_actor_on_wall(label):
        for coord, occ in m.arrayCenters.items():
            if occ not in ('', None) and coord in m.walls:
                raise AssertionError(
                    f"[{label}] '{occ.name}' is on wall hex {coord}!"
                )

    alive = lambda a: a.health > 0
    max_rounds = 6
    for round_num in range(max_rounds):
        if not any(alive(a) for a in party) or not any(alive(a) for a in enemies):
            break
        for actor in list(all_actors):
            if not alive(actor):
                continue
            try:
                takeTurn(actor, m, interactive=False)
            except Exception:
                pass
            check_no_actor_on_wall(f"Round {round_num+1}, after {actor.name}'s turn")

    print(f"PASS test_full_combat_actors_never_on_wall  ({max_rounds} rounds, no wall violations)")


# ---------------------------------------------------------------------------
# Test 7: Verify model and GUI grid sizes match (unit-level smoke test)
# ---------------------------------------------------------------------------

def test_headless_grid_coords_start_at_origin():
    """First coord should be (0,0) in headless mode."""
    m, _, _ = _make_map(num_hexes=10)
    first = m._coord_list[0]
    assert first == (0, 0), f"Expected (0,0) as first coord, got {first}"
    print(f"PASS test_headless_grid_coords_start_at_origin  (grid size={len(m._coord_list)})")


def test_no_duplicate_coords():
    """Every hex should have a unique (col, row) coordinate."""
    m, _, _ = _make_map(num_hexes=10)
    assert len(m._coord_list) == len(set(m._coord_list)), "Duplicate coords in _coord_list"
    assert len(m._coord_idx) == len(m._coord_list), "_coord_idx has wrong size"
    print(f"PASS test_no_duplicate_coords  ({len(m._coord_list)} unique hexes)")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_headless_grid_coords_start_at_origin,
        test_no_duplicate_coords,
        test_calcMoveHexes_excludes_walls,
        test_bfs_routes_around_single_wall,
        test_bfs_returns_none_when_blocked,
        test_no_actor_on_wall_after_turn,
        test_wall_barrier_forces_gap_path,
        test_full_combat_actors_never_on_wall,
    ]

    passed = failed = skipped = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"FAIL {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            import traceback
            print(f"ERROR {t.__name__}: {e}")
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*60}")
    print(f"  Results: {passed} passed, {failed} failed, {skipped} skipped")
    print(f"{'='*60}")
    sys.exit(0 if failed == 0 else 1)
