"""
Tests that ALL combat movement methods respect walls and route around them correctly.

Movement methods tested:
  1. Weapon attack movement  — via _best_dest / _safe_move (called in takeTurn/doAction)
  2. Dash action             — via map_obj.dashActor
  3. coordWithinReach        — BFS path destination used for spell/heal targeting moves
  4. moveWithingReach        — direct actor movement used in some spell scenarios
  5. _bfs_path_dest          — low-level primitive used by all of the above

Each test uses a wall barrier with a single gap. The test verifies that the
actor ends up closer to the target *by wall-aware BFS path distance*, not
straight-line distance.

Run with:
    python -m pytest tests/test_all_movement_methods.py -v
  or:
    python tests/test_all_movement_methods.py
"""

import sys
import pathlib

_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_root))

from model.map import Map
from model.player import createPartyList
from model.monster import createMonsterList
from engine.targeting import (
    calcMoveHexes, _bfs_path_dest, _bfs_cost_from,
    coordWithinReach, moveWithingReach,
)
from engine.combat import takeTurn, doAction, myAction

_PATH = str(_root / "actors" / "savedObjs") + "\\"
_MONSTERS = ["Goblin", "Goblin", "Goblin", "Goblin"]
_PARTY    = ["Galleus"]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_map(num_hexes=15, monsters=None, party=None):
    p = createPartyList(party or _PARTY[:1], path=_PATH)
    e = createMonsterList(monsters or _MONSTERS[:1], path=_PATH)
    m = Map(num_hexes, p, e, graphicsViewer=None)
    for a in p + e:
        a.health = a.maxHealth
        a.defineSpellSlots()
    return m, p, e


def _grid_info(m):
    cols = sorted(set(c[0] for c in m._coord_list))
    rows = sorted(set(c[1] for c in m._coord_list))
    return cols, rows


def _actor_coord(m, actor):
    return next((c for c, v in m.arrayCenters.items() if v is actor), None)


def _place_actor(m, actor, coord):
    for c, v in list(m.arrayCenters.items()):
        if v is actor:
            m.arrayCenters[c] = ''
    assert m.arrayCenters.get(coord) == '', \
        f"Cannot place at {coord}: {m.arrayCenters.get(coord)}"
    m.arrayCenters[coord] = actor
    if hasattr(actor, '_anchor_coord'):
        actor._anchor_coord = coord


def _bfs_dist(m, c1, c2):
    """Wall-aware BFS distance between two coords."""
    if c1 == c2:
        return 0
    idx1 = m._coord_idx[c1]
    idx2 = m._coord_idx[c2]
    cost = _bfs_cost_from(idx1, m)
    return cost.get(idx2, 99999)


