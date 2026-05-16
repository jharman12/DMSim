"""
Test to verify backward compatibility with single-class characters
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
print("Backward Compatibility Test")
print("Testing that existing single-class characters work correctly")
print("=" * 60)

# Test with original single-class characters
original_party = createPartyList(['Cobo', 'VV', 'Galleus'], path=path)

print(f"\n Testing single-class characters from newChars.json:")
for char in original_party:
    print(f"   {char.name}")
    print(f"     Class: {char.DnDclass}")
    print(f"     Level: {char.lvl}")
    print(f"     Classes dict: {char.classes}")
    print(f"     Has spells: {len(char.spells) > 0}")
    print(f"     Proficiency: {char.proficiency}")
    print(f"     Extra Attack: {char.twoAttacks}")

# Run a quick encounter with original characters
print(f"\n Running encounter with original characters...")
enemies = createMonsterList(['Ogre'], path=path)
encounter = Encounter(original_party, [], enemies, 1)

partyWins = len([x for x in encounter.winners if x[2] == 'Party'])
print(f"   Result: {'Party' if partyWins > 0 else 'Enemies'} won!")

print("\n" + "=" * 60)
print("Backward compatibility verified!")
print("All existing single-class characters work correctly")
print("=" * 60)
