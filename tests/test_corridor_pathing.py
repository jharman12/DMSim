"""
Tests for actor movement through narrow wall corridors.

Verifies that:
  - Actors always advance toward their target even when out of weapon range
  - Multiple actors queuing through a narrow corridor all move forward
  - No actor stands still when it has valid moves that bring it closer to the target

Run with:
    python -m pytest tests/test_corridor_pathing.py -v
  or:
    python tests/test_corridor_pathing.py
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
_MONSTERS = ["Goblin", "Goblin", "Goblin", "Goblin"]
_PARTY    = ["Galleus"]


# ---------------------------------------------------------------------------
# Helpers
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
    assert coord in m.arrayCenters and m.arrayCenters[coord] == '', \
        f"Cannot place at {coord}: {m.arrayCenters.get(coord)}"
    m.arrayCenters[coord] = actor
    if hasattr(actor, '_anchor_coord'):
        actor._anchor_coord = coord


def _dist(m, c1, c2):
    return m.distanceCalc(m._coord_idx[c1], m._coord_idx[c2])


def _nearest_free_hex_to(m, ref_coord, candidates):
    """Return the candidate closest (by distanceCalc) to ref_coord that is empty."""
    free = [c for c in candidates if m.arrayCenters.get(c) == '' and c not in m.walls]
    if not free:
        return None
    ref_idx = m._coord_idx[ref_coord]
    return min(free, key=lambda c: m.distanceCalc(ref_idx, m._coord_idx[c]))


def _build_wall_with_gap(m, wall_col):
    """Paint wall_col as impassable except for one gap near the middle.
    Returns the gap coordinate (wall_col, gap_row).
    """
    wall_col_hexes = sorted(
        [c for c in m._coord_list if c[0] == wall_col],
        key=lambda c: c[1]
    )
    if not wall_col_hexes:
        return None
    # Pick the middle hex as the gap so it's reachable from both sides
    gap_coord = wall_col_hexes[len(wall_col_hexes) // 2]
    occupied = {c for c, v in m.arrayCenters.items() if v not in ('', None)}
    for c in wall_col_hexes:
        if c != gap_coord and c not in occupied:
            m.walls.add(c)
    return gap_coord


# ---------------------------------------------------------------------------
# Test 1: Actor advances when no open attack hex is reachable this turn
# ---------------------------------------------------------------------------

def test_actor_advances_when_out_of_range():
    """
    With a large enough map, place the actor far from its target so it cannot
    reach weapon range in one move. It must still move closer, not stand still.
    """
    m, party, enemies = _make_map(num_hexes=15)

    cols, rows = _grid_info(m)
    if len(cols) < 8:
        print("SKIP test_actor_advances_when_out_of_range — grid too small")
        return

    actor = enemies[0]
    target = party[0]

    # Place actor far left, target far right — clear grid first
    for c, v in list(m.arrayCenters.items()):
        if v not in ('', None):
            m.arrayCenters[c] = ''

    left_col  = cols[0]
    right_col = cols[-1]

    left_hexes  = [c for c in m._coord_list if c[0] == left_col  and c not in m.walls]
    right_hexes = [c for c in m._coord_list if c[0] == right_col and c not in m.walls]

    if not left_hexes or not right_hexes:
        print("SKIP test_actor_advances_when_out_of_range — no free edge hexes")
        return

    _place_actor(m, actor, left_hexes[0])
    _place_actor(m, target, right_hexes[0])

    start_dist = _dist(m, _actor_coord(m, actor), _actor_coord(m, target))

    m.party  = [target]
    m.enemy  = [actor]

    try:
        takeTurn(actor, m, interactive=False)
    except SystemExit:
        pass  # distance-check guard in moveActor may fire — that's OK

    end_coord = _actor_coord(m, actor)
    assert end_coord is not None, "Actor disappeared from map"
    end_dist = _dist(m, end_coord, _actor_coord(m, target))

    assert end_dist < start_dist, (
        f"Actor did not advance: start_dist={start_dist}, end_dist={end_dist}. "
        f"Actor stayed at {end_coord}"
    )
    print(f"PASS test_actor_advances_when_out_of_range  "
          f"(dist {start_dist} -> {end_dist})")


# ---------------------------------------------------------------------------
# Test 2: Multiple actors queue through a narrow corridor — all advance
# ---------------------------------------------------------------------------

def test_corridor_queue_all_actors_advance():
    """
    Build a map with a 1-hex-wide corridor through a wall.
    Place several enemies adjacent to the gap (so travel via gap doesn't
    require a long detour) and the party target just past the gap.
    Run one turn for each enemy — every one should be closer to the
    target after its turn than before.
    """
    num_enemies = 3
    p = createPartyList(_PARTY[:1], path=_PATH)
    e = createMonsterList(_MONSTERS[:num_enemies], path=_PATH)
    m = Map(15, p, e, graphicsViewer=None)
    for a in p + e:
        a.health = a.maxHealth
        a.defineSpellSlots()

    cols, rows = _grid_info(m)
    if len(cols) < 8 or len(rows) < 6:
        print("SKIP test_corridor_queue_all_actors_advance — grid too small")
        return

    # --- Clear all actors ---
    for c in list(m.arrayCenters):
        if m.arrayCenters[c] not in ('', None):
            m.arrayCenters[c] = ''

    # --- Build corridor wall with a gap near the middle ---
    wall_col  = cols[len(cols) // 2]
    gap_coord = _build_wall_with_gap(m, wall_col)
    if gap_coord is None:
        print("SKIP test_corridor_queue_all_actors_advance — could not build wall")
        return
    gap_row = gap_coord[1]

    # --- Party target: first empty hex just right of the gap ---
    right_candidates = sorted(
        [c for c in m._coord_list if c[0] > wall_col and c not in m.walls],
        key=lambda c: m.distanceCalc(m._coord_idx[gap_coord], m._coord_idx[c])
    )
    if not right_candidates:
        print("SKIP test_corridor_queue_all_actors_advance — no right-side hexes")
        return
    target = p[0]
    _place_actor(m, target, right_candidates[0])

    # --- Enemies: place closest-to-gap left-side hexes first ---
    left_candidates = sorted(
        [c for c in m._coord_list if c[0] < wall_col and c not in m.walls],
        key=lambda c: m.distanceCalc(m._coord_idx[gap_coord], m._coord_idx[c])
    )
    placed = []
    for enemy in e:
        for coord in left_candidates:
            if m.arrayCenters.get(coord) == '':
                _place_actor(m, enemy, coord)
                placed.append(enemy)
                break

    if len(placed) < num_enemies:
        print(f"SKIP test_corridor_queue_all_actors_advance — "
              f"only placed {len(placed)}/{num_enemies} enemies")
        return

    m.party = [target]
    m.enemy = list(e)

    # --- Run one turn per enemy, track distance change ---
    did_not_advance = []
    for enemy in placed:
        start = _actor_coord(m, enemy)
        start_dist = _dist(m, start, _actor_coord(m, target))

        try:
            takeTurn(enemy, m, interactive=False)
        except SystemExit:
            pass

        end = _actor_coord(m, enemy)
        if end is None:
            continue
        end_dist = _dist(m, end, _actor_coord(m, target))

        if end_dist >= start_dist:
            did_not_advance.append(
                f"{enemy.name} at {start}: dist {start_dist} -> {end_dist} (no advance)"
            )

    assert not did_not_advance, (
        "Some actors did not advance through the corridor:\n  " +
        "\n  ".join(did_not_advance)
    )
    print(f"PASS test_corridor_queue_all_actors_advance  "
          f"({len(placed)} actors all advanced through corridor)")


# ---------------------------------------------------------------------------
# Test 3: Actor at corridor entrance (blocked ahead) still moves into corridor
# ---------------------------------------------------------------------------

def test_actor_enters_corridor_when_path_is_clear():
    """
    Single enemy placed as close as possible to the gap entrance — no other
    actors blocking.  It should cross the gap and end up closer to the target.
    """
    p = createPartyList(_PARTY[:1], path=_PATH)
    e = createMonsterList(_MONSTERS[:1], path=_PATH)
    m = Map(15, p, e, graphicsViewer=None)
    for a in p + e:
        a.health = a.maxHealth
        a.defineSpellSlots()

    cols, rows = _grid_info(m)
    if len(cols) < 6 or len(rows) < 4:
        print("SKIP test_actor_enters_corridor_when_path_is_clear — grid too small")
        return

    # --- Clear all actors ---
    for c in list(m.arrayCenters):
        if m.arrayCenters[c] not in ('', None):
            m.arrayCenters[c] = ''

    # --- Build wall ---
    wall_col  = cols[len(cols) // 2]
    gap_coord = _build_wall_with_gap(m, wall_col)
    if gap_coord is None:
        print("SKIP test_actor_enters_corridor_when_path_is_clear — could not build wall")
        return

    # --- Place target: closest free hex on the right side to gap ---
    right_free = [c for c in m._coord_list if c[0] > wall_col and c not in m.walls]
    left_free  = [c for c in m._coord_list if c[0] < wall_col and c not in m.walls]
    if not right_free or not left_free:
        print("SKIP test_actor_enters_corridor_when_path_is_clear — no free hexes")
        return

    target = p[0]
    actor  = e[0]

    # place target at the closest right-side hex to the gap
    t_coord = min(right_free, key=lambda c: m.distanceCalc(m._coord_idx[gap_coord], m._coord_idx[c]))
    _place_actor(m, target, t_coord)

    # place actor at the closest left-side hex to the gap (excluding target's hex)
    left_free = [c for c in left_free if m.arrayCenters.get(c) == '']
    a_coord = min(left_free, key=lambda c: m.distanceCalc(m._coord_idx[gap_coord], m._coord_idx[c]))
    _place_actor(m, actor, a_coord)

    m.party = [target]
    m.enemy = [actor]

    start_dist = _dist(m, _actor_coord(m, actor), _actor_coord(m, target))

    try:
        takeTurn(actor, m, interactive=False)
    except SystemExit:
        pass

    end = _actor_coord(m, actor)
    assert end is not None
    end_dist = _dist(m, end, _actor_coord(m, target))

    assert end_dist < start_dist, (
        f"Actor did not enter corridor: dist {start_dist} -> {end_dist}\n"
        f"  actor started at {a_coord}, target at {t_coord}, gap at {gap_coord}"
    )
    print(f"PASS test_actor_enters_corridor_when_path_is_clear  "
          f"(dist {start_dist} -> {end_dist})")


# ---------------------------------------------------------------------------
# Test 4: No actor ever idles when it has valid moves closer to target
# ---------------------------------------------------------------------------

def test_no_idle_when_moves_available():
    """
    Run a full 4-round combat with a wall barrier.
    Any actor that had valid moves closer to the target must not stay put.
    """
    p = createPartyList(_PARTY[:1], path=_PATH)
    e = createMonsterList(_MONSTERS[:2], path=_PATH)
    m = Map(15, p, e, graphicsViewer=None)
    for a in p + e:
        a.health = a.maxHealth
        a.defineSpellSlots()

    cols, rows = _grid_info(m)
    if len(cols) < 6:
        print("SKIP test_no_idle_when_moves_available — grid too small")
        return

    # Partial wall with gap
    wall_col = cols[len(cols) // 2]
    gap_row  = rows[len(rows) // 2]
    occupied = {c for c, v in m.arrayCenters.items() if v not in ('', None)}
    m.walls |= {c for c in m._coord_list
                if c[0] == wall_col and c[1] != gap_row and c not in occupied}

    walls = m.walls

    idle_violations = []

    alive = lambda a: a.health > 0
    all_actors = list(p) + list(e)

    for round_num in range(4):
        if not any(alive(a) for a in p) or not any(alive(a) for a in e):
            break
        for actor in list(all_actors):
            if not alive(actor):
                continue

            # Determine opponent list
            opponents = e if actor in p else p
            live_opponents = [o for o in opponents if alive(o)]
            if not live_opponents:
                break

            actor_coord = _actor_coord(m, actor)
            if actor_coord is None:
                continue

            # Find closest opponent
            closest_opp = min(
                live_opponents,
                key=lambda o: _dist(m, actor_coord, _actor_coord(m, o))
                    if _actor_coord(m, o) else 9999
            )
            opp_coord = _actor_coord(m, closest_opp)
            if opp_coord is None:
                continue

            dist_before = _dist(m, actor_coord, opp_coord)

            # Check if there are BFS-reachable hexes closer to target
            reachable = calcMoveHexes(actor, m)
            closer_exists = any(
                m.distanceCalc(m._coord_idx[opp_coord], idx) < dist_before
                for idx in reachable
            )

            try:
                takeTurn(actor, m, interactive=False)
            except (SystemExit, Exception):
                pass

            after_coord = _actor_coord(m, actor)
            if after_coord is None:
                continue
            dist_after = _dist(m, after_coord, opp_coord)

            # Only flag as idle if there were genuinely closer hexes available
            if closer_exists and dist_after >= dist_before:
                idle_violations.append(
                    f"Round {round_num+1} {actor.name}: "
                    f"had closer moves but dist {dist_before} -> {dist_after}"
                )

    assert not idle_violations, (
        "Actors idled when closer moves were available:\n  " +
        "\n  ".join(idle_violations)
    )
    print(f"PASS test_no_idle_when_moves_available")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_actor_advances_when_out_of_range,
        test_actor_enters_corridor_when_path_is_clear,
        test_corridor_queue_all_actors_advance,
        test_no_idle_when_moves_available,
    ]

    passed = failed = 0
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
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    sys.exit(0 if failed == 0 else 1)
