"""
Test multiclass character in combat simulation
"""
import sys
from pathlib import Path

dmSimPath = Path(__file__).parent
sys.path.insert(0, str(dmSimPath))

from model.player import createPartyList
from model.monster import createMonsterList
from model.Simulation.encounterSim import Encounter

# Test paths
path = str(dmSimPath / "actors" / "savedObjs") + "\\"

print("=" * 60)
print("Testing Multiclass in Combat Simulation")
print("=" * 60)

# Create party with multiclass character and single-class character
party = createPartyList(['TestMulticlass', 'Cobo'], path=path)
monsters = createMonsterList(['Ogre'], path=path)

print(f"\n Party:")
for char in party:
    print(f"   - {char.name}: {char.classes}, Total Lvl {char.lvl}, HP {char.health}")

print(f"\n Monsters:")
for monster in monsters:
    print(f"   - {monster.name}: HP {monster.health}")

print("\n Starting encounter...")
encounter = Encounter(party, [], monsters, 1)

# Get results from encounter
partyWins = len([x for x in encounter.winners if x[2] == 'Party'])
enemyWins = len([x for x in encounter.winners if x[2] == 'Enemy'])
if encounter.winners:
    avgTurns = sum([x[1] for x in encounter.winners]) / len(encounter.winners)
else:
    avgTurns = 0

print(f"\n Results:")
print(f"   Winner: {'Party' if partyWins > 0 else 'Monsters'}")
print(f"   Party Wins: {partyWins}")
print(f"   Enemy Wins: {enemyWins}")
print(f"   Avg Turns: {avgTurns}")

print("\n Party Status:")
for char in party:
    print(f"   - {char.name}: {'Alive' if char.alive else 'Dead'}, HP {char.health}/{char.maxHealth}")

print("\n Monster Status:")
for monster in monsters:
    print(f"   - {monster.name}: {'Alive' if monster.alive else 'Dead'}, HP {monster.health}")

print("\n" + "=" * 60)
print("Multiclass combat test complete!")
print("=" * 60)
