# -*- coding: utf-8 -*-
"""Task 54 - Large-Scale Engine Stress Test (100+ encounters, headless)."""

import sys, pathlib, random, traceback
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict

_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_root))

from model.map import Map
from model.player import createPartyList
from model.monster import createMonsterList
from engine.combat import takeTurn

_PATH = str(_root / "actors" / "savedObjs") + "\\"


@dataclass
class Scenario:
    name: str
    party: List[str]
    monsters: List[str]
    num_hexes: int = 15
    wall_layout: str = "none"
    runs: int = 5


SCENARIOS = [
    Scenario("melee_1v1",          ["Galleus"],                      ["Orc"],                              runs=100),
    Scenario("melee_party_horde",  ["Galleus","Aldric"],             ["Goblin","Goblin","Goblin","Goblin"], runs=100),
    Scenario("melee_solo_hero",    ["Aldric"],                       ["Goblin","Goblin","Goblin"],          runs=80),
    Scenario("melee_troll",        ["Galleus","Aldric"],             ["Troll","Troll"],                    runs=80),
    Scenario("spell_archmage",     ["Galleus","Aldric"],             ["Archmage"],                         runs=80),
    Scenario("spell_lich",         ["Galleus","Aldric","VV"],        ["Lich"],                             runs=80),
    Scenario("spell_druid_horde",  ["Galleus","Aldric","Adrel"],     ["Druid","Goblin","Goblin","Goblin"],  runs=80),
    Scenario("spell_vs_spell",     ["VV","Adrel"],                   ["Mage","Cult Fanatic"],               runs=80),
    Scenario("dragon",             ["Galleus","Aldric","Adrel","Cobo"], ["Adult Silver Dragon"],            runs=50),
    Scenario("giant_battle",       ["Galleus","Aldric","VV","Adrel"],["Hill Giant","Hill Giant"],           runs=50),
    Scenario("full_party_horde",   ["Galleus","Aldric","Adrel","Cobo","VV"], ["Goblin"]*8,                 runs=50),
    Scenario("1v8_goblins",        ["Aldric"],                       ["Goblin"]*8,                         runs=50),
    Scenario("full_party_1orc",    ["Galleus","Aldric","Adrel","Cobo","VV"], ["Orc"],                      runs=50),
    Scenario("wall_melee",         ["Galleus","Aldric"],             ["Orc","Orc"],
             wall_layout="barrier",                                                                         runs=50),
    Scenario("wall_spell",         ["Galleus","VV"],                 ["Archmage"],
             wall_layout="barrier",                                                                         runs=50),
]

_MAX_ROUNDS = 50


@dataclass
class RunResult:
    scenario: str
    run_idx: int
    outcome: str
    rounds: int
    error: str = ""
    violations: List[str] = field(default_factory=list)


def _find_integrity_violations(m, party, enemy, round_num):
    issues = []
    walls = getattr(m, "walls", set())
    coord_actors = defaultdict(list)
    for coord, v in m.arrayCenters.items():
        if v not in ("", None):
            coord_actors[coord].append(v)
    for coord, actors in coord_actors.items():
        if coord in walls:
            for a in actors:
                issues.append(f"Round {round_num}: {a.name} on wall {coord}")
        if len(actors) > 1:
            issues.append(f"Round {round_num}: Multiple actors at {coord}: {[a.name for a in actors]}")
    for actor in list(party) + list(enemy):
        if actor.health < 0 and actor.alive:
            issues.append(f"Round {round_num}: {actor.name} negative health {actor.health}")
        if actor.health > 0 and not any(v is actor for v in m.arrayCenters.values()):
            issues.append(f"Round {round_num}: {actor.name} (hp={actor.health}) vanished from map")
    return issues


