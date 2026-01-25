"""
Test script to verify the wall system functionality.
Run this to ensure walls are working correctly.
"""

import sys
import pathlib

# Setup paths
dmSimPath = str(pathlib.Path(__file__).parent.resolve())
sys.path.insert(1, dmSimPath + '\\model')
sys.path.insert(1, dmSimPath + '\\model\\Simulation')

from map import Map
from player import Player, WeaponNew
from monster import Monster

print("=" * 60)
print("WALL SYSTEM TEST")
print("=" * 60)

# Create some test actors
print("\n1. Creating test actors...")

# Create a simple weapon for the player (string format for Player)
test_weapon = WeaponNew(
    name="Longsword",
    attackType="Melee",
    range=5,
    attackMod=5,
    diceType="d8",  # String for Player weapons
    diceCount=1,     # Int for Player weapons
    dmgMod=3
)

# Create player with all required parameters
player1 = Player(
    name="TestHero",
    lvl=5,
    ac=16,
    health=40,
    modDict={
        'Strength': 14,
        'Dexterity': 12,
        'Constitution': 14,
        'Intelligence': 10,
        'Wisdom': 10,
        'Charisma': 10
    },
    turnFactors={'Melee': 1.0, 'Ranged': 1.0, 'Ranged Spell': 1.0, 'Spell CC': 1.0},
    weaponList=[test_weapon],
    type="Fighter",
    Image=False
)

# Create a simple monster weapon
monster_weapon = WeaponNew(
    name="Claws",
    attackType="Melee",
    range=5,
    attackMod=4,
    diceType=[6],  # List of dice types
    diceCount=[1],  # List of dice counts
    dmgMod=2
)

# Create monster with all required parameters
enemy1 = Monster(
    name="TestMonster",
    ac=12,
    health=30,
    speed=30,
    modDict={
        'Strength': 12,
        'Dexterity': 10,
        'Constitution': 12,
        'Intelligence': 8,
        'Wisdom': 8,
        'Charisma': 8
    },
    weaponList=[monster_weapon],
    size=25,
    spells={},
    spellMod=0,
    multiAttack={'Claws': 1},  # Dictionary mapping weapon name to attack count
    Image=None
)

partyList = [player1]
enemyList = [enemy1]
print("✓ Actors created")

# Create map without graphics viewer (for testing)
print("\n2. Creating map...")
testMap = Map(numHex=5, partyList=partyList, enemyList=enemyList, graphicsViewer=None)
print("✓ Map created")
print(f"Available hex coordinates: {list(testMap.arrayCenters.keys())[:10]}...")  # Show first 10

# Test 1: Add walls (using valid coordinates from the hex grid)
print("\n3. Testing wall addition...")
# Get some valid empty coordinates from the map
valid_coords = [coord for coord in testMap.arrayCenters.keys() if testMap.arrayCenters[coord] == ''][:3]
testMap.addWall(valid_coords[0], hp=20, name="Test Wall 1")
testMap.addWall(valid_coords[1], hp=30, name="Test Wall 2")  
testMap.addWall(valid_coords[2], hp=15, name="Weak Wall")
assert testMap.isWall(valid_coords[0]), "Wall 1 not added!"
assert testMap.isWall(valid_coords[1]), "Wall 2 not added!"
assert testMap.isWall(valid_coords[2]), "Wall 3 not added!"
print("✓ Walls added successfully")

# Test 2: Check wall info
print("\n4. Testing wall info retrieval...")
wall_info = testMap.getWallInfo(valid_coords[0])
assert wall_info is not None, "Wall info not found!"
assert wall_info.health == 20, f"Expected hp=20, got {wall_info.health}"
assert wall_info.maxHealth == 20, f"Expected maxHp=20, got {wall_info.maxHealth}"
assert wall_info.name == "Test Wall 1", f"Expected name='Test Wall 1', got {wall_info.name}"
print(f"✓ Wall info correct: {wall_info}")

# Test 3: Check isWall
print("\n5. Testing isWall() method...")
assert testMap.isWall(valid_coords[0]) == True, "isWall failed to detect wall!"
# Find a coordinate that's definitely not a wall
empty_coord = [coord for coord in testMap.arrayCenters.keys() if testMap.arrayCenters[coord] == ''][0]
assert testMap.isWall(empty_coord) == False, "isWall detected wall where none exists!"
print("✓ isWall() working correctly")

# Test 4: Damage wall
print("\n6. Testing wall damage...")
destroyed = testMap.damageWall(valid_coords[2], 10)
assert destroyed == False, "Wall destroyed prematurely!"
wall_info = testMap.getWallInfo(valid_coords[2])
assert wall_info.health == 5, f"Expected hp=5 after damage, got {wall_info.health}"
print(f"✓ Wall damaged correctly (HP: {wall_info.health}/{wall_info.maxHealth})")

# Test 5: Destroy wall
print("\n7. Testing wall destruction...")
destroyed = testMap.damageWall(valid_coords[2], 10)
assert destroyed == True, "Wall should have been destroyed!"
assert not testMap.isWall(valid_coords[2]), "Wall still exists after destruction!"
assert testMap.arrayCenters[valid_coords[2]] == '', "Hex not freed after wall destruction!"
print("✓ Wall destroyed and hex freed")

# Test 6: Remove wall manually
print("\n8. Testing manual wall removal...")
testMap.removeWall(valid_coords[1])
assert not testMap.isWall(valid_coords[1]), "Wall not removed!"
assert testMap.arrayCenters[valid_coords[1]] == '', "Hex not freed after removal!"
print("✓ Wall removed manually")

# Test 7: Create a wall barrier and test pathfinding
print("\n9. Testing pathfinding around walls...")
# Add a vertical wall barrier
for y in range(2, 10, 2):
    testMap.addWall((8, y), hp=20, name="Barrier")

# Test that movement functions exclude walls
from modelMethods import calcMoveHexes

if player1 in [testMap.arrayCenters[coord] for coord in testMap.arrayCenters if testMap.arrayCenters[coord] != '']:
    moveHexes = calcMoveHexes(player1, testMap)
    # Check that no wall hexes are in the movement list
    for hexIndex in moveHexes:
        coord = list(testMap.arrayCenters)[hexIndex]
        assert not testMap.isWall(coord), f"Movement includes wall hex at {coord}!"
    # Count walls in the map
    wall_count = sum(1 for coord in testMap.arrayCenters if testMap.isWall(coord))
    print(f"✓ Movement calculation excludes {wall_count} walls")
else:
    print("⚠ Player not on map, skipping movement test")

# Test 8: Print map with walls
print("\n10. Displaying map with walls (walls shown as #)...")
print("-" * 40)
testMap.printCurrMap()
print("-" * 40)
print("✓ Map displayed")

# Summary
print("\n" + "=" * 60)
print("ALL TESTS PASSED! ✓")
print("=" * 60)
print(f"\nWall Summary:")
# Collect all walls from the map
walls = [(coord, obj) for coord, obj in testMap.arrayCenters.items() if testMap.isWall(coord)]
print(f"  Total walls: {len(walls)}")
for coord, wall in walls:
    print(f"  {coord}: {wall.name} - {wall.health}/{wall.maxHealth} HP")

print("\n" + "=" * 60)
print("Wall system is working correctly!")
print("See wall_system_examples.py for usage examples.")
print("See WALL_SYSTEM_README.md for full documentation.")
print("=" * 60)