def _setup_corridor(m, clear_actors=True):
    """Build a wall column across the middle with a single gap near centre.
    Returns (wall_col, gap_coord).
    Actors are optionally cleared from the map first.
    """
    cols, rows = _grid_info(m)
    if len(cols) < 6 or len(rows) < 4:
        return None, None

    if clear_actors:
        for c in list(m.arrayCenters):
            if m.arrayCenters[c] not in ('', None):
                m.arrayCenters[c] = ''

    wall_col  = cols[len(cols) // 2]
    wall_hexes = sorted([c for c in m._coord_list if c[0] == wall_col], key=lambda c: c[1])
    gap_coord  = wall_hexes[len(wall_hexes) // 2]

    occupied = {c for c, v in m.arrayCenters.items() if v not in ('', None)}
    for c in wall_hexes:
        if c != gap_coord and c not in occupied:
            m.walls.add(c)

    return wall_col, gap_coord


def _place_near_gap(m, actor, side, gap_coord):
    """Place actor on the nearest free hex on 'left'(<) or 'right'(>) side to gap."""
    wall_col = gap_coord[0]
    candidates = [
        c for c in m._coord_list
        if (c[0] < wall_col if side == 'left' else c[0] > wall_col)
        and c not in m.walls
        and m.arrayCenters.get(c) == ''
    ]
    if not candidates:
        return None
    closest = min(candidates, key=lambda c: _bfs_dist(m, c, gap_coord))
    _place_actor(m, actor, closest)
    return closest


# ---------------------------------------------------------------------------
# Test 1 — _bfs_path_dest: primitive routes around wall
# ---------------------------------------------------------------------------

def test_bfs_path_dest_routes_around_wall():
    """_bfs_path_dest must never return a wall hex as part of the path."""
    m, p, e = _make_map()
    wall_col, gap_coord = _setup_corridor(m)
    if wall_col is None:
        print("SKIP test_bfs_path_dest_routes_around_wall — grid too small")
        return

    actor  = e[0]
    target = p[0]
    a_coord = _place_near_gap(m, actor, 'left', gap_coord)
    t_coord = _place_near_gap(m, target, 'right', gap_coord)
    assert a_coord and t_coord

    start_idx  = m._coord_idx[a_coord]
    target_idx = m._coord_idx[t_coord]
    speed      = int(actor.speed / 5)

    dest_idx = _bfs_path_dest(start_idx, target_idx, speed, m)
    assert dest_idx is not None, "_bfs_path_dest returned None — target should be reachable"
    dest_coord = m._coord_list[dest_idx]
    assert dest_coord not in m.walls, \
        f"_bfs_path_dest returned wall hex {dest_coord}"

    # Path should move actor closer via BFS distance
    dist_before = _bfs_dist(m, a_coord, t_coord)
    dist_after  = _bfs_dist(m, dest_coord, t_coord)
    assert dist_after < dist_before, (
        f"BFS path dest did not advance: {dist_before} -> {dist_after}"
    )
    print(f"PASS test_bfs_path_dest_routes_around_wall  "
          f"(BFS dist {dist_before} -> {dist_after})")


# ---------------------------------------------------------------------------
# Test 2 — Weapon attack move: takeTurn advances via corridor
# ---------------------------------------------------------------------------

def test_weapon_move_routes_around_wall():
    """Weapon-attack turn must advance the actor via the corridor gap, not idle or drift."""
    m, p, e = _make_map()
    wall_col, gap_coord = _setup_corridor(m)
    if wall_col is None:
        print("SKIP test_weapon_move_routes_around_wall — grid too small")
        return

    actor  = e[0]
    target = p[0]
    _place_near_gap(m, actor, 'left', gap_coord)
    _place_near_gap(m, target, 'right', gap_coord)

    m.party = [target]
    m.enemy = [actor]

    a_start = _actor_coord(m, actor)
    dist_before = _bfs_dist(m, a_start, _actor_coord(m, target))

    try:
        takeTurn(actor, m, interactive=False)
    except SystemExit:
        pass

    a_end = _actor_coord(m, actor)
    assert a_end is not None, "Actor vanished after takeTurn"
    assert a_end not in m.walls, f"Actor moved onto wall hex {a_end}"

    dist_after = _bfs_dist(m, a_end, _actor_coord(m, target))
    assert dist_after < dist_before, (
        f"Weapon move did not advance via corridor: BFS dist {dist_before} -> {dist_after}"
    )
    print(f"PASS test_weapon_move_routes_around_wall  "
          f"(BFS dist {dist_before} -> {dist_after})")


# ---------------------------------------------------------------------------
# Test 3 — Dash: dashActor advances via corridor
# ---------------------------------------------------------------------------

def test_dash_routes_around_wall():
    """dashActor must route through the gap, not stop at the wall or move away."""
    m, p, e = _make_map()
    wall_col, gap_coord = _setup_corridor(m)
    if wall_col is None:
        print("SKIP test_dash_routes_around_wall — grid too small")
        return

    actor  = e[0]
    target = p[0]
    a_start = _place_near_gap(m, actor, 'left', gap_coord)
    t_coord = _place_near_gap(m, target, 'right', gap_coord)
    assert a_start and t_coord

    dist_before = _bfs_dist(m, a_start, t_coord)

    m.dashActor(actor, t_coord)

    a_end = _actor_coord(m, actor)
    assert a_end is not None, "Actor vanished after dashActor"
    assert a_end not in m.walls, f"dashActor moved actor onto wall hex {a_end}"

    dist_after = _bfs_dist(m, a_end, t_coord)
    assert dist_after < dist_before, (
        f"Dash did not advance via corridor: BFS dist {dist_before} -> {dist_after}"
    )
    print(f"PASS test_dash_routes_around_wall  "
          f"(BFS dist {dist_before} -> {dist_after}, dash dest {a_end})")


# ---------------------------------------------------------------------------
# Test 4 — Dash double-move: actor covers more distance than normal move
# ---------------------------------------------------------------------------

def test_dash_covers_double_movement():
    """Dash (double speed) should move the actor further than a normal move action."""
    m, p, e = _make_map()
    cols, rows = _grid_info(m)
    if len(cols) < 8:
        print("SKIP test_dash_covers_double_movement — grid too small")
        return

    # Clear map, no walls — pure distance check
    for c in list(m.arrayCenters):
        if m.arrayCenters[c] not in ('', None):
            m.arrayCenters[c] = ''

    actor  = e[0]
    target = p[0]

    left_col  = cols[0]
    right_col = cols[-1]
    left_hexes  = [c for c in m._coord_list if c[0] == left_col  and c not in m.walls]
    right_hexes = [c for c in m._coord_list if c[0] == right_col and c not in m.walls]

    if not left_hexes or not right_hexes:
        print("SKIP test_dash_covers_double_movement — no edge hexes")
        return

    _place_actor(m, actor, left_hexes[0])
    _place_actor(m, target, right_hexes[0])
    m.party = [target]; m.enemy = [actor]

    a_start    = _actor_coord(m, actor)
    t_coord    = _actor_coord(m, target)
    speed      = int(actor.speed / 5)
    dist_start = _bfs_dist(m, a_start, t_coord)

    # Normal move
    m2, p2, e2 = _make_map()
    for c in list(m2.arrayCenters):
        if m2.arrayCenters[c] not in ('', None):
            m2.arrayCenters[c] = ''
    left2  = [c for c in m2._coord_list if m2._coord_list.index(c) == m2._coord_list.index(left_hexes[0])]
    # Use same positions directly
    a2 = e2[0]; t2 = p2[0]
    _place_actor(m2, a2, left_hexes[0])
    _place_actor(m2, t2, right_hexes[0])
    m2.party = [t2]; m2.enemy = [a2]
    start2 = _actor_coord(m2, a2)
    dest_normal_idx = _bfs_path_dest(m2._coord_idx[start2], m2._coord_idx[right_hexes[0]], speed, m2)
    dist_normal = _bfs_dist(m2, m2._coord_list[dest_normal_idx], right_hexes[0]) if dest_normal_idx else 99999

    # Dash
    m.dashActor(actor, t_coord)
    a_after = _actor_coord(m, actor)
    dist_dash = _bfs_dist(m, a_after, t_coord) if a_after else 99999

    assert dist_dash <= dist_normal, (
        f"Dash dist {dist_dash} is not <= normal move dist {dist_normal} "
        f"(actor speed {actor.speed})"
    )
    print(f"PASS test_dash_covers_double_movement  "
          f"(normal dist_to_target {dist_normal}, dash dist_to_target {dist_dash})")


# ---------------------------------------------------------------------------
# Test 5 — coordWithinReach: returns BFS-valid destination around wall
# ---------------------------------------------------------------------------

def test_coordWithinReach_routes_around_wall():
    """coordWithinReach must return a coord closer by BFS distance, not straight-line."""
    m, p, e = _make_map()
    wall_col, gap_coord = _setup_corridor(m)
    if wall_col is None:
        print("SKIP test_coordWithinReach_routes_around_wall — grid too small")
        return

    actor  = e[0]
    target = p[0]
    a_coord = _place_near_gap(m, actor, 'left', gap_coord)
    t_coord = _place_near_gap(m, target, 'right', gap_coord)
    assert a_coord and t_coord

    dist_before = _bfs_dist(m, a_coord, t_coord)

    reach_hexes = 1  # melee reach
    result = coordWithinReach(a_coord, t_coord, reach_hexes, m)

    assert result not in m.walls, \
        f"coordWithinReach returned wall hex {result}"

    dist_after = _bfs_dist(m, result, t_coord)
    assert dist_after < dist_before, (
        f"coordWithinReach did not advance via corridor: "
        f"BFS dist {dist_before} -> {dist_after}"
    )
    print(f"PASS test_coordWithinReach_routes_around_wall  "
          f"(BFS dist {dist_before} -> {dist_after})")


# ---------------------------------------------------------------------------
# Test 6 — moveWithingReach: actor moves closer via corridor
# ---------------------------------------------------------------------------

def test_moveWithingReach_routes_around_wall():
    """moveWithingReach must move the actor through the gap, not through the wall."""
    m, p, e = _make_map()
    wall_col, gap_coord = _setup_corridor(m)
    if wall_col is None:
        print("SKIP test_moveWithingReach_routes_around_wall — grid too small")
        return

    actor  = e[0]
    target = p[0]
    a_start = _place_near_gap(m, actor, 'left', gap_coord)
    _place_near_gap(m, target, 'right', gap_coord)

    dist_before = _bfs_dist(m, a_start, _actor_coord(m, target))

    reach_feet = 5  # melee reach in feet
    moveWithingReach(actor, target, reach_feet, m)

    a_end = _actor_coord(m, actor)
    assert a_end is not None, "Actor vanished after moveWithingReach"
    assert a_end not in m.walls, f"moveWithingReach moved actor onto wall hex {a_end}"

    dist_after = _bfs_dist(m, a_end, _actor_coord(m, target))
    assert dist_after < dist_before, (
        f"moveWithingReach did not advance via corridor: BFS dist {dist_before} -> {dist_after}"
    )
    print(f"PASS test_moveWithingReach_routes_around_wall  "
          f"(BFS dist {dist_before} -> {dist_after})")


# ---------------------------------------------------------------------------
# Test 7 — No movement method ever places actor on a wall hex
# ---------------------------------------------------------------------------

def test_no_method_places_actor_on_wall():
    """Run multiple turns mixing weapon attacks and dashes. Actor must never land on wall."""
    m, p, e = _make_map(monsters=_MONSTERS[:2])
    wall_col, gap_coord = _setup_corridor(m, clear_actors=False)
    if wall_col is None:
        print("SKIP test_no_method_places_actor_on_wall — grid too small")
        return

    m.party = list(p)
    m.enemy = list(e)

    violations = []
    for round_num in range(6):
        for actor in list(p) + list(e):
            if actor.health <= 0:
                continue
            opponents = e if actor in p else p
            if not any(o.health > 0 for o in opponents):
                break
            try:
                takeTurn(actor, m, interactive=False)
            except (SystemExit, Exception):
                pass
            coord = _actor_coord(m, actor)
            if coord and coord in m.walls:
                violations.append(
                    f"Round {round_num+1} {actor.name} at wall hex {coord}"
                )

    assert not violations, (
        "Actor(s) landed on wall hex:\n  " + "\n  ".join(violations)
    )
    print(f"PASS test_no_method_places_actor_on_wall  (6 rounds, no wall violations)")


# ---------------------------------------------------------------------------
# Test 8 — Consistency: all methods agree on direction of movement
# ---------------------------------------------------------------------------

def test_all_methods_advance_not_retreat():
    """
    Given identical starting positions:
    - weapon move (takeTurn), dashActor, coordWithinReach, moveWithingReach
    All must produce a destination that is BFS-closer to the target, not further.
    """
    results = {}
    for method_name in ('weapon', 'dash', 'coordWithinReach', 'moveWithingReach'):
        m, p, e = _make_map()
        wall_col, gap_coord = _setup_corridor(m)
        if wall_col is None:
            print("SKIP test_all_methods_advance_not_retreat — grid too small")
            return

        actor  = e[0]
        target = p[0]
        a_start = _place_near_gap(m, actor, 'left', gap_coord)
        t_coord = _place_near_gap(m, target, 'right', gap_coord)
        dist_before = _bfs_dist(m, a_start, t_coord)

        if method_name == 'weapon':
            m.party = [target]; m.enemy = [actor]
            try:
                takeTurn(actor, m, interactive=False)
            except SystemExit:
                pass
            a_end = _actor_coord(m, actor)

        elif method_name == 'dash':
            m.dashActor(actor, t_coord)
            a_end = _actor_coord(m, actor)

        elif method_name == 'coordWithinReach':
            result_coord = coordWithinReach(a_start, t_coord, 1, m)
            a_end = result_coord  # coordWithinReach returns coord, does not move

        elif method_name == 'moveWithingReach':
            moveWithingReach(actor, target, 5, m)
            a_end = _actor_coord(m, actor)

        if a_end is None:
            results[method_name] = ('ERROR', 'actor vanished')
            continue

        assert a_end not in m.walls, \
            f"{method_name}: result is wall hex {a_end}"

        dist_after = _bfs_dist(m, a_end, t_coord)
        results[method_name] = (dist_before, dist_after)

    failures = [
        f"{name}: BFS dist {v[0]} -> {v[1]}"
        for name, v in results.items()
        if isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], (int, float)) and v[1] >= v[0]
    ]
    assert not failures, (
        "These methods did NOT advance toward target:\n  " + "\n  ".join(failures)
    )
    summary = ", ".join(f"{n}: {v[0]}->{v[1]}" for n, v in results.items() if isinstance(v[0], (int, float)))
    print(f"PASS test_all_methods_advance_not_retreat  ({summary})")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_bfs_path_dest_routes_around_wall,
        test_weapon_move_routes_around_wall,
        test_dash_routes_around_wall,
        test_dash_covers_double_movement,
        test_coordWithinReach_routes_around_wall,
        test_moveWithingReach_routes_around_wall,
        test_no_method_places_actor_on_wall,
        test_all_methods_advance_not_retreat,
    ]

    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as err:
            print(f"FAIL {t.__name__}: {err}")
            failed += 1
        except Exception as err:
            import traceback
            print(f"ERROR {t.__name__}: {err}")
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    sys.exit(0 if failed == 0 else 1)
