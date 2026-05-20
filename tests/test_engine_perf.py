"""
Performance profiling test for the DMSim combat engine on large (40-hex) maps.

Run with:
    python tests/test_engine_perf.py

Outputs a cProfile report sorted by cumulative time, followed by a per-function
timing summary that shows which functions are the actual bottlenecks.
"""
import cProfile
import pstats
import io
import sys
import pathlib
import time

_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_root))

from model.monster import createMonsterList
from model.player import createPartyList
from model.map import Map
from engine.combat import takeTurn

_PATH = str(_root / "actors" / "savedObjs") + "\\"

# Use real saved actors — pick ones that are reliably in the JSON files
_MONSTERS = ["Goblin", "Goblin", "Goblin", "Goblin", "Goblin", "Goblin"]
_PARTY    = ["Galleus", "Galleus", "Galleus", "Galleus"]


# ---------------------------------------------------------------------------
# Build a map and run one AI turn, profiling it
# ---------------------------------------------------------------------------

def run_turn_profiled(num_hexes: int, party_names: list, enemy_names: list):
    party   = createPartyList(party_names,   path=_PATH)
    enemies = createMonsterList(enemy_names, path=_PATH)

    m = Map(num_hexes, party, enemies, graphicsViewer=None)

    # Reset health/slots for a clean turn
    for a in party + enemies:
        a.health = a.maxHealth
        a.defineSpellSlots()

    actor = enemies[0]

    pr = cProfile.Profile()
    pr.enable()
    t0 = time.perf_counter()
    takeTurn(actor, m, interactive=False)
    elapsed = time.perf_counter() - t0
    pr.disable()
    return pr, elapsed


def report(pr: cProfile.Profile, elapsed: float, label: str):
    print(f"\n{'='*70}")
    print(f"  {label}  —  wall time: {elapsed*1000:.1f} ms")
    print(f"{'='*70}")
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(25)
    print(s.getvalue())


# ---------------------------------------------------------------------------
# Scaling test: compare small vs large map
# ---------------------------------------------------------------------------

def scaling_test():
    configs = [
        (10, _PARTY[:2], _MONSTERS[:2], "10 hexes, 2v2"),
        (20, _PARTY[:2], _MONSTERS[:3], "20 hexes, 2v3"),
        (40, _PARTY[:4], _MONSTERS[:4], "40 hexes, 4v4"),
        (40, _PARTY[:4], _MONSTERS[:6], "40 hexes, 4v6"),
    ]
    results = []
    for num_hexes, party_names, enemy_names, label in configs:
        try:
            pr, elapsed = run_turn_profiled(num_hexes, party_names, enemy_names)
            results.append((label, elapsed))
            report(pr, elapsed, label)
        except Exception as e:
            print(f"\n[ERROR] {label}: {e}")
            import traceback; traceback.print_exc()

    print(f"\n{'='*70}")
    print("  SCALING SUMMARY")
    print(f"{'='*70}")
    baseline = results[0][1] if results else 1
    for label, elapsed in results:
        bar = "█" * min(int(elapsed / baseline * 10), 60)
        print(f"  {label:<35}  {elapsed*1000:8.1f} ms  {bar}")


if __name__ == "__main__":
    scaling_test()