def _setup_wall_barrier(m):
    cols = sorted(set(c[0] for c in m._coord_list))
    if len(cols) < 4:
        return
    wall_col = cols[len(cols) // 2]
    hexes = sorted([c for c in m._coord_list if c[0] == wall_col], key=lambda c: c[1])
    gap = hexes[len(hexes) // 2]
    occupied = {c for c, v in m.arrayCenters.items() if v not in ("", None)}
    for c in hexes:
        if c != gap and c not in occupied:
            m.walls.add(c)


def _load_actors(scenario):
    party = createPartyList(scenario.party, path=_PATH)
    monsters = createMonsterList(scenario.monsters, path=_PATH)
    for a in party + monsters:
        a.health = a.maxHealth
        a.defineSpellSlots()
        if not hasattr(a, "maxSpeed"):
            a.maxSpeed = a.speed
        a.cc = []
        a.restrained = []
        a.hasAction = True
        a.hasBonusAction = True
        a.concentration_spell = None
        a.active_conditions = set()
    return party, monsters


def run_encounter(scenario, run_idx, rng_seed):
    random.seed(rng_seed)
    violations = []
    try:
        party, monsters = _load_actors(scenario)
    except Exception as e:
        return RunResult(scenario.name, run_idx, "error", 0, error=f"Load: {e}\n{traceback.format_exc()}")
    try:
        m = Map(scenario.num_hexes, party, monsters, graphicsViewer=None)
    except Exception as e:
        return RunResult(scenario.name, run_idx, "error", 0, error=f"Map: {e}\n{traceback.format_exc()}")

    if scenario.wall_layout == "barrier":
        _setup_wall_barrier(m)
    m.party = list(party)
    m.enemy = list(monsters)

    rounds = 0
    stall_hp = None
    stall_count = 0

    try:
        while rounds < _MAX_ROUNDS:
            if not m.party or not m.enemy:
                break
            violations.extend(_find_integrity_violations(m, m.party, m.enemy, rounds))
            hp_total = sum(a.health for a in m.party + m.enemy)
            if stall_hp == hp_total:
                stall_count += 1
                if stall_count >= 5:
                    return RunResult(scenario.name, run_idx, "stall", rounds,
                                     error=f"HP stuck at {hp_total}", violations=violations)
            else:
                stall_hp = hp_total
                stall_count = 0

            for actor in list(m.party) + list(m.enemy):
                if actor.health <= 0 or not m.party or not m.enemy:
                    continue
                try:
                    takeTurn(actor, m, interactive=False)
                except SystemExit:
                    pass
                except Exception as e:
                    violations.append(f"Round {rounds} {actor.name}: {e}")
                dead = [a for a in list(m.party) + list(m.enemy) if a.health <= 0]
                for d in dead:
                    for c in list(m.arrayCenters):
                        if m.arrayCenters[c] is d:
                            m.arrayCenters[c] = ""
                    if d in m.party:
                        m.party.remove(d)
                    if d in m.enemy:
                        m.enemy.remove(d)
            rounds += 1
    except Exception as e:
        return RunResult(scenario.name, run_idx, "error", rounds,
                         error=f"Loop: {e}\n{traceback.format_exc()}", violations=violations)

    violations.extend(_find_integrity_violations(m, m.party, m.enemy, rounds))
    if rounds >= _MAX_ROUNDS:
        outcome = "stall"
    elif not m.enemy:
        outcome = "party_win"
    elif not m.party:
        outcome = "monster_win"
    else:
        outcome = "stall"
    return RunResult(scenario.name, run_idx, outcome, rounds, violations=violations)


def _all_results():
    return [run_encounter(sc, i, rng_seed=i * 1000 + hash(sc.name) % 10000)
            for sc in SCENARIOS for i in range(sc.runs)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_all_scenarios_complete_without_crash():
    errors = [f"[{r.scenario}/{r.run_idx}] {r.error[:200]}"
              for r in _all_results() if r.outcome == "error"]
    assert not errors, "Crashes:\n" + "\n".join(errors[:20])
    print(f"PASS test_all_scenarios_complete_without_crash  ({sum(s.runs for s in SCENARIOS)} runs, 0 crashes)")


def test_no_actor_on_wall_stress():
    viols = [f"[{r.scenario}/{r.run_idx}] {v}"
             for r in _all_results() for v in r.violations if "wall" in v.lower()]
    assert not viols, "Wall violations:\n" + "\n".join(viols[:20])
    print("PASS test_no_actor_on_wall_stress")


def test_no_actor_vanishes_from_map():
    viols = [f"[{r.scenario}/{r.run_idx}] {v}"
             for r in _all_results() for v in r.violations if "vanished" in v]
    assert not viols, "Vanished actors:\n" + "\n".join(viols[:20])
    print("PASS test_no_actor_vanishes_from_map")


def test_no_duplicate_hex_occupation():
    viols = [f"[{r.scenario}/{r.run_idx}] {v}"
             for r in _all_results() for v in r.violations if "Multiple" in v]
    assert not viols, "Duplicate hex:\n" + "\n".join(viols[:20])
    print("PASS test_no_duplicate_hex_occupation")


def test_combat_always_resolves():
    stalls = [f"[{r.scenario}/{r.run_idx}] {r.rounds}r: {r.error}"
              for r in _all_results() if r.outcome == "stall"]
    assert not stalls, "Stalled:\n" + "\n".join(stalls[:10])
    print("PASS test_combat_always_resolves")


def test_minimum_party_win_rate():
    results = _all_results()
    wins = sum(1 for r in results if r.outcome == "party_win")
    losses = sum(1 for r in results if r.outcome == "monster_win")
    total = wins + losses
    assert total > 0, "No encounters resolved"
    win_rate = wins / total
    assert win_rate >= 0.10, f"Party win rate {win_rate:.1%} < 10%"
    print(f"PASS test_minimum_party_win_rate  (party wins {wins}/{total} = {win_rate:.0%})")


def test_100_random_encounters():
    """100 randomly-composed encounters must complete without crash, stall, or wall violations."""
    _PARTY_POOL = ["Galleus","Aldric","Adrel","Cobo","VV"]
    _MON_POOL   = ["Goblin","Orc","Troll","Hobgoblin","Gnoll",
                   "Archmage","Lich","Druid","Mage","Hill Giant"]
    rng = random.Random(42)
    issues = []
    for trial in range(100):
        psize = rng.randint(1, min(4, len(_PARTY_POOL)))
        msize = rng.randint(1, 6)
        sc = Scenario(
            f"rand_{trial}",
            rng.sample(_PARTY_POOL, psize),
            [rng.choice(_MON_POOL) for _ in range(msize)],
            num_hexes=rng.choice([10, 15, 20]),
            wall_layout=rng.choice(["none","none","none","barrier"]),
            runs=1,
        )
        r = run_encounter(sc, 0, rng_seed=trial)
        if r.outcome == "error":
            issues.append(f"Trial {trial} crash: {r.error[:150]}")
        if r.outcome == "stall":
            issues.append(f"Trial {trial} stall: {r.error}")
        issues.extend([f"Trial {trial} wall: {v}" for v in r.violations if "wall" in v.lower()])
    assert not issues, "Issues:\n" + "\n".join(issues[:20])
    print("PASS test_100_random_encounters  (100 trials, 0 issues)")


def _print_statistics(results):
    print("\n" + "=" * 68)
    print("  STRESS TEST OUTCOME SUMMARY")
    print("=" * 68)
    by_scenario = defaultdict(list)
    for r in results:
        by_scenario[r.scenario].append(r)
    for name, runs in sorted(by_scenario.items()):
        wins   = sum(1 for r in runs if r.outcome == "party_win")
        losses = sum(1 for r in runs if r.outcome == "monster_win")
        stalls = sum(1 for r in runs if r.outcome == "stall")
        errors = sum(1 for r in runs if r.outcome == "error")
        avg_r  = sum(r.rounds for r in runs) / len(runs)
        print(f"  {name:33s}  pw={wins:2d}  mw={losses:2d}  stall={stalls}  err={errors}  avg_rounds={avg_r:.1f}")
    print("=" * 68 + "\n")


if __name__ == "__main__":
    tests = [
        test_all_scenarios_complete_without_crash,
        test_no_actor_on_wall_stress,
        test_no_actor_vanishes_from_map,
        test_no_duplicate_hex_occupation,
        test_combat_always_resolves,
        test_minimum_party_win_rate,
        test_100_random_encounters,
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
            print(f"ERROR {t.__name__}: {err}")
            traceback.print_exc()
            failed += 1

    _print_statistics(_all_results())
    total_runs = sum(s.runs for s in SCENARIOS) + 100
    print("=" * 68)
    print(f"  Results: {passed} passed, {failed} failed  ({total_runs} encounter runs)")
    print("=" * 68)
    sys.exit(0 if failed == 0 else 1)
